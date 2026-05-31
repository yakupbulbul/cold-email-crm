"""Deliverability MCP tools."""

import json

from app.mcp_server.db import get_db_session
from app.services.deliverability_service import DeliverabilityService


def register_deliverability_tools(tools: dict):
    tools["crm_deliverability_overview"] = {
        "description": "Get a comprehensive deliverability overview including domain readiness, mailbox health, and campaign stats.",
        "schema": {
            "type": "object",
            "properties": {},
        },
        "handler": handle_deliverability_overview,
    }

    tools["crm_domain_readiness"] = {
        "description": "Check DNS readiness for a specific domain including MX, SPF, DKIM, and DMARC status.",
        "schema": {
            "type": "object",
            "properties": {
                "domain_id": {"type": "string", "description": "Domain ID to check"},
            },
            "required": ["domain_id"],
        },
        "handler": handle_domain_readiness,
    }


def handle_deliverability_overview(args: dict) -> str:
    with get_db_session() as db:
        svc = DeliverabilityService(db)
        result = svc.overview()

    return json.dumps(result, indent=2, default=str)


def handle_domain_readiness(args: dict) -> str:
    domain_id = args["domain_id"]
    with get_db_session() as db:
        svc = DeliverabilityService(db)
        result = svc.domain_readiness(domain_id)

    return json.dumps(result, indent=2, default=str)
