from app.models.core import Domain, Mailbox
from app.workers.imap_sync_worker import sync_all_inboxes


def test_imap_sync_skips_disabled_mailboxes(db, monkeypatch):
    synced_mailboxes: list[str] = []

    verified_domain = Domain(name="verified-workers.example.com", mailcow_status="verified")
    local_only_domain = Domain(name="local-workers.example.com", mailcow_status="local_only")
    db.add_all([verified_domain, local_only_domain])
    db.flush()

    db.add_all(
        [
            Mailbox(
                domain_id=verified_domain.id,
                email="verified@verified-workers.example.com",
                display_name="Verified",
                smtp_host="smtp.example.com",
                smtp_port=587,
                smtp_username="verified@verified-workers.example.com",
                smtp_password_encrypted="encrypted",
                imap_host="imap.example.com",
                imap_port=993,
                imap_username="verified@verified-workers.example.com",
                imap_password_encrypted="encrypted",
            ),
            Mailbox(
                domain_id=local_only_domain.id,
                email="local@local-workers.example.com",
                display_name="Local",
                smtp_host="smtp.example.com",
                smtp_port=587,
                smtp_username="local@local-workers.example.com",
                smtp_password_encrypted="encrypted",
                imap_host="imap.example.com",
                imap_port=993,
                imap_username="local@local-workers.example.com",
                imap_password_encrypted="encrypted",
                inbox_sync_enabled=False,
            ),
        ]
    )
    db.commit()

    monkeypatch.setattr(
        "app.workers.imap_sync_worker.IMAPSyncManager.sync_mailbox",
        lambda self, mailbox_id: synced_mailboxes.append(str(mailbox_id)),
    )
    monkeypatch.setattr("app.workers.imap_sync_worker.SessionLocal", lambda: db)

    sync_all_inboxes()

    assert len(synced_mailboxes) == 1
