from mary2.direct_script import (
    build_direct_writer_prompt,
    current_direct_row,
    direct_script_ready_for_choice,
    ensure_direct_state,
    mark_direct_line_emitted,
    register_direct_user_reply,
)


ROWS = [
    {
        "order": 1,
        "line_id": "linha_01",
        "script_name": "Carona",
        "type": "INTERPRETADA",
        "speech_guide": "esse é seu carro? gostei...",
        "style": "simpatia; naturalidade",
        "precondition": "Mary e o personal chegaram ao carro.",
        "wardrobe": "Legging, rabo de cavalo, tênis.",
        "physical_action": "Pode olhar o carro.",
        "completion_type": "MIXED",
        "recent_memory": "Mary acabou de conhecer o personal na academia.",
        "instant_memory": "Mary está ao lado do carro do personal.",
        "permanent_memory": "Mary viveu uma separação recente.",
        "initial_description": (
            "Mary e o personal acabaram de sair da academia. "
            "O carro pertence ao personal. O personal dirige e Mary é passageira. "
            "Qualquer resposta inicial do usuário corresponde ao início da carona."
        ),
    },
    {
        "order": 2,
        "line_id": "linha_02",
        "script_name": "Carona",
        "type": "INTERPRETADA",
        "speech_guide": "o trânsito deve estar um inferno essa hora",
        "style": "cumplicidade",
        "precondition": "O carro está pronto para sair.",
        "wardrobe": "Legging, rabo de cavalo, tênis.",
        "physical_action": "Pode observar a rua.",
        "completion_type": "MIXED",
        "recent_memory": "Mary acabou de conhecer o personal na academia.",
        "instant_memory": "Estão dentro do carro e prontos para sair.",
        "permanent_memory": "",
        "initial_description": (
            "Mary e o personal estão no carro dele, seguindo para Camburi."
        ),
    },
]


def test_writer_prompt_is_direct_and_contains_only_authorial_fields():
    prompt = build_direct_writer_prompt(
        row=ROWS[0],
        user_text="Vamos, Mary...",
        character_name="Personal",
    )

    assert prompt.startswith("DESCRIÇÃO INICIAL\n")
    assert "O carro pertence ao personal." in prompt
    assert "Qualquer resposta inicial do usuário corresponde ao início da carona." in prompt
    assert prompt.index("DESCRIÇÃO INICIAL") < prompt.index("MEMÓRIA PERMANENTE")
    assert "MEMÓRIA RECENTE PARA ROTEIRO" in prompt
    assert "MEMÓRIA INSTANTÂNEA" in prompt
    assert "FALA DO USUÁRIO\nVamos, Mary..." in prompt
    assert "FALA-GUIA\nesse é seu carro? gostei..." in prompt
    assert "ESTILO / ATITUDE" in prompt
    assert "VESTIMENTA ATUAL" in prompt
    assert "AÇÃO FÍSICA / ENCENAÇÃO" in prompt
    assert "HIERARQUIA DE AUTORIDADE" not in prompt
    assert "STORY LEDGER" not in prompt
    assert "CONTEXTO FIXO DO CAPÍTULO" not in prompt
    assert "FALA DO USUÁRIO é o único acontecimento verbal que acabou de ocorrer" in prompt
    assert "FALA-GUIA é uma MISSÃO AUTORAL" in prompt
    assert "Não é uma fala anterior" in prompt
    assert "Não devem ser recitados, explicados nem transformados em assunto" in prompt
    assert "Não puxe delas informações que o usuário não pediu" in prompt


def test_next_user_reply_advances_directly_without_breath_turn():
    state = ensure_direct_state({}, ROWS)
    assert current_direct_row(ROWS, state)["order"] == 1

    mark_direct_line_emitted(state, ROWS[0])
    assert state["awaiting_reply_order"] == 1

    register_direct_user_reply(state, ROWS, "Tudo bem, vamos.")
    assert current_direct_row(ROWS, state)["order"] == 2
    assert state["awaiting_reply_order"] == 0


def test_last_line_completes_after_following_user_reply():
    state = ensure_direct_state({}, ROWS)
    mark_direct_line_emitted(state, ROWS[0])
    register_direct_user_reply(state, ROWS, "Resposta 1")
    mark_direct_line_emitted(state, ROWS[1])

    register_direct_user_reply(state, ROWS, "Resposta final")

    assert direct_script_ready_for_choice(state) is True
    assert current_direct_row(ROWS, state) == {}
