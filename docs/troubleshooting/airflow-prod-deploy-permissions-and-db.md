# Airflow 운영 배포 트러블슈팅 — 권한·마운트·메타DB

로컬에서 정상 동작하던 Airflow standalone을 운영서버(EC2)에 배포했을 때 마주친 문제들과 해결 과정. 배포 구조 결정의 배경은 [ADR-007](../pipeline/adr/007-airflow-image-build-and-deploy.md) 참조.

---

## 증상 1: 접속 불가 (ERR_CONNECTION_REFUSED / 하얀 화면)

`http://actlog.shop:8081` 접속 시 하얀 화면 또는 `ERR_CONNECTION_REFUSED`.

### 원인

- **하얀 화면**: `actlog.shop/8081`(슬래시)로 접속. `/8081`은 경로로 해석돼 80포트 nginx가 응답했다.
- **refused**: URL을 고쳐도 실패 — 컨테이너는 `Up`이었으나 웹서버가 안 뜬 상태. 실제 원인은 아래 권한 문제로 Airflow가 기동에 실패하고 있었다.

### 진단 감각 (증상별 원인 위치)

| 증상 | 의미 | 원인 위치 |
|---|---|---|
| Timeout | 패킷이 버려짐 | 보안그룹/방화벽 |
| Connection refused | 포트에 리스닝 프로세스 없음 | 컨테이너/프로세스 |
| Connection reset | 기동 중 연결 끊김 | 프로세스 기동 대기 |
| 하얀 화면 | 연결됐으나 내용 없음 | 엉뚱한 서버(80포트 nginx) 응답 |

### 해결

- URL은 `http://도메인:포트` 형식(콜론, `http://` 명시).
- 보안그룹 인바운드에 8081 포트 추가, 소스는 접속 IP `/32`로 제한(전체 개방 금지).
- 근본 원인은 아래 권한 문제였다.

---

## 증상 2: 컨테이너가 기동 중 크래시 (PermissionError)

```
PermissionError: [Errno 13] Permission denied: '/opt/airflow/logs/scheduler'
```
이어서 같은 패턴이 `/opt/airflow/pipeline/config/airflow.cfg`에서도 발생.

### 원인

컨테이너는 UID `50000`(airflow), GID `0`으로 실행(`user: "${AIRFLOW_UID:-50000}:0"`)되는데, 마운트된 호스트 폴더가 `root` 소유였다.

- 마운트 대상 폴더가 없으면 Docker 데몬(root)이 자동 생성 → root 소유가 됨
- airflow(50000)가 그 폴더에 쓰지 못해 `Permission denied` → 기동 실패

```bash
# 확인
ls -la /home/ubuntu/logs
# drwxr-xr-x 2 root root ...  ← root 소유, others 쓰기 없음
```

### 해결

```bash
# 소유권을 airflow(50000:0)에게 넘김 (임시)
sudo chown -R 50000:0 /home/ubuntu/logs /home/ubuntu/data
```

근본 해결은 배포 스크립트가 자동으로 권한을 정리하도록 하는 것. `deploy.sh`에 반영:

```bash
sudo mkdir -p $REMOTE_DIR/logs $REMOTE_DIR/data && \
sudo chown -R 50000:0 $REMOTE_DIR/logs $REMOTE_DIR/data
```

`config`는 마운트가 아니라 **이미지에 굽는 방식**으로 전환(아래 증상 4 참조).

---

## 증상 3: DAG가 UI에 안 보임

접속·기동은 성공했으나 DAG 목록이 비어 있음.

### 원인 A: dags_folder 경로 불일치

```bash
docker exec <컨테이너> airflow config get-value core dags_folder
# → /opt/airflow/dags   (기본값)  ← 실제 DAG는 /opt/airflow/pipeline/dags
```
권한 문제로 Airflow가 `airflow.cfg`를 새로 쓰면서 `dags_folder`가 기본값으로 덮였다.

### 원인 B: 빈 호스트 폴더가 이미지의 DAG를 가림

운영서버의 `~/pipeline/dags`가 비어 있었는데, compose가 이 폴더를 마운트하고 있었다. **빈 바인드 마운트는 이미지 안의 파일을 가린다.** 이미지에는 DAG가 있었다:

```bash
# 마운트를 우회해 이미지 자체 확인
docker run --rm --entrypoint ls <이미지> /opt/airflow/pipeline/dags
# → 1_crawl_dag.py  2_summary_dag.py  3_embedding_vector_dag.py ...
```

### 해결

- **경로**: 환경변수로 못 박음(환경변수가 cfg보다 우선).
  ```yaml
  AIRFLOW__CORE__DAGS_FOLDER: '/opt/airflow/pipeline/dags'
  ```
- **가림**: 운영 compose(`deploy/docker-compose.airflow.prod.yaml`)에서 코드 마운트 제거 → 이미지의 DAG 사용. 상세는 [ADR-007](../pipeline/adr/007-airflow-image-build-and-deploy.md).

---

## 증상 4: config를 이미지에 넣었더니 또 PermissionError

`Dockerfile.airflow`에 config를 COPY했더니 `PermissionError: airflow.cfg`.

### 원인

- 로컬 원본 `airflow.cfg`가 `-rw-------` (소유자만 읽기·쓰기).
- `COPY --chown`은 **소유자만 바꾸고 권한 비트(rwx)는 원본 유지**한다.
- Airflow는 기동 시 cfg에 기본값을 써넣으려 하는데, 그룹(root, GID 0)에 쓰기 권한이 없어 실패.

### 해결

Dockerfile에서 명시적으로 그룹 쓰기 권한 부여:

```dockerfile
COPY --chown=airflow:root pipeline/config /opt/airflow/pipeline/config
RUN chmod -R g+rwX /opt/airflow/pipeline/config
# g+rwX: 그룹에 rw 부여. 대문자 X는 폴더에만 실행 권한(파일엔 X)
```

임시 우회(재빌드 없이 EC2 이미지만 수정)는 `docker commit` 사용:

```bash
docker run --name fix --user root --entrypoint chmod <이미지> -R g+rwX /opt/airflow/pipeline/config
docker commit --change='ENTRYPOINT ["/entrypoint-xvfb.sh"]' --change='CMD ["standalone"]' fix <이미지>
docker rm fix
```
> `commit`은 그 서버 이미지에만 반영된다. 근본 해결은 Dockerfile 수정.

---

## 증상 5: 재기동 시 DB 초기화 단계에서 멈춤

`Checking database is initialized`에서 멈추고 진행하지 않음. `down` → `up`을 해도 반복.

### 실제 로그

```
_XSERVTransmkdir: ERROR: euid != 0, directory /tmp/.X11-unix will not be created.
standalone | Starting Airflow Standalone
standalone | Checking database is initialized
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
WARNI [airflow.models.crypto] empty cryptography key - values will not be stored encrypted.
... flask_limiter ... Using the in-memory storage for tracking rate limits ...
                          ← 여기서 멈춤. 이 뒤로 아무 로그도 안 나옴
```

**진단 포인트 — 조용한 멈춤 vs 요란한 Traceback**:
- 권한 문제(증상 2~4)는 `Traceback ... PermissionError`를 뱉고 **죽었다**(프로세스 종료).
- DB 꼬임은 **에러 없이 hang**한다. `Checking database is initialized`(= alembic 마이그레이션) 단계에서 손상된 SQLite를 읽다 진행을 못 하고 멈춘다. `Airflow is ready`·`Listening at` 같은 다음 단계 로그가 **안 나오는 것**이 신호다.
- 즉 "Traceback이 있나/없나"로 권한 문제와 DB 꼬임을 구분한다.

### 원인

증상 2~4의 권한 문제로 컨테이너가 반복 크래시하는 동안, SQLite 메타DB 파일이 half-written(쓰다 만) 상태로 named volume에 남았다. `-v` 없이 `down`하면 그 손상 파일이 그대로 유지돼 다음 기동 때 마이그레이션이 멈춘다.

### 해결

named volume까지 삭제 후 재기동:

```bash
docker compose -f <compose> down -v   # -v = named volume(SQLite) 삭제
docker compose -f <compose> up -d
```

**주의**: `down -v`는 **DB 꼬임 복구 전용**이다. 매 배포마다 하면 실행 이력이 초기화된다. 크롤링 진행 상태·수집 데이터는 Supabase(외부 PostgreSQL)에 저장되므로 메타DB를 지워도 안전하지만, Airflow 실행 이력은 잃는다.

- 평상시 배포: `up -d` (메타DB 유지)
- DB 꼬임 시에만: `down -v` → `up -d`

> 근본적으로는 SQLite의 크래시 취약성이 원인. 메타DB를 PostgreSQL(Supabase)로 옮기는 것이 근본 해결 — [ADR-007](../pipeline/adr/007-airflow-image-build-and-deploy.md#future-migration) 참조.

---

## 재발 방지 체크리스트

- [ ] URL은 `http://도메인:포트` (콜론, http 명시)
- [ ] 보안그룹: 포트 열림 + 소스 IP `/32` 제한
- [ ] 마운트 호스트 폴더가 UID 50000으로 쓰기 가능한가 (`deploy.sh`가 자동 chown)
- [ ] 코드·설정은 이미지에 굽고, 운영 compose에선 코드 마운트 제거
- [ ] `dags_folder`는 환경변수로 고정
- [ ] 빌드 후 `docker run --entrypoint ls`로 이미지 내용 검증
- [ ] 로컬·서버 아키텍처 일치 (`uname -m`)
- [ ] 평상시 배포는 `up -d`(DB 유지). `down -v`는 꼬임 복구 전용
