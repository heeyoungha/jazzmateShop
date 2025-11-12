# E2E 테스트 설정 작업 내역

## 작업 일시
2025-11-24

## 작업 개요
JazzMate Shop 프로젝트에 Playwright를 활용한 E2E(End-to-End) 테스트 인프라를 구축했습니다. 실제 테스트 코드는 작성하지 않고, 테스트 작성을 위한 기반 구조와 도구들을 설정했습니다.

---

## 1. Playwright 설정 파일 최적화

### 파일: `playwright.config.ts`

**변경 내역:**
- 기본 템플릿에서 JazzMate 프로젝트에 맞춤화된 설정으로 개선
- 전체 스택(Frontend, Backend, AI Service)을 지원하도록 구성

**주요 설정 추가:**

1. **타임아웃 설정**
   - 테스트 실행 타임아웃: 30초
   - 네비게이션 타임아웃: 15초
   - 액션 타임아웃: 10초

2. **리포터 구성**
   - HTML 리포트: `playwright-report/` 폴더
   - List 형식 콘솔 출력
   - JSON 결과 파일: `e2e/test-results/results.json`

3. **Base URL 설정**
   - 기본값: `http://localhost:3000` (프론트엔드)
   - 환경변수로 오버라이드 가능: `BASE_URL`

4. **브라우저 프로젝트 확장**
   - 데스크톱: Chromium, Firefox, WebKit
   - 모바일: Mobile Chrome (Pixel 5), Mobile Safari (iPhone 12)
   - Chromium에 메모리 최적화 플래그 추가: `--disable-dev-shm-usage`

5. **테스트 아티팩트 설정**
   - 실패 시 스크린샷 자동 캡처
   - 실패 시 비디오 녹화
   - 첫 재시도 시 trace 수집

6. **Web Server 자동 시작**
   - 프론트엔드 개발 서버 자동 실행: `cd frontend && npm run dev`
   - 포트 3000에서 대기
   - CI 환경이 아닐 경우 기존 서버 재사용

**이점:**
- 테스트 실행 전 자동으로 프론트엔드 서버 시작
- 다양한 브라우저와 디바이스에서 테스트 가능
- 실패 시 디버깅에 필요한 자료 자동 수집

---

## 2. NPM Scripts 추가

### 파일: `package.json` (루트)

**추가된 스크립트:**

```json
{
  "test:e2e": "playwright test",                          // 모든 테스트 실행 (headless)
  "test:e2e:headed": "playwright test --headed",          // 브라우저 UI 보면서 실행
  "test:e2e:ui": "playwright test --ui",                  // Playwright UI 모드
  "test:e2e:debug": "playwright test --debug",            // 디버그 모드 (단계별 실행)
  "test:e2e:chromium": "playwright test --project=chromium",  // Chrome만
  "test:e2e:firefox": "playwright test --project=firefox",    // Firefox만
  "test:e2e:webkit": "playwright test --project=webkit",      // Safari만
  "test:e2e:mobile": "playwright test --project=mobile-chrome --project=mobile-safari",  // 모바일 뷰포트
  "test:e2e:report": "playwright show-report",            // HTML 리포트 열기
  "test:e2e:codegen": "playwright codegen http://localhost:3000"  // 코드 생성 도구
}
```

**이점:**
- 다양한 테스트 실행 방식 지원
- 특정 브라우저나 환경에서만 테스트 실행 가능
- `codegen`으로 UI 조작을 녹화하여 테스트 코드 자동 생성

---

## 3. 테스트 인프라 구조 생성

### 3.1 테스트 데이터 Fixture

**파일: `e2e/fixtures/test-data.ts`**

**내용:**
- `testUsers`: 테스트용 사용자 데이터 (기본 유저, 프리미엄 유저)
- `testReviews`: 다양한 리뷰 샘플 (긴 리뷰, 짧은 리뷰, 비공개 리뷰)
- `testAlbums`: 앨범 검색 테스트용 데이터 (Kind of Blue, Time Out 등)
- `testTracks`: 트랙 데이터 (So What, Take Five 등)
- `apiEndpoints`: API 엔드포인트 경로 상수

**이점:**
- 일관된 테스트 데이터 사용
- 실제 재즈 앨범/트랙 정보로 현실적인 테스트 가능
- 데이터 중앙 관리로 유지보수 용이

---

### 3.2 API 헬퍼

**파일: `e2e/utils/api-helpers.ts`**

**제공 기능:**
- `ApiHelpers` 클래스: API 요청을 위한 헬퍼 메서드
  - `createUserReview()`: 리뷰 생성
  - `searchAlbums()`: 앨범 검색
  - `getUserReviews()`: 사용자 리뷰 조회
  - `getRecommendations()`: 추천 결과 조회
  - `deleteUserReview()`: 리뷰 삭제 (테스트 후 정리용)
  - `waitForRecommendations()`: 비동기 추천 생성 완료 대기 (폴링 방식)

- 응답 검증 함수:
  - `validateUserReviewResponse()`: 리뷰 응답 구조 검증
  - `validateRecommendationResponse()`: 추천 응답 구조 검증
  - `validateAlbumSearchResponse()`: 앨범 검색 응답 검증

**이점:**
- UI 테스트 전 API로 데이터 준비 가능 (테스트 속도 향상)
- 비동기 추천 생성 과정을 안전하게 대기
- 테스트 후 데이터 정리로 테스트 격리 보장

---

### 3.3 페이지 헬퍼

**파일: `e2e/utils/page-helpers.ts`**

**제공 기능:**
- `PageHelpers` 클래스: 일반적인 페이지 조작
  - `goto()`: 경로 이동 및 네트워크 안정화 대기
  - `fillFieldByLabel()`: 라벨로 폼 필드 채우기
  - `clickButton()`: 버튼 클릭
  - `waitForElement()`: 요소 표시 대기
  - `expectTextVisible()`: 텍스트 표시 검증
  - `screenshot()`: 스크린샷 캡처
  - `waitForApiResponse()`: 특정 API 응답 대기
  - `waitForLoadingComplete()`: 로딩 스피너 사라질 때까지 대기
  - 등등...

- 유틸리티 함수:
  - `delay()`: 지연 생성
  - `generateTestId()`: 고유 테스트 ID 생성
  - `formatKoreanDate()`: 한국어 날짜 포맷

**이점:**
- 반복적인 페이지 조작 코드 재사용
- 안정적인 대기 메커니즘 제공
- 한국어 UI 테스트 지원

---

### 3.4 Page Object Model (POM)

**구조:**
```
e2e/page-objects/
├── base.page.ts          # 모든 페이지의 기본 클래스
├── home.page.ts          # 홈페이지 페이지 객체
└── write-review.page.ts  # 리뷰 작성 페이지 객체
```

#### **base.page.ts**
- 모든 페이지 객체의 부모 클래스
- 공통 기능: goto, reload, goBack, screenshot, waitForApiResponse

#### **home.page.ts**
- 홈페이지 전용 로케이터와 메서드
- 주요 기능:
  - `searchAlbum()`: 앨범 검색
  - `goToWriteReview()`: 리뷰 작성 페이지로 이동
  - `goToMyReviews()`: 내 리뷰 페이지로 이동
  - `goToRecommendations()`: 추천 페이지로 이동

#### **write-review.page.ts**
- 리뷰 작성 페이지 전용
- 주요 기능:
  - `fillReviewForm()`: 리뷰 폼 채우기
  - `submitReview()`: 리뷰 제출
  - `createReview()`: 전체 리뷰 작성 워크플로우

**이점:**
- UI 변경 시 페이지 객체만 수정하면 됨
- 테스트 코드와 UI 구조 분리
- 가독성과 유지보수성 향상

---

## 4. 환경 설정

### 파일: `e2e/.env.example`

**포함 내용:**
- `BASE_URL`: 프론트엔드 URL (기본값: http://localhost:3000)
- `API_URL`: 백엔드 API URL (기본값: http://localhost:8080)
- `AI_SERVICE_URL`: AI 서비스 URL (기본값: http://localhost:8000)
- 테스트 사용자 정보
- 타임아웃 설정
- CI/CD 플래그
- 브라우저 옵션 (HEADLESS, SLOWMO)
- 아티팩트 캡처 설정

**사용 방법:**
```bash
cp e2e/.env.example e2e/.env
# 필요 시 .env 파일 수정
```

**이점:**
- 환경별로 다른 설정 사용 가능
- 민감한 정보 Git에서 제외 (.gitignore에 e2e/.env 추가됨)

---

## 5. CI/CD 파이프라인 설정

### 파일: `.github/workflows/playwright.yml`

**업그레이드 내역:**
- 기본 템플릿에서 JazzMate 전체 스택을 지원하도록 확장

**주요 단계:**

1. **서비스 준비**
   - PostgreSQL 15 컨테이너 시작 (테스트 DB)
   - 헬스 체크 설정

2. **환경 설정**
   - Node.js 20 설치
   - Java 17 (Temurin) 설치
   - Python 3.11 설치
   - 각각 캐시 설정으로 빌드 속도 향상

3. **의존성 설치**
   - 루트 프로젝트 (Playwright 포함)
   - 프론트엔드 (React + Vite)
   - 백엔드 빌드 (Spring Boot)
   - AI 서비스 (Python 패키지)

4. **서비스 시작**
   - Backend: `./gradlew bootRun` (백그라운드)
   - AI Service: `python api_server.py` (백그라운드)
   - Frontend: Playwright가 자동으로 시작

5. **헬스 체크**
   - Backend actuator: `http://localhost:8080/actuator/health`
   - AI Service: `http://localhost:8000/health`
   - `wait-on` 패키지로 최대 2분 대기

6. **테스트 실행**
   - Playwright 테스트 실행
   - CI 환경 플래그 설정

7. **아티팩트 업로드**
   - HTML 리포트 (30일 보관)
   - 테스트 결과 JSON (30일 보관)
   - 실패/성공 여부와 관계없이 업로드

8. **정리**
   - 백그라운드 프로세스 종료

**트리거:**
- `main`, `master`, `develop` 브랜치에 push
- 해당 브랜치로의 PR

**이점:**
- 코드 변경마다 자동으로 E2E 테스트 실행
- 전체 스택 통합 테스트
- 테스트 실패 시 자동으로 리포트 확인 가능

---

## 6. .gitignore 업데이트

### 추가된 항목:
```
e2e/test-results/    # 테스트 실행 결과 및 아티팩트
e2e/screenshots/     # 실패 시 캡처된 스크린샷
e2e/.env            # 환경 변수 파일 (민감 정보 포함 가능)
```

**이점:**
- 테스트 결과물이 Git에 커밋되지 않음
- 로컬 환경 설정이 공유되지 않음

---

## 7. 문서화

### 파일: `e2e/README.md`

**내용:**
- 프로젝트 구조 설명
- 설치 및 설정 가이드
- 테스트 실행 방법 (다양한 옵션 포함)
- 테스트 작성 가이드
  - Page Object 사용법
  - Fixture 활용법
  - Helper 함수 사용법
- 아키텍처 고려사항
  - 비동기 추천 생성 처리 방법
  - API vs UI 테스트 전략
- CI/CD 통합 설명
- 트러블슈팅 가이드
- 베스트 프랙티스
- 성능 최적화 팁
- 관련 리소스 링크

**이점:**
- 새로운 개발자가 빠르게 E2E 테스트 작성 시작 가능
- 프로젝트 특성(비동기 추천 등)에 대한 가이드 제공

---

## 완료된 설정 요약

### ✅ 설정 파일
1. `playwright.config.ts` - Playwright 설정 최적화
2. `package.json` - 테스트 실행 스크립트 추가
3. `.github/workflows/playwright.yml` - CI/CD 파이프라인 구축
4. `.gitignore` - 테스트 아티팩트 제외 설정

### ✅ 테스트 인프라
1. `e2e/fixtures/test-data.ts` - 테스트 데이터 fixture
2. `e2e/utils/api-helpers.ts` - API 헬퍼 유틸리티
3. `e2e/utils/page-helpers.ts` - 페이지 헬퍼 유틸리티
4. `e2e/page-objects/base.page.ts` - 기본 Page Object
5. `e2e/page-objects/home.page.ts` - 홈페이지 Page Object
6. `e2e/page-objects/write-review.page.ts` - 리뷰 작성 페이지 Page Object

### ✅ 환경 및 문서
1. `e2e/.env.example` - 환경변수 예제 파일
2. `e2e/README.md` - 종합 문서화
3. `e2e/task-history.md` - 작업 내역 (이 파일)

---

## 다음 단계 (테스트 작성 시)

### 1. 환경 준비
```bash
# 환경변수 파일 생성
cp e2e/.env.example e2e/.env

# Playwright 브라우저 설치
npx playwright install
```

### 2. 서비스 실행
```bash
# Docker Compose로 전체 스택 실행
docker-compose up -d

# 또는 개별 서비스 실행
cd backend && ./gradlew bootRun
cd backend/ai-service && python api_server.py
cd frontend && npm run dev
```

### 3. 테스트 작성 시작
```typescript
// 예시: e2e/tests/review-submission.spec.ts
import { test, expect } from '@playwright/test';
import { WriteReviewPage } from '../page-objects/write-review.page';
import { testReviews } from '../fixtures/test-data';

test('사용자가 리뷰를 작성할 수 있다', async ({ page }) => {
  const writeReviewPage = new WriteReviewPage(page);
  await writeReviewPage.goto();
  await writeReviewPage.createReview({
    ...testReviews.validReview,
    trackName: 'So What',
    albumName: 'Kind of Blue',
    artistName: 'Miles Davis',
  });

  // 검증 로직...
});
```

### 4. 테스트 실행
```bash
# UI 모드로 실행 (추천)
npm run test:e2e:ui

# 또는 headless 모드
npm run test:e2e
```

---

## 기술 스택

- **테스트 프레임워크**: Playwright 1.56.1
- **언어**: TypeScript
- **패턴**: Page Object Model (POM)
- **CI/CD**: GitHub Actions
- **리포팅**: HTML, JSON

---

## 참고 자료

- [Playwright 공식 문서](https://playwright.dev/)
- [CLAUDE.md](../CLAUDE.md) - JazzMate 프로젝트 아키텍처 가이드
- [e2e/README.md](./README.md) - E2E 테스트 가이드

---

## 작업자 노트

이 설정은 테스트 코드 작성을 위한 완전한 기반을 제공합니다. 특히 JazzMate의 비동기 추천 생성 패턴을 고려하여 `waitForRecommendations()` 같은 헬퍼를 제공했으며, Page Object Model을 통해 UI 변경에 유연하게 대응할 수 있습니다.

실제 테스트 작성 시에는:
1. 주요 사용자 플로우부터 시작 (리뷰 작성 → 추천 확인)
2. Edge case와 에러 케이스 추가
3. API와 UI 테스트를 적절히 혼합하여 속도와 신뢰성 균형 유지

를 권장합니다.
