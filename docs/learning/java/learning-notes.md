# Java 학습 노트

> 이 파일은 `/explain-python` 커맨드가 자동으로 읽고 업데이트합니다.
> 새로 배운 개념은 아래에 추가됩니다.

최종 업데이트: 2026-06-19 (HTTP/1.1 강제 — RestClient + uvicorn 로컬 환경)

---

## 배운 개념 목록

### `@ExtendWith(MockitoExtension.class)` — Mockito와 JUnit5 연결
- JUnit5는 `@Mock`을 기본으로 모른다. `MockitoExtension`을 연결해야 테스트 실행 전 `@Mock` 필드를 가짜 객체로 채워준다.
- `@SpringBootTest` 없이 Spring 전체 컨텍스트를 띄우지 않으므로 훨씬 빠르다.
- ADR-BJ001 Decision 1: Service 단위 테스트는 Mockito 사용.
- 파일: `backendJava/src/test/java/shop/jazzmate/jazzmateshop/userReview/UserReviewServiceTest.java`

### `@Mock` — 가짜 객체 생성
- 실제 DB/외부 의존성 없이 "아무것도 안 하는 가짜 객체"를 만든다.
- Python의 `Fake` 객체, `monkeypatch` 패턴과 같은 원리. Java는 애노테이션으로 처리.
- 파일: `backendJava/src/test/java/shop/jazzmate/jazzmateshop/userReview/UserReviewServiceTest.java`

### `@InjectMocks` — 가짜 객체를 테스트 대상에 자동 주입
- `@Mock` 객체들을 자동으로 찾아 테스트 대상 클래스의 생성자에 주입한다.
- 수동으로 `new Service(mock1, mock2, ...)` 하지 않아도 된다.
- 파일: `backendJava/src/test/java/shop/jazzmate/jazzmateshop/userReview/UserReviewServiceTest.java`

### `given(...).willReturn(...)` — BDD 스타일 스터빙
- "이 메서드가 호출되면 이 값을 반환해라"고 미리 약속하는 것.
- `any(타입.class)`: 어떤 인스턴스를 넘겨도 매칭되는 매처(matcher).
- `when/thenReturn`(구식) 대신 `given/willReturn`(BDD)을 써서 given/when/then 흐름과 일치시킨다.
- 파일: `backendJava/src/test/java/shop/jazzmate/jazzmateshop/userReview/UserReviewServiceTest.java`

### `ArgumentCaptor` — 메서드에 전달된 인자 캡처
- `verify(mock).method(captor.capture())`: 호출 검증과 동시에 전달된 인자를 캡처.
- `captor.getValue()`: 캡처된 인자를 꺼내 필드까지 검증 가능.
- Python의 spy 패턴(`calls = []` 리스트로 인자 기록)과 동일한 역할.
- ADR-BJ001 Decision 2: "행위 기반만으로 부족 — 이벤트 내부 데이터(상태)도 검증해야 한다"에 부합.
- 파일: `backendJava/src/test/java/shop/jazzmate/jazzmateshop/userReview/UserReviewServiceTest.java`

### `verify(...)` — 호출 여부 및 횟수 검증
- `verify(mock)`: 정확히 1번 호출됐는지.
- `verify(mock, times(n))`: 정확히 n번 호출됐는지.
- `verify(mock, never())`: 한 번도 호출되지 않았는지.
- 파일: `backendJava/src/test/java/shop/jazzmate/jazzmateshop/userReview/UserReviewServiceTest.java`

### `@Nested` + `@DisplayName` — 테스트 구조화
- `@Nested`로 메서드별 테스트를 그룹화. IDE/CI에서 계층 구조로 표시.
- `@DisplayName`으로 메서드명 대신 한글 설명 표시.
- `@BeforeEach`를 `@Nested` 클래스 안에 두면 해당 그룹에만 적용되는 공통 셋업.
- Python의 `conftest.py` fixture와 동일한 역할 (setup/teardown 코드 중복 제거).
- 파일: `backendJava/src/test/java/shop/jazzmate/jazzmateshop/userReview/UserReviewServiceTest.java`

### 팩토리 메서드 패턴 (Java `static` 메서드)
- `new` 대신 `static` 메서드로 객체를 생성하는 패턴.
- Python의 `@classmethod` 팩토리와 동일한 원리. Python은 `cls`, Java는 `static`.
- **이름을 붙일 수 있다**: `UUID.fromString()`, `UUID.randomUUID()` — 어떤 UUID인지 의도 표현.
- **상태 조합을 강제할 수 있다**: `completed(albums)` / `failed(errorCode)` — 잘못된 필드 조합 방지.
- **생성자를 숨길 수 있다**: `Optional.of()` / `Optional.empty()` — `new Optional()`로는 만들 수 없음.
- 이 프로젝트 예시: `UUID.fromString(...)`, `Optional.of(...)`, `Optional.empty()`
- 파일: `backendJava/src/test/java/shop/jazzmate/jazzmateshop/userReview/UserReviewServiceTest.java`

### `@EnableSpringDataWebSupport(VIA_DTO)` — Page 직렬화 안정화
- `Page<T>`를 REST API로 반환할 때 내부 구현체(`PageImpl`)를 직접 직렬화하면 버전마다 응답 구조가 달라질 수 있다.
- `VIA_DTO` 모드는 Spring 공식 DTO를 통해 직렬화하므로 응답 구조가 안정적으로 고정된다.
- Spring Boot 3.1+에서 이 설정 없이 `Page<T>`를 반환하면 deprecation 경고가 발생한다.
- **VIA_DTO 응답 구조**: `{ content: [...], page: { number, size, totalElements, totalPages } }`
  - `last` 필드는 응답에 없으므로 클라이언트에서 `number >= totalPages - 1`로 직접 계산한다.
- Spring Boot 3.x + 페이지네이션 API가 있으면 `main` 클래스에 한 번 선언하는 것이 관례.
- 파일: `backendJava/src/main/java/shop/jazzmate/jazzmateshop/JazzmateshopApplication.java`
- 프론트 연동: `frontend/src/pages/MyReviewsPage.tsx` — `PageResponse.page.number/totalPages`로 파싱

### `RestClient` + HTTP 버전 강제 — `JdkClientHttpRequestFactory`
- Spring `RestClient`는 기본적으로 HTTP/2 업그레이드를 시도한다.
- uvicorn(FastAPI 서버)은 단독 실행 시 HTTP/1.1만 지원한다. HTTP/2 upgrade 요청이 오면 `400 Invalid HTTP request received`로 거부한다.
- **로컬 환경**: uvicorn이 직접 노출되어 있어서 이 문제가 발생.
- **운영 환경**: nginx가 앞단에서 HTTP/2를 받아 uvicorn으로는 HTTP/1.1로 전달하므로 문제없음.
- **해결**: `JdkClientHttpRequestFactory`에 `HttpClient.Version.HTTP_1_1`을 지정해 강제.
  ```java
  HttpClient httpClient = HttpClient.newBuilder()
          .version(HttpClient.Version.HTTP_1_1)
          .build();
  RestClient restClient = RestClient.builder()
          .baseUrl(url)
          .requestFactory(new JdkClientHttpRequestFactory(httpClient))
          .build();
  ```
- 내부 서비스 간 통신은 HTTP/1.1이 표준적이므로 운영에서도 이 설정을 유지해도 무방하다.
- 파일: `backendJava/src/main/java/shop/jazzmate/jazzmateshop/recommendation/client/AiRecommendationClient.java`

### AssertJ 예외 검증 — `assertThatThrownBy`
- `assertThatThrownBy(람다).isInstanceOf(예외클래스).hasMessageContaining("키워드")`
- Python의 `pytest.raises(예외타입, match="키워드")`와 완전히 동일한 패턴.
- 예외 타입과 메시지를 함께 검증해 "왜 실패했는지"까지 보장.
- 파일: `backendJava/src/test/java/shop/jazzmate/jazzmateshop/userReview/UserReviewServiceTest.java`
