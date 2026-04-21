from datetime import datetime, timedelta

from app.models.campaign import SendLog
from app.models.command_center import OperatorActionLog, OperatorTask
from app.models.monitoring import JobLog, NotificationReadState, SystemAlert


def test_notification_summary_returns_real_operational_items(client, auth_headers, db):
    alert = SystemAlert(
        alert_type="smtp_health_failed",
        severity="critical",
        title="SMTP failed",
        message="SMTP check failed for a mailbox.",
        source="mailbox",
        is_active=True,
        is_acknowledged=False,
    )
    job = JobLog(
        job_id="job-1",
        job_type="campaign_send",
        status="failed",
        error_message="Worker timed out before delivery.",
        created_at=datetime.utcnow(),
    )
    send = SendLog(
        target_email="recipient@example.com",
        subject="Test",
        delivery_status="failed",
        smtp_response="SMTP server timed out.",
        created_at=datetime.utcnow(),
    )
    task = OperatorTask(
        title="Fix provider issue",
        description="Google Workspace OAuth needs reconnect.",
        status="blocked",
        priority="high",
        category="provider",
        updated_at=datetime.utcnow(),
    )
    action = OperatorActionLog(
        action_type="provider_check",
        source="provider",
        result="failed",
        message="Provider check failed without exposing secrets.",
        created_at=datetime.utcnow(),
    )
    db.add_all([alert, job, send, task, action])
    db.commit()

    resp = client.get("/api/v1/notifications/summary", headers=auth_headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["unread_count"] >= 5
    titles = {item["title"] for item in payload["items"]}
    assert "SMTP failed" in titles
    assert "Email send failed" in titles
    assert any("job failed" in title.lower() for title in titles)
    assert all("password" not in item["message"].lower() for item in payload["items"])


def test_notification_read_state_persists(client, auth_headers, db):
    alert = SystemAlert(
        alert_type="deliverability_blocker",
        severity="warning",
        title="Deliverability blocker",
        message="SPF is missing.",
        source="deliverability",
        is_active=True,
        is_acknowledged=False,
        created_at=datetime.utcnow() - timedelta(minutes=2),
    )
    db.add(alert)
    db.commit()

    summary_resp = client.get("/api/v1/notifications/summary", headers=auth_headers)
    assert summary_resp.status_code == 200
    notification = next(item for item in summary_resp.json()["items"] if item["id"] == f"alert:{alert.id}")
    assert notification["read_at"] is None

    read_resp = client.post(f"/api/v1/notifications/{notification['id']}/read", headers=auth_headers)
    assert read_resp.status_code == 200

    second_summary = client.get("/api/v1/notifications/summary", headers=auth_headers).json()
    updated = next(item for item in second_summary["items"] if item["id"] == notification["id"])
    assert updated["read_at"] is not None
    assert db.query(NotificationReadState).filter(NotificationReadState.notification_key == notification["id"]).count() == 1

