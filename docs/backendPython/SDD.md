# JazzmateShop — Python 백엔드 설계 (SDD)

> - 대상: FastAPI AI 추천 서버
> - 코딩 컨벤션 및 Best Practice: [backendPython/AGENTS.md](../../backendPython/AGENTS.md) 참조
> - 공통 설계 (인프라 라우팅 · API 계약 · 추천 상태 전이): [docs/SDD.md](../SDD.md)

---

## 목차

1. [역할과 책임](#1-역할과-책임)
2. [사용자 플로우별 설계](#2-사용자-플로우별-설계)
3. [참조 문서](#3-참조-문서)

---

## 1. 역할과 책임

Python 백엔드는 사용자 감상문 본문을 기반으로 앨범 추천 후보를 계산하고, 추천 결과를 Spring Boot에 콜백으로 전달한다.

FastAPI는 추천 상태와 추천 결과 저장의 source of truth가 아니다. `recommendationStatus` 전이와 `recommend_album` 저장은 Spring Boot가 담당한다.

| 레이어 | 책임 | 금지 |
|---|---|---|
| Router | 요청 검증, `202 Accepted` 응답, 백그라운드 작업 등록 | OpenAI/DB/Spring 직접 호출 |
| Service | 추천 처리 유스케이스 조합, TOP K 정책 적용 | FastAPI Request/Response 객체 의존 |
| Repository | `v_embedding_with_album` 읽기 전용 유사도 검색 | 추천 상태 변경, Spring 콜백 |
| Client | OpenAI API, Spring Boot 콜백 HTTP 통신 | 비즈니스 정책 판단 |
| Schema | Pydantic 요청/콜백/내부 DTO | DB 또는 HTTP 직접 호출 |
| Config | 환경변수와 기본값 중앙 관리 | `.env` 직접 수정, 코드 하드코딩 |

---

## 2. 사용자 플로우별 설계

| 플로우 | FastAPI 책임 | 전체 플로우 | Python 구현 상세 |
|---|---|---|---|
| 감상문 작성 + AI 추천 요청 | Spring 추천 요청 수신, 추천 처리 시작 | [flows/01-write-review.md](../flows/01-write-review.md) | [flows/01-write-review.md](./flows/01-write-review.md) |
| AI 추천 처리 + 콜백 전송 | 임베딩 생성, 유사도 검색, 추천 사유 생성, Spring 콜백 | [flows/02-recommend.md](../flows/02-recommend.md) | [flows/02-recommend.md](./flows/02-recommend.md) |

---

## 3. 참조 문서

| 문서 | 역할 |
|---|---|
| [docs/architecture.md](../architecture.md) | 전체 시스템 흐름 |
| [docs/SDD.md](../SDD.md) | 공통 시스템 설계 기준 |
| [docs/API_SPEC.md](../API_SPEC.md) | Spring-FastAPI API 계약 |
| [flows/](./flows/) | FastAPI가 참여하는 플로우별 구현 상세 |
| [ADR-BP001](./adr/001-fastapi-module-design.md) | FastAPI 모듈/레이어 설계 결정 |
| [ADR-BP002](./adr/002-recommendation-processing-policy.md) | 추천 처리와 콜백 정책 결정 |
| [ADR-BP003](./adr/003-test-strategy.md) | Python 백엔드 테스트 전략 결정 |
| [backendPython/AGENTS.md](../../backendPython/AGENTS.md) | Python 구현 규칙 |
