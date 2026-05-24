# Multi-Agent Orchestration Rules

> 이 파일은 Claude Code와 Codex가 공통으로 따르는 규칙입니다.
> 영역별 전용 규칙: [pipeline/AGENTS.md](pipeline/AGENTS.md) | [backendJava/AGENTS.md](backendJava/AGENTS.md)

---

## 프로젝트 개요

사용자가 감상문을 작성하면 AI가 해당 감상문과 유사한 재즈 앨범을 비동기로 추천하고, 프론트가 상태 조회 polling으로 결과를 확인하는 시스템이다.
이를 위해 AllAboutJazz 재즈 리뷰를 수집하고, GPT 요약과 임베딩을 거쳐 저장하는 Airflow 기반 데이터 파이프라인을 구축한다.
Spring Boot와 FastAPI는 수집된 데이터를 기반으로 사용자 감상문에 맞는 앨범 추천을 처리한다.

---

## 기술 스택 요약

| 역할 | 기술 |
|---|---|
| 파이프라인 | Apache Airflow 2.8 + Playwright + OpenAI Batch API |
| 관계형 DB | Supabase (PostgreSQL 16) |
| 백엔드 | Spring Boot 3 (Java) |
| 컨테이너 | Docker Compose |

상세 기술 스택: [pipeline/AGENTS.md](pipeline/AGENTS.md)

---

## 전체 아키텍처

시스템 흐름, 모듈별 역할, 문서 링크: [docs/architecture.md](docs/architecture.md)

---

## 공통 작업 제약

- `pipeline/migrations/*.sql` — 파이프라인 마이그레이션, Supabase에 직접 실행하므로 자동 수정 금지
- `backendJava/migrations/*.sql` — 백엔드 마이그레이션, Supabase에 직접 실행하므로 자동 수정 금지
- `.env` — 직접 수정 금지, 필요한 값은 사용자에게 안내만

---

## DB 스키마

상세: [ADR-004](docs/pipeline/adr/004-db-schema-and-state-model.md)
파이프라인 마이그레이션: `pipeline/migrations/*.sql`
백엔드 마이그레이션: `backendJava/migrations/*.sql`

---

## 인프라 및 배포

nginx, Docker Compose, Dockerfile, CORS, 라우팅 아키텍처: [docs/infra/DEPLOY.md](docs/infra/DEPLOY.md)

---

## 구현하지 않을 것 (Scope 외)

다음 기능은 이번 프로젝트 범위에 포함되지 않습니다.
**관련 코드를 생성하지 마세요.**

- 실시간 스트리밍 처리 (Kafka, Flink 등)
- 다른 음악 평론 사이트 크롤링 (AllAboutJazz 전용)
- 모델 파인튜닝
- 개별 사용자별 취향을 탐색하고 그에 맞춰 추천하는 개인 맞춤형 추천 서비스
