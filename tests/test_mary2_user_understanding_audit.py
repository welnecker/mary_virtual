from mary2 import user_understanding_audit as understanding


def test_understanding_uses_fourteen_recent_messages(monkeypatch):
    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return (
            '{"meaning":"entendi","reference":"","obligation":"","relevant_facts":[],'
            '"conflict":"","reaction":"responder naturalmente"}'
        )

    monkeypatch.setattr(understanding, "chat", fake_chat)
    recent = [
        {"role": "user" if index % 2 == 0 else "assistant", "content": f"m{index}"}
        for index in range(20)
    ]

    result = understanding.analyze_user_understanding(
        api_key="test",
        model="director-test",
        fallback_model=None,
        user_text="fala atual",
        recent_messages=recent,
    )

    payload = captured["messages"][1]["content"]
    assert "m5" not in payload
    assert "m6" in payload
    assert "m19" in payload
    assert result["user_meaning"] == "entendi"
    assert result["fallback_used"] is False


def test_double_invalid_json_never_returns_empty_understanding(monkeypatch):
    calls = []

    def fake_chat(**kwargs):
        calls.append(kwargs)
        return '{"meaning":"Eu disse agorinha onde moro'

    monkeypatch.setattr(understanding, "chat", fake_chat)

    result = understanding.analyze_user_understanding(
        api_key="test",
        model="director-test",
        fallback_model=None,
        user_text="Eu disse agorinha onde moro. Você consegue recuperar a memória?",
        recent_messages=[],
    )

    assert len(calls) == 2
    assert result["fallback_used"] is True
    assert result["parse_error"]
    assert result["user_meaning"] == (
        "Eu disse agorinha onde moro. Você consegue recuperar a memória?"
    )
    assert result["user_obligation"]["exists"] is True
    assert result["user_obligation"]["requirement"]
    assert result["expected_mary_reaction"]


def test_understanding_contract_is_compact_and_rejects_error_excuses_as_character(monkeypatch):
    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return (
            '{"meaning":"corrige um erro anterior","reference":"fala anterior de Mary",'
            '"obligation":"esclarecer o erro","relevant_facts":[],'
            '"conflict":"","reaction":"corrigir de forma factual"}'
        )

    monkeypatch.setattr(understanding, "chat", fake_chat)

    understanding.analyze_user_understanding(
        api_key="test",
        model="director-test",
        fallback_model=None,
        user_text="Você está confusa.",
        previous_mary_text="Minha cabeça voou.",
    )

    payload = captured["messages"][1]["content"]
    assert '"meaning"' in payload
    assert '"obligation"' in payload
    assert '"reaction"' in payload
    assert "literal_meaning, reference, intent" not in payload
    assert "não são traços psicológicos autoritativos" in payload
    assert captured["max_tokens"] == 520


def test_relevant_facts_must_be_literal_user_excerpts(monkeypatch):
    def fake_chat(**kwargs):
        return (
            '{"meaning":"informa residência","reference":"","obligation":"",'
            '"relevant_facts":["moro em Camburi","ele também mora em Camburi"],'
            '"conflict":"","reaction":"reconhecer o fato"}'
        )

    monkeypatch.setattr(understanding, "chat", fake_chat)

    result = understanding.analyze_user_understanding(
        api_key="test",
        model="director-test",
        fallback_model=None,
        user_text="Eu moro em Camburi também.",
        recent_user_facts=["meu carro é preto"],
    )

    assert result["relevant_facts"] == ["moro em Camburi"]
    assert result["recent_user_facts"] == ["meu carro é preto", "moro em Camburi"]
    assert "ele também mora em Camburi" not in result["recent_user_facts"]
