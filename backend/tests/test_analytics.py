from datetime import UTC, datetime, timedelta, timezone

from app.services.analytics_service import _as_utc


def test_naive_datetimes_from_sqlite_are_read_as_utc():
    naive = datetime(2026, 10, 1, 12, 0)
    assert _as_utc(naive) == datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def test_aware_datetimes_from_postgres_are_left_alone():
    # Regression: Postgres returns aware values, and comparing them with a naive cutoff
    # crashed the analytics endpoint ("can't compare offset-naive and offset-aware").
    aware = datetime(2026, 10, 1, 15, 0, tzinfo=timezone(timedelta(hours=3)))
    assert _as_utc(aware) is aware
    assert _as_utc(aware) >= datetime.now(UTC) - timedelta(days=36500)


def test_analytics_summary_counts_a_completed_interview(client, auth_headers):
    job = client.post(
        "/api/v1/jobs", headers=auth_headers, json={"title": "Backend", "role_category": "Backend", "seniority": "Senior"}
    ).json()
    candidate = client.post(
        "/api/v1/candidates", headers=auth_headers, json={"job_id": job["id"], "full_name": "Sara", "email": "s@example.com"}
    ).json()
    session = client.post(
        "/api/v1/interviews",
        headers=auth_headers,
        json={"job_id": job["id"], "candidate_id": candidate["id"], "mode": "live"},
    ).json()
    token = auth_headers["Authorization"].removeprefix("Bearer ")
    with client.websocket_connect(f"/api/v1/interviews/{session['id']}/live?token={token}") as ws:
        ws.receive_json()
        ws.receive_bytes()
        ws.send_json({"type": "end"})
        ws.receive_json()

    summary = client.get("/api/v1/analytics/summary", headers=auth_headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()["completed_interviews"] == 1
    assert sum(point["completed"] for point in summary.json()["trend_30d"]) == 1
