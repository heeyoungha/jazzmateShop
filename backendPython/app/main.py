import logging
from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from openai import AsyncOpenAI

from app.api.recommend_router import router as recommend_router
from app.core.config import settings
from app.core.exceptions import ConfigurationError
from app.observability.metrics import render_prometheus_metrics

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


async def create_database_client():
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ConfigurationError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured."
        )
    try:
        from supabase import acreate_client
    except ImportError as exc:
        raise ConfigurationError(
            "supabase package is required to create the database client."
        ) from exc

    from supabase import AsyncClientOptions
    db_http_client = httpx.AsyncClient(
        limits=httpx.Limits(max_connections=500, max_keepalive_connections=200)
    )
    return await acreate_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
        options=AsyncClientOptions(httpx_client=db_http_client),
    )


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
    return httpx.AsyncClient(limits=httpx.Limits(max_connections=600, max_keepalive_connections=200))


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


async def create_pg_pool():
    import asyncpg

    async def _init_conn(conn):
        # asyncpg는 pgvector의 vector 타입을 모르므로 text로 처리한다
        await conn.set_type_codec(
            "vector",
            encoder=str,
            decoder=str,
            schema="public",
            format="text",
        )

    return await asyncpg.create_pool(
        dsn=settings.DATABASE_URL,
        min_size=10,
        max_size=settings.DATABASE_POOL_SIZE,
        init=_init_conn,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # with 블록 진입 시 실행 (startup)
    if settings.DATABASE_URL:
        app.state.pg_pool = await create_pg_pool()
        app.state.database = None
        log.info("DB 연결: asyncpg pool (DATABASE_URL)")
    else:
        app.state.pg_pool = None
        app.state.database = await create_database_client()
        log.info("DB 연결: supabase-py client (SUPABASE_URL)")
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
        pg_pool = getattr(app.state, "pg_pool", None)
        if pg_pool is not None:
            await pg_pool.close()
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


@app.get("/metrics", include_in_schema=False)
async def metrics():
    body, content_type = render_prometheus_metrics()
    return Response(content=body, media_type=content_type)


app.include_router(recommend_router)
