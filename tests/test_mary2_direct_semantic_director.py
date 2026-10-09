from mary2 import direct_semantic_director as director


def _row():
    return {
        "speech_guide": "Pergunte onde ele mora.",
        "permanent_memory": "Mary é casada com Janio.",
        "physical_memory": "",
        "instant_memory": "O interlocutor ativo é o personal.",
        "initial_description": "Mary está conversando com o personal.",
    }


def _interpretation():
    return {
        "user_obligation": {"exists": False, "requirement": ""},
        "user_meaning": "O usuário informou onde mora.",
    }


def test_evidence_source_is_derived_from_real_user_dialogue(monkeypatch):
    def fake_chat(**kwargs):
        return (
            '{"obrigacao_usuario":{"existe":false,"requisito":"","atendida":true,"evidencia":""},'
            '"objetivos_guia":[{"objetivo":"descobrir onde mora","alcancado":true,'
            '"fonte":"FALA-GUIA ORIGINAL","evidencia":"Eu moro em Camburi."}],'
            '"contradicao_dura":{"existe":false,"fato_autoritativo":"","trecho_mary":"","correcao":""},'
            '"cumpriu":true,"faltou":"","motivo":""}'
        )

    monkeypatch.setattr(director, "chat", fake_chat)

    result = director.validate_direct_semantic_turn(
        api_key="test",
        model="director-test",
        fallback_model=None,
        row=_row(),
        interpretation=_interpretation(),
        mary_text="Ah, então somos quase vizinhos.",
        user_text="Eu moro em Camburi.",
        line_dialogue=[],
    )

    assert result["fulfilled"] is True
    assert result["elements"][0]["source"] == "USUÁRIO"
    assert result["elements"][0]["claimed_source"] == "FALA-GUIA ORIGINAL"
    assert result["elements"][0]["evidence"] == "Eu moro em Camburi."
    assert result["invalid_guide_evidence"] is False


def test_evidence_source_prefers_first_real_occurrence(monkeypatch):
    def fake_chat(**kwargs):
        return (
            '{"obrigacao_usuario":{"existe":false,"requisito":"","atendida":true,"evidencia":""},'
            '"objetivos_guia":[{"objetivo":"descobrir onde mora","alcancado":true,'
            '"fonte":"MARY","evidencia":"moro em Camburi"}],'
            '"contradicao_dura":{"existe":false,"fato_autoritativo":"","trecho_mary":"","correcao":""},'
            '"cumpriu":true,"faltou":"","motivo":""}'
        )

    monkeypatch.setattr(director, "chat", fake_chat)

    result = director.validate_direct_semantic_turn(
        api_key="test",
        model="director-test",
        fallback_model=None,
        row=_row(),
        interpretation=_interpretation(),
        mary_text="Você disse que mora em Camburi.",
        user_text="",
        line_dialogue=[
            {"role": "user", "content": "Eu moro em Camburi"},
            {"role": "assistant", "content": "Você mora em Camburi?"},
        ],
    )

    assert result["elements"][0]["source"] == "USUÁRIO"


def test_director_prompt_treats_identity_and_role_as_hard_facts(monkeypatch):
    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return (
            '{"obrigacao_usuario":{"existe":false,"requisito":"","atendida":true,"evidencia":""},'
            '"objetivos_guia":[{"objetivo":"perguntar onde mora","alcancado":false,"fonte":"","evidencia":""}],'
            '"contradicao_dura":{"existe":false,"fato_autoritativo":"","trecho_mary":"","correcao":""},'
            '"cumpriu":false,"faltou":"perguntar onde mora","motivo":""}'
        )

    monkeypatch.setattr(director, "chat", fake_chat)

    director.validate_direct_semantic_turn(
        api_key="test",
        model="director-test",
        fallback_model=None,
        row=_row(),
        interpretation=_interpretation(),
        mary_text="O personal sou eu.",
        user_text="Você é o personal?",
        line_dialogue=[],
    )

    payload = captured["messages"][1]["content"]
    assert "troca de identidade, papel, profissão, função" in payload
    assert "Pronomes e possessivos da FALA-GUIA são lidos da perspectiva de Mary" in payload


def test_grounded_recent_user_fact_can_fulfill_future_line(monkeypatch):
    def fake_chat(**kwargs):
        return (
            '{"obrigacao_usuario":{"existe":false,"requisito":"","atendida":true,"evidencia":""},'
            '"objetivos_guia":[{"objetivo":"descobrir onde mora","alcancado":true,'
            '"fonte":"MARY","evidencia":"moro em Camburi"}],'
            '"contradicao_dura":{"existe":false,"fato_autoritativo":"","trecho_mary":"","correcao":""},'
            '"cumpriu":true,"faltou":"","motivo":""}'
        )

    monkeypatch.setattr(director, "chat", fake_chat)

    interpretation = _interpretation()
    interpretation["recent_user_facts"] = ["moro em Camburi"]

    result = director.validate_direct_semantic_turn(
        api_key="test",
        model="director-test",
        fallback_model=None,
        row=_row(),
        interpretation=interpretation,
        mary_text="Então estamos indo para o mesmo bairro.",
        user_text="",
        line_dialogue=[],
    )

    assert result["fulfilled"] is True
    assert result["elements"][0]["source"] == "USUÁRIO"
    assert result["elements"][0]["evidence"] == "moro em Camburi"


def test_director_rejects_conversational_role_inversion(monkeypatch):
    def fake_chat(**kwargs):
        return (
            '{"obrigacao_usuario":{"existe":false,"requisito":"","atendida":true,"evidencia":""},'
            '"coerencia_conversacional":{"ok":false,"problema":"resposta inverteu destinatario",'
            '"trecho_mary":"voce primeiro","correcao":"Mary deve responder como destinataria"},'
            '"objetivos_guia":[],'
            '"contradicao_dura":{"existe":false,"fato_autoritativo":"","trecho_mary":"","correcao":""},'
            '"cumpriu":false,"faltou":"","motivo":"inversao conversacional"}'
        )

    monkeypatch.setattr(director, "chat", fake_chat)

    interpretation = {
        "relation_to_previous": "continua o movimento anterior",
        "move": "instrui Mary a prosseguir",
        "literal_meaning": "O usuario instrui Mary a prosseguir.",
        "user_obligation": {"exists": False, "requirement": ""},
        "recent_user_facts": [],
    }

    result = director.validate_direct_semantic_turn(
        api_key="test",
        model="director-test",
        fallback_model=None,
        row={**_row(), "speech_guide": ""},
        interpretation=interpretation,
        mary_text="voce primeiro",
        user_text="pode ir",
        line_dialogue=[],
    )

    assert result["conversation_consistency"]["ok"] is False
    assert result["conversation_consistency"]["issue"]
    assert result["fulfilled"] is False


def test_abbreviated_literal_evidence_from_same_mary_turn_is_grounded(monkeypatch):
    def fake_chat(**kwargs):
        return (
            '{"obrigacao_usuario":{"existe":false,"requisito":"","atendida":true,"evidencia":""},'
            '"coerencia_conversacional":{"ok":true,"problema":"","trecho_mary":"","correcao":""},'
            '"objetivos_guia":[{"objetivo":"expressar exaustao","alcancado":true,'
            '"fonte":"MARY","evidencia":"Ufa! Consegui! Nossa, acho que agora foi o meu limite... Minhas pernas estão tremendo real agora"}],'
            '"contradicao_dura":{"existe":false,"fato_autoritativo":"","trecho_mary":"","correcao":""},'
            '"violacao_revelacao":{"existe":false,"conteudo_reservado":"","trecho_mary":"","correcao":""},'
            '"cumpriu":true,"faltou":"","motivo":"cumpriu"}'
        )

    monkeypatch.setattr(director, "chat", fake_chat)

    mary_text = (
        "Ai! Ufa! Consegui! Nossa, acho que agora foi o meu limite... "
        "pronto, série feita! Minhas pernas estão tremendo real agora, "
        "mas a sensação de dever cumprido é maravilhosa."
    )

    result = director.validate_direct_semantic_turn(
        api_key="test",
        model="director-test",
        fallback_model=None,
        row={**_row(), "speech_guide": "Nossa... cheguei no meu limite."},
        interpretation=_interpretation(),
        mary_text=mary_text,
        user_text="Vai, segura e sobe devagar.",
        line_dialogue=[],
    )

    assert result["fulfilled"] is True
    assert result["elements"][0]["source"] == "MARY"


def test_abbreviated_evidence_cannot_mix_fragments_from_different_turns():
    source = director._evidence_source(
        "primeiro fragmento real... segundo fragmento real",
        [
            ("MARY", "Aqui existe apenas o primeiro fragmento real."),
            ("MARY", "Aqui existe apenas o segundo fragmento real."),
        ],
    )

    assert source == ""


def test_automatic_line_can_be_fulfilled_by_mary_thought(monkeypatch):
    def fake_chat(**kwargs):
        payload = kwargs["messages"][1]["content"]
        assert "PENSAMENTO ATUAL DE MARY" in payload
        assert "Assim tão rápido já aparece uma tentação dessas" in payload
        return (
            '{"obrigacao_usuario":{"existe":false,"requisito":"","atendida":true,"evidencia":""},'
            '"coerencia_conversacional":{"ok":true,"problema":"","trecho_mary":"","correcao":""},'
            '"objetivos_guia":[{"objetivo":"reconhecer a tentacao","alcancado":true,'
            '"fonte":"MARY","evidencia":"Assim tão rápido já aparece uma tentação dessas"}],'
            '"contradicao_dura":{"existe":false,"fato_autoritativo":"","trecho_mary":"","correcao":""},'
            '"violacao_revelacao":{"existe":false,"conteudo_reservado":"","trecho_mary":"","correcao":""},'
            '"cumpriu":true,"faltou":"","motivo":"pensamento cumpriu a linha"}'
        )

    monkeypatch.setattr(director, "chat", fake_chat)

    result = director.validate_direct_semantic_turn(
        api_key="test",
        model="director-test",
        fallback_model=None,
        row={
            **_row(),
            "speech_guide": "Hum... Mary... será? Assim tão rápido já aparece uma tentação dessas?",
            "interaction_mode": "automatico",
        },
        interpretation={
            "user_obligation": {"exists": False, "requirement": ""},
            "literal_meaning": "continuação automática",
        },
        mary_text="Vou ajustar o banco do Leg Press.",
        mary_thought="Hum... Mary... será? Assim tão rápido já aparece uma tentação dessas?",
        user_text="",
        line_dialogue=[],
    )

    assert result["fulfilled"] is True
    assert result["elements"][0]["source"] == "MARY"
