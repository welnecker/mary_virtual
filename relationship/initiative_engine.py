from __future__ import annotations

from copy import deepcopy
from typing import Any


TURN_MODE_RESPOND = "respond"
TURN_MODE_SHARE = "share_something"
TURN_MODE_CHANGE_TOPIC = "change_topic"
TURN_MODE_TEASE = "tease"
TURN_MODE_INITIATE_FLIRT = "initiate_flirt"
TURN_MODE_INCREASE_INTIMACY = "increase_intimacy"
TURN_MODE_INITIATE_SEXUAL_TENSION = "initiate_sexual_tension"
TURN_MODE_INITIATE_SEXUAL_SCENE = "initiate_sexual_scene"
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

TOPIC_DIRECTION_CURRENT = "current_topic"
TOPIC_DIRECTION_PERSONAL = "personal"
TOPIC_DIRECTION_RELATIONSHIP = "relationship"
TOPIC_DIRECTION_ROMANTIC = "romantic"
TOPIC_DIRECTION_SEXUAL = "sexual"
TOPIC_DIRECTION_EMOTIONAL = "emotional"
TOPIC_DIRECTION_NEW_TOPIC = "new_topic"
TOPIC_DIRECTION_BOUNDARY = "boundary"


DEFAULT_MARY_INTERNAL_STATE: dict[str, Any] = {
    "current_mood": "confident",
    "current_desire": 0.12,
    "current_curiosity": 0.38,
    "current_affection": 0.0,
    "current_irritation": 0.0,
    "current_playfulness": 0.42,
    "initiative_drive": 0.62,
    "social_energy": 0.72,
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
    "intensity": 0.42,
    "topic_direction": TOPIC_DIRECTION_CURRENT,
    "must_address_user_message": True,
    "may_change_topic": False,
    "may_lead_conversation": True,
    "may_initiate_flirt": True,
    "may_initiate_sexual_tension": False,
    "may_initiate_sexual_scene": False,
    "must_ask_question": False,
    "avoid_question": True,
    "unfinished_intention": "",
    "reason": "react_with_agency",
}


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def limitar_valor(
    value: Any,
    *,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(minimum, min(maximum, safe_float(value, minimum)))


def normalizar_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "sim", "s", "verdadeiro"}:
        return True
    if text in {"false", "0", "no", "nao", "não", "n", "falso", ""}:
        return False
    return default


def normalizar_modo_turno(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in TURN_MODES else TURN_MODE_RESPOND


def criar_estado_interno_mary() -> dict[str, Any]:
    return deepcopy(DEFAULT_MARY_INTERNAL_STATE)


def criar_intencao_turno_padrao() -> dict[str, Any]:
    return deepcopy(DEFAULT_TURN_INTENT)


def normalizar_estado_interno_mary(
    value: dict[str, Any] | None,
) -> dict[str, Any]:
    state = criar_estado_interno_mary()
    if isinstance(value, dict):
        state.update(value)

    for field in (
        "current_desire",
        "current_curiosity",
        "current_affection",
        "current_irritation",
        "current_playfulness",
        "initiative_drive",
        "social_energy",
    ):
        state[field] = limitar_valor(state.get(field))

    for field in (
        "initiative_cooldown",
        "sexual_initiative_cooldown",
        "topic_change_cooldown",
        "consecutive_reactive_turns",
        "consecutive_initiative_turns",
        "turns_since_flirt",
        "turns_since_topic_change",
        "turns_since_personal_share",
    ):
        state[field] = max(0, safe_int(state.get(field)))

    state["preferred_turn_mode"] = normalizar_modo_turno(
        state.get("preferred_turn_mode")
    )
    return state


def normalizar_sinais(signals: dict[str, Any] | None) -> dict[str, Any]:
    return dict(signals) if isinstance(signals, dict) else {}


def obter_estado_interno_mary(
    relationship_state: dict[str, Any],
) -> dict[str, Any]:
    state = normalizar_estado_interno_mary(
        relationship_state.get("mary_internal_state")
    )
    relationship_state["mary_internal_state"] = state
    return state


def obter_nivel_sexual(relationship_state: dict[str, Any]) -> int:
    return max(
        0,
        min(
            5,
            safe_int(
                relationship_state.get(
                    "sexual_level",
                    relationship_state.get("sexual_intimacy", 0),
                )
            ),
        ),
    )


def obter_estagio_emocional(relationship_state: dict[str, Any]) -> str:
    return str(
        relationship_state.get(
            "emotional_stage",
            relationship_state.get("stage", "first_contact"),
        )
        or "first_contact"
    ).strip().lower()


def obter_fase_sexual(relationship_state: dict[str, Any]) -> str:
    sexual_state = relationship_state.get("sexual_state")
    if not isinstance(sexual_state, dict):
        return "idle"
    return str(sexual_state.get("scene_phase") or "idle").strip().lower()


def obter_estado_cenario_ativo(
    relationship_state: dict[str, Any],
) -> dict[str, Any]:
    for key in (
        "active_scenario",
        "scenario_state",
        "scene_state",
        "current_scenario",
        "scenario_context",
    ):
        candidate = relationship_state.get(key)
        if not isinstance(candidate, dict):
            continue
        nested = candidate.get("scene_state")
        if isinstance(nested, dict):
            candidate = nested
        active = candidate.get("scene_active")
        if active is None:
            active = candidate.get("active")
        if active is None:
            active = candidate.get("status") == "active"
        if normalizar_bool(active):
            return candidate
    return {}


def cenario_ativo(relationship_state: dict[str, Any]) -> bool:
    return bool(obter_estado_cenario_ativo(relationship_state))


def obter_nivel_seducao_cenario(
    relationship_state: dict[str, Any],
) -> int:
    scene = obter_estado_cenario_ativo(relationship_state)
    return max(0, min(6, safe_int(scene.get("seduction_level"))))


def fase_sexual_ativa(phase: str) -> bool:
    return str(phase or "").strip().lower() not in {
        "",
        "idle",
        "none",
        "inactive",
    }


def usuario_estabeleceu_limite(signals: dict[str, Any]) -> bool:
    return bool(
        signals.get("boundary_signal")
        or signals.get("rejection_signal")
        or signals.get("stop_signal")
    )


def usuario_foi_hostil(signals: dict[str, Any]) -> bool:
    return bool(signals.get("hostility_signal"))


def _ajustar_estado_por_sinais(
    internal: dict[str, Any],
    signals: dict[str, Any],
) -> None:
    if signals.get("sexual_signal") or signals.get("eager_signal"):
        internal["current_desire"] = limitar_valor(
            internal["current_desire"] + 0.18
        )
        internal["initiative_drive"] = limitar_valor(
            internal["initiative_drive"] + 0.12
        )

    if signals.get("playful_signal") or signals.get("humor_signal"):
        internal["current_playfulness"] = limitar_valor(
            internal["current_playfulness"] + 0.14
        )

    if signals.get("affection_signal") or signals.get("emotional_signal"):
        internal["current_affection"] = limitar_valor(
            internal["current_affection"] + 0.12
        )

    if signals.get("hostility_signal"):
        internal["current_irritation"] = limitar_valor(
            internal["current_irritation"] + 0.28
        )

    if usuario_estabeleceu_limite(signals):
        internal["current_desire"] = limitar_valor(
            internal["current_desire"] - 0.22
        )
        internal["current_irritation"] = limitar_valor(
            internal["current_irritation"] + 0.08
        )


def atualizar_estado_interno_mary(
    relationship_state: dict[str, Any] | None,
    *,
    signals: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = relationship_state if isinstance(relationship_state, dict) else {}
    internal = obter_estado_interno_mary(state)
    signals_normalized = normalizar_sinais(signals)

    for field in (
        "initiative_cooldown",
        "sexual_initiative_cooldown",
        "topic_change_cooldown",
    ):
        internal[field] = max(0, internal[field] - 1)

    for field in (
        "turns_since_flirt",
        "turns_since_topic_change",
        "turns_since_personal_share",
    ):
        internal[field] += 1

    _ajustar_estado_por_sinais(internal, signals_normalized)
    state["mary_internal_state"] = internal
    return internal


def criar_intencao(
    *,
    turn_mode: str = TURN_MODE_RESPOND,
    intensity: float = 0.42,
    topic_direction: str = TOPIC_DIRECTION_CURRENT,
    reason: str = "react_with_agency",
    must_address_user_message: bool = True,
    may_change_topic: bool = False,
    may_lead_conversation: bool = True,
    may_initiate_flirt: bool = True,
    may_initiate_sexual_tension: bool = False,
    may_initiate_sexual_scene: bool = False,
    must_ask_question: bool = False,
    avoid_question: bool = True,
    unfinished_intention: str = "",
) -> dict[str, Any]:
    return {
        "turn_mode": normalizar_modo_turno(turn_mode),
        "intensity": limitar_valor(intensity),
        "topic_direction": topic_direction,
        "must_address_user_message": bool(must_address_user_message),
        "may_change_topic": bool(may_change_topic),
        "may_lead_conversation": bool(may_lead_conversation),
        "may_initiate_flirt": bool(may_initiate_flirt),
        "may_initiate_sexual_tension": bool(may_initiate_sexual_tension),
        "may_initiate_sexual_scene": bool(may_initiate_sexual_scene),
        "must_ask_question": bool(must_ask_question),
        "avoid_question": bool(avoid_question),
        "unfinished_intention": str(unfinished_intention or "").strip(),
        "reason": str(reason or "").strip(),
    }


def _resolver_intencao(
    relationship_state: dict[str, Any],
    internal: dict[str, Any],
    signals: dict[str, Any],
) -> dict[str, Any]:
    phase = obter_fase_sexual(relationship_state)
    sexual_level = obter_nivel_sexual(relationship_state)
    seduction_level = obter_nivel_seducao_cenario(relationship_state)
    interaction_count = safe_int(relationship_state.get("interaction_count"))

    if usuario_estabeleceu_limite(signals):
        return criar_intencao(
            turn_mode=TURN_MODE_SLOW_DOWN,
            intensity=max(0.28, internal["current_playfulness"]),
            topic_direction=TOPIC_DIRECTION_BOUNDARY,
            reason="accept_boundary_without_becoming_bland",
            may_lead_conversation=True,
            may_initiate_flirt=False,
            avoid_question=True,
        )

    if usuario_foi_hostil(signals):
        return criar_intencao(
            turn_mode=TURN_MODE_SHOW_IRRITATION,
            intensity=max(0.48, internal["current_irritation"]),
            topic_direction=TOPIC_DIRECTION_BOUNDARY,
            reason="respond_with_backbone_and_sarcasm",
            may_lead_conversation=True,
            may_initiate_flirt=False,
            avoid_question=True,
        )

    if fase_sexual_ativa(phase):
        return criar_intencao(
            turn_mode=TURN_MODE_INITIATE_SEXUAL_SCENE,
            intensity=max(0.70, internal["current_desire"]),
            topic_direction=TOPIC_DIRECTION_SEXUAL,
            reason="active_intimacy_requires_mary_to_act",
            may_lead_conversation=True,
            may_initiate_flirt=True,
            may_initiate_sexual_tension=True,
            may_initiate_sexual_scene=True,
            avoid_question=True,
        )

    if signals.get("eager_signal") or signals.get("sexual_signal"):
        if sexual_level >= 3 or seduction_level >= 3:
            return criar_intencao(
                turn_mode=TURN_MODE_INITIATE_SEXUAL_SCENE,
                intensity=max(0.68, internal["current_desire"]),
                topic_direction=TOPIC_DIRECTION_SEXUAL,
                reason="match_user_urgency_with_bold_action",
                may_lead_conversation=True,
                may_initiate_flirt=True,
                may_initiate_sexual_tension=True,
                may_initiate_sexual_scene=True,
                avoid_question=True,
            )
        return criar_intencao(
            turn_mode=TURN_MODE_INITIATE_SEXUAL_TENSION,
            intensity=max(0.52, internal["current_desire"]),
            topic_direction=TOPIC_DIRECTION_SEXUAL,
            reason="answer_eagerness_with_desire_and_humor",
            may_lead_conversation=True,
            may_initiate_flirt=True,
            may_initiate_sexual_tension=True,
            avoid_question=True,
        )

    if signals.get("playful_signal") or signals.get("humor_signal"):
        return criar_intencao(
            turn_mode=TURN_MODE_TEASE,
            intensity=max(0.44, internal["current_playfulness"]),
            topic_direction=TOPIC_DIRECTION_CURRENT,
            reason="return_humor_with_a_specific_provocation",
            may_lead_conversation=True,
            may_initiate_flirt=True,
            avoid_question=True,
        )

    if signals.get("affection_signal") or signals.get("emotional_signal"):
        return criar_intencao(
            turn_mode=TURN_MODE_INCREASE_INTIMACY,
            intensity=max(0.42, internal["current_affection"]),
            topic_direction=TOPIC_DIRECTION_EMOTIONAL,
            reason="turn_emotion_into_one_concrete_choice",
            may_lead_conversation=True,
            may_initiate_flirt=sexual_level >= 2,
            avoid_question=True,
        )

    if internal["consecutive_reactive_turns"] >= 2:
        return criar_intencao(
            turn_mode=TURN_MODE_TEASE,
            intensity=max(0.42, internal["initiative_drive"]),
            topic_direction=TOPIC_DIRECTION_CURRENT,
            reason="break_passive_sequence_with_personality",
            may_lead_conversation=True,
            may_initiate_flirt=True,
            avoid_question=True,
        )

    if interaction_count >= 40:
        return criar_intencao(
            turn_mode=TURN_MODE_INCREASE_INTIMACY,
            intensity=max(0.58, internal["initiative_drive"]),
            topic_direction=(
                TOPIC_DIRECTION_SEXUAL
                if sexual_level >= 3
                else TOPIC_DIRECTION_EMOTIONAL
            ),
            reason="short_story_requires_consequence_now",
            may_lead_conversation=True,
            may_initiate_flirt=True,
            may_initiate_sexual_tension=sexual_level >= 2,
            may_initiate_sexual_scene=sexual_level >= 3,
            avoid_question=True,
        )

    return criar_intencao(
        turn_mode=TURN_MODE_RESPOND,
        intensity=max(0.40, internal["initiative_drive"]),
        topic_direction=TOPIC_DIRECTION_CURRENT,
        reason="respond_then_move_without_waiting",
        may_lead_conversation=True,
        may_initiate_flirt=True,
        may_initiate_sexual_tension=sexual_level >= 2,
        may_initiate_sexual_scene=False,
        avoid_question=True,
    )


def escolher_intencao_por_prioridade(
    relationship_state: dict[str, Any],
    internal_state: dict[str, Any],
    signals: dict[str, Any],
) -> dict[str, Any]:
    return _resolver_intencao(
        relationship_state,
        internal_state,
        signals,
    )


def planejar_iniciativa_mary(
    relationship_state: dict[str, Any] | None,
    *,
    signals: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    state = relationship_state if isinstance(relationship_state, dict) else {}
    signals_normalized = normalizar_sinais(signals)
    internal = atualizar_estado_interno_mary(
        state,
        signals=signals_normalized,
    )
    intent = escolher_intencao_por_prioridade(
        state,
        internal,
        signals_normalized,
    )

    internal["preferred_turn_mode"] = intent["turn_mode"]
    internal["last_initiative_reason"] = intent["reason"]
    internal["last_topic_direction"] = intent["topic_direction"]
    state["mary_internal_state"] = internal
    state["current_turn_intent"] = intent
    return state, intent


def modo_e_iniciativa(turn_mode: str) -> bool:
    return normalizar_modo_turno(turn_mode) != TURN_MODE_RESPOND


def aplicar_cooldown_por_modo(
    internal_state: dict[str, Any],
    turn_mode: str,
) -> None:
    mode = normalizar_modo_turno(turn_mode)
    if mode in {TURN_MODE_TEASE, TURN_MODE_INITIATE_FLIRT}:
        internal_state["initiative_cooldown"] = 1
        internal_state["turns_since_flirt"] = 0
    if mode in {
        TURN_MODE_INITIATE_SEXUAL_TENSION,
        TURN_MODE_INITIATE_SEXUAL_SCENE,
    }:
        internal_state["sexual_initiative_cooldown"] = 1
        internal_state["turns_since_flirt"] = 0
    if mode == TURN_MODE_CHANGE_TOPIC:
        internal_state["topic_change_cooldown"] = 1
        internal_state["turns_since_topic_change"] = 0
    if mode == TURN_MODE_SHARE:
        internal_state["turns_since_personal_share"] = 0


def sincronizar_iniciativa_apos_resposta(
    relationship_state: dict[str, Any] | None,
    *,
    executed_turn_mode: str | None = None,
    turn_intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = relationship_state if isinstance(relationship_state, dict) else {}
    internal = obter_estado_interno_mary(state)
    intent = (
        turn_intent
        if isinstance(turn_intent, dict)
        else state.get("current_turn_intent")
    )
    if not isinstance(intent, dict):
        intent = criar_intencao_turno_padrao()

    completed_mode = normalizar_modo_turno(
        executed_turn_mode or intent.get("turn_mode")
    )
    internal["last_turn_mode"] = normalizar_modo_turno(
        intent.get("turn_mode")
    )
    internal["last_completed_turn_mode"] = completed_mode

    if modo_e_iniciativa(completed_mode):
        internal["consecutive_initiative_turns"] += 1
        internal["consecutive_reactive_turns"] = 0
        internal["initiative_drive"] = limitar_valor(
            internal["initiative_drive"] - 0.05
        )
    else:
        internal["consecutive_reactive_turns"] += 1
        internal["consecutive_initiative_turns"] = 0
        internal["initiative_drive"] = limitar_valor(
            internal["initiative_drive"] + 0.10
        )

    aplicar_cooldown_por_modo(internal, completed_mode)
    internal["preferred_turn_mode"] = TURN_MODE_RESPOND
    state["mary_internal_state"] = internal
    state["last_turn_intent"] = intent
    state["current_turn_intent"] = {}
    return state


def montar_contexto_iniciativa(
    relationship_state: dict[str, Any] | None,
    turn_intent: dict[str, Any] | None = None,
) -> str:
    state = relationship_state if isinstance(relationship_state, dict) else {}
    internal = obter_estado_interno_mary(state)
    intent = (
        turn_intent
        if isinstance(turn_intent, dict)
        else state.get("current_turn_intent")
    )
    if not isinstance(intent, dict):
        intent = criar_intencao_turno_padrao()

    return (
        "[INICIATIVA DO TURNO]\n"
        f"modo={intent.get('turn_mode', TURN_MODE_RESPOND)}; "
        f"intensidade={limitar_valor(intent.get('intensity', 0.42)):.2f}; "
        f"direção={intent.get('topic_direction', TOPIC_DIRECTION_CURRENT)}; "
        f"liderar={normalizar_bool(intent.get('may_lead_conversation'), default=True)}; "
        f"flerte={normalizar_bool(intent.get('may_initiate_flirt'))}; "
        f"tensão_sexual={normalizar_bool(intent.get('may_initiate_sexual_tension'))}; "
        f"cena_sexual={normalizar_bool(intent.get('may_initiate_sexual_scene'))}; "
        f"evitar_pergunta={normalizar_bool(intent.get('avoid_question'))}; "
        f"desejo={internal['current_desire']:.2f}; "
        f"humor={internal['current_playfulness']:.2f}; "
        f"irritação={internal['current_irritation']:.2f}; "
        f"impulso={internal['initiative_drive']:.2f}; "
        f"motivo={intent.get('reason', '')}.\n"
        "Mary executa uma iniciativa concreta e compatível com o usuário. "
        "Pode usar humor, sarcasmo, desejo, carinho, vulgaridade ou firmeza. "
        "Não espera comando para cada gesto, não repete preparação e não transforma iniciativa em pergunta."
    )


__all__ = [
    "TURN_MODE_RESPOND",
    "TURN_MODE_SHARE",
    "TURN_MODE_CHANGE_TOPIC",
    "TURN_MODE_TEASE",
    "TURN_MODE_INITIATE_FLIRT",
    "TURN_MODE_INCREASE_INTIMACY",
    "TURN_MODE_INITIATE_SEXUAL_TENSION",
    "TURN_MODE_INITIATE_SEXUAL_SCENE",
    "TURN_MODE_SEEK_AFFECTION",
    "TURN_MODE_SLOW_DOWN",
    "TURN_MODE_SET_BOUNDARY",
    "TURN_MODE_SHOW_IRRITATION",
    "TOPIC_DIRECTION_CURRENT",
    "TOPIC_DIRECTION_PERSONAL",
    "TOPIC_DIRECTION_RELATIONSHIP",
    "TOPIC_DIRECTION_ROMANTIC",
    "TOPIC_DIRECTION_SEXUAL",
    "TOPIC_DIRECTION_EMOTIONAL",
    "TOPIC_DIRECTION_NEW_TOPIC",
    "TOPIC_DIRECTION_BOUNDARY",
    "DEFAULT_MARY_INTERNAL_STATE",
    "DEFAULT_TURN_INTENT",
    "criar_estado_interno_mary",
    "criar_intencao_turno_padrao",
    "normalizar_estado_interno_mary",
    "obter_estado_interno_mary",
    "atualizar_estado_interno_mary",
    "criar_intencao",
    "escolher_intencao_por_prioridade",
    "planejar_iniciativa_mary",
    "sincronizar_iniciativa_apos_resposta",
    "montar_contexto_iniciativa",
]
