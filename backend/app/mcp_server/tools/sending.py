"""Email sending MCP tools."""

import json

from app.mcp_server.db import get_db_session
from app.models.campaign import SendLog
from app.models.core import Mailbox


def register_sending_tools(tools: dict):
    tools["crm_send_email"] = {
        "description": "Send a single email through the backend SMTP pipeline. Uses the same send path as campaigns.",
        "schema": {
            "type": "object",
            "properties": {
                "mailbox_id": {"type": "string", "description": "Sender mailbox ID"},
                "to_email": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body (HTML supported)"},
            },
            "required": ["mailbox_id", "to_email", "subject", "body"],
        },
        "handler": handle_send_email,
    }

    tools["crm_send_logs"] = {
        "description": "Get recent send logs showing delivery status, SMTP responses, and timestamps.",
        "schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20, "description": "Max results"},
                "mailbox_id": {"type": "string", "description": "Filter by mailbox ID"},
            },
        },
        "handler": handle_send_logs,
    }


def handle_send_email(args: dict) -> str:
    mailbox_id = args["mailbox_id"]
    to_email = args["to_email"]
    subject = args["subject"]
    body = args["body"]

    with get_db_session() as db:
        from app.services.smtp_service import SMTPManagerService
        svc = SMTPManagerService(db)

        mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
        if not mailbox:
            return json.dumps({"error": f"Mailbox {mailbox_id} not found"})

        if mailbox.status != "active":
            return json.dumps({"error": "Mailbox must be active before sending email."})

        try:
            result = svc.send_email(
                mailbox=mailbox,
                to_email=to_email,
                subject=subject,
                body=body,
            )
            return json.dumps({
                "success": True,
                "status": "sent",
                "message_id": result.get("message_id"),
                "provider": result.get("provider", "smtp"),
            }, indent=2, default=str)
        except Exception as e:
            return json.dumps({
                "success": False,
                "status": "failed",
                "error": str(e),
            }, indent=2)


def handle_send_logs(args: dict) -> str:
    limit = min(args.get("limit", 20), 100)
    mailbox_id = args.get("mailbox_id")

    with get_db_session() as db:
        query = db.query(SendLog)
        if mailbox_id:
            query = query.filter(SendLog.mailbox_id == mailbox_id)
        logs = query.order_by(SendLog.created_at.desc()).limit(limit).all()

        results = []
        for log in logs:
            results.append({
                "id": log.id,
                "target_email": log.target_email,
                "subject": log.subject,
                "delivery_status": log.delivery_status,
                "smtp_response": getattr(log, "smtp_response", None),
                "created_at": str(log.created_at),
            })

    return json.dumps(results, indent=2, default=str)
