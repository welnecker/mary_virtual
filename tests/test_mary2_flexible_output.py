from mary2.output_filter import parse_mary_components, parse_mary_response


def test_flexible_components_keep_action_speech_and_thought_separate():
    raw = (
        "[AÇÃO] Mary pega a bolsa e sai do quarto.\n"
        "[FALA] Volto depois.\n"
        "[PENSAMENTO] Estou com medo, mas ja decidi."
    )
    assert parse_mary_components(raw) == {
        "action": "Mary pega a bolsa e sai do quarto.",
        "speech": "Volto depois.",
        "thought": "Estou com medo, mas ja decidi.",
    }


def test_flexible_action_only_does_not_invent_speech_or_thought():
    parts = parse_mary_components("[AÇÃO] Mary atravessa a porta.")
    assert parts["action"] == "Mary atravessa a porta."
    assert parts["speech"] == ""
    assert parts["thought"] == ""


def test_flexible_speech_only_does_not_invent_thought():
    parts = parse_mary_components("[FALA] Ja volto.")
    assert parts["speech"] == "Ja volto."
    assert parts["action"] == ""
    assert parts["thought"] == ""


def test_flexible_legacy_speech_still_supported():
    assert parse_mary_components("Oi, tudo bem?")["speech"] == "Oi, tudo bem?"
    assert parse_mary_response("[FALA] Oi. [PENSAMENTO] Tudo certo.") == (
        "Tudo certo.", "Oi."
    )


def test_flexible_repeated_components_preserve_sequence():
    parts = parse_mary_components(
        "[AÇÃO] Ela se levanta. [FALA] Ja vou. [AÇÃO] Ela sai."
    )
    assert parts["action"] == "Ela se levanta.\nEla sai."
    assert parts["speech"] == "Ja vou."
