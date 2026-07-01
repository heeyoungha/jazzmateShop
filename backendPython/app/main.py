import logging
from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI

from app.api.recommend_router import router as recommend_router
from app.core.config import settings
from app.core.exceptions import ConfigurationError

logging.basicConfig(level=settings.LOG_LEVEL.upper())
log = logging.getLogger(__name__)

class FakeEmbeddings:
    async def create(self, model: str, input: str):
        del model
        seed = sum(ord(char) for char in input) % 997
        vector = [
            (((seed + index * 17) % 2000) / 1000.0) - 1.0
            for index in range(settings.EMBEDDING_DIMENSIONS)
        ]
        return SimpleNamespace(data=[SimpleNamespace(embedding=vector)])

class FakeChatCompletions:
    async def create(self, model: str, messages: list[dict[str, str]]):
        del model, messages
        message = SimpleNamespace(
            content="실제 DB 후보를 기반으로 생성한 부하 테스트용 추천 사유입니다."
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

# MOCK_OPENAI=true일 때 실제 OpenAI 대신 사용되는 가짜 클라이언트
class FakeOpenAIClient:
    def __init__(self):
        self.embeddings = FakeEmbeddings()
        self.chat = SimpleNamespace(completions=FakeChatCompletions())

    async def aclose(self) -> None:
        return None


def create_database_client():
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ConfigurationError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured."
        )
    try:
        from supabase import create_client
    except ImportError as exc:
        raise ConfigurationError(
            "supabase package is required to create the database client."
        ) from exc

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def create_openai_embedding_client() -> AsyncOpenAI:
    if settings.MOCK_OPENAI:
        return FakeOpenAIClient()
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def create_openai_chat_client() -> AsyncOpenAI:
    if settings.MOCK_OPENAI:
        return FakeOpenAIClient()
    return AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.OPENAI_TIMEOUT_SECONDS,
        max_retries=settings.OPENAI_MAX_RETRIES,
    )


def create_spring_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(limits=httpx.Limits(max_connections=100, max_keepalive_connections=20))


async def _close_resource(resource) -> None:
    if resource is None:
        return
    aclose = getattr(resource, "aclose", None)
    if aclose is not None:
        await aclose()
        return
    close = getattr(resource, "close", None)
    if close is not None:
        close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # with 블록 진입 시 실행 (startup)
    app.state.database = create_database_client()
    app.state.openai_embedding_client = create_openai_embedding_client()
    app.state.openai_chat_client = create_openai_chat_client()
    app.state.spring_http_client = create_spring_http_client()
    try:
        yield  # ← 앱이 실행되는 구간. with 블록 내부 동안 일시정지
    finally:
        # with 블록 탈출 시 실행 (shutdown)
        await _close_resource(getattr(app.state, "spring_http_client", None))
        await _close_resource(getattr(app.state, "openai_chat_client", None))
        await _close_resource(getattr(app.state, "openai_embedding_client", None))
        await _close_resource(getattr(app.state, "database", None)) 


app = FastAPI(
    title="JazzmateShop AI Recommendation API",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    log.error("422 Validation error | path=%s | body=%s | errors=%s",
              request.url.path, exc.body, exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


app.include_router(recommend_router)
