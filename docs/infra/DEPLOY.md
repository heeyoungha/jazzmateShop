# JazzmateShop — 배포 및 인프라 설계 (DEPLOY.md)

> 최종 업데이트: 2026-05-23
> 기준: 앨범 기반 추천 + thin nginx SSL proxy + polling 상태 조회

---

## 1. 시스템 개요

JazzmateShop은 재즈 음악 감상문 작성 및 AI 기반 앨범 추천 플랫폼이다.

### 시스템 구성

```
Browser
  │
  ▼ :443 HTTPS / :80 redirect
[nginx — thin TLS reverse proxy]
  └── 모든 요청을 Spring Boot :8080으로 전달
        │
        ▼
[Spring Boot Java 17]
  ├── /api/**          → Java REST API 처리
  ├── /ai-api/**       → FastAPI:8000 내부 프록시 (prefix 제거 후 전달)
  └── /**              → frontend/dist/ static 서빙 (SPA fallback → index.html)
         │
         │ 내부 통신 (외부 미노출)
         ▼
[FastAPI Python :8000]
  ├── 앨범 기반 추천 계산 수행
  └── Java 콜백:
       POST /api/user-reviews/{reviewId}/recommendations
         (앨범 upsert + 추천 결과 일괄 저장 + 상태 COMPLETED 전이)
         │
[PostgreSQL]
```

**핵심 원칙:**
- **외부 노출 포트: 80/443은 nginx만** — nginx는 SSL 종료와 reverse proxy만 담당
- **Java가 모든 앱 라우팅 처리** — API, static 파일, AI 프록시 통합
- **서비스 간 통신은 내부 네트워크** — FastAPI는 외부 미노출

### 기술 스택

| 레이어 | 기술 |
|--------|------|
| Frontend | React 18, TypeScript, Vite (빌드 전용), Tailwind CSS, shadcn/ui |
| Backend | Spring Boot 3.5.7, Java 17, JPA/Hibernate |
| 상태 확인 | HTTP polling (`GET /api/user-reviews/{id}`) |
| DB | PostgreSQL (v_review_summary 뷰 포함) |
| AI 서비스 | FastAPI (Python) — 내부 서비스, 외부 미노출 |
| 벡터 검색 | Supabase pgvector (`embedding_vectors` 테이블) — 앨범 유사도 검색 |
| 빌드 | Gradle (frontend 빌드 → static 복사 포함) |

---

## 2. CORS 설정

Java가 단일 진입점이므로 CORS는 Spring `WebConfig` 한 곳에서만 관리한다.

- 허용 Origin: `http://localhost:8080`, `https://actlog.shop`
- 허용 메서드: GET, POST, PUT, DELETE, OPTIONS
- FastAPI는 외부 미노출 → CORS 설정 불필요

---

## 3. 환경 변수

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `AI_SERVICE_URL` | `http://ai-api:8000` | FastAPI 내부 서비스 URL (Java → FastAPI) |
| DB 연결 정보 | .env 파일 | PostgreSQL 접속 정보 |

---

## 4. 인프라 및 라우팅 아키텍처

> nginx는 얇은 TLS reverse proxy로 구성한다.
> 앱 라우팅, static 서빙, `/ai-api` prefix stripping 프록시는 Spring Boot가 담당한다.

### 4-1. 목표 구조 (개발/운영 공통)

```
Browser
  │
  ▼ :443 HTTPS (:80은 HTTPS redirect)
[nginx]
  └── proxy_pass http://java-backend:8080
        │
        ▼
[Spring Boot]
  ├── /api/**        → @RestController 처리
  ├── /ai-api/**     → RestTemplate/WebClient로 FastAPI:8000 내부 프록시
  │                    (prefix /ai-api 제거 후 전달)
  └── /**            → src/main/resources/static/ (Vite 빌드 결과물)
                       SPA fallback: 모든 미매칭 경로 → index.html 반환

[FastAPI :8000]       ← 외부 미노출, Docker 내부 네트워크만
  └── Java에서만 호출
```

### 4-2. 개발/운영 환경 분리

| 항목 | 개발 | 운영 |
|------|------|------|
| 진입점 | nginx:80 또는 Java:8080 직접 | nginx:443 |
| 프론트 서빙 | `npm run build` 후 static | 동일 (CI/CD 빌드 포함) |
| FastAPI | expose only (내부 통신), 필요 시 Vite dev proxy 사용 | expose only |
| nginx | 선택 사용, 모든 요청을 Java로 전달 | 필수, SSL 종료 + Java reverse proxy |
| SSL | 없음 또는 로컬 인증서 | nginx에서 SSL 종료 |
| Spring Profile | `docker` | `production` |
| Gradle 캐시 | `gradle-cache` named volume | 빌드 스테이지에서 처리 |

### 4-3. 구성 파일 명세

#### docker-compose.yml (개발)

```yaml
services:
  nginx:
    image: nginx:alpine
    ports: ['80:80']
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - java-backend

  java-backend:
    build:
      context: ./backendJava
      dockerfile: Dockerfile
    expose: ['8080']
    env_file:
      - ${BACKEND_ENV_FILE:-.env.example}
    environment:
      - SPRING_PROFILES_ACTIVE=docker
      - AI_SERVICE_URL=http://ai-api:8000

# FastAPI 구현/이미지 준비 후 ai-api 서비스를 추가한다.
```

#### docker-compose.prod.yml (운영)

```yaml
services:
  nginx:
    image: nginx:alpine
    ports: ['80:80', '443:443']
    volumes:
      - ./nginx/nginx-prod.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - java-backend

  java-backend:
    image: jazzmateshop-java-backend:latest
    build:
      context: ./backendJava
      dockerfile: Dockerfile
    expose: ['8080']
    env_file: ${BACKEND_ENV_FILE:-.env.example}
    environment:
      - SPRING_PROFILES_ACTIVE=production
      - AI_SERVICE_URL=http://ai-api:8000

# FastAPI 구현/이미지 준비 후 ai-api 서비스를 추가한다.
```

#### backendJava/Dockerfile (멀티스테이지 빌드)

```dockerfile
FROM eclipse-temurin:17-jdk-alpine AS java-builder
WORKDIR /app
COPY gradlew settings.gradle build.gradle ./
COPY gradle ./gradle
RUN ./gradlew dependencies --no-daemon
COPY src src
RUN ./gradlew bootJar --no-daemon

FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=java-builder /app/build/libs/*.jar app.jar
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

#### Spring Boot 설정 추가

```
# 1. /ai-api/** → FastAPI 내부 프록시 Controller
@RestController
@RequestMapping("/ai-api")
class AiApiProxyController {
    // /ai-api/** 요청을 http://ai-api:8000/** 으로 전달 (prefix 제거)
}

# 2. SPA fallback 설정 (WebMvcConfigurer)
# /api/**, /ai-api/** 이외의 모든 경로 → index.html 반환

# 3. static resource 경로
# src/main/resources/static/ 에 Vite 빌드 결과물 위치
```

#### vite.config.ts

```typescript
// 운영 빌드: proxy 설정 불필요 (Spring Boot가 static과 /ai-api 프록시 담당)
// 로컬 개발: Vite dev server를 계속 사용할 수 있으며, 이때만 /api, /ai-api proxy 허용
// build.outDir = 'dist'
```

### 4-4. /ai-api 프록시 라우팅 규칙

nginx는 `/ai-api/**`를 FastAPI로 직접 보내지 않는다. Java가 `/ai-api/**` 프록시를 담당한다.

| 브라우저 요청 | Java 수신 | FastAPI 전달 |
|--------------|----------|-------------|
| `GET /ai-api/admin/data-quality` | `/ai-api/admin/data-quality` | `GET /admin/data-quality` |
| `POST /ai-api/recommend/by-review` | `/ai-api/recommend/by-review` | `POST /recommend/by-review` |

### 4-5. CORS 정책

- **Java WebConfig**: `https://actlog.shop`, `http://localhost:8080` 허용
- **FastAPI**: Java에서만 호출 → CORS 불필요 (외부 미노출)
- **nginx**: CORS 헤더를 추가하지 않음. 중복 헤더 방지를 위해 Java에서만 관리

### 4-6. nginx thin reverse proxy 규칙

```
nginx 책임:
  - 80 → 443 redirect
  - SSL 인증서 처리
  - 모든 요청을 http://java-backend:8080 으로 전달

nginx 금지:
  - React static 직접 서빙
  - /api, /ai-api 별도 upstream 분기
  - /ai-api prefix 제거
  - FastAPI 직접 프록시
```

### 4-7. Docker 보안 설정

```dockerfile
# .env는 이미지에 절대 COPY 금지 — 런타임 env_file로만 주입
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser
```

Docker 이미지 레이어는 `docker history`로 열람 가능하므로
시크릿은 반드시 런타임 환경변수(`env_file`)로만 주입한다.
