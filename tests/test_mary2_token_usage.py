"""Token accounting is passive and never estimates unavailable provider billing."""
from mary2.token_usage import (
    begin_turn, classify_call, make_usage_event, record, update_line_order
)


def test_openrouter_usage_fields_and_stage_are_preserved():
    captured = []
    begin_turn(sink=captured.append, run_id="run-example", seq=7,
               chapter_id="sheet:DeckPiscina1", line_order=15)
    update_line_order(14)
    event = make_usage_event(
        model="google/gemini-3-flash-preview", call_type="REDACTOR",
        attempt=1, duration_ms=1234.12, status="SUCCESS", http_status=200,
        request_messages=[{"role": "user", "content": "Olá"}],
        response={
            "model": "google/gemini-3-flash-preview",
            "usage": {
                "prompt_tokens": 1400, "completion_tokens": 175,
                "total_tokens": 1575, "cost": 0.001225,
                "prompt_tokens_details": {"cached_tokens": 100},
                "completion_tokens_details": {"reasoning_tokens": 70},
            },
        },
    )
    record(event)
    assert len(captured) == 1
    assert event["run_id"] == "run-example"
    assert event["seq"] == 7
    assert event["line_order"] == 14
    assert event["prompt_tokens"] == 1400
    assert event["completion_tokens"] == 175
    assert event["reasoning_tokens"] == 70
    assert event["cached_tokens"] == 100
    assert event["cost_usd"] == 0.001225
    assert event["duration_ms"] == 1234.1
    assert event["request_chars"] == 3
    assert event["event_id"]


def test_missing_usage_is_unknown_not_zero():
    event = make_usage_event(
        model="x", call_type="INPUT_ROUTER", attempt=2, duration_ms=10.0,
        status="HTTP_ERROR", http_status=429,
        request_messages=[{"role": "user", "content": "test"}], response={},
        error_code="HTTP_ERROR",
    )
    for field in ("prompt_tokens", "completion_tokens", "total_tokens",
                  "reasoning_tokens", "cached_tokens", "cost_usd"):
        assert event[field] == ""
    assert event["http_status"] == 429
    assert event["attempt"] == 2


def test_call_classification_and_explicit_override():
    assert classify_call("/app/mary2/input_router.py") == "INPUT_ROUTER"
    assert classify_call("/app/mary2/direct_semantic_director.py") == "SEMANTIC_DIRECTOR"
    assert classify_call("/app/mary2/app.py", call_type="EMOTION_CLASSIFIER") == "EMOTION_CLASSIFIER"
