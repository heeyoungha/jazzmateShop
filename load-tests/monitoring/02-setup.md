# 2. 항목별 설정 방법

## 설정 목표

부하 테스트 중 아래 지표를 볼 수 있게 만든다.

```text
Spring Boot 내부 지표
-> Actuator + Micrometer + Prometheus endpoint

시계열 수집
-> Prometheus

시각화
-> Grafana

DB 쿼리 근거
-> PostgreSQL slow query log
```

## 1. Spring Boot Actuator와 Prometheus endpoint

### 1.1 Actuator dependency

현재 `backendJava/build.gradle`에는 Actuator가 있다.

```gradle
implementation 'org.springframework.boot:spring-boot-starter-actuator'
```

Actuator는 `/actuator/health`, `/actuator/metrics` 같은 endpoint를 제공한다.

### 1.2 Prometheus registry dependency

Grafana + Prometheus로 Spring 지표를 보려면 Prometheus 형식 endpoint가 필요하다.

`backendJava/build.gradle`에 추가한다.

```gradle
implementation 'io.micrometer:micrometer-registry-prometheus'
```

이 dependency가 있어야 `/actuator/prometheus` endpoint를 사용할 수 있다.

정리:

```text
/actuator/metrics 만 curl로 볼 것
-> spring-boot-starter-actuator

Prometheus가 scrape할 /actuator/prometheus가 필요
-> micrometer-registry-prometheus 추가
```

### 1.3 Actuator endpoint 노출 설정

Spring Boot는 보안상 모든 Actuator endpoint를 기본 노출하지 않는다.

부하 테스트 compose에서는 `java-backend.environment`에 둔다.

```yaml
MANAGEMENT_ENDPOINTS_WEB_EXPOSURE_INCLUDE: health,metrics,prometheus
MANAGEMENT_ENDPOINT_HEALTH_SHOW_DETAILS: always
```

의미:

| 설정 | 의미 |
|---|---|
| `MANAGEMENT_ENDPOINTS_WEB_EXPOSURE_INCLUDE` | HTTP로 노출할 Actuator endpoint 목록 |
| `health` | `/actuator/health` 노출 |
| `metrics` | `/actuator/metrics` 노출 |
| `prometheus` | `/actuator/prometheus` 노출 |
| `MANAGEMENT_ENDPOINT_HEALTH_SHOW_DETAILS` | health 상세 정보 표시 |

로컬 `bootRun`에서도 항상 보고 싶다면 `backendJava/src/main/resources/application.properties`에 넣을 수 있다.

```properties
management.endpoints.web.exposure.include=health,metrics,prometheus
management.endpoint.health.show-details=always
```

현재는 부하 테스트 전용 목적이므로 compose 환경변수에 두는 것이 더 안전하다.

### 1.4 재빌드 필요

`build.gradle` dependency를 바꿨다면 기존 컨테이너에는 자동 반영되지 않는다.

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml down
docker compose -f load-tests/docker-compose.recommendation-e2e.yml up --build
```

확인:

```bash
curl http://localhost:8080/actuator
curl http://localhost:8080/actuator/prometheus
```

`/actuator` 응답에 `prometheus` 링크가 보여야 한다.

## 2. Prometheus 설정

설정 파일 위치:

```text
load-tests/observability/prometheus.yml
```

현재 설정:

```yaml
global:
  scrape_interval: 5s
  evaluation_interval: 5s

scrape_configs:
  - job_name: "java-backend"
    metrics_path: "/actuator/prometheus"
    static_configs:
      - targets: ["java-backend:8080"]
```

의미:

| 항목 | 의미 |
|---|---|
| `scrape_interval: 5s` | 5초마다 지표 수집 |
| `job_name: java-backend` | Prometheus target 이름 |
| `metrics_path: /actuator/prometheus` | Spring Boot Prometheus endpoint |
| `targets: ["java-backend:8080"]` | Docker compose 내부 서비스 주소 |

주의:

```text
Prometheus 컨테이너에서 Spring Boot를 볼 때는 localhost:8080이 아니다.
같은 Docker network 안의 service name인 java-backend:8080을 사용한다.
```

## 3. Grafana datasource 설정

설정 파일 위치:

```text
load-tests/observability/grafana/provisioning/datasources/prometheus.yml
```

현재 설정:

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
```

의미:

| 항목 | 의미 |
|---|---|
| `type: prometheus` | Grafana datasource 종류 |
| `url: http://prometheus:9090` | Docker compose 내부 Prometheus 주소 |
| `isDefault: true` | 기본 datasource로 등록 |

Grafana 접속:

```text
http://localhost:3000
```

기본 계정:

```text
ID: admin
PW: admin
```

## 4. Docker Compose 설정

설정 파일:

```text
load-tests/docker-compose.recommendation-e2e.yml
```

구성 서비스:

```text
e2e-db
ai-api
java-backend
prometheus
grafana
```

### 4.1 java-backend 설정

필수 설정:

```yaml
java-backend:
  build:
    context: ../backendJava
    dockerfile: Dockerfile
  ports:
    - "8080:8080"
  environment:
    SPRING_PROFILES_ACTIVE: production
    SPRING_DATASOURCE_URL: jdbc:postgresql://e2e-db:5432/jazzmate_e2e_loadtest
    SPRING_DATASOURCE_USERNAME: jazzmate
    SPRING_DATASOURCE_PASSWORD: jazzmate
    AI_SERVICE_URL: http://ai-api:8000
    SPRING_BASE_URL: http://java-backend:8080
    MANAGEMENT_ENDPOINTS_WEB_EXPOSURE_INCLUDE: health,metrics,prometheus
    MANAGEMENT_ENDPOINT_HEALTH_SHOW_DETAILS: always
    SERVER_TOMCAT_MBEANREGISTRY_ENABLED: "true"
```

`SERVER_TOMCAT_MBEANREGISTRY_ENABLED=true`는 Tomcat thread pool 관련 MBean/metric을 보기 위해 둔다. 이 설정이 없으면 `/actuator/prometheus`에 `tomcat_sessions_*`만 보이고 `tomcat_threads_*`가 안 보일 수 있다.

### 4.2 prometheus 설정

```yaml
prometheus:
  image: prom/prometheus:v3.0.1
  depends_on:
    java-backend:
      condition: service_started
  ports:
    - "9090:9090"
  volumes:
    - ./observability/prometheus.yml:/etc/prometheus/prometheus.yml:ro
  command:
    - "--config.file=/etc/prometheus/prometheus.yml"
    - "--storage.tsdb.retention.time=2h"
```

### 4.3 grafana 설정

```yaml
grafana:
  image: grafana/grafana:11.3.1
  depends_on:
    prometheus:
      condition: service_started
  ports:
    - "3000:3000"
  environment:
    GF_SECURITY_ADMIN_USER: admin
    GF_SECURITY_ADMIN_PASSWORD: admin
    GF_USERS_ALLOW_SIGN_UP: "false"
  volumes:
    - ./observability/grafana/provisioning:/etc/grafana/provisioning:ro
```

## 5. PostgreSQL slow query log 설정

DB 쿼리 단위 근거를 남기기 위해 `e2e-db`에 slow query log를 켠다.

현재 `load-tests/docker-compose.recommendation-e2e.yml`의 `e2e-db`에는 아래 설정을 둔다.

```yaml
e2e-db:
  image: postgres:16-alpine
  command:
    - "postgres"
    - "-c"
    - "log_min_duration_statement=300"
    - "-c"
    - "log_lock_waits=on"
    - "-c"
    - "deadlock_timeout=200ms"
```

설정 의미:

| 설정 | 의미 |
|---|---|
| `log_min_duration_statement=300` | 300ms 이상 걸린 SQL 로그 |
| `log_lock_waits=on` | lock wait 로그 |
| `deadlock_timeout=200ms` | 200ms 이상 lock 대기 시 로그 판단 |

확인:

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml logs -f e2e-db
```

주의:

```text
slow query log는 Grafana 대체제가 아니다.
Grafana는 "언제 느려졌는지"를 보여주고,
slow query log는 "어떤 SQL이 느렸는지"를 보여준다.
```

## 6. 설정 확인 순서

스택 실행:

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml up --build
```

Spring Actuator 확인:

```bash
curl http://localhost:8080/actuator
curl http://localhost:8080/actuator/prometheus
```

Prometheus target 확인:

```text
http://localhost:9090/targets
```

`java-backend` target이 `UP`이어야 한다.

Grafana 확인:

```text
http://localhost:3000
```

Grafana의 Prometheus datasource는 provisioning으로 자동 등록된다.

## 7. 세팅 완료 확인 명령어

아래 명령이 모두 기대 결과를 만족하면 Grafana/Prometheus 기반 모니터링 준비가 끝난 것이다.

### 7.1 컨테이너 상태

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml ps
```

기대 결과:

```text
java-backend Up
ai-api Up
e2e-db Up (healthy)
prometheus Up
grafana Up
```

### 7.2 Spring Actuator endpoint

```bash
curl -s http://localhost:8080/actuator
```

기대 결과:

```text
health
metrics
prometheus
```

위 링크들이 응답에 포함되어야 한다.

### 7.3 Prometheus endpoint

```bash
curl -s http://localhost:8080/actuator/prometheus | head
```

기대 결과:

```text
# HELP ...
# TYPE ...
```

Prometheus 형식 metric이 출력되어야 한다.

### 7.4 Tomcat metric

```bash
curl -s http://localhost:8080/actuator/prometheus | grep tomcat_threads
```

기대 결과:

```text
tomcat_threads_busy_threads{name="http-nio-8080"} ...
tomcat_threads_config_max_threads{name="http-nio-8080"} ...
tomcat_threads_current_threads{name="http-nio-8080"} ...
```

`tomcat_sessions_*`만 나오고 `tomcat_threads_*`가 안 나오면 `SERVER_TOMCAT_MBEANREGISTRY_ENABLED=true`가 반영되지 않은 것이다.

### 7.5 Hikari metric

```bash
curl -s http://localhost:8080/actuator/prometheus | grep hikaricp_connections
```

기대 결과:

```text
hikaricp_connections_active ...
hikaricp_connections_idle ...
hikaricp_connections_pending ...
```

### 7.6 JVM thread / CPU metric

```bash
curl -s http://localhost:8080/actuator/prometheus | grep jvm_threads_live_threads
curl -s http://localhost:8080/actuator/prometheus | grep process_cpu_usage
```

기대 결과:

```text
jvm_threads_live_threads ...
process_cpu_usage ...
```

### 7.7 Prometheus target

브라우저:

```text
http://localhost:9090/targets
```

또는 명령어:

```bash
curl -s http://localhost:9090/api/v1/targets | grep java-backend
```

기대 결과:

```text
java-backend
health: up
```

브라우저 화면에서는 `java-backend` target이 `UP`이어야 한다.

### 7.8 Prometheus query API

```bash
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=tomcat_threads_busy_threads'
```

기대 결과:

```text
"status":"success"
"resultType":"vector"
```

`result` 배열에 값이 있어야 한다.

### 7.9 Grafana datasource

브라우저:

```text
http://localhost:3000
```

로그인:

```text
admin / admin
```

Grafana에서 확인:

```text
Connections -> Data sources -> Prometheus
```

또는 Explore에서 아래 PromQL 실행:

```promql
tomcat_threads_busy_threads
```

값이 나오면 Grafana datasource 설정이 정상이다.

### 7.10 PostgreSQL slow query log 설정

DB에 설정이 반영됐는지 확인한다.

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml exec -T e2e-db \
psql -U jazzmate -d jazzmate_e2e_loadtest \
-c "show log_min_duration_statement; show log_lock_waits; show deadlock_timeout;"
```

기대 결과:

```text
log_min_duration_statement = 300ms
log_lock_waits = on
deadlock_timeout = 200ms
```

### 7.11 전체 준비 완료 기준

아래가 모두 만족되면 k6 테스트를 실행한다.

```text
1. /actuator/prometheus 응답이 나온다.
2. tomcat_threads_* metric이 나온다.
3. hikaricp_connections_* metric이 나온다.
4. Prometheus target에서 java-backend가 UP이다.
5. Grafana Explore에서 tomcat_threads_busy_threads 값이 나온다.
6. PostgreSQL slow query 설정이 show 명령으로 확인된다.
```
