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
