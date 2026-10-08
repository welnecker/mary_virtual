from mary2 import conversation_state


def test_mary_move_interpreter_builds_generic_semantic_state(monkeypatch):
    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return (
            '{"speaker":"MARY","move":"provocacao_bem_humorada","target":"interlocutor",'
            '"topic":"um favor","meaning":"Mary brinca sobre o favor recebido.",'
            '"tone":"leve","open_thread":"o interlocutor pode devolver a brincadeira",'
            '"facts_created":[],"decisions_created":[]}'
        )

    monkeypatch.setattr(conversation_state, "chat", fake_chat)

    result = conversation_state.analyze_mary_move(
        api_key="test",
        model="director-test",
        fallback_model=None,
        mary_text="Vai cansar de me ajudar desse jeito? Brincadeira!",
        user_text="Tudo certo por aí?",
        user_understanding={"meaning": "pergunta sobre estado"},
        previous_conversation_state={},
        active_interlocutor="papel=PERSONAGEM_DA_CENA",
    )

    assert result["speaker"] == "MARY"
    assert result["move"] == "provocacao_bem_humorada"
    assert result["topic"] == "um favor"
    assert result["facts_created"] == []
    assert result["decisions_created"] == []
    payload = captured["messages"][1]["content"]
    assert "Interprete SOMENTE o movimento conversacional" in payload
    assert "não viram automaticamente fatos ou decisões" in payload


def test_mary_move_parse_failure_preserves_literal_meaning(monkeypatch):
    calls = []

    def fake_chat(**kwargs):
        calls.append(kwargs)
        return "{invalid"

    monkeypatch.setattr(conversation_state, "chat", fake_chat)

    result = conversation_state.analyze_mary_move(
        api_key="test",
        model="director-test",
        fallback_model=None,
        mary_text="Tudo bem, eu aceito.",
        user_text="Você aceita?",
    )

    assert len(calls) == 2
    assert result["speaker"] == "MARY"
    assert result["meaning"] == "Tudo bem, eu aceito."
    assert result["_parse_error"]
