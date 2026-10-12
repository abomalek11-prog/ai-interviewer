from types import SimpleNamespace

from app.services.live_interview_service import (
    MAX_CAMERA_FRAMES,
    LiveInterviewService,
    _as_breakdown,
    _as_string_list,
)


def _service_without_db() -> LiveInterviewService:
    session = SimpleNamespace(ai_model_profile_id=None)
    return LiveInterviewService(db=None, session=session, language_tag="en-US")


def test_camera_frames_stay_bounded_and_spread_over_the_interview():
    service = _service_without_db()
    for i in range(30):  # a 15-minute interview at one snapshot every 30s
        service.add_camera_frame(f"data:image/jpeg;base64,{i}")
    kept = [int(frame.rsplit(",", 1)[1]) for frame in service.camera_frames]
    assert len(kept) <= MAX_CAMERA_FRAMES
    assert kept[0] == 0  # the start of the interview is still represented
    assert kept[-1] >= 16  # ...and so is the second half, not just the opening minutes
    assert kept == sorted(kept)


def test_camera_frames_reject_anything_but_image_data_urls():
    service = _service_without_db()
    service.add_camera_frame("https://example.com/tracker.png")
    service.add_camera_frame("javascript:alert(1)")
    assert service.camera_frames == []


def test_presence_analysis_is_normalized(monkeypatch):
    service = _service_without_db()
    service.add_camera_frame("data:image/jpeg;base64,AAAA")
    seen = {}

    def fake_analyze(system_prompt, user_prompt, images):
        seen.update(system=system_prompt, images=images)
        return {"summary": " Mostly looking at the screen. ", "observations": "- Upright posture\n- Good lighting", "flags": []}

    monkeypatch.setattr(service.ai_service, "analyze_images_json", fake_analyze)
    presence = service._analyze_presence()

    assert presence == {
        "summary": "Mostly looking at the screen.",
        "observations": ["Upright posture", "Good lighting"],
        "flags": [],
        "frames_analyzed": 1,
    }
    # Guardrails are part of the request, not an afterthought.
    assert "do not infer emotions" in seen["system"]
    assert "ethnicity" in seen["system"]


def test_no_presence_section_without_snapshots_or_a_vision_model(monkeypatch):
    service = _service_without_db()
    assert service._analyze_presence() is None  # camera never sent anything
    service.add_camera_frame("data:image/jpeg;base64,AAAA")
    monkeypatch.setattr(service.ai_service, "analyze_images_json", lambda *a: None)
    assert service._analyze_presence() is None  # nothing invented when no model could look


def test_string_list_passes_lists_through():
    assert _as_string_list(["Clear metrics", "  ", "Knows trade-offs"]) == ["Clear metrics", "Knows trade-offs"]


def test_string_list_splits_a_single_string_on_lines_and_bullets():
    assert _as_string_list("- Uses profiling\n- Measures p95\n") == ["Uses profiling", "Measures p95"]
    assert _as_string_list("تحديد دقيق للمشكلة؛ قياس التحسن") == ["تحديد دقيق للمشكلة", "قياس التحسن"]


def test_string_list_keeps_an_unseparated_string_whole():
    # Splitting on commas would cut sentences apart; one long item is the safer failure.
    assert _as_string_list("Good metrics, clear trade-offs") == ["Good metrics, clear trade-offs"]


def test_string_list_ignores_garbage():
    assert _as_string_list(None) == []
    assert _as_string_list(42) == []


def test_breakdown_normalizes_items():
    raw = [
        {"topic": "Caching", "score": "82", "comment": "Solid TTL reasoning."},
        {"question": "Scaling", "score": 140, "feedback": "Very strong."},
        {"score": 50},  # nothing to show
        "not an object",
    ]
    assert _as_breakdown(raw) == [
        {"topic": "Caching", "score": 82, "comment": "Solid TTL reasoning."},
        {"topic": "Scaling", "score": 100, "comment": "Very strong."},
    ]
    assert _as_breakdown("oops") == []


def test_build_evaluation_from_the_shape_nemotron_actually_returned():
    # Captured from a real run: list fields came back as plain strings.
    result = {
        "score": 65, "correctness": 90, "depth": 70, "clarity": 90, "terminology": "85",
        "feedback": "قدمت المرشحة مثالاً تقنياً قوياً.",
        "strengths": "تحديد دقيق للمشكلة\nقياس التحسن كمياً",
        "improvements": "الاستعداد لمناقشة تفاصيل التنفيذ",
    }
    evaluation = LiveInterviewService._build_evaluation(result, 78)

    assert evaluation.score == 78
    assert evaluation.terminology == 85
    assert evaluation.strengths == ["تحديد دقيق للمشكلة", "قياس التحسن كمياً"]
    assert evaluation.improvements == ["الاستعداد لمناقشة تفاصيل التنفيذ"]
    assert evaluation.question_breakdown == []


def test_no_evaluation_without_a_score():
    assert LiveInterviewService._build_evaluation({"correctness": 50}, None) is None
    assert LiveInterviewService._build_evaluation(["not", "a", "dict"], 50) is None
