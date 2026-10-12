import pytest

from app.services.email_service import EmailService
from app.services.live_interview_service import resolve_language, to_spoken_text


# --- auth -----------------------------------------------------------------------------


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_login_and_me(client, auth_headers):
    me = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me.status_code == 200
    assert me.json()["email"] == "recruiter@example.com"

    login = client.post("/api/v1/auth/login", json={"email": "recruiter@example.com", "password": "s3cret-pass"})
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_wrong_password_is_rejected(client, auth_headers):
    login = client.post("/api/v1/auth/login", json={"email": "recruiter@example.com", "password": "wrong-pass"})
    assert login.status_code == 401


def test_protected_route_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_password_reset_with_otp(client, auth_headers, monkeypatch):
    sent: dict[str, str] = {}
    monkeypatch.setattr(EmailService, "send_otp_email", lambda self, to, code: sent.update(to=to, code=code))

    assert client.post("/api/v1/auth/forgot-password", json={"email": "recruiter@example.com"}).status_code == 200
    assert sent["to"] == "recruiter@example.com"

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"email": "recruiter@example.com", "code": sent["code"], "new_password": "brand-new-pass"},
    )
    assert reset.status_code == 200, reset.text

    login = client.post("/api/v1/auth/login", json={"email": "recruiter@example.com", "password": "brand-new-pass"})
    assert login.status_code == 200


def test_forgot_password_does_not_reveal_unknown_accounts(client):
    response = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert response.status_code == 200


def test_otp_is_logged_when_smtp_is_not_configured(caplog):
    with caplog.at_level("INFO", logger="app.email"):
        EmailService().send_otp_email("dev@example.com", "123456")
    assert "123456" in caplog.text


def test_unconfigured_oauth_providers_are_reported_off(client):
    providers = client.get("/api/v1/auth/oauth/providers").json()
    assert providers == {"apple": False, "github": False, "google": False, "x": False}


# --- jobs, candidates, interviews -----------------------------------------------------


@pytest.fixture()
def candidate(client, auth_headers):
    job = client.post(
        "/api/v1/jobs",
        headers=auth_headers,
        json={"title": "Backend Engineer", "role_category": "Backend", "seniority": "Senior"},
    )
    assert job.status_code == 201, job.text
    created = client.post(
        "/api/v1/candidates",
        headers=auth_headers,
        json={"job_id": job.json()["id"], "full_name": "Sara Candidate", "email": "sara@example.com"},
    )
    assert created.status_code == 201, created.text
    return created.json()


def test_structured_interview_generates_questions(client, auth_headers, candidate):
    response = client.post(
        "/api/v1/interviews",
        headers=auth_headers,
        json={"job_id": candidate["job_id"], "candidate_id": candidate["id"]},
    )
    assert response.status_code == 201, response.text
    assert len(response.json()["questions"]) > 0


def test_other_users_cannot_see_a_session(client, auth_headers, candidate):
    session = client.post(
        "/api/v1/interviews",
        headers=auth_headers,
        json={"job_id": candidate["job_id"], "candidate_id": candidate["id"]},
    ).json()
    other = client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "other-pass1", "full_name": "Other User"},
    ).json()
    response = client.get(
        f"/api/v1/interviews/{session['id']}", headers={"Authorization": f"Bearer {other['access_token']}"}
    )
    assert response.status_code == 404


def test_live_interview_websocket_round_trip(client, auth_headers, candidate):
    session = client.post(
        "/api/v1/interviews",
        headers=auth_headers,
        json={"job_id": candidate["job_id"], "candidate_id": candidate["id"], "mode": "live"},
    ).json()
    token = auth_headers["Authorization"].removeprefix("Bearer ")

    with client.websocket_connect(f"/api/v1/interviews/{session['id']}/live?token={token}&lang=ar-SA") as ws:
        opening = ws.receive_json()
        assert opening["type"] == "ai_text"
        assert "مرحب" in opening["text"]  # greeting already in the handshake language
        ws.receive_bytes()  # TTS audio (empty without a speech provider -> browser speaks it)

        # Periodic webcam snapshot: accepted silently, no reply, doesn't disturb the turn order.
        ws.send_json({"type": "camera_frame", "image": "data:image/jpeg;base64,AAAA"})
        ws.send_json({"type": "camera_frame", "image": "not-an-image"})
        ws.send_json({"type": "user_text", "text": "I built a caching layer with Redis to cut latency."})
        assert ws.receive_json() == {
            "type": "transcript",
            "text": "I built a caching layer with Redis to cut latency.",
        }
        assert ws.receive_json()["type"] == "ai_text"
        ws.receive_bytes()

        ws.send_json({"type": "end"})
        summary = ws.receive_json()
        assert summary["type"] == "summary"
        assert summary["status"] == "completed"

    stored = client.get(f"/api/v1/interviews/{session['id']}", headers=auth_headers).json()
    assert stored["status"] == "completed"
    evaluation = stored["evaluation"]
    assert evaluation is not None
    assert evaluation["score"] == stored["overall_score"]
    assert {"correctness", "depth", "clarity", "terminology", "feedback", "strengths", "improvements"} <= evaluation.keys()
    assert isinstance(evaluation["question_breakdown"], list)
    assert [m["role"] for m in stored["conversation_messages"]] == ["ai", "candidate", "ai"]


def test_live_interview_rejects_bad_token(client, auth_headers, candidate):
    session = client.post(
        "/api/v1/interviews",
        headers=auth_headers,
        json={"job_id": candidate["job_id"], "candidate_id": candidate["id"], "mode": "live"},
    ).json()
    with pytest.raises(Exception):
        with client.websocket_connect(f"/api/v1/interviews/{session['id']}/live?token=garbage") as ws:
            ws.receive_json()


@pytest.mark.parametrize(
    ("tag", "expected"),
    [("ar-SA", ("Arabic", "ar")), ("en-US", ("English", "en")), ("AR", ("Arabic", "ar")), (None, ("English", "en")), ("fr-FR", ("English", "en"))],
)
def test_resolve_language(tag, expected):
    assert resolve_language(tag) == expected


def test_long_spoken_reply_is_trimmed_but_keeps_the_closing_question():
    from app.services.live_interview_service import MAX_SPOKEN_CHARS, limit_spoken_length

    review = (
        "Thanks, I've looked at both functions. The f-string in get_user is a SQL injection risk. "
        + "There is a lot more detail here about parameterized queries and drivers. " * 12
        + "Was skipping the first sample deliberate?"
    )
    spoken = limit_spoken_length(review)
    assert len(spoken) <= MAX_SPOKEN_CHARS
    assert spoken.startswith("Thanks, I've looked at both functions.")
    assert spoken.endswith("Was skipping the first sample deliberate?")
    assert limit_spoken_length("Short and sweet. Any questions?") == "Short and sweet. Any questions?"


def test_spoken_text_drops_markdown_but_keeps_words():
    raw = "بالتأكيد، أقصد مشروع **محددة**.\n- قاعدة البيانات\n- الـ `Redis` *cache*"
    assert to_spoken_text(raw) == "بالتأكيد، أقصد مشروع محددة. قاعدة البيانات الـ Redis cache"
    assert to_spoken_text("p95 = 2 * 60ms") == "p95 = 2 * 60ms"  # arithmetic is not emphasis
