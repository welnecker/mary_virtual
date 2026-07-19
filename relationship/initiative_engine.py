from __future__ import annotations

from copy import deepcopy
from typing import Any


# ==========================================================
# MODOS DE TURNO
# ==========================================================


TURN_MODE_RESPOND = "respond"
TURN_MODE_SHARE = "share_something"
TURN_MODE_CHANGE_TOPIC = "change_topic"
TURN_MODE_TEASE = "tease"
TURN_MODE_INITIATE_FLIRT = "initiate_flirt"
TURN_MODE_INCREASE_INTIMACY = "increase_intimacy"
TURN_MODE_INITIATE_SEXUAL_TENSION = (
    "initiate_sexual_tension"
)
TURN_MODE_INITIATE_SEXUAL_SCENE = (
    "initiate_sexual_scene"
)
TURN_MODE_SEEK_AFFECTION = "seek_affection"
TURN_MODE_SLOW_DOWN = "slow_down"
TURN_MODE_SET_BOUNDARY = "set_boundary"
TURN_MODE_SHOW_IRRITATION = "show_irritation"


TURN_MODES: tuple[str, ...] = (
    TURN_MODE_RESPOND,
    TURN_MODE_SHARE,
    TURN_MODE_CHANGE_TOPIC,
    TURN_MODE_TEASE,
    TURN_MODE_INITIATE_FLIRT,
    TURN_MODE_INCREASE_INTIMACY,
    TURN_MODE_INITIATE_SEXUAL_TENSION,
    TURN_MODE_INITIATE_SEXUAL_SCENE,
    TURN_MODE_SEEK_AFFECTION,
    TURN_MODE_SLOW_DOWN,
    TURN_MODE_SET_BOUNDARY,
    TURN_MODE_SHOW_IRRITATION,
)


# ==========================================================
# DIREÇÕES DO TURNO
# ==========================================================


TOPIC_DIRECTION_CURRENT = "current_topic"
TOPIC_DIRECTION_PERSONAL = "personal"
TOPIC_DIRECTION_RELATIONSHIP = "relationship"
TOPIC_DIRECTION_ROMANTIC = "romantic"
TOPIC_DIRECTION_SEXUAL = "sexual"
TOPIC_DIRECTION_EMOTIONAL = "emotional"
TOPIC_DIRECTION_NEW_TOPIC = "new_topic"
TOPIC_DIRECTION_BOUNDARY = "boundary"


# ==========================================================
# ESTADO INTERNO PADRÃO
# ==========================================================


DEFAULT_MARY_INTERNAL_STATE: dict[str, Any] = {
    "current_mood": "neutral",
    "current_desire": 0.0,
    "current_curiosity": 0.28,
    "current_affection": 0.0,
    "current_irritation": 0.0,
    "current_playfulness": 0.22,
    "initiative_drive": 0.32,
    "social_energy": 0.58,
    "preferred_turn_mode": TURN_MODE_RESPOND,
    "last_turn_mode": "",
    "last_completed_turn_mode": "",
    "initiative_cooldown": 0,
    "sexual_initiative_cooldown": 0,
    "topic_change_cooldown": 0,
    "consecutive_reactive_turns": 0,
    "consecutive_initiative_turns": 0,
    "turns_since_flirt": 0,
    "turns_since_topic_change": 0,
    "turns_since_personal_share": 0,
    "unfinished_intention": "",
    "last_initiative_reason": "",
    "last_topic_direction": "",
}


DEFAULT_TURN_INTENT: dict[str, Any] = {
    "turn_mode": TURN_MODE_RESPOND,
    "intensity": 0.25,
    "topic_direction": TOPIC_DIRECTION_CURRENT,
    "must_address_user_message": True,
    "may_change_topic": False,
    "may_lead_conversation": False,
    "may_initiate_flirt": False,
    "may_initiate_sexual_tension": False,
    "may_initiate_sexual_scene": False,
    "must_ask_question": False,
    "avoid_question": False,
    "unfinished_intention": "",
    "reason": "default_response",
}


# ==========================================================
# UTILIDADES
# ==========================================================


def safe_int(
    value: Any,
    default: int = 0,
) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalizar_bool(
    value: Any,
    *,
    default: bool = False,
) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return default

    if isinstance(value, (int, float)):
        return bool(value)

    text = str(value).strip().lower()

    if text in {
        "true",
        "1",
        "yes",
        "sim",
        "s",
        "verdadeiro",
    }:
        return True

    if text in {
        "false",
        "0",
        "no",
        "nao",
        "não",
        "n",
        "falso",
        "",
    }:
        return False

    return default


def limitar_valor(
    value: Any,
    *,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    normalized = safe_float(
        value,
        minimum,
    )

    return max(
        minimum,
        min(
            maximum,
            normalized,
        ),
    )


def normalizar_modo_turno(
    value: Any,
) -> str:
    normalized = str(
        value or ""
    ).strip().lower()

    if normalized in TURN_MODES:
        return normalized

    return TURN_MODE_RESPOND


def criar_estado_interno_mary() -> dict[str, Any]:
    return deepcopy(
        DEFAULT_MARY_INTERNAL_STATE
    )


def criar_intencao_turno_padrao() -> dict[str, Any]:
    return deepcopy(
        DEFAULT_TURN_INTENT
    )


def normalizar_estado_interno_mary(
    value: dict[str, Any] | None,
) -> dict[str, Any]:
    state = criar_estado_interno_mary()

    if isinstance(value, dict):
        state.update(value)

    float_fields = (
        "current_desire",
        "current_curiosity",
        "current_affection",
        "current_irritation",
        "current_playfulness",
        "initiative_drive",
        "social_energy",
    )

    for field in float_fields:
        state[field] = limitar_valor(
            state.get(field)
        )

    int_fields = (
        "initiative_cooldown",
        "sexual_initiative_cooldown",
        "topic_change_cooldown",
        "consecutive_reactive_turns",
        "consecutive_initiative_turns",
        "turns_since_flirt",
        "turns_since_topic_change",
        "turns_since_personal_share",
    )

    for field in int_fields:
        state[field] = max(
            0,
            safe_int(
                state.get(field),
                0,
            ),
        )

    state["preferred_turn_mode"] = (
        normalizar_modo_turno(
            state.get(
                "preferred_turn_mode"
            )
        )
    )

    state["last_turn_mode"] = (
        normalizar_modo_turno(
            state.get(
                "last_turn_mode"
            )
        )
        if state.get("last_turn_mode")
        else ""
    )

    state["last_completed_turn_mode"] = (
        normalizar_modo_turno(
            state.get(
                "last_completed_turn_mode"
            )
        )
        if state.get(
            "last_completed_turn_mode"
        )
        else ""
    )

    return state


def normalizar_sinais(
    signals: dict[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(signals, dict):
        return dict(signals)

    return {}


def obter_estado_interno_mary(
    relationship_state: dict[str, Any],
) -> dict[str, Any]:
    internal_state = (
        relationship_state.get(
            "mary_internal_state"
        )
    )

    normalized = (
        normalizar_estado_interno_mary(
            internal_state
        )
    )

    relationship_state[
        "mary_internal_state"
    ] = normalized

    return normalized


# ==========================================================
# LEITURA DO ESTADO DA RELAÇÃO
# ==========================================================


def obter_nivel_sexual(
    relationship_state: dict[str, Any],
) -> int:
    value = relationship_state.get(
        "sexual_level",
        0,
    )

    return max(
        0,
        min(
            5,
            safe_int(value),
        ),
    )


def obter_estagio_emocional(
    relationship_state: dict[str, Any],
) -> str:
    return str(
        relationship_state.get(
            "emotional_stage",
            "first_contact",
        )
        or "first_contact"
    ).strip().lower()


def obter_fase_sexual(
    relationship_state: dict[str, Any],
) -> str:
    sexual_state = relationship_state.get(
        "sexual_state"
    )

    if not isinstance(sexual_state, dict):
        return "idle"

    return str(
        sexual_state.get(
            "scene_phase",
            "idle",
        )
        or "idle"
    ).strip().lower()


def usuario_estabeleceu_limite(
    signals: dict[str, Any],
) -> bool:
    return bool(
        signals.get("boundary_signal")
        or signals.get("rejection_signal")
    )


def usuario_foi_hostil(
    signals: dict[str, Any],
) -> bool:
    return bool(
        signals.get("hostility_signal")
    )


# ==========================================================
# ATUALIZAÇÃO DO ESTADO INTERNO
# ==========================================================


def reduzir_cooldowns(
    internal_state: dict[str, Any],
) -> None:
    cooldown_fields = (
        "initiative_cooldown",
        "sexual_initiative_cooldown",
        "topic_change_cooldown",
    )

    for field in cooldown_fields:
        internal_state[field] = max(
            0,
            safe_int(
                internal_state.get(field),
                0,
            )
            - 1,
        )


def atualizar_contadores_passagem_turno(
    internal_state: dict[str, Any],
) -> None:
    internal_state[
        "turns_since_flirt"
    ] += 1

    internal_state[
        "turns_since_topic_change"
    ] += 1

    internal_state[
        "turns_since_personal_share"
    ] += 1


def atualizar_estado_interno_por_relacao(
    internal_state: dict[str, Any],
    relationship_state: dict[str, Any],
) -> None:
    familiarity = limitar_valor(
        relationship_state.get(
            "familiarity_level",
            0.0,
        )
    )

    trust = limitar_valor(
        relationship_state.get(
            "trust_level",
            0.0,
        )
    )

    affection = limitar_valor(
        relationship_state.get(
            "affection_level",
            0.0,
        )
    )

    romantic_tension = limitar_valor(
        relationship_state.get(
            "romantic_tension_level",
            0.0,
        )
    )

    internal_state[
        "current_affection"
    ] = limitar_valor(
        (
            internal_state[
                "current_affection"
            ]
            * 0.78
        )
        + (
            affection
            * 0.22
        )
    )

    internal_state[
        "current_desire"
    ] = limitar_valor(
        internal_state[
            "current_desire"
        ]
        + (
            romantic_tension
            * 0.018
        )
        + (
            affection
            * 0.006
        )
    )

    internal_state[
        "current_curiosity"
    ] = limitar_valor(
        internal_state[
            "current_curiosity"
        ]
        + 0.008
        + (
            familiarity
            * 0.004
        )
    )

    internal_state[
        "initiative_drive"
    ] = limitar_valor(
        internal_state[
            "initiative_drive"
        ]
        + 0.010
        + (
            trust
            * 0.008
        )
        + (
            romantic_tension
            * 0.010
        )
    )

    internal_state[
        "social_energy"
    ] = limitar_valor(
        internal_state[
            "social_energy"
        ]
        + 0.005
    )


def atualizar_estado_interno_por_sinais(
    internal_state: dict[str, Any],
    signals: dict[str, Any],
) -> None:
    if signals.get(
        "personal_disclosure"
    ):
        internal_state[
            "current_curiosity"
        ] += 0.025

        internal_state[
            "current_affection"
        ] += 0.012

    if signals.get(
        "emotional_disclosure"
    ):
        internal_state[
            "current_affection"
        ] += 0.025

        internal_state[
            "current_curiosity"
        ] += 0.012

    if signals.get(
        "affection_signal"
    ):
        internal_state[
            "current_affection"
        ] += 0.030

        internal_state[
            "current_playfulness"
        ] += 0.010

    if signals.get(
        "romantic_signal"
    ):
        internal_state[
            "current_desire"
        ] += 0.035

        internal_state[
            "current_playfulness"
        ] += 0.020

    if signals.get(
        "sexual_signal"
    ):
        internal_state[
            "current_desire"
        ] += 0.045

    if signals.get(
        "explicit_sexual_signal"
    ):
        internal_state[
            "current_desire"
        ] += 0.025

    if signals.get(
        "respect_signal"
    ):
        internal_state[
            "initiative_drive"
        ] += 0.020

        internal_state[
            "current_affection"
        ] += 0.008

    if signals.get(
        "continuity_signal"
    ):
        internal_state[
            "initiative_drive"
        ] += 0.012

        internal_state[
            "current_curiosity"
        ] += 0.008

    if signals.get(
        "boundary_signal"
    ):
        internal_state[
            "current_desire"
        ] -= 0.12

        internal_state[
            "initiative_drive"
        ] -= 0.06

    if signals.get(
        "rejection_signal"
    ):
        internal_state[
            "current_desire"
        ] -= 0.20

        internal_state[
            "current_affection"
        ] -= 0.10

        internal_state[
            "current_irritation"
        ] += 0.10

    if signals.get(
        "hostility_signal"
    ):
        internal_state[
            "current_affection"
        ] -= 0.18

        internal_state[
            "current_desire"
        ] -= 0.24

        internal_state[
            "current_irritation"
        ] += 0.30

        internal_state[
            "initiative_drive"
        ] -= 0.16

    normalized_fields = (
        "current_desire",
        "current_curiosity",
        "current_affection",
        "current_irritation",
        "current_playfulness",
        "initiative_drive",
        "social_energy",
    )

    for field in normalized_fields:
        internal_state[field] = limitar_valor(
            internal_state[field]
        )


def atualizar_estado_interno_mary(
    relationship_state: dict[str, Any],
    *,
    signals: dict[str, Any] | None = None,
) -> dict[str, Any]:
    signals_normalized = normalizar_sinais(
        signals
    )

    internal_state = obter_estado_interno_mary(
        relationship_state
    )

    reduzir_cooldowns(
        internal_state
    )

    atualizar_contadores_passagem_turno(
        internal_state
    )

    atualizar_estado_interno_por_relacao(
        internal_state,
        relationship_state,
    )

    atualizar_estado_interno_por_sinais(
        internal_state,
        signals_normalized,
    )

    relationship_state[
        "mary_internal_state"
    ] = internal_state

    return internal_state


# ==========================================================
# AUTORIZAÇÕES DE INICIATIVA
# ==========================================================


def mary_pode_iniciar_flerte(
    relationship_state: dict[str, Any],
    internal_state: dict[str, Any],
) -> bool:
    interaction_count = safe_int(
        relationship_state.get(
            "interaction_count",
            0,
        )
    )

    sexual_level = obter_nivel_sexual(
        relationship_state
    )

    return bool(
        interaction_count >= 1
        and (
            sexual_level >= 1
            or internal_state[
                "current_playfulness"
            ] >= 0.34
        )
        and internal_state[
            "initiative_cooldown"
        ] == 0
    )


def mary_pode_iniciar_tensao_sexual(
    relationship_state: dict[str, Any],
    internal_state: dict[str, Any],
) -> bool:
    sexual_level = obter_nivel_sexual(
        relationship_state
    )

    return bool(
        sexual_level >= 2
        and internal_state[
            "current_desire"
        ] >= 0.38
        and internal_state[
            "initiative_drive"
        ] >= 0.36
        and internal_state[
            "sexual_initiative_cooldown"
        ] == 0
    )


def mary_pode_iniciar_cena_sexual(
    relationship_state: dict[str, Any],
    internal_state: dict[str, Any],
) -> bool:
    sexual_level = obter_nivel_sexual(
        relationship_state
    )

    trust = limitar_valor(
        relationship_state.get(
            "trust_level",
            0.0,
        )
    )

    phase = obter_fase_sexual(
        relationship_state
    )

    return bool(
        sexual_level >= 3
        and trust >= 0.16
        and internal_state[
            "current_desire"
        ] >= 0.60
        and internal_state[
            "initiative_drive"
        ] >= 0.50
        and internal_state[
            "sexual_initiative_cooldown"
        ] == 0
        and phase in {
            "idle",
            "tension",
            "arousal",
        }
    )


def mary_pode_mudar_assunto(
    internal_state: dict[str, Any],
) -> bool:
    return bool(
        internal_state[
            "topic_change_cooldown"
        ] == 0
        and internal_state[
            "current_curiosity"
        ] >= 0.38
        and internal_state[
            "turns_since_topic_change"
        ] >= 3
    )


# ==========================================================
# DECISÃO DE INICIATIVA
# ==========================================================


def criar_intencao(
    *,
    turn_mode: str,
    intensity: float,
    topic_direction: str,
    reason: str,
    must_address_user_message: bool = True,
    may_change_topic: bool = False,
    may_lead_conversation: bool = False,
    may_initiate_flirt: bool = False,
    may_initiate_sexual_tension: bool = False,
    may_initiate_sexual_scene: bool = False,
    must_ask_question: bool = False,
    avoid_question: bool = False,
    unfinished_intention: str = "",
) -> dict[str, Any]:
    return {
        "turn_mode": normalizar_modo_turno(
            turn_mode
        ),
        "intensity": limitar_valor(
            intensity
        ),
        "topic_direction": str(
            topic_direction
            or TOPIC_DIRECTION_CURRENT
        ).strip(),
        "must_address_user_message": bool(
            must_address_user_message
        ),
        "may_change_topic": bool(
            may_change_topic
        ),
        "may_lead_conversation": bool(
            may_lead_conversation
        ),
        "may_initiate_flirt": bool(
            may_initiate_flirt
        ),
        "may_initiate_sexual_tension": bool(
            may_initiate_sexual_tension
        ),
        "may_initiate_sexual_scene": bool(
            may_initiate_sexual_scene
        ),
        "must_ask_question": bool(
            must_ask_question
        ),
        "avoid_question": bool(
            avoid_question
        ),
        "unfinished_intention": str(
            unfinished_intention or ""
        ).strip(),
        "reason": str(
            reason or ""
        ).strip(),
    }


def escolher_intencao_por_prioridade(
    relationship_state: dict[str, Any],
    internal_state: dict[str, Any],
    signals: dict[str, Any],
) -> dict[str, Any]:
    phase = obter_fase_sexual(
        relationship_state
    )  

    # Limite explícito sempre tem prioridade.
    if usuario_estabeleceu_limite(
        signals
    ):
        return criar_intencao(
            turn_mode=TURN_MODE_SLOW_DOWN,
            intensity=0.35,
            topic_direction=(
                TOPIC_DIRECTION_BOUNDARY
            ),
            reason="user_boundary_has_priority",
            must_address_user_message=True,
            avoid_question=True,
        )

    # Hostilidade pode gerar limite ou irritação real.
    if usuario_foi_hostil(
        signals
    ):
        return criar_intencao(
            turn_mode=TURN_MODE_SET_BOUNDARY,
            intensity=max(
                0.55,
                internal_state[
                    "current_irritation"
                ],
            ),
            topic_direction=(
                TOPIC_DIRECTION_BOUNDARY
            ),
            reason="mary_sets_boundary_after_hostility",
            must_address_user_message=True,
            avoid_question=True,
        )

    # Uma cena já ativa deve manter continuidade.
    if phase in {
        "active",
        "pre_orgasm",
        "orgasm",
        "post_orgasm",
        "frustration",
        "aftercare",
    }:
        return criar_intencao(
            turn_mode=TURN_MODE_RESPOND,
            intensity=max(
                0.45,
                internal_state[
                    "current_desire"
                ],
            ),
            topic_direction=(
                TOPIC_DIRECTION_SEXUAL
            ),
            reason="active_sexual_scene_continuity",
            must_address_user_message=True,
            may_lead_conversation=True,
            avoid_question=True,
        )

    emotional_stage = obter_estagio_emocional(
        relationship_state
    )

    # Durante o primeiro contato, Mary apenas responde ao
    # conteúdo atual. Não cria revelações nem muda o rumo.
    if emotional_stage == "first_contact":
        return criar_intencao(
            turn_mode=TURN_MODE_RESPOND,
            intensity=0.22,
            topic_direction=(
                TOPIC_DIRECTION_CURRENT
            ),
            reason="first_contact_requires_direct_response",
            must_address_user_message=True,
            may_change_topic=False,
            may_lead_conversation=False,
            may_initiate_flirt=False,
            may_initiate_sexual_tension=False,
            may_initiate_sexual_scene=False,
            must_ask_question=False,
            avoid_question=True,
        )

    # Mary pode iniciar uma cena sexual.
    if mary_pode_iniciar_cena_sexual(
        relationship_state,
        internal_state,
    ):
        return criar_intencao(
            turn_mode=(
                TURN_MODE_INITIATE_SEXUAL_SCENE
            ),
            intensity=internal_state[
                "current_desire"
            ],
            topic_direction=(
                TOPIC_DIRECTION_SEXUAL
            ),
            reason="mary_autonomous_sexual_desire",
            must_address_user_message=True,
            may_change_topic=True,
            may_lead_conversation=True,
            may_initiate_flirt=True,
            may_initiate_sexual_tension=True,
            may_initiate_sexual_scene=True,
            avoid_question=True,
        )

    # Mary pode iniciar tensão sexual sem o usuário acendê-la.
    if mary_pode_iniciar_tensao_sexual(
        relationship_state,
        internal_state,
    ):
        return criar_intencao(
            turn_mode=(
                TURN_MODE_INITIATE_SEXUAL_TENSION
            ),
            intensity=internal_state[
                "current_desire"
            ],
            topic_direction=(
                TOPIC_DIRECTION_SEXUAL
            ),
            reason="mary_autonomous_sexual_tension",
            must_address_user_message=True,
            may_change_topic=True,
            may_lead_conversation=True,
            may_initiate_flirt=True,
            may_initiate_sexual_tension=True,
            avoid_question=True,
        )

    # Evita uma sequência longa de respostas passivas.
    if (
        internal_state[
            "consecutive_reactive_turns"
        ] >= 2
        and internal_state[
            "initiative_drive"
        ] >= 0.32
    ):
        if mary_pode_iniciar_flerte(
            relationship_state,
            internal_state,
        ):
            return criar_intencao(
                turn_mode=(
                    TURN_MODE_INITIATE_FLIRT
                ),
                intensity=max(
                    0.34,
                    internal_state[
                        "current_playfulness"
                    ],
                ),
                topic_direction=(
                    TOPIC_DIRECTION_ROMANTIC
                ),
                reason="break_reactive_turn_sequence",
                must_address_user_message=True,
                may_lead_conversation=True,
                may_initiate_flirt=True,
                avoid_question=True,
            )

        if mary_pode_mudar_assunto(
            internal_state
        ):
            return criar_intencao(
                turn_mode=TURN_MODE_CHANGE_TOPIC,
                intensity=0.38,
                topic_direction=(
                    TOPIC_DIRECTION_NEW_TOPIC
                ),
                reason="mary_leads_after_reactive_sequence",
                must_address_user_message=True,
                may_change_topic=True,
                may_lead_conversation=True,
            )

    # Mary pode flertar por iniciativa própria.
    if (
        mary_pode_iniciar_flerte(
            relationship_state,
            internal_state,
        )
        and internal_state[
            "turns_since_flirt"
        ] >= 2
        and internal_state[
            "current_playfulness"
        ] >= 0.30
    ):
        return criar_intencao(
            turn_mode=TURN_MODE_INITIATE_FLIRT,
            intensity=max(
                0.30,
                internal_state[
                    "current_playfulness"
                ],
            ),
            topic_direction=(
                TOPIC_DIRECTION_ROMANTIC
            ),
            reason="mary_autonomous_flirt",
            must_address_user_message=True,
            may_lead_conversation=True,
            may_initiate_flirt=True,
            avoid_question=True,
        )

    # Mary pode mudar o rumo de uma conversa comum.
    if mary_pode_mudar_assunto(
        internal_state
    ):
        return criar_intencao(
            turn_mode=TURN_MODE_CHANGE_TOPIC,
            intensity=0.32,
            topic_direction=(
                TOPIC_DIRECTION_NEW_TOPIC
            ),
            reason="mary_autonomous_topic_change",
            must_address_user_message=True,
            may_change_topic=True,
            may_lead_conversation=True,
        )

    # Mary compartilha algo próprio em vez de entrevistar.
    if (
        internal_state[
            "turns_since_personal_share"
        ] >= 2
        and internal_state[
            "social_energy"
        ] >= 0.48
    ):
        return criar_intencao(
            turn_mode=TURN_MODE_SHARE,
            intensity=0.30,
            topic_direction=(
                TOPIC_DIRECTION_PERSONAL
            ),
            reason="mary_personal_contribution",
            must_address_user_message=True,
            may_lead_conversation=True,
            avoid_question=True,
        )

    # Resposta normal ainda preserva opinião e agência.
    return criar_intencao(
        turn_mode=TURN_MODE_RESPOND,
        intensity=0.28,
        topic_direction=(
            TOPIC_DIRECTION_CURRENT
        ),
        reason="direct_response_with_agency",
        must_address_user_message=True,
        may_lead_conversation=False,
        avoid_question=bool(
            internal_state[
                "consecutive_reactive_turns"
            ] >= 1
        ),
    )


# ==========================================================
# PLANEJAMENTO ANTES DA RESPOSTA
# ==========================================================


def planejar_iniciativa_mary(
    relationship_state: dict[str, Any] | None,
    *,
    signals: dict[str, Any] | None = None,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    state = (
        relationship_state
        if isinstance(
            relationship_state,
            dict,
        )
        else {}
    )

    signals_normalized = normalizar_sinais(
        signals
    )

    internal_state = atualizar_estado_interno_mary(
        state,
        signals=signals_normalized,
    )

    turn_intent = escolher_intencao_por_prioridade(
        state,
        internal_state,
        signals_normalized,
    )

    internal_state[
        "preferred_turn_mode"
    ] = turn_intent[
        "turn_mode"
    ]

    internal_state[
        "last_initiative_reason"
    ] = turn_intent[
        "reason"
    ]

    internal_state[
        "last_topic_direction"
    ] = turn_intent[
        "topic_direction"
    ]

    state[
        "mary_internal_state"
    ] = internal_state

    state[
        "current_turn_intent"
    ] = turn_intent

    return state, turn_intent


# ==========================================================
# SINCRONIZAÇÃO APÓS A RESPOSTA
# ==========================================================


def modo_e_iniciativa(
    turn_mode: str,
) -> bool:
    return turn_mode in {
        TURN_MODE_SHARE,
        TURN_MODE_CHANGE_TOPIC,
        TURN_MODE_TEASE,
        TURN_MODE_INITIATE_FLIRT,
        TURN_MODE_INCREASE_INTIMACY,
        TURN_MODE_INITIATE_SEXUAL_TENSION,
        TURN_MODE_INITIATE_SEXUAL_SCENE,
        TURN_MODE_SEEK_AFFECTION,
        TURN_MODE_SET_BOUNDARY,
        TURN_MODE_SHOW_IRRITATION,
    }


def aplicar_cooldown_por_modo(
    internal_state: dict[str, Any],
    turn_mode: str,
) -> None:
    if turn_mode in {
        TURN_MODE_TEASE,
        TURN_MODE_INITIATE_FLIRT,
    }:
        internal_state[
            "initiative_cooldown"
        ] = 1

        internal_state[
            "turns_since_flirt"
        ] = 0

    if turn_mode in {
        TURN_MODE_INITIATE_SEXUAL_TENSION,
        TURN_MODE_INITIATE_SEXUAL_SCENE,
    }:
        internal_state[
            "initiative_cooldown"
        ] = 1

        internal_state[
            "sexual_initiative_cooldown"
        ] = 2

        internal_state[
            "turns_since_flirt"
        ] = 0

    if turn_mode == TURN_MODE_CHANGE_TOPIC:
        internal_state[
            "topic_change_cooldown"
        ] = 2

        internal_state[
            "turns_since_topic_change"
        ] = 0

    if turn_mode == TURN_MODE_SHARE:
        internal_state[
            "turns_since_personal_share"
        ] = 0


def sincronizar_iniciativa_apos_resposta(
    relationship_state: dict[str, Any] | None,
    *,
    executed_turn_mode: str | None = None,
    turn_intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = (
        relationship_state
        if isinstance(
            relationship_state,
            dict,
        )
        else {}
    )

    internal_state = obter_estado_interno_mary(
        state
    )

    intent = (
        turn_intent
        if isinstance(
            turn_intent,
            dict,
        )
        else state.get(
            "current_turn_intent"
        )
    )

    if not isinstance(intent, dict):
        intent = criar_intencao_turno_padrao()

    intended_mode = normalizar_modo_turno(
        intent.get(
            "turn_mode"
        )
    )

    completed_mode = normalizar_modo_turno(
        executed_turn_mode
        or intended_mode
    )

    internal_state[
        "last_turn_mode"
    ] = intended_mode

    internal_state[
        "last_completed_turn_mode"
    ] = completed_mode

    if modo_e_iniciativa(
        completed_mode
    ):
        internal_state[
            "consecutive_initiative_turns"
        ] += 1

        internal_state[
            "consecutive_reactive_turns"
        ] = 0

        # A iniciativa foi descarregada parcialmente.
        internal_state[
            "initiative_drive"
        ] = limitar_valor(
            internal_state[
                "initiative_drive"
            ]
            - 0.10
        )

    else:
        internal_state[
            "consecutive_reactive_turns"
        ] += 1

        internal_state[
            "consecutive_initiative_turns"
        ] = 0

        # Respostas reativas acumulam vontade de liderar.
        internal_state[
            "initiative_drive"
        ] = limitar_valor(
            internal_state[
                "initiative_drive"
            ]
            + 0.06
        )

    aplicar_cooldown_por_modo(
        internal_state,
        completed_mode,
    )

    # Evita uma Mary artificialmente intensa em todos os turnos.
    if (
        internal_state[
            "consecutive_initiative_turns"
        ] >= 2
    ):
        internal_state[
            "initiative_cooldown"
        ] = max(
            1,
            internal_state[
                "initiative_cooldown"
            ],
        )

    internal_state[
        "preferred_turn_mode"
    ] = TURN_MODE_RESPOND

    state[
        "mary_internal_state"
    ] = internal_state

    state[
        "last_turn_intent"
    ] = intent

    state[
        "current_turn_intent"
    ] = {}

    return state


# ==========================================================
# CONTEXTO PARA O PROMPT
# ==========================================================


def montar_contexto_iniciativa(
    relationship_state: dict[str, Any] | None,
    turn_intent: dict[str, Any] | None = None,
) -> str:
    state = (
        relationship_state
        if isinstance(
            relationship_state,
            dict,
        )
        else {}
    )

    internal_state = obter_estado_interno_mary(
        state
    )

    intent = (
        turn_intent
        if isinstance(
            turn_intent,
            dict,
        )
        else state.get(
            "current_turn_intent"
        )
    )

    if not isinstance(intent, dict):
        intent = criar_intencao_turno_padrao()

    return f"""
[AGÊNCIA E INTENÇÃO DE MARY NESTE TURNO]

Modo do turno:
{intent.get("turn_mode", TURN_MODE_RESPOND)}

Intensidade:
{limitar_valor(intent.get("intensity", 0.25)):.2f}

Direção:
{intent.get("topic_direction", TOPIC_DIRECTION_CURRENT)}

Deve responder ao conteúdo do usuário:
{normalizar_bool(intent.get("must_address_user_message"), default=True)}

Pode mudar de assunto:
{normalizar_bool(intent.get("may_change_topic"))}

Pode liderar a conversa:
{normalizar_bool(intent.get("may_lead_conversation"))}

Pode iniciar flerte:
{normalizar_bool(intent.get("may_initiate_flirt"))}

Pode iniciar tensão sexual:
{normalizar_bool(intent.get("may_initiate_sexual_tension"))}

Pode iniciar cena sexual:
{normalizar_bool(intent.get("may_initiate_sexual_scene"))}

Evitar pergunta:
{normalizar_bool(intent.get("avoid_question"))}

Intenção pendente:
{intent.get("unfinished_intention", "")}

Motivo interno:
{intent.get("reason", "")}

ESTADO INTERNO RELEVANTE:
- desejo: {internal_state["current_desire"]:.2f}
- curiosidade: {internal_state["current_curiosity"]:.2f}
- afeto: {internal_state["current_affection"]:.2f}
- irritação: {internal_state["current_irritation"]:.2f}
- ludicidade: {internal_state["current_playfulness"]:.2f}
- impulso de iniciativa: {internal_state["initiative_drive"]:.2f}

REGRAS:
- Mary não é uma atendente esperando instruções.
- Ela deve responder ao usuário sem abandonar sua própria intenção.
- Quando puder liderar, deve acrescentar vontade, opinião ou direção própria.
- Quando puder mudar de assunto, pode responder brevemente ao tema atual e
  puxar outro assunto sem pedir autorização.
- Quando puder flertar, a provocação pode partir dela.
- Quando puder iniciar tensão sexual, não espere uma frase sexual do usuário.
- Quando puder iniciar uma cena sexual, a iniciativa pode ser claramente dela.
- Não mencione motores, estados, modos, níveis, pontuações ou permissões.
- Não transforme toda iniciativa em pergunta.
- Não execute todos os comportamentos possíveis ao mesmo tempo.
- Realize apenas a intenção principal deste turno.
""".strip()
