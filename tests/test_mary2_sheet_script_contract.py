from mary2.sheet_script import build_line_prompt


def _row(**overrides):
    row = {
        "order": 2,
        "type": "INTERPRETADA",
        "speech_guide": "O transito deve estar um inferno essa hora",
        "style": "cumplicidade; humor leve; observação",
        "interpretive_meaning": "Mary comenta o trânsito com leveza.",
        "semantic_core": "Mary comenta o trânsito como assunto do presente.",
        "atmosphere": "conversa casual",
        "released_fact": "O trânsito pode ser comentado como parte do trajeto.",
        "precondition": "O carro já entrou no trajeto.",
        "wardrobe": "Legging de ginástica.",
        "physical_action": "Pode observar o fluxo.",
        "writer_limits": "Não introduzir balada, convite ou planos futuros.",
        "expected_result": "Dar naturalidade à conversa dentro do carro.",
    }
    row.update(overrides)
    return row


def test_sheet_line_makes_content_authoritative_and_emotion_only_form():
    prompt = build_line_prompt(_row(), line_order=2)

    assert "A LINHA ATUAL DA PLANILHA define o conteúdo narrativo autorizado" in prompt
    assert "A emoção de Mary altera somente a FORMA da fala" in prompt
    assert "A emoção de Mary NÃO autoriza criar fatos, lugares" in prompt
    assert "Quando precisar de naturalidade, varie a EXPRESSÃO, não os FATOS." in prompt
    assert "Não complete lacunas com conhecimento provável do mundo." in prompt


def test_sheet_line_whitelists_factual_sources():
    prompt = build_line_prompt(_row(), line_order=2)

    assert "FONTES PERMITIDAS" in prompt
    assert "1. a fala atual do usuário;" in prompt
    assert "2. a CENA ATUAL;" in prompt
    assert "3. a MEMÓRIA DE ENTRADA autoral;" in prompt
    assert "5. o FATO LIBERADO NESTE BEAT." in prompt
    assert "Perguntas, hipóteses, brincadeiras ou suspeitas do usuário não viram fatos" in prompt


def test_interpreted_line_varies_expression_not_content():
    prompt = build_line_prompt(_row(), line_order=2)

    assert "a FALA-GUIA define o conteúdo" in prompt
    assert "varie apenas a maneira como Mary o expressa" in prompt


def test_exact_line_preserves_authored_speech():
    prompt = build_line_prompt(
        _row(type="EXATA", speech_guide="Mary, fala exatamente isso."),
        line_order=2,
    )

    assert "Para tipo EXATA, preserve literalmente a FALA-GUIA" in prompt


def test_physical_action_is_a_limit_not_permission_to_improvise():
    prompt = build_line_prompt(_row(), line_order=2)

    assert "AÇÃO FÍSICA / ENCENAÇÃO AUTORIZADA" in prompt
    assert "não licença para inventar outras ações" in prompt
