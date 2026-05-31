"""Contact management MCP tools."""

import json
from datetime import datetime, timezone
from uuid import uuid4

from app.mcp_server.db import get_db_session
from app.models.campaign import Contact


def register_contact_tools(tools: dict):
    tools["crm_list_contacts"] = {
        "description": "List contacts with optional filters. Returns email, name, status, verification, and tags.",
        "schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results (default 50)", "default": 50},
                "search": {"type": "string", "description": "Search by email or name"},
                "status": {"type": "string", "description": "Filter by status: active, bounced, unsubscribed"},
            },
        },
        "handler": handle_list_contacts,
    }

    tools["crm_create_contact"] = {
        "description": "Create a new contact with email and optional metadata.",
        "schema": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "Email address"},
                "first_name": {"type": "string", "description": "First name"},
                "last_name": {"type": "string", "description": "Last name"},
                "company": {"type": "string", "description": "Company name"},
                "contact_type": {"type": "string", "enum": ["b2b", "b2c"], "description": "Contact type"},
            },
            "required": ["email"],
        },
        "handler": handle_create_contact,
    }

    tools["crm_search_contacts"] = {
        "description": "Search contacts by email pattern, company, or tags.",
        "schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (matches email, name, company)"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["query"],
        },
        "handler": handle_search_contacts,
    }


def _serialize_contact(c: Contact) -> dict:
    return {
        "id": c.id,
        "email": c.email,
        "first_name": c.first_name,
        "last_name": c.last_name,
        "company": getattr(c, "company", None),
        "contact_type": getattr(c, "contact_type", None),
        "status": c.status,
        "is_suppressed": getattr(c, "is_suppressed", False),
        "verification_status": getattr(c, "verification_status", None),
        "trust_score": getattr(c, "trust_score", None),
        "created_at": str(c.created_at),
    }


def handle_list_contacts(args: dict) -> str:
    limit = min(args.get("limit", 50), 200)
    search = args.get("search")
    status = args.get("status")

    with get_db_session() as db:
        query = db.query(Contact)
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                Contact.email.ilike(pattern)
                | Contact.first_name.ilike(pattern)
                | Contact.last_name.ilike(pattern)
            )
        if status:
            query = query.filter(Contact.status == status)

        contacts = query.order_by(Contact.created_at.desc()).limit(limit).all()
        results = [_serialize_contact(c) for c in contacts]

    return json.dumps(results, indent=2, default=str)


def handle_create_contact(args: dict) -> str:
    with get_db_session() as db:
        existing = db.query(Contact).filter(Contact.email == args["email"]).first()
        if existing:
            return json.dumps({"error": f"Contact with email {args['email']} already exists", "id": existing.id})

        contact = Contact(
            id=str(uuid4()),
            email=args["email"],
            first_name=args.get("first_name"),
            last_name=args.get("last_name"),
            status="active",
            created_at=datetime.now(timezone.utc),
        )
        if hasattr(Contact, "company") and args.get("company"):
            contact.company = args["company"]
        if hasattr(Contact, "contact_type") and args.get("contact_type"):
            contact.contact_type = args["contact_type"]

        db.add(contact)
        db.flush()

        result = _serialize_contact(contact)
        result["message"] = "Contact created."

    return json.dumps(result, indent=2, default=str)


def handle_search_contacts(args: dict) -> str:
    query_str = args["query"]
    limit = min(args.get("limit", 20), 100)

    with get_db_session() as db:
        pattern = f"%{query_str}%"
        contacts = (
            db.query(Contact)
            .filter(
                Contact.email.ilike(pattern)
                | Contact.first_name.ilike(pattern)
                | Contact.last_name.ilike(pattern)
            )
            .limit(limit)
            .all()
        )
        results = [_serialize_contact(c) for c in contacts]

    return json.dumps(results, indent=2, default=str)
