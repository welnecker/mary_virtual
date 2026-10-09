from mary2.direct_script import (
    build_direct_chapter,
    build_direct_writer_prompt,
    current_direct_row,
    direct_chapter_id,
    direct_line_correction_prompt,
    direct_script_ready_for_choice,
    ensure_direct_state,
    load_direct_script_catalog,
    mark_direct_line_emitted,
    next_direct_script,
    parse_direct_script_id,
    register_direct_user_reply,
)


def test_indexed_script_id_builds_virtual_direct_chapter():
    parsed = parse_direct_script_id("apartamento5")
    assert parsed == {
        "script_id": "apartamento5",
        "script_name": "apartamento",
        "script_index": 5,
        "valid": True,
    }

    chapter = build_direct_chapter("apartamento5")
    assert direct_chapter_id("apartamento5") == "sheet:apartamento5"
    assert chapter["script_mode"] == "direct_sheet"
    assert chapter["script_worksheet"] == "MINHA_SUGESTAO"
    assert chapter["script_name"] == "apartamento5"
    assert chapter["sheet_script_index"] == 5
    assert chapter["choices"] == []


def test_sheet_catalog_discovers_scripts_and_sorts_by_trailing_index(monkeypatch):
    values = [
        ["Ordem", "Roteiro", "Fala-guia"],
        ["1", "Carona4", "fala 1"],
        ["2", "Carona4", "fala 2"],
        ["1", "Confissão1", "fala 1"],
        ["1", "apartamento5", "fala 1"],
        ["1", "SemIndice", "ignorado"],
    ]

    class FakeWorksheet:
        def get_all_values(self):
            return values

    class FakeBook:
        def worksheet(self, name):
            assert name == "MINHA_SUGESTAO"
            return FakeWorksheet()

    class FakeClient:
        def open_by_key(self, key):
            assert key == "sheet-id"
            return FakeBook()

    monkeypatch.setattr(
        "mary2.direct_script.gspread.service_account_from_dict",
        lambda info: FakeClient(),
    )

    catalog = load_direct_script_catalog(
        service_account_info={"client_email": "test@example.com"},
        spreadsheet_id="sheet-id",
    )

    assert [item["script_id"] for item in catalog] == [
        "Confissão1",
        "Carona4",
        "apartamento5",
    ]
    assert [item["row_count"] for item in catalog] == [1, 2, 1]
    assert [item["executable_row_count"] for item in catalog] == [1, 2, 1]
    assert next_direct_script(catalog, "Carona4")["script_id"] == "apartamento5"
    assert next_direct_script(catalog, "apartamento5") == {}


def test_sheet_catalog_rejects_duplicate_script_index(monkeypatch):
    values = [
        ["Ordem", "Roteiro", "Fala-guia"],
        ["1", "Carona4", "fala"],
        ["1", "Outro4", "fala"],
    ]

    class FakeWorksheet:
        def get_all_values(self):
            return values

    class FakeBook:
        def worksheet(self, name):
            return FakeWorksheet()

    class FakeClient:
        def open_by_key(self, key):
            return FakeBook()

    monkeypatch.setattr(
        "mary2.direct_script.gspread.service_account_from_dict",
        lambda info: FakeClient(),
    )

    try:
        load_direct_script_catalog(
            service_account_info={"client_email": "test@example.com"},
            spreadsheet_id="sheet-id",
        )
    except ValueError as exc:
        assert "Índice de roteiro duplicado 4" in str(exc)
    else:
        raise AssertionError("índice narrativo duplicado deveria falhar")



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


def test_writer_prompt_contains_full_script_real_conversation_and_active_line():
    prompt = build_direct_writer_prompt(
        row=ROWS[0],
        all_rows=ROWS,
        recent_messages=[
            {"role": "assistant", "content": "Você cansou?"},
            {"role": "user", "content": "Um pouco, mas gostei."},
        ],
        user_text="Vamos.",
        interpretation={
            "relation_to_previous": "responde à pergunta",
            "move": "aceita prosseguir",
            "literal_meaning": "O usuário aceita prosseguir.",
            "user_obligation": {"exists": False, "requirement": ""},
        },
        character_name="Personal",
    )

    assert prompt.startswith("VOCÊ É MARY.\n")
    assert "ROTEIRO COMPLETO DO CAPÍTULO" in prompt
    assert "LINHA 1 [ATIVA — PODE SER DESENVOLVIDA AGORA]" in prompt
    assert "LINHA 2 [FUTURA — NÃO EXECUTAR NEM ANTECIPAR]" in prompt
    assert "CONVERSA REAL — FONTE PRINCIPAL DE CONTINUIDADE" in prompt
    assert "MARY: Você cansou?" in prompt
    assert "USUÁRIO: Um pouco, mas gostei." in prompt
    assert "USUÁRIO AGORA:\nVamos." in prompt
    assert "APOIO SEMÂNTICO — SECUNDÁRIO" in prompt
    assert "Se este apoio parecer incompatível com a conversa real" in prompt
    assert "LINHA ATIVA AGORA" in prompt
    assert "esse é seu carro? gostei..." in prompt
    assert "Nunca mencione prompt, fala-guia, roteiro, modelo, Diretor, memória" in prompt


def test_all_script_lines_are_visible_but_future_lines_are_read_only():
    first = build_direct_writer_prompt(
        row=ROWS[0],
        all_rows=ROWS,
        recent_messages=[],
        user_text="Vamos.",
        character_name="Personal",
    )
    second = build_direct_writer_prompt(
        row=ROWS[1],
        all_rows=ROWS,
        recent_messages=[
            {"role": "assistant", "content": "Gostei do carro."},
            {"role": "user", "content": "Valeu."},
        ],
        user_text="Seguimos?",
        character_name="Personal",
    )

    assert "LINHA 1 [ATIVA — PODE SER DESENVOLVIDA AGORA]" in first
    assert "LINHA 2 [FUTURA — NÃO EXECUTAR NEM ANTECIPAR]" in first
    future_block = first.split("LINHA 2 [FUTURA — NÃO EXECUTAR NEM ANTECIPAR]", 1)[1].split("REGRA DE EXECUÇÃO DO ROTEIRO", 1)[0]
    assert "o trânsito deve estar um inferno essa hora" not in future_block
    assert "Objetivo futuro: existe um próximo passo autoral reservado pelo runtime." in future_block
    assert "LINHA 1 [PASSADA — NÃO REPETIR]" in second
    assert "LINHA 2 [ATIVA — PODE SER DESENVOLVIDA AGORA]" in second
    assert "Mary e o personal estão no carro dele, seguindo para Camburi." in second


def test_direct_state_never_regresses_to_completed_line():
    narrative = {
        "direct_script": {
            "engine": "direct_sheet_v1",
            "index": 0,
            "current_order": 1,
            "awaiting_reply_order": 0,
            "completed_orders": [1],
            "completed": False,
        }
    }

    state = ensure_direct_state(narrative, ROWS)

    assert state["index"] == 1
    assert state["current_order"] == 2
    assert current_direct_row(ROWS, state)["order"] == 2


def test_next_user_reply_advances_directly_without_breath_turn():
    state = ensure_direct_state({}, ROWS)
    assert current_direct_row(ROWS, state)["order"] == 1

    mark_direct_line_emitted(state, ROWS[0])
    assert state["awaiting_reply_order"] == 1

    register_direct_user_reply(state, ROWS, "Tudo bem, vamos.")
    assert current_direct_row(ROWS, state)["order"] == 2
    assert state["awaiting_reply_order"] == 0


def test_last_line_completes_immediately_when_validated():
    state = ensure_direct_state({}, ROWS)
    mark_direct_line_emitted(state, ROWS[0], ROWS)
    register_direct_user_reply(state, ROWS, "Resposta 1")
    mark_direct_line_emitted(state, ROWS[1], ROWS)

    assert direct_script_ready_for_choice(state) is True
    assert current_direct_row(ROWS, state) == {}
    assert state["completed_orders"] == [1, 2]
    assert state["awaiting_reply_order"] == 0



def test_direct_line_correction_prompt_keeps_same_mission():
    prompt = direct_line_correction_prompt(
        {
            "speech_guide": "então, onde você mora? Camburi fica muito fora do seu caminho?"
        },
        {
            "fulfilled": False,
            "missing": "perguntar onde mora e se Camburi fica fora do caminho",
        },
    )

    assert "CORREÇÃO CIRÚRGICA DA MESMA LINHA" in prompt
    assert "perguntar onde mora e se Camburi fica fora do caminho" in prompt
    assert "A FALA-GUIA continua sendo" in prompt
    assert "Preserve personalidade, continuidade e espontaneidade" in prompt
    assert "Faça a menor alteração necessária" in prompt
    assert "Não invente fatos, dados, ações ou informações" in prompt



