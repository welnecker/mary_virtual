from mary2.direct_script import (
    build_direct_writer_prompt,
    current_direct_row,
    direct_line_correction_prompt,
    direct_script_ready_for_choice,
    ensure_direct_state,
    mark_direct_line_emitted,
    register_direct_user_reply,
    validate_direct_line_completion,
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
        user_text="Obrigado pelo elogio...",
        previous_mary_text="Gostei do seu carro. Parece bem cuidado.",
        character_name="Personal",
    )

    assert prompt.startswith("IDENTIDADE INVARIÁVEL\n")
    assert "Você é Mary." in prompt
    assert "Nunca responda como o usuário" in prompt
    assert "A ÚLTIMA FALA DE MARY não é autoridade factual" in prompt
    assert "DESCRIÇÃO INICIAL\n" in prompt
    assert "O carro pertence ao personal." in prompt
    assert "Qualquer resposta inicial do usuário corresponde ao início da carona." in prompt
    assert prompt.index("DESCRIÇÃO INICIAL") < prompt.index("MEMÓRIA PERMANENTE")
    assert "MEMÓRIA RECENTE PARA ROTEIRO" in prompt
    assert "MEMÓRIA INSTANTÂNEA" in prompt
    assert "ÚLTIMA FALA DE MARY\nGostei do seu carro. Parece bem cuidado." in prompt
    assert "FALA DO USUÁRIO\nObrigado pelo elogio..." in prompt
    assert "FALA-GUIA\nesse é seu carro? gostei..." in prompt
    assert "ESTILO / ATITUDE" in prompt
    assert "VESTIMENTA ATUAL" in prompt
    assert "AÇÃO FÍSICA / ENCENAÇÃO" in prompt
    assert "HIERARQUIA DE AUTORIDADE" not in prompt
    assert "STORY LEDGER" not in prompt
    assert "CONTEXTO FIXO DO CAPÍTULO" not in prompt
    assert "O usuário não conhece o roteiro" in prompt
    assert "Use primeiro a ÚLTIMA FALA DE MARY" in prompt
    assert "Não introduza cidade, lugar, pessoa, objeto, acontecimento ou fato" in prompt
    assert "INTERPRETAR O USUÁRIO -> REAGIR COMO MARY -> CUMPRIR A FALA-GUIA" in prompt
    assert "A resposta só está completa" in prompt
    assert "nunca autoriza omitir, inverter, contradizer ou substituir" in prompt
    assert "Uma parte não substitui a outra" in prompt
    assert "Preserve rigorosamente os papéis e propriedades" in prompt
    assert "Não devem ser recitados, explicados nem transformados em assunto" in prompt
    assert "A fala do usuário é material de interpretação, não material para repetição" in prompt


def test_initial_description_is_only_sent_on_first_line():
    first = build_direct_writer_prompt(
        row=ROWS[0],
        user_text="Vamos.",
        previous_mary_text="",
        character_name="Personal",
    )
    second = build_direct_writer_prompt(
        row=ROWS[1],
        user_text="Vamos.",
        previous_mary_text="Gostei do seu carro.",
        character_name="Personal",
    )

    assert "DESCRIÇÃO INICIAL\n" in first
    assert "O carro pertence ao personal." in first
    assert "DESCRIÇÃO INICIAL\n" not in second
    assert "Mary e o personal estão no carro dele, seguindo para Camburi." not in second


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



def test_director_validator_only_checks_guide_completion(monkeypatch):
    def fake_chat(**kwargs):
        return '{"elementos":[{"requisito":"perguntar onde o usuário mora","encontrado":false,"evidencia":""},{"requisito":"perguntar se Camburi fica fora do caminho do usuário","encontrado":false,"evidencia":""}],"cumpriu":false,"faltou":"perguntar onde mora","motivo":"a pergunta da fala-guia não apareceu"}'

    monkeypatch.setattr("mary2.direct_script.chat", fake_chat)

    result = validate_direct_line_completion(
        api_key="test",
        model="director-test",
        fallback_model=None,
        row={
            "speech_guide": "então, onde você mora? Camburi fica muito fora do seu caminho?"
        },
        mary_text="Gostei muito do treino hoje. Você pegou pesado.",
    )

    assert result["fulfilled"] is False
    assert result["missing"] == "perguntar onde mora"
    assert "qualidade literária" in result["input_payload"]
    assert result["parsed_response"]["cumpriu"] is False


def test_director_validator_accepts_rephrased_guide(monkeypatch):
    def fake_chat(**kwargs):
        return '{"elementos":[{"requisito":"perguntar onde o usuário mora","encontrado":true,"evidencia":"você mora onde?"},{"requisito":"perguntar se Camburi fica fora do caminho do usuário","encontrado":true,"evidencia":"Camburi desvia muito do seu caminho?"}],"cumpriu":true,"faltou":"","motivo":"a missão essencial foi realizada"}'

    monkeypatch.setattr("mary2.direct_script.chat", fake_chat)

    result = validate_direct_line_completion(
        api_key="test",
        model="director-test",
        fallback_model=None,
        row={
            "speech_guide": "então, onde você mora? Camburi fica muito fora do seu caminho?"
        },
        mary_text="Gostei sim do treino. Agora me conta: você mora onde? Camburi desvia muito do seu caminho?",
    )

    assert result["fulfilled"] is True
    assert result["missing"] == ""


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



def test_director_prompt_preserves_subject_action_and_intention(monkeypatch):
    captured = {}

    def fake_chat(**kwargs):
        captured["messages"] = kwargs["messages"]
        return '{"elementos":[{"requisito":"Mary pedir ao usuário que a leve ao Clube Náutico","encontrado":false,"evidencia":""},{"requisito":"Mary indicar que será uma companhia divertida","encontrado":false,"evidencia":""}],"cumpriu":false,"faltou":"pedido para levá-la e promessa de companhia divertida","motivo":"o clube foi mencionado, mas os atos de fala não ocorreram"}'

    monkeypatch.setattr("mary2.direct_script.chat", fake_chat)

    result = validate_direct_line_completion(
        api_key="test",
        model="director-test",
        fallback_model=None,
        row={
            "speech_guide": "O que me diz de me levar pra balada no Clube Náutico? Eu prometo que vou ser bem divertida..."
        },
        mary_text="Quem sabe a gente não encontra algo por lá hoje? Seria divertido.",
    )

    payload = captured["messages"][1]["content"]
    assert "Um assunto apenas mencionado NÃO satisfaz uma ação específica" in payload
    assert "Preserve sujeito e papéis" in payload
    assert result["fulfilled"] is False
    assert len(result["elements"]) == 2


def test_director_prompt_does_not_demand_missing_concrete_data(monkeypatch):
    captured = {}

    def fake_chat(**kwargs):
        captured["messages"] = kwargs["messages"]
        return '{"elementos":[{"requisito":"Mary mencionar que a bateria morreu","encontrado":true,"evidencia":"minha bateria morreu"},{"requisito":"Mary pedir ao outro personagem que registre o contato","encontrado":true,"evidencia":"anota meu número"}],"cumpriu":true,"faltou":"","motivo":"os atos de fala essenciais foram realizados"}'

    monkeypatch.setattr("mary2.direct_script.chat", fake_chat)

    result = validate_direct_line_completion(
        api_key="test",
        model="director-test",
        fallback_model=None,
        row={
            "speech_guide": "droga...lembrei que minha bateria morreu. Anota meu número pra gente não perder contato."
        },
        mary_text="Droga, minha bateria morreu. Anota meu número pra gente não perder contato.",
    )

    payload = captured["messages"][1]["content"]
    assert "não exija que Mary anote algo fisicamente" in payload
    assert "Nunca exija dado concreto" in payload
    assert result["fulfilled"] is True
