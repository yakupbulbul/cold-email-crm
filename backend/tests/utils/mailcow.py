from __future__ import annotations

from unittest.mock import Mock


def mocked_mailcow_response(*, status_code: int = 200, payload: dict | None = None) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload or {}
    return response
