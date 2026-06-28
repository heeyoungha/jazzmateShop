from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    OPENAI_API_KEY: str
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str
    EMBEDDING_DIMENSIONS: int
    RECOMMENDATION_TOP_K: int
    RECOMMENDATION_CANDIDATE_POOL_SIZE: int
    SPRING_BASE_URL: str
    OPENAI_TIMEOUT_SECONDS: float
    OPENAI_MAX_RETRIES: int = 2


settings = Settings()
