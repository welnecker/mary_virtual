from mary2 import user_understanding_audit as understanding


def _response(**overrides):
    base = {
        "relation_to_previous": "",
        "move": "",
        "meaning": "entendi",
        "reference": "",
        "obligation": "",
        "state_changes": [],
        "conflict": "",
        "reaction": "responder naturalmente",
    }
    base.update(overrides)
    import json
    return json.dumps(base, ensure_ascii=False)


def test_understanding_uses_fourteen_recent_messages(monkeypatch):
    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return _response()

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


def test_understanding_consumes_interpreted_previous_move(monkeypatch):
    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return _response(
            relation_to_previous="devolve a provocação anterior",
            move="provocação de volta seguida de continuação da ação",
        )

    monkeypatch.setattr(understanding, "chat", fake_chat)

    result = understanding.analyze_user_understanding(
        api_key="test",
        model="director-test",
        fallback_model=None,
        user_text="Tudo bem, então vamos.",
        previous_conversation_state={
            "speaker": "MARY",
            "move": "provocacao_bem_humorada",
            "topic": "um favor",
            "meaning": "Mary brincou sobre o favor.",
            "open_thread": "o interlocutor pode devolver a brincadeira",
        },
    )

    payload = captured["messages"][1]["content"]
    assert "ESTADO CONVERSACIONAL ANTERIOR" in payload
    assert "provocacao_bem_humorada" in payload
    assert "use-o para determinar COMO a fala atual do usuário se relaciona" in payload
    assert result["relation_to_previous"] == "devolve a provocação anterior"
    assert result["move"] == "provocação de volta seguida de continuação da ação"


def test_questions_and_banter_are_not_promoted_to_persistent_facts(monkeypatch):
    def fake_chat(**kwargs):
        return _response(
            meaning="o usuário brinca e faz uma pergunta",
            state_changes=[],
        )

    monkeypatch.setattr(understanding, "chat", fake_chat)

    result = understanding.analyze_user_understanding(
        api_key="test",
        model="director-test",
        fallback_model=None,
        user_text="Vai me abandonar aqui? rs",
        recent_user_facts=["fato anterior válido"],
    )

    assert result["state_changes"] == []
    assert result["relevant_facts"] == []
    assert result["recent_user_facts"] == ["fato anterior válido"]


def test_explicit_state_change_is_returned_but_not_auto_promoted(monkeypatch):
    def fake_chat(**kwargs):
        return _response(
            meaning="o usuário informa onde mora",
            state_changes=["O usuário mora em Camburi"],
        )

    monkeypatch.setattr(understanding, "chat", fake_chat)

    result = understanding.analyze_user_understanding(
        api_key="test",
        model="director-test",
        fallback_model=None,
        user_text="Eu moro em Camburi.",
        recent_user_facts=["fato anterior válido"],
    )

    assert result["state_changes"] == ["O usuário mora em Camburi"]
    assert result["recent_user_facts"] == ["fato anterior válido"]


def test_understanding_receives_scene_direction_and_dialogue_without_collapsing_them(monkeypatch):
    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return _response(
            meaning="O personal informa que sai em 10 minutos e reage com uma risada curta.",
            state_changes=["O personal sai em 10 minutos"],
        )

    monkeypatch.setattr(understanding, "chat", fake_chat)

    result = understanding.analyze_user_understanding(
        api_key="test",
        model="director-test",
        fallback_model=None,
        user_text="Ha!",
        user_scene_direction="Eu saio em 10 minutos... só preciso organizar os pesos para o próximo turno...",
        recent_messages=[],
    )

    payload = captured["messages"][1]["content"]
    assert "DIREÇÃO/ENCENAÇÃO ATUAL DO USUÁRIO" in payload
    assert "Eu saio em 10 minutos" in payload
    assert "FALA VERBAL ATUAL DO USUÁRIO" in payload
    assert "Ha!" in payload
    assert result["state_changes"] == ["O personal sai em 10 minutos"]
