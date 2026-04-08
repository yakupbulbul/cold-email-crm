from fastapi.testclient import TestClient


def test_settings_summary_returns_real_runtime_state(client: TestClient, auth_headers: dict):
    response = client.get("/api/v1/settings/summary", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["app_env"] in {"development", "test", "staging", "production"}
    assert payload["worker_mode"] in {"lean", "full"}
    assert payload["frontend_mailcow_direct_access"] is False
    assert payload["auth_enabled"] is True
    assert payload["session_healthy"] is True
    assert payload["current_user"]["email"] == "test-admin@example.com"
    assert payload["health"]["database"]["status"] in {"healthy", "failed"}
    assert payload["health"]["redis"]["status"] in {"healthy", "failed"}
    assert payload["health"]["mailcow"]["status"] in {"healthy", "failed", "degraded", "unknown"}


def test_settings_summary_does_not_return_secret_values(client: TestClient, auth_headers: dict):
    response = client.get("/api/v1/settings/summary", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    serialized = str(payload)
    forbidden_keys = [
        "SECRET_KEY",
        "MAILCOW_API_KEY",
        "POSTGRES_URL",
        "REDIS_URL",
        "smtp_password",
        "imap_password",
        "access_token",
    ]
    for key in forbidden_keys:
        assert key not in serialized
