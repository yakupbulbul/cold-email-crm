"""Lead list management MCP tools."""

import json
from datetime import datetime, timezone
from uuid import uuid4

from app.mcp_server.db import get_db_session
from app.models.lists import LeadList, LeadListMembership
from app.models.campaign import Contact


def register_list_tools(tools: dict):
    tools["crm_list_lists"] = {
        "description": "List all lead lists with contact counts.",
        "schema": {
            "type": "object",
            "properties": {},
        },
        "handler": handle_list_lists,
    }

    tools["crm_create_list"] = {
        "description": "Create a new lead list.",
        "schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "List name"},
                "description": {"type": "string", "description": "List description"},
            },
            "required": ["name"],
        },
        "handler": handle_create_list,
    }

    tools["crm_add_contacts_to_list"] = {
        "description": "Add contacts to a lead list by their IDs.",
        "schema": {
            "type": "object",
            "properties": {
                "list_id": {"type": "string", "description": "List ID"},
                "contact_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Contact IDs to add",
                },
            },
            "required": ["list_id", "contact_ids"],
        },
        "handler": handle_add_contacts,
    }


def handle_list_lists(args: dict) -> str:
    with get_db_session() as db:
        lists = db.query(LeadList).order_by(LeadList.created_at.desc()).all()
        results = []
        for lst in lists:
            count = db.query(LeadListMembership).filter(
                LeadListMembership.list_id == lst.id
            ).count()
            results.append({
                "id": lst.id,
                "name": lst.name,
                "description": lst.description,
                "contact_count": count,
                "created_at": str(lst.created_at),
            })

    return json.dumps(results, indent=2, default=str)


def handle_create_list(args: dict) -> str:
    with get_db_session() as db:
        lead_list = LeadList(
            id=str(uuid4()),
            name=args["name"],
            description=args.get("description"),
            created_at=datetime.now(timezone.utc),
        )
        db.add(lead_list)
        db.flush()

        result = {
            "id": lead_list.id,
            "name": lead_list.name,
            "message": "List created.",
        }

    return json.dumps(result, indent=2, default=str)


def handle_add_contacts(args: dict) -> str:
    list_id = args["list_id"]
    contact_ids = args["contact_ids"]

    with get_db_session() as db:
        lead_list = db.query(LeadList).filter(LeadList.id == list_id).first()
        if not lead_list:
            return json.dumps({"error": f"List {list_id} not found"})

        added = 0
        skipped = 0
        for cid in contact_ids:
            existing = db.query(LeadListMembership).filter(
                LeadListMembership.list_id == list_id,
                LeadListMembership.contact_id == cid,
            ).first()
            if existing:
                skipped += 1
                continue

            contact = db.query(Contact).filter(Contact.id == cid).first()
            if not contact:
                skipped += 1
                continue

            membership = LeadListMembership(
                id=str(uuid4()),
                list_id=list_id,
                contact_id=cid,
                created_at=datetime.now(timezone.utc),
            )
            db.add(membership)
            added += 1

        db.flush()

    return json.dumps({
        "list_id": list_id,
        "added": added,
        "skipped": skipped,
        "message": f"Added {added} contacts to list.",
    }, indent=2)
