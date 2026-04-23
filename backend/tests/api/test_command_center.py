from datetime import date, datetime, timedelta, timezone

from app.models.command_center import OperatorActionLog


def test_command_center_task_note_runbook_flow(client, auth_headers):
    task_resp = client.post(
        "/api/v1/command-center/tasks",
        headers=auth_headers,
        json={
            "title": "Test campaign execution",
            "description": "Run dry-run before sending.",
            "priority": "high",
            "category": "campaign",
            "due_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        },
    )
    assert task_resp.status_code == 200
    task = task_resp.json()
    assert task["title"] == "Test campaign execution"
    assert task["status"] == "todo"
    assert task["priority"] == "high"

    patch_resp = client.patch(
        f"/api/v1/command-center/tasks/{task['id']}",
        headers=auth_headers,
        json={"status": "in_progress"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "in_progress"

    note_resp = client.post(
        "/api/v1/command-center/daily-notes",
        headers=auth_headers,
        json={"note_date": date.today().isoformat(), "content": "Inbox sync tested."},
    )
    assert note_resp.status_code == 200
    assert note_resp.json()["content"] == "Inbox sync tested."

    runbook_resp = client.post(
        "/api/v1/command-center/runbooks",
        headers=auth_headers,
        json={
            "name": "Campaign launch checklist",
            "category": "campaign",
            "steps": [
                {"step_order": 1, "title": "Run dry-run"},
                {"step_order": 2, "title": "Check deliverability"},
            ],
        },
    )
    assert runbook_resp.status_code == 200
    runbook = runbook_resp.json()
    assert len(runbook["steps"]) == 2

    start_resp = client.post(f"/api/v1/command-center/runbooks/{runbook['id']}/start", headers=auth_headers)
    assert start_resp.status_code == 200
    started_tasks = start_resp.json()
    assert [item["title"] for item in started_tasks] == ["Run dry-run", "Check deliverability"]

    summary_resp = client.get("/api/v1/command-center/summary", headers=auth_headers)
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["stats"]["in_progress"] >= 1
    assert summary["recent_actions"]


def test_command_center_rejects_invalid_task_state(client, auth_headers):
    resp = client.post(
        "/api/v1/command-center/tasks",
        headers=auth_headers,
        json={"title": "Bad task", "status": "later", "priority": "normal", "category": "manual"},
    )
    assert resp.status_code == 422


def test_command_center_action_metadata_is_sanitized(client, auth_headers, db):
    resp = client.post(
        "/api/v1/command-center/tasks",
        headers=auth_headers,
        json={
            "title": "Secret safety check",
            "metadata": {
                "token": "should-not-persist",
                "smtp_password": "should-not-persist",
                "safe_value": "visible",
            },
        },
    )
    assert resp.status_code == 200

    action = db.query(OperatorActionLog).filter(OperatorActionLog.action_type == "task_created").order_by(OperatorActionLog.created_at.desc()).first()
    assert action is not None
    assert action.metadata_blob["safe_value"] == "visible"
    assert "token" not in action.metadata_blob
    assert "smtp_password" not in action.metadata_blob
