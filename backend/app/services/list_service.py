from __future__ import annotations

from collections import Counter
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.campaign import Campaign, CampaignLead, Contact
from app.models.lists import CampaignList, LeadList, LeadListMember
from app.services.verification_service import contact_is_reachable


class LeadListService:
    def __init__(self, db: Session):
        self.db = db

    def get_list_or_404(self, list_id: str) -> LeadList:
        lead_list = self.db.query(LeadList).filter(LeadList.id == list_id).first()
        if not lead_list:
            raise ValueError("List not found")
        return lead_list

    def validate_list_name(self, name: str, *, current_list_id: str | None = None) -> str:
        normalized = name.strip()
        if len(normalized) < 2:
            raise ValueError("List name must be at least 2 characters long.")
        existing = self.db.query(LeadList).filter(LeadList.name == normalized).first()
        if existing and str(existing.id) != current_list_id:
            raise ValueError("A list with this name already exists.")
        return normalized

    def summarize_contact_collection(self, contacts: list[Contact]) -> dict:
        counts = Counter(contact.email_status or "unverified" for contact in contacts)
        unique_ids = {str(contact.id) for contact in contacts}
        reachable = sum(1 for contact in contacts if contact_is_reachable(contact))
        risky = sum(1 for contact in contacts if (contact.email_status or "unverified") == "risky")
        invalid = sum(1 for contact in contacts if (contact.email_status or "unverified") not in {"valid", "risky"})
        suppressed = sum(1 for contact in contacts if contact.is_suppressed or (contact.email_status or "unverified") == "suppressed")
        return {
            "lead_count": len(unique_ids),
            "reachable_count": reachable,
            "risky_count": risky,
            "invalid_count": invalid,
            "suppressed_count": suppressed,
            "status_counts": dict(counts),
        }

    def summarize_list(self, lead_list: LeadList) -> dict:
        contacts = [member.lead for member in lead_list.members]
        summary = self.summarize_contact_collection(contacts)
        return {
            "id": str(lead_list.id),
            "name": lead_list.name,
            "description": lead_list.description,
            "type": lead_list.type,
            "filter_definition": lead_list.filter_definition,
            "created_at": lead_list.created_at.isoformat() if lead_list.created_at else None,
            "updated_at": lead_list.updated_at.isoformat() if lead_list.updated_at else None,
            **summary,
        }

    def summarize_campaign_lists(self, campaign_id: str) -> dict:
        campaign_lists = (
            self.db.query(CampaignList)
            .filter(CampaignList.campaign_id == campaign_id)
            .all()
        )
        list_payloads = []
        deduped: dict[str, Contact] = {}
        for campaign_list in campaign_lists:
            contacts = [member.lead for member in campaign_list.lead_list.members]
            for contact in contacts:
                deduped[str(contact.id)] = contact
            list_payloads.append(self.summarize_list(campaign_list.lead_list))
        aggregate = self.summarize_contact_collection(list(deduped.values()))
        aggregate["lists"] = list_payloads
        return aggregate

    def sync_campaign_leads(self, campaign_id: str) -> dict:
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise ValueError("Campaign not found")

        attached_lists = self.db.query(CampaignList).filter(CampaignList.campaign_id == campaign.id).all()
        deduped_contacts: dict[str, Contact] = {}
        for attached in attached_lists:
            for member in attached.lead_list.members:
                deduped_contacts[str(member.lead.id)] = member.lead

        existing_leads = self.db.query(CampaignLead).filter(CampaignLead.campaign_id == campaign.id).all()
        existing_by_contact = {str(lead.contact_id): lead for lead in existing_leads}
        target_contact_ids = set(deduped_contacts.keys())

        for contact_id, lead in existing_by_contact.items():
            if contact_id not in target_contact_ids and lead.status == "scheduled":
                self.db.delete(lead)

        for contact_id in target_contact_ids:
            if contact_id in existing_by_contact:
                continue
            self.db.add(
                CampaignLead(
                    campaign_id=campaign.id,
                    contact_id=UUID(contact_id),
                    status="scheduled",
                )
            )

        self.db.commit()
        return self.summarize_campaign_lists(str(campaign.id))
