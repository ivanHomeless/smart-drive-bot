import os
import pytest


def test_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-123")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("ADMIN_CHAT_ID", "999")

    from pydantic_settings import BaseSettings
    from src.config import Settings

    s = Settings(
        TELEGRAM_BOT_TOKEN="test-token-123",
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/1",
        ADMIN_CHAT_ID=999,
    )

    assert s.TELEGRAM_BOT_TOKEN == "test-token-123"
    assert s.ADMIN_CHAT_ID == 999
    assert s.AMOCRM_MOCK_MODE is True
    assert s.HEALTH_CHECK_PORT == 8080
    assert s.LOG_LEVEL == "INFO"
    assert s.OPENAI_MODEL == "gpt-4o-mini"
