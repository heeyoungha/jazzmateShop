from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from openai import AsyncOpenAI

from app.api.recommend_router import router as recommend_router
from app.core.config import settings
from app.core.exceptions import ConfigurationError


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
    return AsyncOpenAI()


def create_openai_chat_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        timeout=settings.OPENAI_TIMEOUT_SECONDS,
        max_retries=settings.OPENAI_MAX_RETRIES,
    )


def create_spring_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient()


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
app.include_router(recommend_router)
