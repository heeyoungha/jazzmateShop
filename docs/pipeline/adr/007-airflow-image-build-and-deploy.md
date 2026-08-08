# ADR-007: Airflow 이미지 빌드 및 운영 배포 전략

## Context

Airflow standalone을 운영서버(EC2)에 배포하는 과정에서, 로컬과 운영이 동일 compose를 공유하며 여러 문제가 발생했다(권한 에러, 빈 마운트가 이미지의 DAG를 가림 등, 상세: [트러블슈팅 문서](../../troubleshooting/airflow-prod-deploy-permissions-and-db.md)).

핵심 질문은 두 가지였다.

1. 로컬은 코드를 즉시 반영해야(개발 편의) 하고, 운영은 코드가 이미지에 고정돼야(배포 일관성) 한다. 하나의 이미지로 둘 다 만족시킬 수 있는가?
2. 운영 메타DB를 어떻게 둘 것인가?

## Decision

**하나의 이미지(원소스)를 빌드하고, compose 파일로 환경 차이를 표현한다.**

- 코드·설정(`dags`, `pipeline_services`, `config`)은 `Dockerfile.airflow`에서 이미지에 COPY한다.
- 환경 차이는 **이미지가 아니라 compose의 마운트 유무**로 표현한다.
  - **로컬**(`docker-compose.airflow.standalone.yaml`): 코드 마운트 O → 마운트가 이미지를 덮어 로컬 코드가 즉시 반영.
  - **운영**(`deploy/docker-compose.airflow.prod.yaml`): 코드 마운트 X → 이미지에 구운 코드·설정 사용. 런타임(`logs`, `data`)과 메타DB(named volume)만 마운트.

```text
Dockerfile.airflow (단일)
   │ docker build (standalone.yaml의 build:)
   ▼
jazzmateshop-airflow-standalone:latest   ← 원소스
   ├── 로컬: standalone.yaml (마운트 O) → 로컬 코드로 덮어 개발
   └── 운영: deploy/prod.yaml (마운트 X) → 이미지 코드 사용
```

빌드는 `standalone.yaml`이 담당한다(`image:` + `build:` 동시 지정으로 이미지 이름 고정). 운영 배포는 `deploy.sh`가 build → save → scp → load → 재기동을 자동화한다.

## Alternatives Considered

| 방식 | 장점 | 단점 |
|---|---|---|
| Dockerfile을 dev/prod로 분리 | 이미지가 환경별로 명확 | 이미지 2개 → 관리·버전추적 2배, dev/prod parity 깨짐(로컬 테스트 이미지 ≠ 운영 이미지) |
| 코드를 운영서버 호스트에 두고 마운트 | 재빌드 없이 파일만 교체 | 서버에 소스 흩어짐, 이미지-파일 버전 불일치 위험(빈 마운트가 이미지를 가리는 사고) |
| **단일 이미지 + compose로 환경 표현** (채택) | 로컬에서 테스트한 이미지가 그대로 운영에 감, 관리 단순 | 코드 수정 시 재빌드 필요 |

## Rationale

- **dev/prod parity**: "로컬에서 테스트한 바로 그 이미지가 운영에 간다"를 보장한다(12-Factor App). Dockerfile을 나누면 dev에선 통과하고 prod에서 터지는 상황이 생긴다.
- **마운트는 이미지를 덮는다**: 이 성질 덕분에 config를 이미지에 구워도, 로컬에선 마운트가 덮어 로컬 파일이 우선한다. 이미지 하나로 두 환경을 모두 지원할 수 있는 근거.
- **환경 차이는 설정 주입으로**: 이미지가 아니라 마운트/환경변수로 환경을 구분하는 것이 원칙이다.

## Consequences

- 코드·설정 수정 시 이미지 재빌드·재배포가 필요하다(`deploy.sh`).
- `config`를 이미지에 굽되, 원본 권한(`-rw-------`)이 컨테이너에서 쓰기 불가하므로 Dockerfile에서 `chmod -R g+rwX`로 그룹 쓰기를 열어야 한다.
- 운영 compose는 코드 마운트가 없으므로, 서버의 빈 소스 폴더가 이미지를 가리는 사고가 원천 차단된다.
- 배포는 레지스트리 없이 `docker save | gzip` → `scp` → `docker load` 방식(약 800MB). 로컬·서버 아키텍처(`uname -m`)가 일치해야 한다.

## 메타DB 결정 (현재)

운영은 **standalone(SQLite 메타DB)** 을 유지한다. 운영 EC2 리소스가 작아 멀티 컨테이너(PostgreSQL 기반 local/celery, 4GB+ 필요)를 띄우기 부담스럽기 때문이다.

- 평상시 배포는 `up -d`로 메타DB(named volume)를 유지 → 실행 이력 보존.
- 크롤링 진행 상태·수집 데이터는 Supabase(외부 PostgreSQL)에 있어, 메타DB를 잃어도 파이프라인 데이터는 안전하다([ADR-004](004-db-schema-and-state-model.md)).

## Future Migration

SQLite는 크래시·동시접근에 취약해(공식적으로 개발/체험용), 컨테이너 크래시 시 메타DB가 손상돼 기동 불능이 될 수 있다(실제 발생, [트러블슈팅 증상 5](../../troubleshooting/airflow-prod-deploy-permissions-and-db.md#증상-5-재기동-시-db-초기화-단계에서-멈춤)). 근본 해결은 메타DB를 PostgreSQL로 옮기는 것.

**가장 실용적인 방향** (컨테이너를 늘리지 않고 안정성 확보): 크롤링 데이터가 이미 Supabase에 있으므로, Airflow 메타DB도 Supabase를 쓰도록 지정한다.

```yaml
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://<user>:<pw>@<supabase-host>/<db>
```

검토 필요 사항: Supabase 커넥션 풀, airflow 전용 스키마 분리, 마이그레이션 절차.

**결정 기준**:
- 리소스 작음 + 이력 "있으면 좋음" → 현재 standalone 유지(권한 문제 해결로 크래시 없어 충분)
- 이력 "반드시 유지" + 크래시 견고성 필요 → 메타DB를 Supabase로 전환
