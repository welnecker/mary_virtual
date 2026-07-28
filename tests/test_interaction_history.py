from persistence.interaction_history import has_real_error


def test_false_like_sheet_values_are_not_errors() -> None:
    for value in (None, "", False, "FALSE", "false", "0", "não", "NAO", "ok", "success"):
        assert has_real_error(value) is False


def test_real_error_text_is_detected() -> None:
    assert has_real_error("OpenRouter timeout") is True
    assert has_real_error(True) is True
