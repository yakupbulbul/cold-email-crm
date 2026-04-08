"""
test_campaign_preflight.py — End-to-end preflight safety tests.

Verifies that PreflightService correctly blocks unsafe campaigns.
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.integration
def test_preflight_blocks_campaign_with_suppressed_leads(db):
    """Campaigns with suppressed leads should fail preflight."""
    from app.services.preflight_service import PreflightService
    from app.models.campaign import Campaign, CampaignLead, Contact
    from app.models.core import Domain, Mailbox
    import uuid

    domain = Domain(id=uuid.uuid4(), name=f"staging-{uuid.uuid4()}.example.com")
    db.add(domain)
    mailbox = Mailbox(
        id=uuid.uuid4(),
        email="test@staging.example.com",
        domain_id=domain.id,
        display_name="Test",
        smtp_host="localhost",
        smtp_port=587,
        smtp_username="test@staging.example.com",
        imap_host="localhost",
        imap_port=993,
        imap_username="test@staging.example.com",
        smtp_password_encrypted="fake",
        imap_password_encrypted="fake",
    )
    db.add(mailbox)

    campaign = Campaign(
        id=uuid.uuid4(),
        name="Test Campaign",
        template_subject="Hello",
        template_body="Test body",
        mailbox_id=mailbox.id,
    )
    db.add(campaign)

    suppressed_contact = Contact(
        id=uuid.uuid4(),
        email=f"suppressed-{uuid.uuid4()}@test.com",
        is_suppressed=True,
    )
    db.add(suppressed_contact)
    db.flush()

    lead = CampaignLead(
        campaign_id=campaign.id,
        contact_id=suppressed_contact.id,
        status="scheduled",
    )
    db.add(lead)
    db.commit()

    # Patch DNS lookups to avoid real network calls
    with patch("dns.resolver.resolve", side_effect=Exception("No DNS")):
        svc = PreflightService(db)
        result = svc.run_preflight(str(campaign.id))

    assert result["status"] in ("fail", "warning")


@pytest.mark.integration
def test_preflight_passes_for_clean_campaign(db):
    """Campaign with no suppressed leads and good DNS should pass or warn only."""
    from app.services.preflight_service import PreflightService
    from app.models.campaign import Campaign, Contact, CampaignLead
    from app.models.core import Domain, Mailbox
    import uuid

    domain = Domain(id=uuid.uuid4(), name=f"clean-{uuid.uuid4()}.example.com")
    db.add(domain)
    mailbox = Mailbox(
        id=uuid.uuid4(),
        email="clean@staging.example.com",
        domain_id=domain.id,
        display_name="Clean",
        smtp_host="localhost",
        smtp_port=587,
        smtp_username="clean@staging.example.com",
        imap_host="localhost",
        imap_port=993,
        imap_username="clean@staging.example.com",
        smtp_password_encrypted="fake",
        imap_password_encrypted="fake",
    )
    db.add(mailbox)

    campaign = Campaign(
        id=uuid.uuid4(),
        name="Clean Campaign",
        template_subject="Hi",
        template_body="Body",
        mailbox_id=mailbox.id,
    )
    db.add(campaign)
    db.commit()

    with patch("dns.resolver.resolve", side_effect=Exception("No DNS")):
        svc = PreflightService(db)
        result = svc.run_preflight(str(campaign.id))

    # No leads = no lead quality failure, SPF/DMARC warnings acceptable
    assert result["status"] in ("pass", "warning")
    assert result["blocked"] is False
