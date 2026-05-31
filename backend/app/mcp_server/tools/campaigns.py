"""Campaign management MCP tools."""

import json
from datetime import datetime, timezone

from app.mcp_server.db import get_db_session
from app.models.campaign import Campaign, CampaignLead, Contact, EmailTemplate


def register_campaign_tools(tools: dict):
    tools["crm_list_campaigns"] = {
        "description": "List all campaigns with their status, mailbox, and execution summary.",
        "schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status: draft, active, paused, completed, archived",
                },
            },
        },
        "handler": handle_list_campaigns,
    }

    tools["crm_get_campaign"] = {
        "description": "Get detailed information about a specific campaign including leads and sequence steps.",
        "schema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string", "description": "Campaign ID"},
            },
            "required": ["campaign_id"],
        },
        "handler": handle_get_campaign,
    }

    tools["crm_create_campaign"] = {
        "description": "Create a new campaign with a name, mailbox, subject, and body.",
        "schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Campaign name"},
                "mailbox_id": {"type": "string", "description": "Sender mailbox ID"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body (HTML supported)"},
                "campaign_type": {"type": "string", "enum": ["b2b", "b2c"], "description": "Campaign type"},
                "daily_limit": {"type": "integer", "description": "Max sends per day", "default": 50},
            },
            "required": ["name", "mailbox_id", "subject", "body"],
        },
        "handler": handle_create_campaign,
    }

    tools["crm_campaign_status"] = {
        "description": "Get campaign execution status: lead counts, send stats, blockers, and next scheduled action.",
        "schema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string", "description": "Campaign ID"},
            },
            "required": ["campaign_id"],
        },
        "handler": handle_campaign_status,
    }


def handle_list_campaigns(args: dict) -> str:
    status_filter = args.get("status")
    with get_db_session() as db:
        query = db.query(Campaign)
        if status_filter:
            query = query.filter(Campaign.status == status_filter)
        campaigns = query.order_by(Campaign.created_at.desc()).all()

        results = []
        for c in campaigns:
            results.append({
                "id": c.id,
                "name": c.name,
                "status": c.status,
                "campaign_type": c.campaign_type,
                "mailbox_id": c.mailbox_id,
                "subject": c.subject,
                "daily_limit": c.daily_limit,
                "created_at": str(c.created_at),
            })

    return json.dumps(results, indent=2, default=str)


def handle_get_campaign(args: dict) -> str:
    campaign_id = args["campaign_id"]
    with get_db_session() as db:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return json.dumps({"error": f"Campaign {campaign_id} not found"})

        leads = db.query(CampaignLead).filter(CampaignLead.campaign_id == campaign_id).all()
        lead_data = []
        for lead in leads:
            contact = db.query(Contact).filter(Contact.id == lead.contact_id).first()
            lead_data.append({
                "contact_id": lead.contact_id,
                "email": contact.email if contact else "unknown",
                "status": lead.status,
                "current_step": lead.current_step,
                "last_sent_at": str(lead.last_sent_at) if lead.last_sent_at else None,
            })

        result = {
            "id": campaign.id,
            "name": campaign.name,
            "status": campaign.status,
            "campaign_type": campaign.campaign_type,
            "mailbox_id": campaign.mailbox_id,
            "subject": campaign.subject,
            "body": campaign.body,
            "daily_limit": campaign.daily_limit,
            "goal_type": campaign.goal_type,
            "compliance_mode": campaign.compliance_mode,
            "created_at": str(campaign.created_at),
            "leads_count": len(lead_data),
            "leads": lead_data[:50],  # Cap to avoid huge responses
        }

    return json.dumps(result, indent=2, default=str)


def handle_create_campaign(args: dict) -> str:
    with get_db_session() as db:
        from uuid import uuid4
        campaign = Campaign(
            id=str(uuid4()),
            name=args["name"],
            mailbox_id=args["mailbox_id"],
            subject=args["subject"],
            body=args["body"],
            campaign_type=args.get("campaign_type", "b2b"),
            daily_limit=args.get("daily_limit", 50),
            status="draft",
            created_at=datetime.now(timezone.utc),
        )
        db.add(campaign)
        db.flush()

        result = {
            "id": campaign.id,
            "name": campaign.name,
            "status": campaign.status,
            "message": "Campaign created in draft status.",
        }

    return json.dumps(result, indent=2, default=str)


def handle_campaign_status(args: dict) -> str:
    campaign_id = args["campaign_id"]
    with get_db_session() as db:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return json.dumps({"error": f"Campaign {campaign_id} not found"})

        leads = db.query(CampaignLead).filter(CampaignLead.campaign_id == campaign_id).all()
        status_counts = {}
        for lead in leads:
            status_counts[lead.status] = status_counts.get(lead.status, 0) + 1

        result = {
            "campaign_id": campaign.id,
            "name": campaign.name,
            "status": campaign.status,
            "total_leads": len(leads),
            "lead_statuses": status_counts,
        }

    return json.dumps(result, indent=2, default=str)
