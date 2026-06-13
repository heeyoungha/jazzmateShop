# JazzmateShop — 배포 및 인프라 설계 (DEPLOY.md)

> 최종 업데이트: 2026-05-23
> 기준: 앨범 기반 추천 + nginx reverse proxy/static serving + polling 상태 조회

---

## 1. 시스템 개요

JazzmateShop은 재즈 음악 감상문 작성 및 AI 기반 앨범 추천 플랫폼이다.

### 시스템 구성

```
Browser
  │
  ▼ :80
[nginx]
  ├── /**              → frontend/dist static 서빙 (SPA fallback → index.html)
  └── /api/**          → Spring Boot :8080
[Spring Boot Java 17]
  └── 내부 통신
[FastAPI Python :8000]
  ├── 앨범 기반 추천 계산 수행
  └── Java 콜백:
       POST /api/user-reviews/{reviewId}/recommendations
         (앨범 upsert + 추천 결과 일괄 저장 + 상태 COMPLETED 전이)
         │
[PostgreSQL]
```

**핵심 원칙:**
- **외부 노출 포트는 nginx만** — 로컬 리허설은 `80`, 운영 TLS는 nginx 설정/포트로 확장
- **nginx가 frontend static과 `/api/**` 프록시를 담당**
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
| 빌드 | Docker multi-stage (nginx image가 frontend build 결과 포함) |

---

## 2. CORS 설정

브라우저 API 요청은 nginx를 거쳐 Spring Boot로 전달되며, CORS는 Spring `WebConfig` 한 곳에서만 관리한다.

- 허용 Origin: 로컬 Vite 개발 서버, 운영 도메인
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

> Docker Compose는 운영 전 리허설용 전체 스택으로 구성한다.
> 일상 개발은 프론트 `npm run dev`, Java `./gradlew bootRun`, FastAPI 로컬 또는 개별 컨테이너 실행을 사용한다.

### 4-1. 목표 구조

```
Browser
  ▼ :80
[nginx]
  ├── /**        → React static + SPA fallback
  └── /api/**   → http://java-backend:8080

[Spring Boot]
  └── /api/**    → @RestController 처리

[FastAPI :8000]       ← 외부 미노출, Docker 내부 네트워크만
  └── Java에서만 호출
```

### 4-2. 개발/리허설 환경 분리 (ADR)

> **결정일**: 2026-06-13

#### 배경

코드 수정 시 변경 사항을 즉시 확인하려면 매번 Docker 이미지를 빌드해야 하는 병목이 있었다.
이를 해소하면서 운영 환경의 안정성(nginx SSL 종료, static 서빙)도 유지할 방법을 검토했다.

#### 검토한 대안

| 대안 | 설명 | 장점 | 단점 |
|------|------|------|------|
| **A. 현행 유지** (nginx 이미지 안에 dist 복사) | nginx Dockerfile에서 `npm run build` 후 dist를 이미지에 COPY | 개발·운영 구조 동일 | 코드 한 줄 바꿔도 `docker-compose build nginx` 필요. 피드백 루프가 느림 |
| **B. nginx volume mount** | `dist/`를 nginx 컨테이너에 bind mount | 빌드만 하면 반영 | `npm run build`는 여전히 필요. HMR 불가 |
| **C. Vite dev server + nginx 프록시** | Vite(:5173)를 nginx 뒤에 두고 HMR 연결 | HMR 가능 | nginx ↔ Vite websocket 터널링 설정이 복잡. nginx가 개발에도 필요 |
| **D. (채택) 개발: nginx 제거 + Vite proxy / 운영: nginx 유지** | 개발 시 nginx 없이 Vite dev server가 `/api` 프록시 담당. 운영은 nginx가 static 서빙 + API 프록시 | 개발: 저장 즉시 HMR 반영, 도커 재빌드 불필요. 운영: nginx의 static 서빙 성능·SSL 종료 유지 | 개발·운영 진입점이 다름 (허용 가능한 차이) |

#### 채택: 개발은 로컬 실행, Docker Compose는 운영 유사 리허설

**일상 개발**
- frontend: `npm run dev`
- Java: `./gradlew bootRun`
- FastAPI: 로컬 `uvicorn` 또는 필요 시 개별 컨테이너
- Docker 이미지 재빌드 없이 코드 변경 피드백을 빠르게 확인한다.

**운영 전 리허설**
- `docker-compose.yml`: nginx + frontend static + java-backend + ai-api 전체 스택
- nginx가 `dist/` static 파일 서빙 + `/api/*` → java-backend 프록시
- java-backend, ai-api는 외부 미노출 (`expose` only)

#### 환경별 비교

| 항목 | 일상 개발 | Docker 리허설 |
|------|------|------|
| 프론트 서빙 | Vite dev server HMR (:5173) | nginx가 image 내 `dist/` 서빙 |
| API 프록시 | Vite proxy → local Java:8080 | nginx → java-backend:8080 |
| nginx | 없음 | 필수 |
| java-backend 포트 | 로컬 노출 (:8080) | 외부 미노출 (expose only) |
| Spring Profile | 로컬 설정 | `production` |
| 코드 반영 속도 | 저장 즉시 | 이미지 재빌드 필요 |

### 4-3. 구성 파일 명세

#### docker-compose.yml (운영 유사 리허설)

```yaml
services:
  nginx:
    build:
      context: .
      dockerfile: nginx/Dockerfile
    ports:
      - "80:80"
    depends_on:
      - java-backend
      - ai-api

  java-backend:
    build:
      context: ./backendJava
      dockerfile: Dockerfile
    expose:
      - "8080"
    env_file: ${BACKEND_ENV_FILE:-.env.example}
    environment:
      SPRING_PROFILES_ACTIVE: production
      AI_SERVICE_URL: ${AI_SERVICE_URL:-http://ai-api:8000}

  ai-api:
    build:
      context: ./backendPython
      dockerfile: Dockerfile
    expose:
      - "8000"
    env_file: ${AI_ENV_FILE:-.env.example}
    environment:
      SPRING_BASE_URL: ${SPRING_BASE_URL:-http://java-backend:8080}
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

#### nginx/Dockerfile

```dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx/nginx-prod.conf /etc/nginx/nginx.conf
```

#### vite.config.ts

```typescript
// Docker 리허설/운영 빌드: nginx가 static과 /api 프록시 담당
// 로컬 개발: Vite dev server에서 /api proxy 허용
// build.outDir = 'dist'
```

### 4-4. 서비스 간 통신 규칙

FastAPI는 브라우저에서 직접 호출하지 않는다. 추천 시작과 콜백은 Docker 내부 네트워크에서만 오간다.

| 방향 | URL |
|------|-----|
| Java → FastAPI | `http://ai-api:8000/recommend/review` |
| FastAPI → Java callback | `http://java-backend:8080/api/user-reviews/{reviewId}/recommendations` |

### 4-5. CORS 정책

- **Java WebConfig**: 로컬 개발 Vite origin과 운영 origin 허용
- **FastAPI**: Java에서만 호출 → CORS 불필요 (외부 미노출)
- **nginx**: CORS 헤더를 추가하지 않음. 중복 헤더 방지를 위해 Java에서만 관리

### 4-6. nginx reverse proxy/static 규칙

```
nginx 책임:
  - React static 직접 서빙
  - SPA fallback: / → index.html
  - /api/** → http://java-backend:8080 프록시

nginx 금지:
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
