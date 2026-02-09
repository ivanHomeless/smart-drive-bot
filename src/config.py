from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    ADMIN_CHAT_ID: int = 0

    # PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/smartdrive"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # AmoCRM
    AMOCRM_SUBDOMAIN: str = ""
    AMOCRM_CLIENT_ID: str = ""
    AMOCRM_CLIENT_SECRET: str = ""
    AMOCRM_REDIRECT_URI: str = "https://example.com"
    AMOCRM_PIPELINE_ID: int = 0
    AMOCRM_STATUS_ID: int = 0
    AMOCRM_RESPONSIBLE_USER_ID: int = 0
    AMOCRM_MOCK_MODE: bool = True

    # AmoCRM Custom Field IDs
    AMOCRM_FIELD_TELEGRAM_ID: int = 0
    AMOCRM_FIELD_TELEGRAM_USERNAME: int = 0
    AMOCRM_FIELD_SERVICE_TYPE: int = 0
    AMOCRM_FIELD_CAR_BRAND: int = 0
    AMOCRM_FIELD_CAR_MODEL: int = 0
    AMOCRM_FIELD_CAR_YEAR: int = 0
    AMOCRM_FIELD_BUDGET: int = 0
    AMOCRM_FIELD_MILEAGE: int = 0
    AMOCRM_FIELD_TRANSMISSION: int = 0
    AMOCRM_FIELD_DRIVE_TYPE: int = 0
    AMOCRM_FIELD_BODY_TYPE: int = 0
    AMOCRM_FIELD_VIN_NUMBER: int = 0
    AMOCRM_FIELD_CHECK_TYPE: int = 0
    AMOCRM_FIELD_SOURCE: int = 0

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_FALLBACK_MODEL: str = "gpt-4o"
    OPENAI_MAX_TOKENS: int = 500
    OPENAI_TEMPERATURE: float = 0.3
    OPENAI_SMART_FALLBACK_CONFIDENCE: float = 0.65

    # App
    LOG_LEVEL: str = "INFO"
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_BACKOFF_BASE: int = 2
    HEALTH_CHECK_PORT: int = 8080

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
