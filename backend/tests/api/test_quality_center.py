from app.models.campaign import Campaign
from app.models.command_center import OperatorActionLog
from app.models.monitoring import QualityCheckRun


def test_quality_center_summary_returns_real_checks(client, auth_headers):
    resp = client.get("/api/v1/quality-center/summary", headers=auth_headers)

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["overall_status"] in {"ready", "warning", "blocked", "unknown"}
    assert payload["runtime_checks"]
    assert payload["integrity_checks"]
    assert "recommended_next_fixes" in payload


def test_quality_center_smoke_run_persists_results_and_logs_action(client, auth_headers, db):
    resp = client.post("/api/v1/quality-center/runs/smoke", headers=auth_headers)

    assert resp.status_code == 200
    run = resp.json()
    assert run["run_type"] == "smoke"
    assert run["status"] in {"passed", "warning", "failed", "blocked", "skipped", "unknown"}
    assert run["results"]

    persisted = db.query(QualityCheckRun).filter(QualityCheckRun.id == run["id"]).first()
    assert persisted is not None
    assert persisted.results

    action = (
        db.query(OperatorActionLog)
        .filter(OperatorActionLog.action_type == "quality_smoke_run")
        .order_by(OperatorActionLog.created_at.desc())
        .first()
    )
    assert action is not None
    assert action.source == "quality_center"
    assert "password" not in (action.message or "").lower()


def test_quality_center_integrity_detects_active_campaign_without_mailbox(client, auth_headers, db):
    campaign = Campaign(
        name="Broken campaign",
        status="active",
        mailbox_id=None,
        template_subject="Hello",
        template_body="Body",
    )
    db.add(campaign)
    db.commit()

    resp = client.get("/api/v1/quality-center/checks", headers=auth_headers)

    assert resp.status_code == 200
    checks = resp.json()
    assert any(
        check["name"] == "Campaign mailbox linkage"
        and check["status"] in {"failed", "blocked"}
        and check["entity_id"] == str(campaign.id)
        for check in checks
    )

