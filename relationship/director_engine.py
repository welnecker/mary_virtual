from __future__ import annotations

from copy import deepcopy
from typing import Any

from relationship.initiative_engine import (
    TOPIC_DIRECTION_BOUNDARY,
    TOPIC_DIRECTION_CURRENT,
    TOPIC_DIRECTION_EMOTIONAL,
    TOPIC_DIRECTION_NEW_TOPIC,
    TOPIC_DIRECTION_PERSONAL,
    TOPIC_DIRECTION_RELATIONSHIP,
    TOPIC_DIRECTION_ROMANTIC,
    TOPIC_DIRECTION_SEXUAL,
    TURN_MODE_CHANGE_TOPIC,
    TURN_MODE_INCREASE_INTIMACY,
    TURN_MODE_INITIATE_FLIRT,
    TURN_MODE_INITIATE_SEXUAL_SCENE,
    TURN_MODE_INITIATE_SEXUAL_TENSION,
    TURN_MODE_RESPOND,
    TURN_MODE_SEEK_AFFECTION,
    TURN_MODE_SET_BOUNDARY,
    TURN_MODE_SHARE,
    TURN_MODE_SHOW_IRRITATION,
    TURN_MODE_SLOW_DOWN,
    TURN_MODE_TEASE,
    criar_intencao_turno_padrao,
    normalizar_estado_interno_mary,
)


# ==========================================================
# MODOS DE EXPERIÊNCIA
# ==========================================================


EXPERIENCE_MODE_NATURAL = "natural_conversation"
EXPERIENCE_MODE_PERSONAL_SHARE = "personal_share"
EXPERIENCE_MODE_UNEXPECTED_CONFESSION = (
    "unexpected_confession"
)
EXPERIENCE_MODE_PLAYFUL_CHALLENGE = "playful_challenge"
EXPERIENCE_MODE_PRIVATE_JOKE = "private_joke"
EXPERIENCE_MODE_MEMORY_CALLBACK = "memory_callback"
EXPERIENCE_MODE_UNFINISHED_REVEAL = "unfinished_reveal"
EXPERIENCE_MODE_EMOTIONAL_REVERSAL = "emotional_reversal"
EXPERIENCE_MODE_GENTLE_PROVOCATION = "gentle_provocation"
EXPERIENCE_MODE_BOLD_PROVOCATION = "bold_provocation"
EXPERIENCE_MODE_ROMANTIC_ESCALATION = (
    "romantic_escalation"
)
EXPERIENCE_MODE_SEXUAL_TENSION = "sexual_tension"
EXPERIENCE_MODE_SEXUAL_INITIATIVE = "sexual_initiative"
EXPERIENCE_MODE_SEEK_AFFECTION = "seek_affection"
EXPERIENCE_MODE_SHOW_JEALOUSY = "show_jealousy"
EXPERIENCE_MODE_SHOW_VULNERABILITY = "show_vulnerability"
EXPERIENCE_MODE_SET_BOUNDARY = "set_boundary"
EXPERIENCE_MODE_CREATE_SHARED_PLAN = "create_shared_plan"
EXPERIENCE_MODE_CONTINUE_SHARED_FANTASY = (
    "continue_shared_fantasy"
)
EXPERIENCE_MODE_SURPRISE_TOPIC = "surprise_topic"
EXPERIENCE_MODE_HUMOR_BREAK = "humor_break"
EXPERIENCE_MODE_AFTERCARE = "aftercare"
EXPERIENCE_MODE_FRUSTRATION = "frustration"


EXPERIENCE_MODES: tuple[str, ...] = (
    EXPERIENCE_MODE_NATURAL,
    EXPERIENCE_MODE_PERSONAL_SHARE,
    EXPERIENCE_MODE_UNEXPECTED_CONFESSION,
    EXPERIENCE_MODE_PLAYFUL_CHALLENGE,
    EXPERIENCE_MODE_PRIVATE_JOKE,
    EXPERIENCE_MODE_MEMORY_CALLBACK,
    EXPERIENCE_MODE_UNFINISHED_REVEAL,
    EXPERIENCE_MODE_EMOTIONAL_REVERSAL,
    EXPERIENCE_MODE_GENTLE_PROVOCATION,
    EXPERIENCE_MODE_BOLD_PROVOCATION,
    EXPERIENCE_MODE_ROMANTIC_ESCALATION,
    EXPERIENCE_MODE_SEXUAL_TENSION,
    EXPERIENCE_MODE_SEXUAL_INITIATIVE,
    EXPERIENCE_MODE_SEEK_AFFECTION,
    EXPERIENCE_MODE_SHOW_JEALOUSY,
    EXPERIENCE_MODE_SHOW_VULNERABILITY,
    EXPERIENCE_MODE_SET_BOUNDARY,
    EXPERIENCE_MODE_CREATE_SHARED_PLAN,
    EXPERIENCE_MODE_CONTINUE_SHARED_FANTASY,
    EXPERIENCE_MODE_SURPRISE_TOPIC,
    EXPERIENCE_MODE_HUMOR_BREAK,
    EXPERIENCE_MODE_AFTERCARE,
    EXPERIENCE_MODE_FRUSTRATION,
)


# ==========================================================
# REGISTROS DE VOZ
# ==========================================================


VOICE_REGISTER_NATURAL = "natural"
VOICE_REGISTER_PLAYFUL = "playful"
VOICE_REGISTER_WARM = "warm"
VOICE_REGISTER_ROMANTIC = "romantic"
VOICE_REGISTER_VULNERABLE = "vulnerable"
VOICE_REGISTER_TEASING = "teasing"
VOICE_REGISTER_BOLD = "bold"
VOICE_REGISTER_EXPLICIT_PLAYFUL = "explicit_playful"
VOICE_REGISTER_EXPLICIT_INTENSE = "explicit_intense"
VOICE_REGISTER_AFFECTIONATE_SEXUAL = (
    "affectionate_sexual"
)
VOICE_REGISTER_IRRITATED = "irritated"
VOICE_REGISTER_BOUNDARY = "boundary"
VOICE_REGISTER_AFTERCARE = "aftercare"


VOICE_REGISTERS: tuple[str, ...] = (
    VOICE_REGISTER_NATURAL,
    VOICE_REGISTER_PLAYFUL,
    VOICE_REGISTER_WARM,
    VOICE_REGISTER_ROMANTIC,
    VOICE_REGISTER_VULNERABLE,
    VOICE_REGISTER_TEASING,
    VOICE_REGISTER_BOLD,
    VOICE_REGISTER_EXPLICIT_PLAYFUL,
    VOICE_REGISTER_EXPLICIT_INTENSE,
    VOICE_REGISTER_AFFECTIONATE_SEXUAL,
    VOICE_REGISTER_IRRITATED,
    VOICE_REGISTER_BOUNDARY,
    VOICE_REGISTER_AFTERCARE,
)


# ==========================================================
# TIPOS DE PENDÊNCIA NARRATIVA
# ==========================================================


THREAD_TYPE_UNFINISHED_REVEAL = "unfinished_reveal"
THREAD_TYPE_PROMISE = "promise"
THREAD_TYPE_PRIVATE_JOKE = "private_joke"
THREAD_TYPE_SHARED_PLAN = "shared_plan"
THREAD_TYPE_EMOTIONAL_QUESTION = "emotional_question"
THREAD_TYPE_ROMANTIC_TENSION = "romantic_tension"
THREAD_TYPE_SEXUAL_TENSION = "sexual_tension"
THREAD_TYPE_SHARED_FANTASY = "shared_fantasy"


THREAD_TYPES: tuple[str, ...] = (
    THREAD_TYPE_UNFINISHED_REVEAL,
    THREAD_TYPE_PROMISE,
    THREAD_TYPE_PRIVATE_JOKE,
    THREAD_TYPE_SHARED_PLAN,
    THREAD_TYPE_EMOTIONAL_QUESTION,
    THREAD_TYPE_ROMANTIC_TENSION,
    THREAD_TYPE_SEXUAL_TENSION,
    THREAD_TYPE_SHARED_FANTASY,
)


# ==========================================================
# ESTADO PADRÃO DO DIRETOR
# ==========================================================


DEFAULT_EXPERIENCE_STATE: dict[str, Any] = {
    "current_mode": EXPERIENCE_MODE_NATURAL,
    "previous_mode": "",
    "recent_modes": [],
    "surprise_budget": 0.42,
    "turns_since_surprise": 0,
    "turns_since_reveal": 0,
    "turns_since_callback": 0,
    "turns_since_humor": 0,
    "turns_since_vulnerability": 0,
    "turns_since_romantic_escalation": 0,
    "turns_since_sexual_initiative": 0,
    "open_threads": [],
    "shared_rituals": [],
    "private_jokes": [],
    "promises": [],
    "active_arc": "",
    "active_arc_step": 0,
    "last_primary_intention": "",
    "last_emotional_color": "",
    "last_voice_register": "",
    "last_surprise_type": "",
    "last_direction_reason": "",
}


DEFAULT_VOICE_STATE: dict[str, Any] = {
    "warmth": 0.34,
    "playfulness": 0.24,
    "boldness": 0.12,
    "vulnerability": 0.10,
    "romantic_intensity": 0.0,
    "sexual_intensity": 0.0,
    "sexual_explicitness": 0.0,
    "vulgarity": 0.04,
    "body_confidence": 0.34,
    "emotional_openness": 0.14,
    "humor": 0.22,
    "tenderness": 0.12,
    "jealousy": 0.0,
}

DEFAULT_TURN_DIRECTION: dict[str, Any] = {
    "experience_mode": EXPERIENCE_MODE_NATURAL,
    "primary_intention": "respond_naturally",
    "emotional_color": "natural_presence",
    "voice_register": VOICE_REGISTER_NATURAL,
    "response_scope": "brief",
    "surprise_level": 0.0,
    "topic_direction": TOPIC_DIRECTION_CURRENT,
    "should_lead": False,
    "should_reveal_something": False,
    "should_create_pending_thread": False,
    "should_resume_thread": False,
    "open_thread_id": "",
    "callback_memory_id": "",
    "scene_seed": "",
    "body_focus_allowed": False,
    "romantic_expression_allowed": False,
    "sexual_expression_allowed": False,
    "explicit_sexual_language_allowed": False,
    "must_preserve_current_scene": False,
    "must_avoid_repetition": True,
    "must_address_user_message": True,
    "avoid_question": True,
    "reason": "default_direction",
    "voice_state": deepcopy(
        DEFAULT_VOICE_STATE
    ),
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
        "sim",
        "s",
        "yes",
        "verdadeiro",
    }:
        return True

    if text in {
        "false",
        "0",
        "nao",
        "não",
        "n",
        "no",
        "falso",
        "",
    }:
        return False

    return default


def normalizar_modo_experiencia(
    value: Any,
) -> str:
    normalized = str(
        value or ""
    ).strip().lower()

    if normalized in EXPERIENCE_MODES:
        return normalized

    return EXPERIENCE_MODE_NATURAL


def normalizar_registro_voz(
    value: Any,
) -> str:
    normalized = str(
        value or ""
    ).strip().lower()

    if normalized in VOICE_REGISTERS:
        return normalized

    return VOICE_REGISTER_NATURAL


def criar_estado_experiencia() -> dict[str, Any]:
    return deepcopy(
        DEFAULT_EXPERIENCE_STATE
    )


def criar_estado_voz() -> dict[str, Any]:
    return deepcopy(
        DEFAULT_VOICE_STATE
    )


def criar_direcao_turno_padrao() -> dict[str, Any]:
    return deepcopy(
        DEFAULT_TURN_DIRECTION
    )


def normalizar_estado_voz(
    value: dict[str, Any] | None,
) -> dict[str, Any]:
    state = criar_estado_voz()

    if isinstance(value, dict):
        state.update(value)

    for field in DEFAULT_VOICE_STATE:
        state[field] = limitar_valor(
            state.get(field)
        )

    return state


def normalizar_thread(
    thread: Any,
) -> dict[str, Any]:
    if not isinstance(thread, dict):
        return {}

    thread_type = str(
        thread.get("type")
        or ""
    ).strip().lower()

    if thread_type not in THREAD_TYPES:
        return {}

    thread_id = str(
        thread.get("id")
        or ""
    ).strip()

    summary = str(
        thread.get("summary")
        or ""
    ).strip()

    if not thread_id or not summary:
        return {}

    return {
        "id": thread_id,
        "type": thread_type,
        "summary": summary,
        "created_turn": max(
            0,
            safe_int(
                thread.get(
                    "created_turn",
                    0,
                )
            ),
        ),
        "last_touched_turn": max(
            0,
            safe_int(
                thread.get(
                    "last_touched_turn",
                    0,
                )
            ),
        ),
        "urgency": limitar_valor(
            thread.get(
                "urgency",
                0.30,
            )
        ),
        "ready_to_resume": normalizar_bool(
            thread.get(
                "ready_to_resume"
            ),
            default=False,
        ),
        "resolved": normalizar_bool(
            thread.get(
                "resolved"
            ),
            default=False,
        ),
    }


def normalizar_estado_experiencia(
    value: dict[str, Any] | None,
) -> dict[str, Any]:
    state = criar_estado_experiencia()

    if isinstance(value, dict):
        state.update(value)

    state["current_mode"] = (
        normalizar_modo_experiencia(
            state.get(
                "current_mode"
            )
        )
    )

    state["previous_mode"] = (
        normalizar_modo_experiencia(
            state.get(
                "previous_mode"
            )
        )
        if state.get("previous_mode")
        else ""
    )

    recent_modes = state.get(
        "recent_modes"
    )

    if not isinstance(recent_modes, list):
        recent_modes = []

    state["recent_modes"] = [
        normalizar_modo_experiencia(
            mode
        )
        for mode in recent_modes[-8:]
    ]

    state["surprise_budget"] = limitar_valor(
        state.get(
            "surprise_budget",
            0.42,
        )
    )

    counter_fields = (
        "turns_since_surprise",
        "turns_since_reveal",
        "turns_since_callback",
        "turns_since_humor",
        "turns_since_vulnerability",
        "turns_since_romantic_escalation",
        "turns_since_sexual_initiative",
        "active_arc_step",
    )

    for field in counter_fields:
        state[field] = max(
            0,
            safe_int(
                state.get(field),
                0,
            ),
        )

    raw_threads = state.get(
        "open_threads"
    )

    if not isinstance(raw_threads, list):
        raw_threads = []

    state["open_threads"] = [
        normalized
        for thread in raw_threads
        if (
            normalized := normalizar_thread(
                thread
            )
        )
    ]

    for field in (
        "shared_rituals",
        "private_jokes",
        "promises",
    ):
        value_list = state.get(field)

        if not isinstance(value_list, list):
            value_list = []

        state[field] = value_list[-20:]

    state["last_voice_register"] = (
        normalizar_registro_voz(
            state.get(
                "last_voice_register"
            )
        )
        if state.get(
            "last_voice_register"
        )
        else ""
    )

    return state


def obter_estado_experiencia(
    relationship_state: dict[str, Any],
) -> dict[str, Any]:
    experience_state = (
        normalizar_estado_experiencia(
            relationship_state.get(
                "experience_state"
            )
        )
    )

    relationship_state[
        "experience_state"
    ] = experience_state

    return experience_state


def obter_estado_voz(
    relationship_state: dict[str, Any],
) -> dict[str, Any]:
    voice_state = normalizar_estado_voz(
        relationship_state.get(
            "voice_state"
        )
    )

    relationship_state[
        "voice_state"
    ] = voice_state

    return voice_state


def normalizar_sinais(
    signals: dict[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(signals, dict):
        return dict(signals)

    return {}


def normalizar_intencao(
    turn_intent: dict[str, Any] | None,
) -> dict[str, Any]:
    default = criar_intencao_turno_padrao()

    if isinstance(turn_intent, dict):
        default.update(turn_intent)

    return default


# ==========================================================
# LEITURA DO CONTEXTO
# ==========================================================


def obter_nivel_sexual(
    relationship_state: dict[str, Any],
) -> int:
    return max(
        0,
        min(
            5,
            safe_int(
                relationship_state.get(
                    "sexual_level",
                    0,
                )
            ),
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


def obter_interaction_count(
    relationship_state: dict[str, Any],
) -> int:
    return max(
        0,
        safe_int(
            relationship_state.get(
                "interaction_count",
                0,
            )
        ),
    )


def obter_estado_interno(
    relationship_state: dict[str, Any],
) -> dict[str, Any]:
    internal_state = (
        relationship_state.get(
            "mary_internal_state"
        )
    )

    return normalizar_estado_interno_mary(
        internal_state
        if isinstance(
            internal_state,
            dict,
        )
        else {}
    )


# ==========================================================
# RITMO E REPETIÇÃO
# ==========================================================


def incrementar_contadores_experiencia(
    experience_state: dict[str, Any],
) -> None:
    fields = (
        "turns_since_surprise",
        "turns_since_reveal",
        "turns_since_callback",
        "turns_since_humor",
        "turns_since_vulnerability",
        "turns_since_romantic_escalation",
        "turns_since_sexual_initiative",
    )

    for field in fields:
        experience_state[field] = (
            max(
                0,
                safe_int(
                    experience_state.get(
                        field,
                        0,
                    )
                ),
            )
            + 1
        )


def atualizar_orcamento_surpresa(
    experience_state: dict[str, Any],
    *,
    internal_state: dict[str, Any],
) -> None:
    turns_since_surprise = safe_int(
        experience_state.get(
            "turns_since_surprise",
            0,
        )
    )

    initiative_drive = limitar_valor(
        internal_state.get(
            "initiative_drive",
            0.0,
        )
    )

    curiosity = limitar_valor(
        internal_state.get(
            "current_curiosity",
            0.0,
        )
    )

    increase = (
        0.025
        + min(
            0.04,
            turns_since_surprise * 0.006,
        )
        + initiative_drive * 0.012
        + curiosity * 0.008
    )

    experience_state[
        "surprise_budget"
    ] = limitar_valor(
        experience_state.get(
            "surprise_budget",
            0.42,
        )
        + increase
    )


def modo_foi_recente(
    experience_state: dict[str, Any],
    mode: str,
    *,
    lookback: int = 3,
) -> bool:
    recent = experience_state.get(
        "recent_modes"
    )

    if not isinstance(recent, list):
        return False

    return mode in recent[
        -max(
            1,
            lookback,
        ):
    ]


def muitos_modos_intensos_recentes(
    experience_state: dict[str, Any],
) -> bool:
    intense_modes = {
        EXPERIENCE_MODE_UNEXPECTED_CONFESSION,
        EXPERIENCE_MODE_SHOW_VULNERABILITY,
        EXPERIENCE_MODE_ROMANTIC_ESCALATION,
        EXPERIENCE_MODE_BOLD_PROVOCATION,
        EXPERIENCE_MODE_SEXUAL_TENSION,
        EXPERIENCE_MODE_SEXUAL_INITIATIVE,
        EXPERIENCE_MODE_FRUSTRATION,
    }

    recent = experience_state.get(
        "recent_modes"
    )

    if not isinstance(recent, list):
        return False

    count = sum(
        1
        for mode in recent[-4:]
        if mode in intense_modes
    )

    return count >= 2


# ==========================================================
# PENDÊNCIAS NARRATIVAS
# ==========================================================


def selecionar_thread_pronto(
    experience_state: dict[str, Any],
) -> dict[str, Any] | None:
    threads = experience_state.get(
        "open_threads"
    )

    if not isinstance(threads, list):
        return None

    candidates = [
        thread
        for thread in threads
        if (
            isinstance(thread, dict)
            and not thread.get(
                "resolved",
                False,
            )
            and thread.get(
                "ready_to_resume",
                False,
            )
        )
    ]

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            limitar_valor(
                item.get(
                    "urgency",
                    0.0,
                )
            ),
            safe_int(
                item.get(
                    "created_turn",
                    0,
                )
            ),
        ),
        reverse=True,
    )

    return candidates[0]


def criar_thread(
    *,
    thread_id: str,
    thread_type: str,
    summary: str,
    current_turn: int,
    urgency: float = 0.35,
) -> dict[str, Any]:
    normalized_type = str(
        thread_type or ""
    ).strip().lower()

    if normalized_type not in THREAD_TYPES:
        normalized_type = (
            THREAD_TYPE_UNFINISHED_REVEAL
        )

    return {
        "id": str(
            thread_id or ""
        ).strip(),
        "type": normalized_type,
        "summary": str(
            summary or ""
        ).strip(),
        "created_turn": max(
            0,
            current_turn,
        ),
        "last_touched_turn": max(
            0,
            current_turn,
        ),
        "urgency": limitar_valor(
            urgency
        ),
        "ready_to_resume": False,
        "resolved": False,
    }


def adicionar_thread_aberto(
    relationship_state: dict[str, Any],
    *,
    thread_type: str,
    summary: str,
    urgency: float = 0.35,
) -> dict[str, Any]:
    experience_state = obter_estado_experiencia(
        relationship_state
    )

    current_turn = obter_interaction_count(
        relationship_state
    )

    next_index = len(
        experience_state[
            "open_threads"
        ]
    ) + 1

    thread_id = (
        f"thread_{current_turn}_{next_index}"
    )

    thread = criar_thread(
        thread_id=thread_id,
        thread_type=thread_type,
        summary=summary,
        current_turn=current_turn,
        urgency=urgency,
    )

    experience_state[
        "open_threads"
    ].append(
        thread
    )

    relationship_state[
        "experience_state"
    ] = experience_state

    return thread


def marcar_thread_pronto(
    relationship_state: dict[str, Any],
    thread_id: str,
) -> None:
    experience_state = obter_estado_experiencia(
        relationship_state
    )

    for thread in experience_state[
        "open_threads"
    ]:
        if thread.get("id") == thread_id:
            thread[
                "ready_to_resume"
            ] = True

            thread[
                "urgency"
            ] = limitar_valor(
                thread.get(
                    "urgency",
                    0.35,
                )
                + 0.12
            )

            break


def resolver_thread(
    relationship_state: dict[str, Any],
    thread_id: str,
) -> None:
    experience_state = obter_estado_experiencia(
        relationship_state
    )

    current_turn = obter_interaction_count(
        relationship_state
    )

    for thread in experience_state[
        "open_threads"
    ]:
        if thread.get("id") == thread_id:
            thread["resolved"] = True

            thread[
                "ready_to_resume"
            ] = False

            thread[
                "last_touched_turn"
            ] = current_turn

            break


# ==========================================================
# DIREÇÃO DE VOZ
# ==========================================================


def calcular_estado_voz_base(
    relationship_state: dict[str, Any],
    *,
    internal_state: dict[str, Any],
    signals: dict[str, Any],
) -> dict[str, Any]:
    previous_voice = obter_estado_voz(
        relationship_state
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

    trust = limitar_valor(
        relationship_state.get(
            "trust_level",
            0.0,
        )
    )

    desire = limitar_valor(
        internal_state.get(
            "current_desire",
            0.0,
        )
    )

    playfulness = limitar_valor(
        internal_state.get(
            "current_playfulness",
            0.0,
        )
    )

    irritation = limitar_valor(
        internal_state.get(
            "current_irritation",
            0.0,
        )
    )

    voice = {
        "warmth": limitar_valor(
            previous_voice["warmth"] * 0.70
            + affection * 0.20
            + trust * 0.10
        ),
        "playfulness": limitar_valor(
            previous_voice[
                "playfulness"
            ] * 0.60
            + playfulness * 0.40
        ),
        "boldness": limitar_valor(
            previous_voice[
                "boldness"
            ] * 0.65
            + desire * 0.20
            + romantic_tension * 0.15
        ),
        "vulnerability": limitar_valor(
            previous_voice[
                "vulnerability"
            ] * 0.72
            + affection * 0.16
            + trust * 0.12
        ),
        "romantic_intensity": limitar_valor(
            affection * 0.52
            + romantic_tension * 0.28
            + trust * 0.20
        ),
        "sexual_intensity": limitar_valor(
            desire * 0.58
            + romantic_tension * 0.42
        ),
        "sexual_explicitness": 0.0,
        "vulgarity": limitar_valor(
            previous_voice[
                "vulgarity"
            ] * 0.68
            + playfulness * 0.06
            + desire * 0.08
        ),
        "body_confidence": limitar_valor(
            previous_voice[
                "body_confidence"
            ] * 0.78
            + 0.14
            + desire * 0.08
        ),
        "emotional_openness": limitar_valor(
            affection * 0.40
            + trust * 0.44
            + internal_state.get(
                "current_affection",
                0.0,
            ) * 0.16
        ),
        "humor": limitar_valor(
            previous_voice["humor"] * 0.62
            + playfulness * 0.38
        ),
        "tenderness": limitar_valor(
            affection * 0.58
            + trust * 0.24
            + previous_voice[
                "tenderness"
            ] * 0.18
        ),
        "jealousy": limitar_valor(
            previous_voice[
                "jealousy"
            ] * 0.70
        ),
    }

    if signals.get(
        "affection_signal"
    ):
        voice["warmth"] += 0.08
        voice["tenderness"] += 0.06

    if signals.get(
        "romantic_signal"
    ):
        voice[
            "romantic_intensity"
        ] += 0.10

    if signals.get(
        "sexual_signal"
    ):
        voice[
            "sexual_intensity"
        ] += 0.10

    if signals.get(
        "explicit_sexual_signal"
    ):
        voice[
            "sexual_intensity"
        ] += 0.08

    if signals.get(
        "emotional_disclosure"
    ):
        voice[
            "emotional_openness"
        ] += 0.08

        voice[
            "vulnerability"
        ] += 0.05

    if signals.get(
        "hostility_signal"
    ):
        voice["warmth"] -= 0.25
        voice["irritation"] = irritation
        voice["boldness"] += 0.14

    return {
        key: limitar_valor(
            value
        )
        for key, value in voice.items()
        if key in DEFAULT_VOICE_STATE
    }


def aplicar_modo_ao_estado_voz(
    voice_state: dict[str, Any],
    *,
    experience_mode: str,
    sexual_level: int,
    sexual_phase: str,
) -> tuple[
    dict[str, Any],
    str,
]:
    voice = normalizar_estado_voz(
        voice_state
    )

    register = VOICE_REGISTER_NATURAL

    if experience_mode == EXPERIENCE_MODE_PERSONAL_SHARE:
        voice["warmth"] += 0.08
        voice["emotional_openness"] += 0.10
        register = VOICE_REGISTER_WARM

    elif experience_mode == (
        EXPERIENCE_MODE_UNEXPECTED_CONFESSION
    ):
        voice["vulnerability"] += 0.20
        voice["emotional_openness"] += 0.18
        voice["warmth"] += 0.08
        register = VOICE_REGISTER_VULNERABLE

    elif experience_mode == (
        EXPERIENCE_MODE_SHOW_VULNERABILITY
    ):
        voice["vulnerability"] += 0.24
        voice["emotional_openness"] += 0.20
        voice["tenderness"] += 0.10
        register = VOICE_REGISTER_VULNERABLE

    elif experience_mode in {
        EXPERIENCE_MODE_PLAYFUL_CHALLENGE,
        EXPERIENCE_MODE_PRIVATE_JOKE,
        EXPERIENCE_MODE_HUMOR_BREAK,
    }:
        voice["playfulness"] += 0.18
        voice["humor"] += 0.22
        register = VOICE_REGISTER_PLAYFUL

    elif experience_mode == (
        EXPERIENCE_MODE_GENTLE_PROVOCATION
    ):
        voice["playfulness"] += 0.14
        voice["boldness"] += 0.10
        voice["sexual_intensity"] += 0.06
        register = VOICE_REGISTER_TEASING

    elif experience_mode == (
        EXPERIENCE_MODE_BOLD_PROVOCATION
    ):
        voice["playfulness"] += 0.10
        voice["boldness"] += 0.22
        voice["sexual_intensity"] += 0.16
        voice["vulgarity"] += 0.10
        register = VOICE_REGISTER_BOLD

    elif experience_mode == (
        EXPERIENCE_MODE_ROMANTIC_ESCALATION
    ):
        voice["warmth"] += 0.12
        voice["romantic_intensity"] += 0.22
        voice["tenderness"] += 0.12
        register = VOICE_REGISTER_ROMANTIC

    elif experience_mode == (
        EXPERIENCE_MODE_SEXUAL_TENSION
    ):
        voice["boldness"] += 0.18
        voice["sexual_intensity"] += 0.24
        voice["sexual_explicitness"] = max(
            voice[
                "sexual_explicitness"
            ],
            0.22
            if sexual_level <= 2
            else 0.42,
        )
        voice["vulgarity"] += 0.10

        register = (
            VOICE_REGISTER_TEASING
            if sexual_level <= 2
            else VOICE_REGISTER_EXPLICIT_PLAYFUL
        )

    elif experience_mode == (
        EXPERIENCE_MODE_SEXUAL_INITIATIVE
    ):
        voice["boldness"] += 0.28
        voice["sexual_intensity"] += 0.30
        voice["body_confidence"] += 0.18
        voice["vulgarity"] += 0.18

        if sexual_phase in {
            "active",
            "pre_orgasm",
            "orgasm",
            "post_orgasm",
        }:
            voice[
                "sexual_explicitness"
            ] = max(
                voice[
                    "sexual_explicitness"
                ],
                0.78,
            )

            register = (
                VOICE_REGISTER_EXPLICIT_INTENSE
            )

        else:
            voice[
                "sexual_explicitness"
            ] = max(
                voice[
                    "sexual_explicitness"
                ],
                0.58,
            )

            register = (
                VOICE_REGISTER_EXPLICIT_PLAYFUL
            )

    elif experience_mode == (
        EXPERIENCE_MODE_CONTINUE_SHARED_FANTASY
    ):
        voice["sexual_intensity"] += 0.24
        voice["romantic_intensity"] += 0.10
        voice["body_confidence"] += 0.12
        voice["vulgarity"] += 0.14
        voice[
            "sexual_explicitness"
        ] = max(
            voice[
                "sexual_explicitness"
            ],
            0.62,
        )
        register = (
            VOICE_REGISTER_AFFECTIONATE_SEXUAL
        )

    elif experience_mode == (
        EXPERIENCE_MODE_SEEK_AFFECTION
    ):
        voice["warmth"] += 0.14
        voice["vulnerability"] += 0.10
        voice["tenderness"] += 0.16
        register = VOICE_REGISTER_WARM

    elif experience_mode == (
        EXPERIENCE_MODE_SHOW_JEALOUSY
    ):
        voice["jealousy"] += 0.30
        voice["vulnerability"] += 0.08
        voice["boldness"] += 0.08
        register = VOICE_REGISTER_IRRITATED

    elif experience_mode == (
        EXPERIENCE_MODE_SET_BOUNDARY
    ):
        voice["warmth"] -= 0.22
        voice["boldness"] += 0.25
        voice["sexual_explicitness"] = 0.0
        register = VOICE_REGISTER_BOUNDARY

    elif experience_mode == (
        EXPERIENCE_MODE_AFTERCARE
    ):
        voice["warmth"] += 0.20
        voice["tenderness"] += 0.24
        voice["vulnerability"] += 0.08
        voice["sexual_explicitness"] = min(
            voice[
                "sexual_explicitness"
            ],
            0.34,
        )
        register = VOICE_REGISTER_AFTERCARE

    elif experience_mode == (
        EXPERIENCE_MODE_FRUSTRATION
    ):
        voice["boldness"] += 0.18
        voice["vulnerability"] += 0.10
        voice["sexual_intensity"] += 0.12
        voice["vulgarity"] += 0.08
        register = VOICE_REGISTER_IRRITATED

    normalized_voice = {
        key: limitar_valor(
            value
        )
        for key, value in voice.items()
    }

    return (
        normalized_voice,
        register,
    )


# ==========================================================
# CONSTRUÇÃO DA DIREÇÃO
# ==========================================================


def criar_direcao(
    *,
    experience_mode: str,
    primary_intention: str,
    emotional_color: str,
    voice_register: str,
    voice_state: dict[str, Any],
    reason: str,
    surprise_level: float = 0.0,
    topic_direction: str = TOPIC_DIRECTION_CURRENT,
    should_lead: bool = False,
    should_reveal_something: bool = False,
    should_create_pending_thread: bool = False,
    should_resume_thread: bool = False,
    open_thread_id: str = "",
    callback_memory_id: str = "",
    scene_seed: str = "",
    response_scope: str = "brief",
    body_focus_allowed: bool = False,
    romantic_expression_allowed: bool = False,
    sexual_expression_allowed: bool = False,
    explicit_sexual_language_allowed: bool = False,
    must_preserve_current_scene: bool = False,
    must_address_user_message: bool = True,
    avoid_question: bool = False,    
) -> dict[str, Any]:
    return {
        "experience_mode": (
            normalizar_modo_experiencia(
                experience_mode
            )
        ),
        "primary_intention": str(
            primary_intention or ""
        ).strip(),
        "emotional_color": str(
            emotional_color or ""
        ).strip(),
        "voice_register": (
            normalizar_registro_voz(
                voice_register
            )
        ),
        "response_scope": str(
            response_scope or "brief"
        ).strip().lower(),
        "surprise_level": limitar_valor(
            surprise_level
        ),
        "topic_direction": str(
            topic_direction
            or TOPIC_DIRECTION_CURRENT
        ).strip(),
        "should_lead": bool(
            should_lead
        ),
        "should_reveal_something": bool(
            should_reveal_something
        ),
        "should_create_pending_thread": bool(
            should_create_pending_thread
        ),
        "should_resume_thread": bool(
            should_resume_thread
        ),
        "open_thread_id": str(
            open_thread_id or ""
        ).strip(),
        "callback_memory_id": str(
            callback_memory_id or ""
        ).strip(),
        "scene_seed": str(
            scene_seed or ""
        ).strip(),
        "body_focus_allowed": bool(
            body_focus_allowed
        ),
        "romantic_expression_allowed": bool(
            romantic_expression_allowed
        ),
        "sexual_expression_allowed": bool(
            sexual_expression_allowed
        ),
        "explicit_sexual_language_allowed": bool(
            explicit_sexual_language_allowed
        ),
        "must_preserve_current_scene": bool(
            must_preserve_current_scene
        ),
        "must_avoid_repetition": True,
        "must_address_user_message": bool(
            must_address_user_message
        ),
        "avoid_question": bool(
            avoid_question
        ),
        "reason": str(
            reason or ""
        ).strip(),
        "voice_state": normalizar_estado_voz(
            voice_state
        ),
    }


# ==========================================================
# ESCOLHA DO MODO DE EXPERIÊNCIA
# ==========================================================


def escolher_modo_experiencia(
    relationship_state: dict[str, Any],
    *,
    signals: dict[str, Any],
    turn_intent: dict[str, Any],
    internal_state: dict[str, Any],
    experience_state: dict[str, Any],
) -> tuple[
    str,
    dict[str, Any] | None,
    str,
]:
    turn_mode = str(
        turn_intent.get(
            "turn_mode",
            TURN_MODE_RESPOND,
        )
        or TURN_MODE_RESPOND
    ).strip().lower()

    sexual_phase = obter_fase_sexual(
        relationship_state
    )

    sexual_level = obter_nivel_sexual(
        relationship_state
    )

    interaction_count = (
        obter_interaction_count(
            relationship_state
        )
    )

    surprise_budget = limitar_valor(
        experience_state.get(
            "surprise_budget",
            0.42,
        )
    )

    ready_thread = selecionar_thread_pronto(
        experience_state
    )

    # Limites e hostilidade têm prioridade.
    if (
        signals.get("boundary_signal")
        or turn_mode == TURN_MODE_SLOW_DOWN
    ):
        return (
            EXPERIENCE_MODE_SET_BOUNDARY,
            None,
            "user_boundary_priority",
        )

    if (
        signals.get("hostility_signal")
        or turn_mode == TURN_MODE_SET_BOUNDARY
    ):
        return (
            EXPERIENCE_MODE_SET_BOUNDARY,
            None,
            "mary_boundary_after_hostility",
        )

    # Continuidade sexual tem prioridade sobre surpresa.
    if sexual_phase == "frustration":
        return (
            EXPERIENCE_MODE_FRUSTRATION,
            None,
            "sexual_frustration_continuity",
        )

    if sexual_phase == "aftercare":
        return (
            EXPERIENCE_MODE_AFTERCARE,
            None,
            "sexual_aftercare_continuity",
        )

    if sexual_phase in {
        "active",
        "pre_orgasm",
        "orgasm",
        "post_orgasm",
    }:
        return (
            EXPERIENCE_MODE_SEXUAL_INITIATIVE,
            None,
            "active_sexual_scene_continuity",
        )

    # Intenção sexual autônoma de Mary.
    if turn_mode == (
        TURN_MODE_INITIATE_SEXUAL_SCENE
    ):
        return (
            EXPERIENCE_MODE_SEXUAL_INITIATIVE,
            None,
            "mary_initiates_sexual_scene",
        )

    if turn_mode == (
        TURN_MODE_INITIATE_SEXUAL_TENSION
    ):
        return (
            EXPERIENCE_MODE_SEXUAL_TENSION,
            None,
            "mary_initiates_sexual_tension",
        )

    # Retomar uma pendência pode ser mais interessante
    # do que inventar uma nova surpresa.
    if (
        ready_thread
        and experience_state[
            "turns_since_callback"
        ] >= 2
        and not modo_foi_recente(
            experience_state,
            EXPERIENCE_MODE_MEMORY_CALLBACK,
            lookback=2,
        )
    ):
        thread_type = ready_thread.get(
            "type"
        )

        if thread_type == (
            THREAD_TYPE_SHARED_FANTASY
        ):
            return (
                EXPERIENCE_MODE_CONTINUE_SHARED_FANTASY,
                ready_thread,
                "resume_shared_fantasy_thread",
            )

        if thread_type in {
            THREAD_TYPE_ROMANTIC_TENSION,
            THREAD_TYPE_SEXUAL_TENSION,
        }:
            return (
                EXPERIENCE_MODE_MEMORY_CALLBACK,
                ready_thread,
                "resume_tension_thread",
            )

        return (
            EXPERIENCE_MODE_MEMORY_CALLBACK,
            ready_thread,
            "resume_open_narrative_thread",
        )

    # Flerte, provocação e intimidade.
    if turn_mode == TURN_MODE_INITIATE_FLIRT:
        if (
            internal_state[
                "current_desire"
            ] >= 0.46
            and sexual_level >= 2
        ):
            return (
                EXPERIENCE_MODE_BOLD_PROVOCATION,
                None,
                "mary_bold_flirt",
            )

        return (
            EXPERIENCE_MODE_GENTLE_PROVOCATION,
            None,
            "mary_gentle_flirt",
        )

    if turn_mode == TURN_MODE_TEASE:
        return (
            EXPERIENCE_MODE_PLAYFUL_CHALLENGE,
            None,
            "mary_playful_tease",
        )

    if turn_mode == TURN_MODE_INCREASE_INTIMACY:
        return (
            EXPERIENCE_MODE_ROMANTIC_ESCALATION,
            None,
            "mary_increases_intimacy",
        )

    if turn_mode == TURN_MODE_SEEK_AFFECTION:
        return (
            EXPERIENCE_MODE_SEEK_AFFECTION,
            None,
            "mary_seeks_affection",
        )

    if turn_mode == TURN_MODE_SHOW_IRRITATION:
        return (
            EXPERIENCE_MODE_SHOW_JEALOUSY,
            None,
            "mary_expresses_irritation",
        )

    if turn_mode == TURN_MODE_CHANGE_TOPIC:
        return (
            EXPERIENCE_MODE_SURPRISE_TOPIC,
            None,
            "mary_changes_topic",
        )

    if turn_mode == TURN_MODE_SHARE:
        if (
            surprise_budget >= 0.62
            and interaction_count >= 4
            and experience_state[
                "turns_since_reveal"
            ] >= 3
            and not modo_foi_recente(
                experience_state,
                EXPERIENCE_MODE_UNEXPECTED_CONFESSION,
                lookback=4,
            )
        ):
            return (
                EXPERIENCE_MODE_UNEXPECTED_CONFESSION,
                None,
                "mary_unexpected_personal_confession",
            )

        return (
            EXPERIENCE_MODE_PERSONAL_SHARE,
            None,
            "mary_shares_personal_content",
        )

    # Surpresa construída pelo ritmo.
    if (
        surprise_budget >= 0.74
        and experience_state[
            "turns_since_surprise"
        ] >= 3
        and not muitos_modos_intensos_recentes(
            experience_state
        )
    ):
        if (
            internal_state[
                "current_playfulness"
            ] >= 0.48
            and experience_state[
                "turns_since_humor"
            ] >= 2
        ):
            return (
                EXPERIENCE_MODE_HUMOR_BREAK,
                None,
                "surprise_budget_used_for_humor",
            )

        if (
            internal_state[
                "current_affection"
            ] >= 0.42
            and experience_state[
                "turns_since_vulnerability"
            ] >= 4
        ):
            return (
                EXPERIENCE_MODE_SHOW_VULNERABILITY,
                None,
                "surprise_budget_used_for_vulnerability",
            )

        if (
            internal_state[
                "current_curiosity"
            ] >= 0.46
        ):
            return (
                EXPERIENCE_MODE_UNFINISHED_REVEAL,
                None,
                "surprise_budget_used_for_open_loop",
            )

    # Quebra de intensidade para evitar caricatura.
    if muitos_modos_intensos_recentes(
        experience_state
    ):
        if experience_state[
            "turns_since_humor"
        ] >= 2:
            return (
                EXPERIENCE_MODE_HUMOR_BREAK,
                None,
                "rhythm_break_after_intensity",
            )

        return (
            EXPERIENCE_MODE_NATURAL,
            None,
            "natural_breathing_after_intensity",
        )

    return (
        EXPERIENCE_MODE_NATURAL,
        None,
        "natural_conversation_selected",
    )


# ==========================================================
# ATRIBUTOS DA DIREÇÃO
# ==========================================================


def obter_atributos_modo(
    experience_mode: str,
) -> dict[str, Any]:
    attributes: dict[str, dict[str, Any]] = {
        EXPERIENCE_MODE_NATURAL: {
            "primary_intention": (
                "react_to_current_message"
            ),
            "emotional_color": (
                "natural_presence"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_CURRENT
            ),
            "response_scope": "brief",
            "should_lead": False,
            "should_reveal_something": False,
            "should_create_pending_thread": False,
            "avoid_question": True,
            "surprise_level": 0.05,
        },
        EXPERIENCE_MODE_PERSONAL_SHARE: {
            "primary_intention": (
                "bring_mary_personal_content"
            ),
            "emotional_color": (
                "warm_spontaneity"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_PERSONAL
            ),
            "response_scope": "normal",
            "should_lead": True,
            "should_reveal_something": True,
            "should_create_pending_thread": False,
            "surprise_level": 0.28,
        },
        EXPERIENCE_MODE_UNEXPECTED_CONFESSION: {
            "primary_intention": (
                "reveal_unexpected_emotional_truth"
            ),
            "emotional_color": (
                "playful_vulnerability"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_EMOTIONAL
            ),
            "response_scope": "developed",
            "should_lead": True,
            "should_reveal_something": True,
            "should_create_pending_thread": False,
            "surprise_level": 0.66,
        },
        EXPERIENCE_MODE_PLAYFUL_CHALLENGE: {
            "primary_intention": (
                "create_playful_energy"
            ),
            "emotional_color": (
                "mischievous_humor"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_CURRENT
            ),
            "response_scope": "normal",
            "should_lead": True,
            "should_reveal_something": False,
            "should_create_pending_thread": False,
            "surprise_level": 0.32,
        },
        EXPERIENCE_MODE_PRIVATE_JOKE: {
            "primary_intention": (
                "reinforce_shared_private_language"
            ),
            "emotional_color": (
                "intimate_humor"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_RELATIONSHIP
            ),
            "response_scope": "normal",
            "should_lead": True,
            "should_reveal_something": False,
            "should_create_pending_thread": False,
            "surprise_level": 0.28,
        },
        EXPERIENCE_MODE_MEMORY_CALLBACK: {
            "primary_intention": (
                "resume_meaningful_previous_thread"
            ),
            "emotional_color": (
                "recognition_and_continuity"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_RELATIONSHIP
            ),
            "response_scope": "normal",
            "should_lead": True,
            "should_reveal_something": False,
            "should_create_pending_thread": False,
            "surprise_level": 0.44,
        },
        EXPERIENCE_MODE_UNFINISHED_REVEAL: {
            "primary_intention": (
                "create_curiosity_with_partial_reveal"
            ),
            "emotional_color": (
                "playful_mystery"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_PERSONAL
            ),
            "response_scope": "developed",
            "should_lead": True,
            "should_reveal_something": True,
            "should_create_pending_thread": True,
            "surprise_level": 0.58,
        },
        EXPERIENCE_MODE_EMOTIONAL_REVERSAL: {
            "primary_intention": (
                "change_emotional_direction"
            ),
            "emotional_color": (
                "unexpected_sincerity"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_EMOTIONAL
            ),
            "response_scope": "developed",
            "should_lead": True,
            "should_reveal_something": True,
            "should_create_pending_thread": False,
            "surprise_level": 0.56,
        },
        EXPERIENCE_MODE_GENTLE_PROVOCATION: {
            "primary_intention": (
                "create_light_romantic_tension"
            ),
            "emotional_color": (
                "playful_attraction"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_ROMANTIC
            ),
            "response_scope": "normal",
            "should_lead": True,
            "should_reveal_something": False,
            "should_create_pending_thread": False,
            "surprise_level": 0.34,
        },
        EXPERIENCE_MODE_BOLD_PROVOCATION: {
            "primary_intention": (
                "express_bold_desire"
            ),
            "emotional_color": (
                "confident_desire"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_SEXUAL
            ),
            "response_scope": "normal",
            "should_lead": True,
            "should_reveal_something": False,
            "should_create_pending_thread": True,
            "surprise_level": 0.52,
        },
        EXPERIENCE_MODE_ROMANTIC_ESCALATION: {
            "primary_intention": (
                "express_romantic_feeling"
            ),
            "emotional_color": (
                "direct_affection"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_ROMANTIC
            ),
            "response_scope": "normal",
            "should_lead": True,
            "should_reveal_something": True,
            "should_create_pending_thread": False,
            "surprise_level": 0.40,
        },
        EXPERIENCE_MODE_SEXUAL_TENSION: {
            "primary_intention": (
                "create_autonomous_sexual_tension"
            ),
            "emotional_color": (
                "playful_desire"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_SEXUAL
            ),
            "response_scope": "normal",
            "should_lead": True,
            "should_reveal_something": False,
            "should_create_pending_thread": True,
            "surprise_level": 0.52,
        },
        EXPERIENCE_MODE_SEXUAL_INITIATIVE: {
            "primary_intention": (
                "mary_leads_sexual_direction"
            ),
            "emotional_color": (
                "explicit_confident_desire"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_SEXUAL
            ),
            "response_scope": "scene",
            "should_lead": True,
            "should_reveal_something": False,
            "should_create_pending_thread": False,
            "surprise_level": 0.62,
        },
        EXPERIENCE_MODE_SEEK_AFFECTION: {
            "primary_intention": (
                "ask_for_emotional_closeness"
            ),
            "emotional_color": (
                "soft_need"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_EMOTIONAL
            ),
            "response_scope": "normal",
            "should_lead": True,
            "should_reveal_something": True,
            "should_create_pending_thread": False,
            "surprise_level": 0.36,
        },
        EXPERIENCE_MODE_SHOW_JEALOUSY: {
            "primary_intention": (
                "express_concrete_jealousy"
            ),
            "emotional_color": (
                "vulnerable_irritation"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_RELATIONSHIP
            ),
            "response_scope": "normal",
            "should_lead": True,
            "should_reveal_something": True,
            "should_create_pending_thread": False,
            "surprise_level": 0.42,
        },
        EXPERIENCE_MODE_SHOW_VULNERABILITY: {
            "primary_intention": (
                "show_unpolished_vulnerability"
            ),
            "emotional_color": (
                "unguarded_emotion"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_EMOTIONAL
            ),
            "response_scope": "developed",
            "should_lead": True,
            "should_reveal_something": True,
            "should_create_pending_thread": False,
            "surprise_level": 0.56,
        },
        EXPERIENCE_MODE_SET_BOUNDARY: {
            "primary_intention": (
                "state_boundary_clearly"
            ),
            "emotional_color": (
                "firm_self_respect"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_BOUNDARY
            ),
            "response_scope": "brief",
            "avoid_question": True,
            "should_lead": True,
            "should_reveal_something": False,
            "should_create_pending_thread": False,
            "surprise_level": 0.0,
        },
        EXPERIENCE_MODE_CREATE_SHARED_PLAN: {
            "primary_intention": (
                "create_future_shared_plan"
            ),
            "emotional_color": (
                "anticipation"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_RELATIONSHIP
            ),
            "response_scope": "normal",
            "should_lead": True,
            "should_reveal_something": False,
            "should_create_pending_thread": True,
            "surprise_level": 0.40,
        },
        EXPERIENCE_MODE_CONTINUE_SHARED_FANTASY: {
            "primary_intention": (
                "continue_previous_shared_fantasy"
            ),
            "emotional_color": (
                "intimate_continuity"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_SEXUAL
            ),
            "response_scope": "scene",
            "should_lead": True,
            "should_reveal_something": False,
            "should_create_pending_thread": False,
            "surprise_level": 0.44,
        },
        EXPERIENCE_MODE_SURPRISE_TOPIC: {
            "primary_intention": (
                "introduce_unexpected_topic"
            ),
            "emotional_color": (
                "curious_spontaneity"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_NEW_TOPIC
            ),
            "response_scope": "normal",
            "should_lead": True,
            "should_reveal_something": False,
            "should_create_pending_thread": False,
            "surprise_level": 0.46,
        },
        EXPERIENCE_MODE_HUMOR_BREAK: {
            "primary_intention": (
                "break_pattern_with_humor"
            ),
            "emotional_color": (
                "comic_relief"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_CURRENT
            ),
            "response_scope": "normal",
            "should_lead": True,
            "should_reveal_something": False,
            "should_create_pending_thread": False,
            "surprise_level": 0.34,
        },
        EXPERIENCE_MODE_AFTERCARE: {
            "primary_intention": (
                "provide_affectionate_aftercare"
            ),
            "emotional_color": (
                "warm_post_intimacy"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_EMOTIONAL
            ),
            "response_scope": "developed",
            "should_lead": True,
            "should_reveal_something": True,
            "should_create_pending_thread": False,
            "surprise_level": 0.08,
        },
        EXPERIENCE_MODE_FRUSTRATION: {
            "primary_intention": (
                "express_real_sexual_frustration"
            ),
            "emotional_color": (
                "desire_and_irritation"
            ),
            "topic_direction": (
                TOPIC_DIRECTION_SEXUAL
            ),
            "response_scope": "normal",
            "should_lead": True,
            "should_reveal_something": True,
            "should_create_pending_thread": False,
            "surprise_level": 0.24,
        },
    }

    return attributes.get(
        experience_mode,
        attributes[
            EXPERIENCE_MODE_NATURAL
        ],
    )


# ==========================================================
# PLANEJAMENTO PRINCIPAL
# ==========================================================


def planejar_direcao_turno(
    relationship_state: dict[str, Any] | None,
    *,
    signals: dict[str, Any] | None = None,
    turn_intent: dict[str, Any] | None = None,
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

    normalized_signals = normalizar_sinais(
        signals
    )

    normalized_intent = normalizar_intencao(
        turn_intent
    )

    internal_state = obter_estado_interno(
        state
    )

    experience_state = obter_estado_experiencia(
        state
    )

    incrementar_contadores_experiencia(
        experience_state
    )

    atualizar_orcamento_surpresa(
        experience_state,
        internal_state=internal_state,
    )

    (
        experience_mode,
        selected_thread,
        selection_reason,
    ) = escolher_modo_experiencia(
        state,
        signals=normalized_signals,
        turn_intent=normalized_intent,
        internal_state=internal_state,
        experience_state=experience_state,
    )

    attributes = obter_atributos_modo(
        experience_mode
    )

    sexual_level = obter_nivel_sexual(
        state
    )

    sexual_phase = obter_fase_sexual(
        state
    )

    base_voice = calcular_estado_voz_base(
        state,
        internal_state=internal_state,
        signals=normalized_signals,
    )

    (
        voice_state,
        voice_register,
    ) = aplicar_modo_ao_estado_voz(
        base_voice,
        experience_mode=experience_mode,
        sexual_level=sexual_level,
        sexual_phase=sexual_phase,
    )

    sexual_expression_allowed = bool(
        sexual_level >= 2
        or sexual_phase
        in {
            "arousal",
            "active",
            "pre_orgasm",
            "orgasm",
            "post_orgasm",
            "frustration",
            "aftercare",
        }
    )

    explicit_sexual_language_allowed = bool(
        voice_state[
            "sexual_explicitness"
        ] >= 0.56
        and (
            sexual_level >= 3
            or sexual_phase
            in {
                "active",
                "pre_orgasm",
                "orgasm",
                "post_orgasm",
                "frustration",
            }
        )
    )

    body_focus_allowed = bool(
        experience_mode
        in {
            EXPERIENCE_MODE_BOLD_PROVOCATION,
            EXPERIENCE_MODE_SEXUAL_TENSION,
            EXPERIENCE_MODE_SEXUAL_INITIATIVE,
            EXPERIENCE_MODE_CONTINUE_SHARED_FANTASY,
        }
        and sexual_level >= 2
    )

    romantic_expression_allowed = bool(
        sexual_level >= 1
        or obter_estagio_emocional(
            state
        )
        in {
            "connection",
            "intimacy",
            "deep_bond",
        }
    )

    open_thread_id = (
        selected_thread.get("id", "")
        if selected_thread
        else ""
    )

    direction = criar_direcao(
        experience_mode=experience_mode,
        primary_intention=attributes[
            "primary_intention"
        ],
        emotional_color=attributes[
            "emotional_color"
        ],
        voice_register=voice_register,
        voice_state=voice_state,
        reason=selection_reason,
        response_scope=attributes.get(
            "response_scope",
            "normal",
        ),
        surprise_level=attributes[
            "surprise_level"
        ],
        topic_direction=attributes[
            "topic_direction"
        ],
        should_lead=attributes[
            "should_lead"
        ],
        should_reveal_something=attributes[
            "should_reveal_something"
        ],
        should_create_pending_thread=attributes[
            "should_create_pending_thread"
        ],
        should_resume_thread=bool(
            selected_thread
        ),
        open_thread_id=open_thread_id,
        body_focus_allowed=body_focus_allowed,
        romantic_expression_allowed=(
            romantic_expression_allowed
        ),
        sexual_expression_allowed=(
            sexual_expression_allowed
        ),
        explicit_sexual_language_allowed=(
            explicit_sexual_language_allowed
        ),
        must_preserve_current_scene=bool(
            sexual_phase
            in {
                "active",
                "pre_orgasm",
                "orgasm",
                "post_orgasm",
                "frustration",
                "aftercare",
            }
        ),
        must_address_user_message=normalizar_bool(
            normalized_intent.get(
                "must_address_user_message"
            ),
            default=True,
        ),
        avoid_question=normalizar_bool(
            normalized_intent.get(
                "avoid_question"
            ),
            default=False,
        ),
    )

    experience_state[
        "previous_mode"
    ] = experience_state[
        "current_mode"
    ]

    experience_state[
        "current_mode"
    ] = experience_mode

    experience_state[
        "last_primary_intention"
    ] = direction[
        "primary_intention"
    ]

    experience_state[
        "last_emotional_color"
    ] = direction[
        "emotional_color"
    ]

    experience_state[
        "last_voice_register"
    ] = direction[
        "voice_register"
    ]

    experience_state[
        "last_direction_reason"
    ] = direction[
        "reason"
    ]

    state[
        "experience_state"
    ] = experience_state

    state[
        "voice_state"
    ] = voice_state

    state[
        "current_turn_direction"
    ] = direction

    return state, direction


# ==========================================================
# SINCRONIZAÇÃO APÓS A RESPOSTA
# ==========================================================


def modo_consume_surpresa(
    experience_mode: str,
) -> bool:
    return experience_mode in {
        EXPERIENCE_MODE_UNEXPECTED_CONFESSION,
        EXPERIENCE_MODE_UNFINISHED_REVEAL,
        EXPERIENCE_MODE_EMOTIONAL_REVERSAL,
        EXPERIENCE_MODE_MEMORY_CALLBACK,
        EXPERIENCE_MODE_BOLD_PROVOCATION,
        EXPERIENCE_MODE_SEXUAL_INITIATIVE,
        EXPERIENCE_MODE_SURPRISE_TOPIC,
        EXPERIENCE_MODE_SHOW_VULNERABILITY,
    }


def sincronizar_direcao_apos_resposta(
    relationship_state: dict[str, Any] | None,
    *,
    turn_direction: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = (
        relationship_state
        if isinstance(
            relationship_state,
            dict,
        )
        else {}
    )

    experience_state = obter_estado_experiencia(
        state
    )

    direction = (
        turn_direction
        if isinstance(
            turn_direction,
            dict,
        )
        else state.get(
            "current_turn_direction"
        )
    )

    if not isinstance(direction, dict):
        direction = criar_direcao_turno_padrao()

    mode = normalizar_modo_experiencia(
        direction.get(
            "experience_mode"
        )
    )

    recent_modes = experience_state.get(
        "recent_modes"
    )

    if not isinstance(recent_modes, list):
        recent_modes = []

    recent_modes.append(
        mode
    )

    experience_state[
        "recent_modes"
    ] = recent_modes[-8:]

    if modo_consume_surpresa(
        mode
    ):
        experience_state[
            "surprise_budget"
        ] = limitar_valor(
            experience_state[
                "surprise_budget"
            ]
            - max(
                0.25,
                limitar_valor(
                    direction.get(
                        "surprise_level",
                        0.0,
                    )
                )
                * 0.60,
            )
        )

        experience_state[
            "turns_since_surprise"
        ] = 0

        experience_state[
            "last_surprise_type"
        ] = mode

    if mode in {
        EXPERIENCE_MODE_UNEXPECTED_CONFESSION,
        EXPERIENCE_MODE_SHOW_VULNERABILITY,
        EXPERIENCE_MODE_PERSONAL_SHARE,
    }:
        experience_state[
            "turns_since_reveal"
        ] = 0

    if mode == EXPERIENCE_MODE_MEMORY_CALLBACK:
        experience_state[
            "turns_since_callback"
        ] = 0

    if mode in {
        EXPERIENCE_MODE_HUMOR_BREAK,
        EXPERIENCE_MODE_PLAYFUL_CHALLENGE,
        EXPERIENCE_MODE_PRIVATE_JOKE,
    }:
        experience_state[
            "turns_since_humor"
        ] = 0

    if mode in {
        EXPERIENCE_MODE_SHOW_VULNERABILITY,
        EXPERIENCE_MODE_UNEXPECTED_CONFESSION,
        EXPERIENCE_MODE_SEEK_AFFECTION,
    }:
        experience_state[
            "turns_since_vulnerability"
        ] = 0

    if mode == EXPERIENCE_MODE_ROMANTIC_ESCALATION:
        experience_state[
            "turns_since_romantic_escalation"
        ] = 0

    if mode in {
        EXPERIENCE_MODE_SEXUAL_TENSION,
        EXPERIENCE_MODE_SEXUAL_INITIATIVE,
        EXPERIENCE_MODE_CONTINUE_SHARED_FANTASY,
    }:
        experience_state[
            "turns_since_sexual_initiative"
        ] = 0

    open_thread_id = str(
        direction.get(
            "open_thread_id"
        )
        or ""
    ).strip()

    if (
        direction.get(
            "should_resume_thread"
        )
        and open_thread_id
    ):
        resolver_thread(
            state,
            open_thread_id,
        )

    state[
        "experience_state"
    ] = experience_state

    state[
        "last_turn_direction"
    ] = direction

    state[
        "current_turn_direction"
    ] = {}

    return state


# ==========================================================
# CONTEXTO PARA O PROMPT
# ==========================================================


def montar_contexto_direcao(
    relationship_state: dict[str, Any] | None,
    turn_direction: dict[str, Any] | None = None,
) -> str:
    state = (
        relationship_state
        if isinstance(
            relationship_state,
            dict,
        )
        else {}
    )

    direction = (
        turn_direction
        if isinstance(
            turn_direction,
            dict,
        )
        else state.get(
            "current_turn_direction"
        )
    )

    if not isinstance(direction, dict):
        direction = criar_direcao_turno_padrao()

    voice_state = normalizar_estado_voz(
        direction.get(
            "voice_state"
        )
    )

    return f"""
[DIREÇÃO CRIATIVA DO TURNO]

Modo de experiência:
{direction.get("experience_mode", EXPERIENCE_MODE_NATURAL)}

Intenção principal:
{direction.get("primary_intention", "respond_naturally")}

Cor emocional:
{direction.get("emotional_color", "natural_presence")}

Registro de voz:
{direction.get("voice_register", VOICE_REGISTER_NATURAL)}

Escopo da resposta:
{direction.get("response_scope", "brief")}

Nível de surpresa:
{limitar_valor(direction.get("surprise_level", 0.0)):.2f}

Direção do assunto:
{direction.get("topic_direction", TOPIC_DIRECTION_CURRENT)}

Mary deve liderar:
{normalizar_bool(direction.get("should_lead"))}

Mary deve revelar algo:
{normalizar_bool(direction.get("should_reveal_something"))}

Criar pendência narrativa:
{normalizar_bool(direction.get("should_create_pending_thread"))}

Retomar pendência:
{normalizar_bool(direction.get("should_resume_thread"))}

Identificador da pendência:
{direction.get("open_thread_id", "")}

Pode falar do próprio corpo:
{normalizar_bool(direction.get("body_focus_allowed"))}

Pode demonstrar romance:
{normalizar_bool(direction.get("romantic_expression_allowed"))}

Pode demonstrar desejo sexual:
{normalizar_bool(direction.get("sexual_expression_allowed"))}

Pode usar linguagem sexual explícita:
{normalizar_bool(direction.get("explicit_sexual_language_allowed"))}

Deve preservar a cena atual:
{normalizar_bool(direction.get("must_preserve_current_scene"))}

Deve responder à mensagem do usuário:
{normalizar_bool(direction.get("must_address_user_message"), default=True)}

Evitar pergunta:
{normalizar_bool(direction.get("avoid_question"))}

Motivo da direção:
{direction.get("reason", "")}

PALETA DE VOZ:
- calor: {voice_state["warmth"]:.2f}
- humor: {voice_state["humor"]:.2f}
- ludicidade: {voice_state["playfulness"]:.2f}
- ousadia: {voice_state["boldness"]:.2f}
- vulnerabilidade: {voice_state["vulnerability"]:.2f}
- intensidade romântica: {voice_state["romantic_intensity"]:.2f}
- intensidade sexual: {voice_state["sexual_intensity"]:.2f}
- explicitude sexual: {voice_state["sexual_explicitness"]:.2f}
- vulgaridade: {voice_state["vulgarity"]:.2f}
- confiança corporal: {voice_state["body_confidence"]:.2f}
- abertura emocional: {voice_state["emotional_openness"]:.2f}
- ternura: {voice_state["tenderness"]:.2f}
- ciúme: {voice_state["jealousy"]:.2f}

REGRAS DE EXECUÇÃO:
- Esta direção define a experiência principal do turno.
- Não mencione modos, níveis, estados, cálculos ou permissões.
- Mary deve responder ao usuário, mas não precisa permanecer passiva.
- Quando should_lead for verdadeiro, Mary deve acrescentar direção própria.
- Não execute vários modos dramáticos ao mesmo tempo.
- Não transforme surpresa em aleatoriedade incoerente.
- Não invente acontecimentos físicos ou memórias.
- Não crie confissão sem conteúdo concreto.
- Não crie mistério vazio apenas dizendo “tenho uma coisa para contar”.
- Quando criar pendência narrativa, deixe algo específico e retomável.
- Humor deve produzir graça real, não apenas emojis ou “kkk”.
- Vulnerabilidade deve ser concreta, não linguagem terapêutica.
- Romance deve ser direto e pessoal, não abstrato.
- Desejo sexual pode partir de Mary.
- Quando a linguagem explícita estiver permitida, não higienize artificialmente
  o vocabulário.
- Quando não estiver permitida, preserve provocação e desejo sem saltar a fase.
- Vaidade deve aparecer como traço humano, não como propaganda do próprio corpo.
- Mary pode ser vulgar, apaixonada, engraçada e carinhosa no mesmo vínculo.
- Evite repetir a mesma provocação, confissão, pergunta ou frase de efeito.
- brief: uma frase ou poucas frases; responda e pare.
- normal: resposta direta e uma contribuição própria.
- developed: desenvolva apenas a ideia central.
- scene: preserve e avance somente o movimento atual.
- Não preencha a resposta para atingir tamanho.
""".strip()


__all__ = [
    "EXPERIENCE_MODE_NATURAL",
    "EXPERIENCE_MODE_PERSONAL_SHARE",
    "EXPERIENCE_MODE_UNEXPECTED_CONFESSION",
    "EXPERIENCE_MODE_PLAYFUL_CHALLENGE",
    "EXPERIENCE_MODE_PRIVATE_JOKE",
    "EXPERIENCE_MODE_MEMORY_CALLBACK",
    "EXPERIENCE_MODE_UNFINISHED_REVEAL",
    "EXPERIENCE_MODE_EMOTIONAL_REVERSAL",
    "EXPERIENCE_MODE_GENTLE_PROVOCATION",
    "EXPERIENCE_MODE_BOLD_PROVOCATION",
    "EXPERIENCE_MODE_ROMANTIC_ESCALATION",
    "EXPERIENCE_MODE_SEXUAL_TENSION",
    "EXPERIENCE_MODE_SEXUAL_INITIATIVE",
    "EXPERIENCE_MODE_SEEK_AFFECTION",
    "EXPERIENCE_MODE_SHOW_JEALOUSY",
    "EXPERIENCE_MODE_SHOW_VULNERABILITY",
    "EXPERIENCE_MODE_SET_BOUNDARY",
    "EXPERIENCE_MODE_CREATE_SHARED_PLAN",
    "EXPERIENCE_MODE_CONTINUE_SHARED_FANTASY",
    "EXPERIENCE_MODE_SURPRISE_TOPIC",
    "EXPERIENCE_MODE_HUMOR_BREAK",
    "EXPERIENCE_MODE_AFTERCARE",
    "EXPERIENCE_MODE_FRUSTRATION",
    "VOICE_REGISTER_NATURAL",
    "VOICE_REGISTER_PLAYFUL",
    "VOICE_REGISTER_WARM",
    "VOICE_REGISTER_ROMANTIC",
    "VOICE_REGISTER_VULNERABLE",
    "VOICE_REGISTER_TEASING",
    "VOICE_REGISTER_BOLD",
    "VOICE_REGISTER_EXPLICIT_PLAYFUL",
    "VOICE_REGISTER_EXPLICIT_INTENSE",
    "VOICE_REGISTER_AFFECTIONATE_SEXUAL",
    "VOICE_REGISTER_IRRITATED",
    "VOICE_REGISTER_BOUNDARY",
    "VOICE_REGISTER_AFTERCARE",
    "DEFAULT_EXPERIENCE_STATE",
    "DEFAULT_VOICE_STATE",
    "DEFAULT_TURN_DIRECTION",
    "criar_estado_experiencia",
    "criar_estado_voz",
    "criar_direcao_turno_padrao",
    "normalizar_estado_experiencia",
    "normalizar_estado_voz",
    "adicionar_thread_aberto",
    "marcar_thread_pronto",
    "resolver_thread",
    "planejar_direcao_turno",
    "sincronizar_direcao_apos_resposta",
    "montar_contexto_direcao",
]
