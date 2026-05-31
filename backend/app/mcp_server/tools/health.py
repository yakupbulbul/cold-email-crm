"""Health and system status MCP tools."""

import json

from app.mcp_server.db import get_db_session
from app.services.health_service import HealthService
from app.services.readiness_service import ReadinessService


def register_health_tools(tools: dict):
    tools["crm_system_health"] = {
        "description": "Check overall system health including database, Redis, workers, and SMTP/IMAP providers.",
        "schema": {
            "type": "object",
            "properties": {},
        },
        "handler": handle_system_health,
    }

    tools["crm_readiness_check"] = {
        "description": "Run production readiness checks covering configuration, infrastructure, and operational bounds.",
        "schema": {
            "type": "object",
            "properties": {},
        },
        "handler": handle_readiness_check,
    }


def handle_system_health(args: dict) -> str:
    with get_db_session() as db:
        svc = HealthService(db)
        result = svc.check_overall_health()
    return json.dumps(result, indent=2, default=str)


def handle_readiness_check(args: dict) -> str:
    with get_db_session() as db:
        svc = ReadinessService(db)
        result = svc.run_checklist()
    return json.dumps(result, indent=2, default=str)
