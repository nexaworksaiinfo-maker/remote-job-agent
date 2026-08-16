"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Remote Job Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = Field(default="", min_length=32)
    API_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "remote_job_agent"
    POSTGRES_POOL_SIZE: int = 20
    POSTGRES_MAX_OVERFLOW: int = 10
    POSTGRES_POOL_TIMEOUT: int = 30

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_MAX_CONNECTIONS: int = 50

    @property
    def REDIS_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 300
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 4

    # Ollama (Local LLM - Free)
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "llama3.1:70b"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    USE_OLLAMA_FOR_CHAT: bool = True
    USE_OLLAMA_FOR_EMBEDDINGS: bool = True

    # OpenAI (Optional - for embeddings only, can use sentence-transformers instead)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"
    OPENAI_MAX_TOKENS: int = 4096
    OPENAI_TEMPERATURE: float = 0.7

    # Ollama (Local LLM - Primary for chat/completion)
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "llama3.1:70b"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    USE_OLLAMA_FOR_CHAT: bool = True
    USE_OLLAMA_FOR_EMBEDDINGS: bool = False

    # LinkedIn
    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None
    LINKEDIN_REDIRECT_URI: Optional[str] = None

    # Indeed
    INDEED_API_KEY: Optional[str] = None
    INDEED_PUBLISHER_ID: Optional[str] = None

    # RemoteOK
    REMOTEOK_API_KEY: Optional[str] = None

    # Wellfound (AngelList)
    WELLFOUND_API_KEY: Optional[str] = None

    # Y Combinator
    YC_JOBS_API_KEY: Optional[str] = None

    # Glassdoor
    GLASSDOOR_API_KEY: Optional[str] = None
    GLASSDOOR_PARTNER_ID: Optional[str] = None

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    TELEGRAM_ADMIN_IDS: List[int] = []

    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    EMAIL_FROM: str = "noreply@remotejobagent.com"
    EMAIL_FROM_NAME: str = "Remote Job Agent"

    # Cal.com (Scheduling)
    CAL_COM_API_KEY: Optional[str] = None
    CAL_COM_USERNAME: Optional[str] = None

    # Google Calendar
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None

    # Browser Automation (Playwright)
    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_SLOW_MO: int = 100
    PLAYWRIGHT_TIMEOUT: int = 30000
    PLAYWRIGHT_USER_DATA_DIR: str = "/tmp/playwright"

    # Anti-detection
    ROTATE_USER_AGENTS: bool = True
    ROTATE_PROXIES: bool = False
    PROXY_LIST: List[str] = []
    REQUEST_DELAY_MIN: float = 2.0
    REQUEST_DELAY_MAX: float = 5.0

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60

    # Job Matching
    MATCH_THRESHOLD: float = 0.65
    SEMANTIC_WEIGHT: float = 0.5
    SKILL_WEIGHT: float = 0.3
    EXPERIENCE_WEIGHT: float = 0.15
    SALARY_WEIGHT: float = 0.05

    # Application Settings
    MAX_DAILY_APPLICATIONS: int = 20
    MAX_CONCURRENT_APPLICATIONS: int = 3
    APPLICATION_TIMEOUT: int = 120
    RETRY_FAILED_APPLICATIONS: bool = True
    MAX_RETRIES: int = 3

    # Monitoring
    SENTRY_DSN: Optional[str] = None
    PROMETHEUS_ENABLED: bool = True
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: List[str] = ["*"]

    # Security
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60 * 24 * 7  # 7 days
    PASSWORD_MIN_LENGTH: int = 12
    ENCRYPTION_KEY: str = Field(default="", min_length=32)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()