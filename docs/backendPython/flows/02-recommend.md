# [FastAPI] AI 추천 처리 + 콜백 전송

> 전체 플로우: [docs/flows/02-recommend.md](../../flows/02-recommend.md)

## 요구사항

- 추천 수는 `config.RECOMMENDATION_TOP_K` (기본값 3)로 관리한다. 변경 시 이 값만 수정한다.
- 유사도 검색 대상은 `v_embedding_with_album`으로 고정한다.
- 추천 사유는 유사도 검색 결과와 `review_content`를 함께 사용해 생성한다.
- Spring 콜백 전송 실패 시 재시도 정책은 별도 결정 전까지 로그만 기록한다.
- FastAPI는 `user_reviews`, `recommend_album`을 직접 수정하지 않는다. 추천 결과 저장과 상태 전이는 Spring Boot 콜백에 위임한다.

## 관련 구성요소

| 단계 | 구성요소 | 역할 | 입력 | 출력 | DB/API |
|------|----------|------|------|------|--------|
| 1 | `recommend_router` | POST /recommend/by-review 수신 | review_id, review_content | - | - |
| 2 | `embedding_service` | 감상문 임베딩 생성 | review_content | embedding vector | OpenAI Python SDK Embeddings API |
| 3 | `similarity_search` | `v_embedding_with_album` 유사도 검색 | embedding vector | TOP K 앨범 | v_embedding_with_album SELECT |
| 4 | `recommendation_reason_service` | 앨범별 추천 사유 생성 | review_content, TOP K 앨범 | recommendationReason 목록 | OpenAI Python SDK Chat API |
| 5 | `callback_client` | Spring 처리 결과 콜백 전송 | review_id, COMPLETED/FAILED 결과 | - | POST Spring /api/user-reviews/{id}/recommendations |

## 테스트 시나리오

### `RecommendRouterTest`

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| 유효한 추천 요청 | HTTP 202, background task 등록 | `post_byReview_validRequest_returns202` |
| `review_id` 누락 | HTTP 422 | `post_byReview_missingReviewId_returns422` |
| `review_content` 공백 | HTTP 422 | `post_byReview_blankReviewContent_returns422` |

### `RecommendationSchemaTest`

콜백 item DTO는 외부로 단독 전송하지 않고, Spring 처리 결과 콜백 DTO의 `recommendations[]` 원소로 사용한다.

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| inbound 요청 DTO 생성 | snake_case 필드 매핑 | `request_valid_mapsFields` |
| 콜백 item DTO 생성 | camelCase 필드 직렬화 | `callbackItem_serializesCamelCase` |
| 성공 콜백 DTO 생성 | `status=COMPLETED`, `recommendations[]` 포함 | `callbackRequest_completedContainsRecommendations` |
| 실패 콜백 DTO 생성 | `status=FAILED`, errorCode/message, 빈 `recommendations[]` 포함 | `callbackRequest_failedContainsErrorAndEmptyRecommendations` |

### `EmbeddingServiceTest`

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| 감상문 본문 임베딩 성공 | 1536차원 vector 반환 | `embedReview_success_returns1536Vector` |
| OpenAI 임베딩 API 실패 | 도메인 예외 또는 실패 결과로 변환 | `embedReview_openAiFailure_raisesEmbeddingError` |
| 설정 모델명 사용 | `OPENAI_EMBEDDING_MODEL`로 호출 | `embedReview_usesConfiguredModel` |

### `RecommendationServiceTest`

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| 성공 경로 | 임베딩 생성 → TOP K 검색 → 추천 사유 생성 → Spring 콜백 | `recommendByReview_success_sendsCallback` |
| TOP K 정책 | `RECOMMENDATION_TOP_K` 값으로 검색 | `recommendByReview_usesConfiguredTopK` |
| 점수 정규화 | 콜백 score가 0.0000~1.0000 범위 | `recommendByReview_normalizesScoreForCallback` |
| 후보 0건 | 추천 사유 생성 없이 FAILED 콜백 전송 | `recommendByReview_noCandidates_sendsFailedCallback` |
| 임베딩 실패 | 검색/LLM 미호출, FAILED 콜백 전송 | `recommendByReview_embeddingFailure_sendsFailedCallback` |
| 유사도 검색 실패 | LLM 미호출, FAILED 콜백 전송 | `recommendByReview_searchFailure_sendsFailedCallback` |
| 콜백 전송 실패 | 별도 결정 전까지 로그만 기록 | `recommendByReview_callbackFailure_logsOnly` |

### `AlbumEmbeddingRepositoryTest`

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| TOP K 유사도 검색 | similarity DESC 정렬, 최대 K건 반환 | `findSimilarAlbums_returnsTopKBySimilarity` |
| 조회 대상 고정 | `v_embedding_with_album`만 조회 | `findSimilarAlbums_queriesEmbeddingWithAlbumView` |
| 후보 없음 | 빈 리스트 반환 | `findSimilarAlbums_noRows_returnsEmptyList` |
| DB 조회 실패 | 도메인 예외로 변환 | `findSimilarAlbums_dbFailure_raisesRepositoryError` |

### `RecommendationReasonServiceTest`

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| 후보별 추천 사유 생성 | 후보 수와 동일한 reason 반환 | `generateReasons_success_returnsReasonPerAlbum` |
| 추천 사유 매핑 | 각 reason이 원래 album_id와 매칭 | `generateReasons_preservesAlbumIdMapping` |
| OpenAI SDK 사용 | 설정된 모델/timeout/retry로 호출 | `generateReasons_usesConfiguredOpenAiClient` |
| 후보별 병렬 생성 | 여러 후보를 async로 동시에 처리 | `generateReasons_multipleCandidates_runsConcurrently` |
| 프롬프트 컨텍스트 구성 | 사용자 감상문, 앨범 정보, 리뷰 원문/요약 포함 | `generateReasons_buildsPromptWithReviewContext` |
| OpenAI Chat 실패 | fallback 추천 사유 반환 | `generateReasons_openAiFailure_returnsFallbackReason` |
| 빈 LLM 응답 | fallback 추천 사유 반환 | `generateReasons_emptyResponse_returnsFallbackReason` |
| 빈 후보 목록 | OpenAI 호출 없이 빈 결과 | `generateReasons_emptyCandidates_skipsOpenAi` |
| fallback 키워드 매칭 | 사용자 감상문과 후보 리뷰의 공통 음악 키워드 반영 | `fallbackReason_commonKeywords_mentionsSharedFeature` |

### `SpringCallbackClientTest`

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| 성공 콜백 | 올바른 URL과 `status=COMPLETED` payload로 POST | `sendCompletedResult_postsExpectedPayload` |
| 실패 콜백 | 올바른 URL과 `status=FAILED` payload로 POST | `sendFailedResult_postsExpectedPayload` |
| Spring 콜백 응답 body 없음 | Spring이 200 OK + empty body를 반환하면 성공 처리 | `sendRecommendations_emptySpringResponseBody200_success` |
| 4xx/5xx 응답 | 콜백 전송 실패로 기록 | `sendRecommendations_non2xx_raisesCallbackError` |
| timeout | 콜백 전송 실패로 기록 | `sendRecommendations_timeout_raisesCallbackError` |

### `RecommendationFlowIntegrationTest`

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| 정상 요청 전체 흐름 | 202 반환 후 콜백 client 호출 확인 | `recommendFlow_validRequest_returns202AndProcessesCallback` |
| 중복 요청 | 같은 review_id 두 번 요청해도 콜백 payload 구조 유지 | `recommendFlow_duplicateRequest_remainsCallbackCompatible` |

## 관련 API

- [API_SPEC.md — POST /recommend/by-review](../../API_SPEC.md#post-recommendby-review)
- [API_SPEC.md — POST /api/user-reviews/{reviewId}/recommendations](../../API_SPEC.md#post-apiuser-reviewsreviewidrecommendations)
