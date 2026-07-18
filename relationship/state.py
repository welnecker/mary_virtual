from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from relationship.director_engine import (
    DEFAULT_EXPERIENCE_STATE,
    DEFAULT_TURN_DIRECTION,
    DEFAULT_VOICE_STATE,
    normalizar_estado_experiencia,
    normalizar_estado_voz,
)
from relationship.initiative_engine import (
    DEFAULT_MARY_INTERNAL_STATE,
    DEFAULT_TURN_INTENT,
    normalizar_estado_interno_mary,
)


RELATIONSHIP_STATE_VERSION = (
    "relationship-state-v2-agency-director"
)


# ==========================================================
# ESTADO SEXUAL PADRÃO
# ==========================================================


DEFAULT_SEXUAL_STATE: dict[str, Any] = {
    "scene_phase": "idle",
    "previous_scene_phase": "",
    "arousal_level": 0.0,
    "tension_level": 0.0,
    "stimulation_turns": 0,
    "mary_pre_orgasm": False,
    "mary_orgasm_allowed": False,
    "mary_orgasm_done": False,
    "user_orgasm_pending": False,
    "user_orgasm_done": False,
    "frustration_state": "",
    "aftercare_required": False,
    "last_stimulus_type": "",
    "last_transition_reason": "",
}


# ==========================================================
# ESTADO CANÔNICO DA RELAÇÃO
# ==========================================================


DEFAULT_RELATIONSHIP_STATE: dict[str, Any] = {
    "state_version": RELATIONSHIP_STATE_VERSION,

    # Relação emocional.
    "emotional_stage": "first_contact",
    "previous_emotional_stage": "",

    # Liberdade e intimidade sexual.
    "sexual_level": 0,
    "previous_sexual_level": 0,

    # Métricas silenciosas de longo prazo.
    "trust_level": 0.0,
    "affection_level": 0.0,
    "familiarity_level": 0.0,
    "romantic_tension_level": 0.0,

    # Histórico geral.
    "interaction_count": 0,
    "relationship_summary": "",

    # Continuidade da cena sexual.
    "sexual_state": deepcopy(
        DEFAULT_SEXUAL_STATE
    ),

    # Vida interna e agência de Mary.
    "mary_internal_state": deepcopy(
        DEFAULT_MARY_INTERNAL_STATE
    ),

    # Direção narrativa e ritmo da experiência.
    "experience_state": deepcopy(
        DEFAULT_EXPERIENCE_STATE
    ),

    # Paleta verbal e emocional ativa.
    "voice_state": deepcopy(
        DEFAULT_VOICE_STATE
    ),

    # Planejamento do turno atual.
    "current_turn_intent": {},
    "current_turn_direction": {},

    # Último turno concluído.
    "last_turn_intent": {},
    "last_turn_direction": {},

    # Diagnósticos e sinais do último ciclo.
    "last_relationship_signals": {},
    "last_sexual_validation": {},
    "last_relationship_increments": {},
    "last_emotional_transition_reason": "",
    "last_sexual_transition_reason": "",

    # Controle temporal.
    "created_at": "",
    "updated_at": "",
}


# ==========================================================
# UTILIDADES
# ==========================================================


def utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


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


def normalizar_dict(
    value: Any,
) -> dict[str, Any]:
    if isinstance(
        value,
        dict,
    ):
        return deepcopy(
            value
        )

    return {}


def normalizar_bool(
    value: Any,
    *,
    default: bool = False,
) -> bool:
    if isinstance(
        value,
        bool,
    ):
        return value

    if value is None:
        return default

    if isinstance(
        value,
        (int, float),
    ):
        return bool(
            value
        )

    text = str(
        value
    ).strip().lower()

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


def normalizar_texto(
    value: Any,
    *,
    default: str = "",
) -> str:
    if value is None:
        return default

    return str(
        value
    ).strip()


# ==========================================================
# NORMALIZAÇÃO DO ESTADO SEXUAL
# ==========================================================


def criar_estado_sexual_padrao() -> dict[str, Any]:
    return deepcopy(
        DEFAULT_SEXUAL_STATE
    )


def normalizar_estado_sexual(
    value: dict[str, Any] | None,
) -> dict[str, Any]:
    state = criar_estado_sexual_padrao()

    if isinstance(
        value,
        dict,
    ):
        state.update(
            deepcopy(
                value
            )
        )

    state["scene_phase"] = (
        normalizar_texto(
            state.get(
                "scene_phase"
            ),
            default="idle",
        )
        or "idle"
    )

    state["previous_scene_phase"] = (
        normalizar_texto(
            state.get(
                "previous_scene_phase"
            )
        )
    )

    state["arousal_level"] = limitar_valor(
        state.get(
            "arousal_level",
            0.0,
        )
    )

    state["tension_level"] = limitar_valor(
        state.get(
            "tension_level",
            0.0,
        )
    )

    state["stimulation_turns"] = max(
        0,
        safe_int(
            state.get(
                "stimulation_turns",
                0,
            )
        ),
    )

    boolean_fields = (
        "mary_pre_orgasm",
        "mary_orgasm_allowed",
        "mary_orgasm_done",
        "user_orgasm_pending",
        "user_orgasm_done",
        "aftercare_required",
    )

    for field in boolean_fields:
        state[field] = normalizar_bool(
            state.get(field),
            default=False,
        )

    text_fields = (
        "frustration_state",
        "last_stimulus_type",
        "last_transition_reason",
    )

    for field in text_fields:
        state[field] = normalizar_texto(
            state.get(field)
        )

    return state


# ==========================================================
# CRIAÇÃO DO ESTADO
# ==========================================================


def criar_estado_relacao_padrao() -> dict[str, Any]:
    state = deepcopy(
        DEFAULT_RELATIONSHIP_STATE
    )

    agora = utc_now_iso()

    state["created_at"] = agora
    state["updated_at"] = agora

    return state


# ==========================================================
# NORMALIZAÇÃO DOS BLOCOS DO TURNO
# ==========================================================


def normalizar_intencao_turno(
    value: dict[str, Any] | None,
    *,
    permitir_vazio: bool = True,
) -> dict[str, Any]:
    if (
        permitir_vazio
        and not value
    ):
        return {}

    intent = deepcopy(
        DEFAULT_TURN_INTENT
    )

    if isinstance(
        value,
        dict,
    ):
        intent.update(
            deepcopy(
                value
            )
        )

    return intent


def normalizar_direcao_turno(
    value: dict[str, Any] | None,
    *,
    permitir_vazio: bool = True,
) -> dict[str, Any]:
    if (
        permitir_vazio
        and not value
    ):
        return {}

    direction = deepcopy(
        DEFAULT_TURN_DIRECTION
    )

    if isinstance(
        value,
        dict,
    ):
        direction.update(
            deepcopy(
                value
            )
        )

    direction["voice_state"] = (
        normalizar_estado_voz(
            direction.get(
                "voice_state"
            )
        )
    )

    return direction


# ==========================================================
# NORMALIZAÇÃO CANÔNICA
# ==========================================================


def normalizar_estado_relacao(
    state: dict[str, Any] | None,
    *,
    tocar_updated_at: bool = False,
) -> dict[str, Any]:
    """
    Converte qualquer estado antigo ou parcial para a estrutura canônica.

    Por padrão, apenas normalizar não altera updated_at. Use
    tocar_updated_at=True somente quando o estado tiver sido realmente
    modificado por uma interação ou ação do aplicativo.
    """

    normalized = criar_estado_relacao_padrao()

    if not isinstance(
        state,
        dict,
    ):
        return normalized
    
    normalized[
        "state_version"
    ] = RELATIONSHIP_STATE_VERSION

    normalized[
        "emotional_stage"
    ] = (
        normalizar_texto(
            state.get(
                "emotional_stage"
            )
            or state.get(
                "stage"
            ),
            default="first_contact",
        )
        or "first_contact"
    )

    normalized[
        "previous_emotional_stage"
    ] = normalizar_texto(
        state.get(
            "previous_emotional_stage"
        )
        or state.get(
            "previous_stage"
        )
    )

    normalized[
        "sexual_level"
    ] = max(
        0,
        min(
            5,
            safe_int(
                state.get(
                    "sexual_level",
                    state.get(
                        "sexual_intimacy",
                        0,
                    ),
                )
            ),
        ),
    )

    normalized[
        "previous_sexual_level"
    ] = max(
        0,
        min(
            5,
            safe_int(
                state.get(
                    "previous_sexual_level",
                    0,
                )
            ),
        ),
    )

    normalized[
        "last_relationship_increments"
    ] = normalizar_dict(
        state.get(
            "last_relationship_increments"
        )
    )
    
    normalized[
        "last_emotional_transition_reason"
    ] = normalizar_texto(
        state.get(
            "last_emotional_transition_reason"
        )
    )
    
    normalized[
        "last_sexual_transition_reason"
    ] = normalizar_texto(
        state.get(
            "last_sexual_transition_reason"
        )
    )

    metric_aliases = {
        "trust_level": (
            "trust_level",
            "trust",
        ),
        "affection_level": (
            "affection_level",
            "affection",
        ),
        "familiarity_level": (
            "familiarity_level",
            "familiarity",
        ),
        "romantic_tension_level": (
            "romantic_tension_level",
            "romantic_tension",
        ),
    }

    for canonical_key, aliases in (
        metric_aliases.items()
    ):
        raw_value: Any = 0.0

        for alias in aliases:
            if alias in state:
                raw_value = state[
                    alias
                ]
                break

        normalized[
            canonical_key
        ] = limitar_valor(
            raw_value
        )

    normalized[
        "interaction_count"
    ] = max(
        0,
        safe_int(
            state.get(
                "interaction_count",
                0,
            )
        ),
    )

    normalized[
        "relationship_summary"
    ] = normalizar_texto(
        state.get(
            "relationship_summary"
        )
    )

    normalized[
        "sexual_state"
    ] = normalizar_estado_sexual(
        state.get(
            "sexual_state"
        )
    )

    normalized[
        "mary_internal_state"
    ] = normalizar_estado_interno_mary(
        state.get(
            "mary_internal_state"
        )
    )

    normalized[
        "experience_state"
    ] = normalizar_estado_experiencia(
        state.get(
            "experience_state"
        )
    )

    normalized[
        "voice_state"
    ] = normalizar_estado_voz(
        state.get(
            "voice_state"
        )
    )

    normalized[
        "current_turn_intent"
    ] = normalizar_intencao_turno(
        state.get(
            "current_turn_intent"
        ),
        permitir_vazio=True,
    )

    normalized[
        "current_turn_direction"
    ] = normalizar_direcao_turno(
        state.get(
            "current_turn_direction"
        ),
        permitir_vazio=True,
    )

    normalized[
        "last_turn_intent"
    ] = normalizar_intencao_turno(
        state.get(
            "last_turn_intent"
        ),
        permitir_vazio=True,
    )

    normalized[
        "last_turn_direction"
    ] = normalizar_direcao_turno(
        state.get(
            "last_turn_direction"
        ),
        permitir_vazio=True,
    )

    normalized[
        "last_relationship_signals"
    ] = normalizar_dict(
        state.get(
            "last_relationship_signals"
        )
    )

    normalized[
        "last_sexual_validation"
    ] = normalizar_dict(
        state.get(
            "last_sexual_validation"
        )
    )

    created_at = normalizar_texto(
        state.get(
            "created_at"
        )
    )

    updated_at = normalizar_texto(
        state.get(
            "updated_at"
        )
    )

    normalized[
        "created_at"
    ] = (
        created_at
        or normalized[
            "created_at"
        ]
    )

    normalized[
        "updated_at"
    ] = (
        updated_at
        or normalized[
            "updated_at"
        ]
    )

    if tocar_updated_at:
        normalized[
            "updated_at"
        ] = utc_now_iso()

    return normalized


# ==========================================================
# ATUALIZAÇÃO CONTROLADA
# ==========================================================


def marcar_estado_relacao_atualizado(
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = normalizar_estado_relacao(
        state,
        tocar_updated_at=False,
    )

    normalized[
        "updated_at"
    ] = utc_now_iso()

    return normalized


def limpar_planejamento_turno(
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = normalizar_estado_relacao(
        state,
        tocar_updated_at=False,
    )

    normalized[
        "current_turn_intent"
    ] = {}

    normalized[
        "current_turn_direction"
    ] = {}

    normalized[
        "updated_at"
    ] = utc_now_iso()

    return normalized


def preparar_estado_para_persistencia(
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Produz uma cópia limpa e canônica para salvar no banco ou Google Sheets.

    O planejamento atual é mantido, pois pode ser útil para recuperação após
    falha. O chamador pode usar limpar_planejamento_turno antes de persistir
    quando desejar salvar somente turnos concluídos.
    """

    return normalizar_estado_relacao(
        state,
        tocar_updated_at=False,
    )


# ==========================================================
# DIAGNÓSTICO
# ==========================================================


def montar_resumo_estado_relacao(
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = normalizar_estado_relacao(
        state,
        tocar_updated_at=False,
    )

    internal_state = normalized[
        "mary_internal_state"
    ]

    experience_state = normalized[
        "experience_state"
    ]

    voice_state = normalized[
        "voice_state"
    ]

    sexual_state = normalized[
        "sexual_state"
    ]

    current_intent = normalized[
        "current_turn_intent"
    ]

    current_direction = normalized[
        "current_turn_direction"
    ]

    return {
        "state_version": normalized[
            "state_version"
        ],
        "emotional_stage": normalized[
            "emotional_stage"
        ],
        "sexual_level": normalized[
            "sexual_level"
        ],
        "interaction_count": normalized[
            "interaction_count"
        ],
        "trust_level": normalized[
            "trust_level"
        ],
        "affection_level": normalized[
            "affection_level"
        ],
        "familiarity_level": normalized[
            "familiarity_level"
        ],
        "romantic_tension_level": normalized[
            "romantic_tension_level"
        ],
        "sexual_phase": sexual_state.get(
            "scene_phase",
            "idle",
        ),
        "mary_mood": internal_state.get(
            "current_mood",
            "neutral",
        ),
        "mary_desire": internal_state.get(
            "current_desire",
            0.0,
        ),
        "mary_curiosity": internal_state.get(
            "current_curiosity",
            0.0,
        ),
        "mary_initiative_drive": (
            internal_state.get(
                "initiative_drive",
                0.0,
            )
        ),
        "experience_mode": (
            experience_state.get(
                "current_mode",
                "natural_conversation",
            )
        ),
        "surprise_budget": (
            experience_state.get(
                "surprise_budget",
                0.0,
            )
        ),
        "voice_register": (
            current_direction.get(
                "voice_register"
            )
            or experience_state.get(
                "last_voice_register"
            )
            or "natural"
        ),
        "sexual_explicitness": (
            voice_state.get(
                "sexual_explicitness",
                0.0,
            )
        ),
        "vulgarity": voice_state.get(
            "vulgarity",
            0.0,
        ),
        "current_turn_mode": (
            current_intent.get(
                "turn_mode",
                "",
            )
        ),
        "current_experience_mode": (
            current_direction.get(
                "experience_mode",
                "",
            )
        ),
        "open_thread_count": len(
            [
                thread
                for thread in experience_state.get(
                    "open_threads",
                    []
                )
                if (
                    isinstance(
                        thread,
                        dict,
                    )
                    and not thread.get(
                        "resolved",
                        False,
                    )
                )
            ]
        ),
        "created_at": normalized[
            "created_at"
        ],
        "updated_at": normalized[
            "updated_at"
        ],
    }


__all__ = [
    "RELATIONSHIP_STATE_VERSION",
    "DEFAULT_SEXUAL_STATE",
    "DEFAULT_RELATIONSHIP_STATE",
    "utc_now_iso",
    "safe_int",
    "safe_float",
    "limitar_valor",
    "normalizar_dict",
    "normalizar_bool",
    "normalizar_texto",
    "criar_estado_sexual_padrao",
    "normalizar_estado_sexual",
    "criar_estado_relacao_padrao",
    "normalizar_intencao_turno",
    "normalizar_direcao_turno",
    "normalizar_estado_relacao",
    "marcar_estado_relacao_atualizado",
    "limpar_planejamento_turno",
    "preparar_estado_para_persistencia",
    "montar_resumo_estado_relacao",
]
