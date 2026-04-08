"""test_config.py — Settings validation tests."""
import pytest

from app.core.config import Settings


def test_settings_require_non_placeholder_secret_outside_test():
    with pytest.raises(ValueError):
        Settings(APP_ENV="development", SECRET_KEY="dev-only-change-me")


def test_settings_allow_placeholder_secret_in_test_env():
    settings = Settings(APP_ENV="test", SECRET_KEY="dev-only-change-me")
    assert settings.APP_ENV == "test"


def test_settings_require_mailcow_url_and_key_together():
    with pytest.raises(ValueError):
        Settings(APP_ENV="test", SECRET_KEY="long-enough-test-secret", MAILCOW_API_URL="https://mail.example.com/api/v1")
