"""Mailbox management MCP tools."""

import json

from app.mcp_server.db import get_db_session
from app.models.core import Mailbox


def register_mailbox_tools(tools: dict):
    tools["crm_list_mailboxes"] = {
        "description": "List all mailboxes with their status, SMTP health, and warm-up state.",
        "schema": {
            "type": "object",
            "properties": {},
        },
        "handler": handle_list_mailboxes,
    }

    tools["crm_mailbox_status"] = {
        "description": "Get detailed status for a specific mailbox including SMTP check results and OAuth state.",
        "schema": {
            "type": "object",
            "properties": {
                "mailbox_id": {"type": "string", "description": "Mailbox ID"},
            },
            "required": ["mailbox_id"],
        },
        "handler": handle_mailbox_status,
    }

    tools["crm_smtp_check"] = {
        "description": "Run an SMTP connectivity check for a mailbox and return diagnostic results.",
        "schema": {
            "type": "object",
            "properties": {
                "mailbox_id": {"type": "string", "description": "Mailbox ID to check"},
            },
            "required": ["mailbox_id"],
        },
        "handler": handle_smtp_check,
    }


def _serialize_mailbox(m: Mailbox) -> dict:
    return {
        "id": m.id,
        "email": m.email,
        "display_name": m.display_name,
        "smtp_host": m.smtp_host,
        "smtp_port": m.smtp_port,
        "status": m.status,
        "provider_type": getattr(m, "provider_type", "google_workspace"),
        "oauth_connection_status": getattr(m, "oauth_connection_status", None),
        "warmup_enabled": getattr(m, "warmup_enabled", False),
        "smtp_last_check_status": getattr(m, "smtp_last_check_status", None),
        "smtp_last_check_message": getattr(m, "smtp_last_check_message", None),
        "daily_send_limit": getattr(m, "daily_send_limit", 50),
        "current_warmup_stage": getattr(m, "current_warmup_stage", 0),
        "created_at": str(m.created_at),
    }


def handle_list_mailboxes(args: dict) -> str:
    with get_db_session() as db:
        mailboxes = db.query(Mailbox).order_by(Mailbox.created_at.desc()).all()
        results = [_serialize_mailbox(m) for m in mailboxes]

    return json.dumps(results, indent=2, default=str)


def handle_mailbox_status(args: dict) -> str:
    mailbox_id = args["mailbox_id"]
    with get_db_session() as db:
        mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
        if not mailbox:
            return json.dumps({"error": f"Mailbox {mailbox_id} not found"})

        result = _serialize_mailbox(mailbox)

    return json.dumps(result, indent=2, default=str)


def handle_smtp_check(args: dict) -> str:
    mailbox_id = args["mailbox_id"]
    with get_db_session() as db:
        from app.services.smtp_service import SMTPManagerService
        svc = SMTPManagerService(db)
        mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
        if not mailbox:
            return json.dumps({"error": f"Mailbox {mailbox_id} not found"})

        result = svc.diagnose_connection(mailbox)

    return json.dumps(result, indent=2, default=str)
