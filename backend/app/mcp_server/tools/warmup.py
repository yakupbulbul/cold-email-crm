"""Warm-up management MCP tools."""

import json

from app.mcp_server.db import get_db_session
from app.services.warmup_service import WarmupService


def register_warmup_tools(tools: dict):
    tools["crm_warmup_status"] = {
        "description": "Get warm-up engine status including global state, participating mailboxes, active pairs, health, and blockers.",
        "schema": {
            "type": "object",
            "properties": {},
        },
        "handler": handle_warmup_status,
    }

    tools["crm_warmup_toggle"] = {
        "description": "Enable or disable global warm-up. When enabled, an immediate warm-up cycle is queued.",
        "schema": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean", "description": "True to enable, false to pause"},
            },
            "required": ["enabled"],
        },
        "handler": handle_warmup_toggle,
    }

    tools["crm_warmup_mailbox_toggle"] = {
        "description": "Enable or disable warm-up participation for a specific mailbox.",
        "schema": {
            "type": "object",
            "properties": {
                "mailbox_id": {"type": "string", "description": "Mailbox ID"},
                "warmup_enabled": {"type": "boolean", "description": "True to enable participation"},
            },
            "required": ["mailbox_id", "warmup_enabled"],
        },
        "handler": handle_warmup_mailbox_toggle,
    }

    tools["crm_warmup_logs"] = {
        "description": "Get recent warm-up activity logs.",
        "schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 50},
            },
        },
        "handler": handle_warmup_logs,
    }


def handle_warmup_status(args: dict) -> str:
    with get_db_session() as db:
        svc = WarmupService(db)
        result = svc.get_status_payload()

    return json.dumps(result, indent=2, default=str)


def handle_warmup_toggle(args: dict) -> str:
    enabled = args["enabled"]
    with get_db_session() as db:
        svc = WarmupService(db)
        svc.set_global_enabled(enabled)
        result = svc.get_status_payload()
        result["message"] = f"Warm-up {'enabled' if enabled else 'paused'} globally."

    return json.dumps(result, indent=2, default=str)


def handle_warmup_mailbox_toggle(args: dict) -> str:
    mailbox_id = args["mailbox_id"]
    warmup_enabled = args["warmup_enabled"]

    with get_db_session() as db:
        svc = WarmupService(db)
        mailbox = svc.set_mailbox_participation(mailbox_id, warmup_enabled)

        result = {
            "mailbox_id": mailbox.id,
            "email": mailbox.email,
            "warmup_enabled": mailbox.warmup_enabled,
            "message": f"Warm-up {'enabled' if warmup_enabled else 'disabled'} for {mailbox.email}.",
        }

    return json.dumps(result, indent=2, default=str)


def handle_warmup_logs(args: dict) -> str:
    limit = min(args.get("limit", 50), 200)
    with get_db_session() as db:
        svc = WarmupService(db)
        result = svc.get_logs_payload(limit=limit)

    return json.dumps(result, indent=2, default=str)
