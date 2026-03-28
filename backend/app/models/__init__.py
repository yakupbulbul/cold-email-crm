from .base import Base
from .core import Domain, Mailbox
from .warmup import WarmupPair, WarmupEvent
from .campaign import Contact, Campaign, CampaignLead, SendLog
from .email import Thread, Message, AiSummary

# Expose all models for Alembic environment mapping
__all__ = [
    "Base",
    "Domain",
    "Mailbox",
    "WarmupPair",
    "WarmupEvent",
    "Contact",
    "Campaign",
    "CampaignLead",
    "SendLog",
    "Thread",
    "Message",
    "AiSummary"
]
