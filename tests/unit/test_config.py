"""Unit test for application configuration loading."""

from app.core.config import settings


def test_settings_load():
    assert settings.APP_NAME == "doctor-appointment-agent"
    assert settings.API_V1_PREFIX == "/api/v1"
