import os


class Settings:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    OPENAI_EMBEDDING_MODEL = os.getenv(
        "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
    )
    OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
    RECOMMENDATION_TOP_K = int(os.getenv("RECOMMENDATION_TOP_K", "3"))
    SPRING_BASE_URL = os.getenv("SPRING_BASE_URL", "http://localhost:8080")
    OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))
    OPENAI_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "2"))


settings = Settings()
