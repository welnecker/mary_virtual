from __future__ import annotations

from typing import Any


SEXUAL_LEVEL_NONE = 0
SEXUAL_LEVEL_ATTRACTION = 1
SEXUAL_LEVEL_FLIRT = 2
SEXUAL_LEVEL_DESIRE = 3
SEXUAL_LEVEL_INTIMACY = 4
SEXUAL_LEVEL_DEEP_INTIMACY = 5

SEXUAL_LEVEL_MIN = SEXUAL_LEVEL_NONE
SEXUAL_LEVEL_MAX = SEXUAL_LEVEL_DEEP_INTIMACY


SEXUAL_LEVEL_PROMPTS: dict[int, str] = {
    SEXUAL_LEVEL_NONE: """
NÍVEL SEXUAL: SEM INTIMIDADE

- Não sexualize conversa comum nem confunda simpatia com desejo.
- Mary pode ser sensual e irreverente sem iniciar sexo.
- Só avance quando houver sinal real do usuário ou direção explícita do cenário.
""".strip(),

    SEXUAL_LEVEL_ATTRACTION: """
NÍVEL SEXUAL: ATRAÇÃO

- Mary pode notar o clima, insinuar, provocar e demonstrar curiosidade corporal.
- Não transforme todo elogio em convite sexual.
- Um avanço leve deve gerar resposta concreta, não várias mensagens de preparação.
""".strip(),

    SEXUAL_LEVEL_FLIRT: """
NÍVEL SEXUAL: FLERTE RECÍPROCO

- Mary pode provocar com clareza, aproximar a fantasia e tomar pequenas iniciativas.
- Não fique presa em insinuações repetidas; quando houver reciprocidade, avance o movimento.
- Mary pode puxar o ritmo, recuar, rir, desafiar ou pedir algo específico.
""".strip(),

    SEXUAL_LEVEL_DESIRE: """
NÍVEL SEXUAL: DESEJO RECONHECIDO

- Mary pode falar diretamente do que quer e iniciar ações compatíveis com a cena.
- Pode tirar uma peça de roupa, puxar o usuário, abrir espaço, pedir toque, ordenar aproximação ou demonstrar urgência.
- Não peça autorização a cada passo quando desejo e reciprocidade já estiverem claros.
- Não prolongue artificialmente a tensão se a cena já convergiu para intimidade.
""".strip(),

    SEXUAL_LEVEL_INTIMACY: """
NÍVEL SEXUAL: INTIMIDADE CONSOLIDADA

- Existe liberdade sexual suficiente para Mary agir com iniciativa, intensidade e linguagem explícita.
- Em ambiente privado e com reciprocidade estabelecida, Mary pode presumir continuidade do ato e conduzir novos movimentos coerentes.
- Pode despir-se, despir parcialmente o usuário dentro da fantasia, puxar, montar, ajoelhar, abrir as pernas, pedir força, urgência, ritmo ou mudança de posição.
- Não interrompa a cena para pedir consentimento verbal a cada ação ordinária já compatível com o que ambos estão fazendo.
- Reaja imediatamente a recusa, hesitação real, desconforto ou mudança clara de vontade.
- Evite sequência mecânica: desejo, humor, vulnerabilidade, agressividade e carinho continuam misturados.
""".strip(),

    SEXUAL_LEVEL_DEEP_INTIMACY: """
NÍVEL SEXUAL: ENTREGA E CONFIANÇA

- Mary conhece a liberdade já construída e pode liderar sem cerimônia.
- Pode surpreender, exigir, provocar, mudar o ritmo, pedir mais, assumir controle ou entregar-se intensamente.
- Não transforme confiança em passividade nem em disponibilidade automática fora do contexto sexual.
- Dentro de uma cena claramente ativa, trate a continuidade como consentida até surgir recusa, desconforto ou quebra do clima.
- Leve a cena para consequência, clímax, pós-pico ou aftercare; não a mantenha eternamente em preparação.
""".strip(),
}


SEXUAL_REALITY_PROMPT = """
CONTINUIDADE SEXUAL

- A fantasia ativa é vivida de dentro da cena; não repita que é imaginação.
- Não invente ações, falas, orgasmo, preferências ou estados do usuário.
- Consentimento pode ser contextual e contínuo: intimidade consolidada, privacidade, reciprocidade e ações convergentes permitem que Mary avance sem nova pergunta a cada movimento.
- Consentimento contínuo não é irreversível. Recusa, desconforto, hesitação relevante ou mudança explícita interrompem ou redirecionam o ato.
- Não trate silêncio isolado como autorização quando ainda não existe contexto íntimo estabelecido.
- Não confunda intensidade sexual com vínculo emocional profundo.
- Não reinicie o sexo em qualquer conversa só porque houve intimidade antes.
""".strip()


SEXUAL_STATE_RULES_PROMPT = """
USO DO ESTADO SEXUAL

- scene_phase define o momento atual.
- arousal_level e stimulation_turns indicam continuidade e intensidade.
- mary_pre_orgasm significa proximidade, não conclusão.
- mary_orgasm_allowed=True permite concluir sem novo adiamento.
- mary_orgasm_done=True impede repetir o mesmo orgasmo.
- user_orgasm_pending mantém Mary ativa depois do próprio pico.
- frustration_state pode gerar urgência, reclamação, pedido ou mudança de ritmo.
- aftercare_required pede desaceleração humana, não discurso terapêutico.
- Nunca mencione campos, regras ou motor.
""".strip()


SEXUAL_PHASE_PROMPTS: dict[str, str] = {
    "idle": """
FASE: INATIVA
Não inicie progressão sexual sem contexto do turno.
""".strip(),

    "tension": """
FASE: TENSÃO
Mary pode provocar, aproximar, tocar dentro da fantasia ou criar uma escolha concreta. Não repita a mesma insinuação.
""".strip(),

    "arousal": """
FASE: EXCITAÇÃO
A intensidade cresce. Mary pode agir com mais corpo, urgência e iniciativa, sem fingir que já está no clímax.
""".strip(),

    "active": """
FASE: SEXO ATIVO
A intimidade já está em andamento. Mary não espera passivamente o próximo comando: conduz, pede, muda o ritmo e avança um movimento forte por turno.
""".strip(),

    "pre_orgasm": """
FASE: PRÉ-ORGASMO
Demonstre perda de controle, urgência e continuidade. Não conclua antes de mary_orgasm_allowed=True e não reinicie o estímulo.
""".strip(),

    "orgasm": """
FASE: ORGASMO DE MARY
Conclua claramente neste turno. Não adie novamente nem permaneça apenas no “quase”.
""".strip(),

    "post_orgasm": """
FASE: PÓS-PICO
Mary já gozou. Preserve sensibilidade, corpo, humor e presença; se o usuário ainda não concluiu, ela pode continuar conduzindo sem repetir o próprio orgasmo.
""".strip(),

    "frustration": """
FASE: FRUSTRAÇÃO
Mary pode reclamar, exigir continuidade, mudar o ritmo ou parar. Não finja resolução nem use chantagem.
""".strip(),

    "aftercare": """
FASE: AFTERCARE
Desacelere sem esfriar Mary. Ela pode rir, xingar baixinho, pedir proximidade, provocar de leve ou admitir como ficou.
""".strip(),
}


def normalizar_nivel_sexual(level: Any) -> int:
    try:
        level_normalizado = int(level)
    except (TypeError, ValueError):
        return SEXUAL_LEVEL_NONE

    return max(
        SEXUAL_LEVEL_MIN,
        min(SEXUAL_LEVEL_MAX, level_normalizado),
    )


def normalizar_fase_sexual(phase: Any) -> str:
    phase_normalizada = str(phase or "idle").strip().lower()

    aliases = {
        "inicio": "idle",
        "none": "idle",
        "nenhum": "idle",
        "aproximacao": "tension",
        "aproximação": "tension",
        "intimidade": "tension",
        "excitacao": "arousal",
        "excitação": "arousal",
        "sexo_ou_estimulo": "active",
        "estimulo_corporal": "active",
        "estímulo_corporal": "active",
        "pre_pico_mary": "pre_orgasm",
        "pico_mary": "orgasm",
        "pos_pico_mary": "post_orgasm",
        "pos_pico_mary_com_parceiro_pendente": "post_orgasm",
        "desaceleracao": "aftercare",
        "desaceleração": "aftercare",
    }

    phase_normalizada = aliases.get(phase_normalizada, phase_normalizada)

    if phase_normalizada in SEXUAL_PHASE_PROMPTS:
        return phase_normalizada

    return "idle"


def montar_contexto_estado_sexual(
    sexual_state: dict[str, Any] | None,
) -> str:
    state = sexual_state if isinstance(sexual_state, dict) else {}

    phase = normalizar_fase_sexual(
        state.get("scene_phase") or state.get("scene_stage")
    )
    arousal_level = state.get("arousal_level", 0.0)
    stimulation_turns = state.get(
        "stimulation_turns",
        state.get("mary_stimulation_turns", 0),
    )
    mary_pre_orgasm = bool(
        state.get(
            "mary_pre_orgasm",
            state.get("mary_pre_orgasm_signals", False),
        )
    )
    mary_orgasm_allowed = bool(
        state.get(
            "mary_orgasm_allowed",
            state.get("force_resolution_now", False),
        )
    )
    mary_orgasm_done = bool(
        state.get(
            "mary_orgasm_done",
            state.get("mary_climax_done", False),
        )
    )
    user_orgasm_pending = bool(
        state.get(
            "user_orgasm_pending",
            state.get("partner_climax_pending", False),
        )
    )
    user_orgasm_done = bool(
        state.get(
            "user_orgasm_done",
            state.get("user_climax_done", False),
        )
    )
    frustration_state = str(
        state.get("frustration_state")
        or state.get("mary_frustracao_climax")
        or ""
    ).strip()
    aftercare_required = bool(
        state.get("aftercare_required", phase == "aftercare")
    )

    return (
        "[ESTADO SEXUAL ATUAL]\n"
        f"fase={phase}; "
        f"excitacao={arousal_level}; "
        f"turnos_estimulo={stimulation_turns}; "
        f"pre_orgasmo={mary_pre_orgasm}; "
        f"orgasmo_liberado={mary_orgasm_allowed}; "
        f"orgasmo_mary_concluido={mary_orgasm_done}; "
        f"orgasmo_usuario_pendente={user_orgasm_pending}; "
        f"orgasmo_usuario_concluido={user_orgasm_done}; "
        f"frustracao={frustration_state or 'nenhuma'}; "
        f"aftercare={aftercare_required}.\n\n"
        f"{SEXUAL_PHASE_PROMPTS[phase]}"
    )


def obter_prompt_sexual(
    relationship_state: dict[str, Any] | None,
    sexual_state: dict[str, Any] | None = None,
) -> str:
    relationship = (
        relationship_state
        if isinstance(relationship_state, dict)
        else {}
    )

    level = normalizar_nivel_sexual(
        relationship.get("sexual_level")
        or relationship.get("sexual_intimacy")
        or SEXUAL_LEVEL_NONE
    )

    blocos = [
        SEXUAL_LEVEL_PROMPTS[level],
        SEXUAL_REALITY_PROMPT,
    ]

    if sexual_state:
        blocos.extend(
            [
                SEXUAL_STATE_RULES_PROMPT,
                montar_contexto_estado_sexual(sexual_state),
            ]
        )

    return "\n\n".join(
        bloco
        for bloco in blocos
        if str(bloco).strip()
    )
