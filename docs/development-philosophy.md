# 개발 철학

## AI 에이전트 시대의 개발자 역할

AI 에이전트 기술이 고도화되면서 코드 작성의 주체가 개발자에서 AI로 이동하고 있다. 이에 따라 개발자의 역할은 직접 코드를 작성하는 것보다 **전체 프로세스를 설계하고, AI가 생성한 결과를 검증하는 것**에 집중해야 한다.

이 관점에서 이 프로젝트는 다음 원칙을 따른다.

- **설계가 먼저다** — 구현보다 문서(SDD, 다이어그램)를 먼저 작성한다. AI에게 구현을 위임하기 전에 의도를 명확히 고정해야 한다.
- **검증이 핵심이다** — AI가 생성한 코드가 설계 의도대로 동작하는지 테스트(TDD)로 확인한다.
- **맥락을 문서화한다** — 결정의 배경과 트레이드오프를 기록해 AI가 어느 시점에 어떤 모델로 구현하더라도 일관된 판단을 할 수 있게 한다.

참고: [Claude Code 마스터](https://github.com/claude-code-expert/)

## 적용 방식

### SDD (Spec-Driven Development)

구현 전에 설계 문서를 먼저 작성하고, AI 에이전트는 그 문서를 기준으로 구현한다.

- 설계 변경이 필요하면 코드가 아니라 문서를 먼저 수정한다
- AI가 설계 범위를 벗어난 구현을 하지 않도록 문서가 경계를 정의한다
- 관련 문서: [docs/SDD.md](SDD.md)

### TDD (Test-Driven Development)

AI가 생성한 코드의 품질을 테스트로 검증한다.

- 테스트 시나리오에 없는 동작을 임의로 추가하지 않는다
- 각 모듈의 테스트 전략: [backendJava ADR-001](backendJava/adr/001-test-strategy.md) · [backendPython ADR-003](backendPython/adr/003-test-strategy.md) · [frontend ADR-003](frontend/adr/003-frontend-test-strategy.md)
