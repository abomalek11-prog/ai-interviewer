from app.services.live_interview_service import LiveInterviewService, _as_breakdown, _as_string_list


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
