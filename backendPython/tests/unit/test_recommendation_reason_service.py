import asyncio
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.core.exceptions import ConfigurationError
from app.services.recommendation_reason_service import RecommendationReasonService

from tests.fixtures import ALBUM_ID_1, ALBUM_ID_2, REVIEW_CONTENT, make_candidate


class FakeChatCompletions:
    def __init__(self, content="추천 사유입니다.", error=None, delay=0):
        self.content = content
        self.error = error
        self.delay = delay
        self.calls = []
        self.active_count = 0
        self.max_active_count = 0

    async def create(self, **kwargs):
        self.calls.append(kwargs) # ← spy 역할. 호출인자를 기록
        self.active_count += 1
        self.max_active_count = max(self.max_active_count, self.active_count)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            if self.error:
                raise self.error
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=self.content),
                    )
                ]
            )
        finally:
            self.active_count -= 1


class FakeOpenAiClient:
    def __init__(self, completions):
        self.chat = SimpleNamespace(completions=completions)


def test_recommendation_reason_service_requires_open_ai_client():
    """운영 조립 경로에서 OpenAI client 누락은 설정 오류로 실패한다."""
    with pytest.raises(ConfigurationError, match="openai client"):
        RecommendationReasonService(openai_client=None)


@pytest.mark.asyncio
async def test_generate_reasons_success_returns_reason_per_album():
    """후보 앨범의 개수만큼 추천 사유를 생성해 반환한다."""
    service = RecommendationReasonService(
        openai_client=FakeOpenAiClient(FakeChatCompletions("차분한 분위기가 잘 맞습니다."))
    )
    candidates = [make_candidate(ALBUM_ID_1), make_candidate(ALBUM_ID_2)]

    result = await service.generate_reasons(REVIEW_CONTENT, candidates)

    assert len(result) == 2
    assert all(reason.recommendation_reason for reason in result)



@pytest.mark.asyncio
async def test_generate_reasons_uses_configured_open_ai_client():
    """설정된 OPENAI_CHAT_MODEL로 OpenAI SDK를 호출한다."""
    completions = FakeChatCompletions("추천 사유입니다.")
    service = RecommendationReasonService(openai_client=FakeOpenAiClient(completions))

    await service.generate_reasons(REVIEW_CONTENT, [make_candidate()])

    assert completions.calls[0]["model"] == settings.OPENAI_CHAT_MODEL


@pytest.mark.asyncio
async def test_generate_reasons_multiple_candidates_runs_concurrently():
    """여러 후보의 추천 사유를 async로 병렬 생성한다."""
    completions = FakeChatCompletions("추천 사유입니다.", delay=0.05)
    service = RecommendationReasonService(openai_client=FakeOpenAiClient(completions))
    candidates = [make_candidate(ALBUM_ID_1), make_candidate(ALBUM_ID_2)]

    await service.generate_reasons(REVIEW_CONTENT, candidates)

    assert completions.max_active_count == 2


@pytest.mark.asyncio
async def test_generate_reasons_builds_prompt_with_review_context():
    """프롬프트에 사용자 감상문, 앨범 정보, 리뷰 원문/요약을 포함한다."""
    completions = FakeChatCompletions("추천 사유입니다.")
    service = RecommendationReasonService(openai_client=FakeOpenAiClient(completions))

    await service.generate_reasons(REVIEW_CONTENT, [make_candidate()])

    prompt = str(completions.calls[0]["messages"])
    # make_candidate()의 review_content참고
    assert REVIEW_CONTENT in prompt
    assert "Kind of Blue" in prompt
    assert "차분한 모달 재즈" in prompt
    assert "modal jazz" in prompt


@pytest.mark.asyncio
async def test_generate_reasons_open_ai_failure_returns_fallback_reason():
    """OpenAI Chat 실패 시 fallback 추천 사유를 반환한다."""
    service = RecommendationReasonService(
        openai_client=FakeOpenAiClient(FakeChatCompletions(error=RuntimeError("llm down")))
    )

    result = await service.generate_reasons(REVIEW_CONTENT, [make_candidate()])

    assert result[0].recommendation_reason # 값이 존재
    assert "추천" in result[0].recommendation_reason # fallback 사유에 추천이라는 단어가 있는 문장


@pytest.mark.asyncio
async def test_generate_reasons_empty_response_returns_fallback_reason():
    """빈 LLM 응답 시 fallback 추천 사유를 반환한다."""
    service = RecommendationReasonService(
        openai_client=FakeOpenAiClient(FakeChatCompletions(""))
    )

    result = await service.generate_reasons(REVIEW_CONTENT, [make_candidate()])

    assert result[0].recommendation_reason
    assert "추천" in result[0].recommendation_reason



def test_fallback_reason_common_keywords_mentions_shared_feature():
    """fallback 사유는 감상문과 후보 리뷰의 공통 음악 키워드를 반영한다."""
    service = RecommendationReasonService(
        openai_client=FakeOpenAiClient(FakeChatCompletions())
    )
    candidate = make_candidate(review_summary="modal jazz와 차분한 분위기가 돋보입니다.")

    reason = service.build_fallback_reason(REVIEW_CONTENT, candidate)

    assert "차분" in reason or "modal" in reason or "모달" in reason
