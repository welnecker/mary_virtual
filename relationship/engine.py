from __future__ import annotations

from typing import Any

from relationship.signals import (
    DEFAULT_RELATIONSHIP_SIGNALS,
)
from relationship.state import (
    normalizar_estado_relacao,
    utc_now_iso,
)


# ==========================================================
# ESTÁGIOS EMOCIONAIS
# ==========================================================


EMOTIONAL_STAGE_FIRST_CONTACT = "first_contact"
EMOTIONAL_STAGE_ACQUAINTANCE = "acquaintance"
EMOTIONAL_STAGE_CONNECTION = "connection"
EMOTIONAL_STAGE_INTIMACY = "intimacy"
EMOTIONAL_STAGE_DEEP_BOND = "deep_bond"


EMOTIONAL_STAGE_ORDER: tuple[str, ...] = (
    EMOTIONAL_STAGE_FIRST_CONTACT,
    EMOTIONAL_STAGE_ACQUAINTANCE,
    EMOTIONAL_STAGE_CONNECTION,
    EMOTIONAL_STAGE_INTIMACY,
    EMOTIONAL_STAGE_DEEP_BOND,
)


# ==========================================================
# NÍVEIS SEXUAIS
# ==========================================================


SEXUAL_LEVEL_NONE = 0
SEXUAL_LEVEL_ATTRACTION = 1
SEXUAL_LEVEL_FLIRT = 2
SEXUAL_LEVEL_DESIRE = 3
SEXUAL_LEVEL_INTIMACY = 4
SEXUAL_LEVEL_DEEP_INTIMACY = 5


SEXUAL_LEVEL_MIN = SEXUAL_LEVEL_NONE
SEXUAL_LEVEL_MAX = SEXUAL_LEVEL_DEEP_INTIMACY


# ==========================================================
# CONFIGURAÇÃO DE PROGRESSÃO
# ==========================================================


EMOTIONAL_STAGE_REQUIREMENTS: dict[str, dict[str, Any]] = {
    EMOTIONAL_STAGE_FIRST_CONTACT: {
        "min_interactions": 0,
        "min_familiarity": 0.0,
        "min_trust": 0.0,
        "min_affection": 0.0,
    },
    EMOTIONAL_STAGE_ACQUAINTANCE: {
        "min_interactions": 3,
        "min_familiarity": 0.12,
        "min_trust": 0.04,
        "min_affection": 0.02,
    },
    EMOTIONAL_STAGE_CONNECTION: {
        "min_interactions": 8,
        "min_familiarity": 0.32,
        "min_trust": 0.22,
        "min_affection": 0.16,
    },
    EMOTIONAL_STAGE_INTIMACY: {
        "min_interactions": 18,
        "min_familiarity": 0.58,
        "min_trust": 0.50,
        "min_affection": 0.42,
    },
    EMOTIONAL_STAGE_DEEP_BOND: {
        "min_interactions": 35,
        "min_familiarity": 0.78,
        "min_trust": 0.72,
        "min_affection": 0.68,
    },
}


SEXUAL_LEVEL_REQUIREMENTS: dict[int, dict[str, Any]] = {
    SEXUAL_LEVEL_NONE: {
        "min_interactions": 0,
        "min_familiarity": 0.0,
        "min_trust": 0.0,
        "min_affection": 0.0,
        "min_romantic_tension": 0.0,
        "min_emotional_stage": (
            EMOTIONAL_STAGE_FIRST_CONTACT
        ),
    },
    SEXUAL_LEVEL_ATTRACTION: {
        "min_interactions": 4,
        "min_familiarity": 0.15,
        "min_trust": 0.06,
        "min_affection": 0.04,
        "min_romantic_tension": 0.12,
        "min_emotional_stage": (
            EMOTIONAL_STAGE_ACQUAINTANCE
        ),
    },
    SEXUAL_LEVEL_FLIRT: {
        "min_interactions": 8,
        "min_familiarity": 0.28,
        "min_trust": 0.16,
        "min_affection": 0.12,
        "min_romantic_tension": 0.28,
        "min_emotional_stage": (
            EMOTIONAL_STAGE_CONNECTION
        ),
    },
    SEXUAL_LEVEL_DESIRE: {
        "min_interactions": 14,
        "min_familiarity": 0.42,
        "min_trust": 0.30,
        "min_affection": 0.24,
        "min_romantic_tension": 0.48,
        "min_emotional_stage": (
            EMOTIONAL_STAGE_CONNECTION
        ),
    },
    SEXUAL_LEVEL_INTIMACY: {
        "min_interactions": 22,
        "min_familiarity": 0.60,
        "min_trust": 0.52,
        "min_affection": 0.42,
        "min_romantic_tension": 0.66,
        "min_emotional_stage": (
            EMOTIONAL_STAGE_INTIMACY
        ),
    },
    SEXUAL_LEVEL_DEEP_INTIMACY: {
        "min_interactions": 38,
        "min_familiarity": 0.80,
        "min_trust": 0.74,
        "min_affection": 0.66,
        "min_romantic_tension": 0.82,
        "min_emotional_stage": (
            EMOTIONAL_STAGE_DEEP_BOND
        ),
    },
}


# ==========================================================
# UTILIDADES
# ==========================================================


def safe_int(
    value: Any,
    default: int = 0,
) -> int:
    try:
        return int(
            value
        )
    except (TypeError, ValueError):
        return default


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        return float(
            value
        )
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


def normalizar_estagio_emocional(
    stage: Any,
) -> str:
    normalized = str(
        stage or ""
    ).strip().lower()

    if normalized in EMOTIONAL_STAGE_ORDER:
        return normalized

    return EMOTIONAL_STAGE_FIRST_CONTACT


def obter_indice_estagio_emocional(
    stage: Any,
) -> int:
    normalized = normalizar_estagio_emocional(
        stage
    )

    return EMOTIONAL_STAGE_ORDER.index(
        normalized
    )


def limitar_nivel_sexual(
    level: Any,
) -> int:
    normalized = safe_int(
        level,
        SEXUAL_LEVEL_NONE,
    )

    return max(
        SEXUAL_LEVEL_MIN,
        min(
            SEXUAL_LEVEL_MAX,
            normalized,
        ),
    )


def normalizar_sinais(
    signals: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = dict(
        DEFAULT_RELATIONSHIP_SIGNALS
    )

    if isinstance(
        signals,
        dict,
    ):
        normalized.update(
            signals
        )

    return normalized


# ==========================================================
# CÁLCULO DE INCREMENTOS
# ==========================================================


def calcular_incrementos_relacao(
    signals: dict[str, Any] | None,
) -> dict[str, float]:
    signals_normalized = normalizar_sinais(
        signals
    )

    familiarity_delta = 0.0
    trust_delta = 0.0
    affection_delta = 0.0
    romantic_delta = 0.0

    if signals_normalized.get(
        "interaction_exists"
    ):
        familiarity_delta += 0.018

    if signals_normalized.get(
        "user_returned"
    ):
        familiarity_delta += 0.010

    if signals_normalized.get(
        "continuity_signal"
    ):
        familiarity_delta += 0.018
        trust_delta += 0.006

    if signals_normalized.get(
        "personal_disclosure"
    ):
        familiarity_delta += 0.022
        trust_delta += 0.018

    if signals_normalized.get(
        "emotional_disclosure"
    ):
        trust_delta += 0.030
        affection_delta += 0.016

    if signals_normalized.get(
        "trust_signal"
    ):
        trust_delta += 0.040
        affection_delta += 0.010

    if signals_normalized.get(
        "affection_signal"
    ):
        affection_delta += 0.034
        trust_delta += 0.008

    if signals_normalized.get(
        "romantic_signal"
    ):
        romantic_delta += 0.040
        affection_delta += 0.018

    if signals_normalized.get(
        "sexual_signal"
    ):
        romantic_delta += 0.028

    if signals_normalized.get(
        "explicit_sexual_signal"
    ):
        romantic_delta += 0.022

    if signals_normalized.get(
        "respect_signal"
    ):
        trust_delta += 0.020
        affection_delta += 0.006

    if signals_normalized.get(
        "image_shared"
    ):
        familiarity_delta += 0.012
        trust_delta += 0.008

    if signals_normalized.get(
        "boundary_signal"
    ):
        romantic_delta -= 0.035

    if signals_normalized.get(
        "rejection_signal"
    ):
        trust_delta -= 0.055
        affection_delta -= 0.060
        romantic_delta -= 0.090

    if signals_normalized.get(
        "hostility_signal"
    ):
        trust_delta -= 0.090
        affection_delta -= 0.075
        romantic_delta -= 0.100

    return {
        "familiarity_delta": familiarity_delta,
        "trust_delta": trust_delta,
        "affection_delta": affection_delta,
        "romantic_tension_delta": romantic_delta,
    }


# ==========================================================
# ATUALIZAÇÃO DOS MARCADORES
# ==========================================================


def aplicar_incrementos_relacao(
    state: dict[str, Any],
    increments: dict[str, float],
) -> None:
    state[
        "familiarity_level"
    ] = limitar_valor(
        safe_float(
            state.get(
                "familiarity_level",
                0.0,
            )
        )
        + safe_float(
            increments.get(
                "familiarity_delta",
                0.0,
            )
        )
    )

    state[
        "trust_level"
    ] = limitar_valor(
        safe_float(
            state.get(
                "trust_level",
                0.0,
            )
        )
        + safe_float(
            increments.get(
                "trust_delta",
                0.0,
            )
        )
    )

    state[
        "affection_level"
    ] = limitar_valor(
        safe_float(
            state.get(
                "affection_level",
                0.0,
            )
        )
        + safe_float(
            increments.get(
                "affection_delta",
                0.0,
            )
        )
    )

    state[
        "romantic_tension_level"
    ] = limitar_valor(
        safe_float(
            state.get(
                "romantic_tension_level",
                0.0,
            )
        )
        + safe_float(
            increments.get(
                "romantic_tension_delta",
                0.0,
            )
        )
    )


# ==========================================================
# GATE EMOCIONAL
# ==========================================================


def requisitos_estagio_emocional_atendidos(
    state: dict[str, Any],
    target_stage: str,
) -> bool:
    target = normalizar_estagio_emocional(
        target_stage
    )

    requirements = (
        EMOTIONAL_STAGE_REQUIREMENTS[
            target
        ]
    )

    interaction_count = safe_int(
        state.get(
            "interaction_count",
            0,
        )
    )

    familiarity = limitar_valor(
        state.get(
            "familiarity_level",
            0.0,
        )
    )

    trust = limitar_valor(
        state.get(
            "trust_level",
            0.0,
        )
    )

    affection = limitar_valor(
        state.get(
            "affection_level",
            0.0,
        )
    )

    return (
        interaction_count
        >= requirements[
            "min_interactions"
        ]
        and familiarity
        >= requirements[
            "min_familiarity"
        ]
        and trust
        >= requirements[
            "min_trust"
        ]
        and affection
        >= requirements[
            "min_affection"
        ]
    )


def calcular_estagio_emocional_maximo(
    state: dict[str, Any],
) -> str:
    maximum_stage = (
        EMOTIONAL_STAGE_FIRST_CONTACT
    )

    for stage in EMOTIONAL_STAGE_ORDER:
        if requisitos_estagio_emocional_atendidos(
            state,
            stage,
        ):
            maximum_stage = stage
        else:
            break

    return maximum_stage


def atualizar_estagio_emocional(
    state: dict[str, Any],
) -> None:
    current_stage = (
        normalizar_estagio_emocional(
            state.get(
                "emotional_stage"
            )
        )
    )

    target_stage = (
        calcular_estagio_emocional_maximo(
            state
        )
    )

    current_index = (
        obter_indice_estagio_emocional(
            current_stage
        )
    )

    target_index = (
        obter_indice_estagio_emocional(
            target_stage
        )
    )

    # Nunca avançar mais de um estágio por interação.
    if target_index > current_index:
        new_stage = EMOTIONAL_STAGE_ORDER[
            current_index + 1
        ]

        state[
            "previous_emotional_stage"
        ] = current_stage

        state[
            "emotional_stage"
        ] = new_stage

        state[
            "last_emotional_transition_reason"
        ] = (
            "emotional_requirements_reached"
        )

        return

    # Regressão exige uma diferença real e relevante.
    if target_index < current_index:
        trust = limitar_valor(
            state.get(
                "trust_level",
                0.0,
            )
        )

        affection = limitar_valor(
            state.get(
                "affection_level",
                0.0,
            )
        )

        current_requirements = (
            EMOTIONAL_STAGE_REQUIREMENTS[
                current_stage
            ]
        )

        severe_drop = (
            trust
            < max(
                0.0,
                current_requirements[
                    "min_trust"
                ] - 0.20,
            )
            or affection
            < max(
                0.0,
                current_requirements[
                    "min_affection"
                ] - 0.20,
            )
        )

        if severe_drop:
            new_stage = EMOTIONAL_STAGE_ORDER[
                max(
                    0,
                    current_index - 1,
                )
            ]

            state[
                "previous_emotional_stage"
            ] = current_stage

            state[
                "emotional_stage"
            ] = new_stage

            state[
                "last_emotional_transition_reason"
            ] = (
                "significant_relationship_damage"
            )


# ==========================================================
# GATE SEXUAL
# ==========================================================


def requisitos_nivel_sexual_atendidos(
    state: dict[str, Any],
    target_level: int,
    signals: dict[str, Any] | None = None,
) -> bool:
    level = limitar_nivel_sexual(
        target_level
    )

    requirements = (
        SEXUAL_LEVEL_REQUIREMENTS[
            level
        ]
    )

    interaction_count = safe_int(
        state.get(
            "interaction_count",
            0,
        )
    )

    familiarity = limitar_valor(
        state.get(
            "familiarity_level",
            0.0,
        )
    )

    trust = limitar_valor(
        state.get(
            "trust_level",
            0.0,
        )
    )

    affection = limitar_valor(
        state.get(
            "affection_level",
            0.0,
        )
    )

    romantic_tension = limitar_valor(
        state.get(
            "romantic_tension_level",
            0.0,
        )
    )

    emotional_stage = (
        normalizar_estagio_emocional(
            state.get(
                "emotional_stage"
            )
        )
    )

    emotional_stage_index = (
        obter_indice_estagio_emocional(
            emotional_stage
        )
    )

    required_stage_index = (
        obter_indice_estagio_emocional(
            requirements[
                "min_emotional_stage"
            ]
        )
    )

    basic_requirements = (
        interaction_count
        >= requirements[
            "min_interactions"
        ]
        and familiarity
        >= requirements[
            "min_familiarity"
        ]
        and trust
        >= requirements[
            "min_trust"
        ]
        and affection
        >= requirements[
            "min_affection"
        ]
        and romantic_tension
        >= requirements[
            "min_romantic_tension"
        ]
        and emotional_stage_index
        >= required_stage_index
    )

    if not basic_requirements:
        return False

    signals_normalized = normalizar_sinais(
        signals
    )

    # Do nível 1 em diante, deve existir alguma reciprocidade
    # romântica ou sexual no histórico recente.
    if level >= SEXUAL_LEVEL_ATTRACTION:
        has_relevant_signal = bool(
            signals_normalized.get(
                "romantic_signal"
            )
            or signals_normalized.get(
                "sexual_signal"
            )
            or signals_normalized.get(
                "affection_signal"
            )
        )

        if not has_relevant_signal:
            return False

    # Níveis de desejo e intimidade exigem sinal sexual.
    if level >= SEXUAL_LEVEL_DESIRE:
        if not bool(
            signals_normalized.get(
                "sexual_signal"
            )
            or signals_normalized.get(
                "explicit_sexual_signal"
            )
        ):
            return False

    # Intimidade alta exige confiança e respeito no turno.
    if level >= SEXUAL_LEVEL_INTIMACY:
        if signals_normalized.get(
            "boundary_signal"
        ):
            return False

        if signals_normalized.get(
            "rejection_signal"
        ):
            return False

        if signals_normalized.get(
            "hostility_signal"
        ):
            return False

    return True


def calcular_nivel_sexual_maximo(
    state: dict[str, Any],
    signals: dict[str, Any] | None = None,
) -> int:
    maximum_level = SEXUAL_LEVEL_NONE

    for level in range(
        SEXUAL_LEVEL_MIN,
        SEXUAL_LEVEL_MAX + 1,
    ):
        if requisitos_nivel_sexual_atendidos(
            state,
            level,
            signals,
        ):
            maximum_level = level
        else:
            break

    return maximum_level


def atualizar_nivel_sexual(
    state: dict[str, Any],
    signals: dict[str, Any] | None = None,
) -> None:
    signals_normalized = normalizar_sinais(
        signals
    )

    current_level = limitar_nivel_sexual(
        state.get(
            "sexual_level",
            0,
        )
    )

    target_level = (
        calcular_nivel_sexual_maximo(
            state,
            signals_normalized,
        )
    )

    # Limites explícitos interrompem progressão imediatamente.
    if signals_normalized.get(
        "boundary_signal"
    ):
        state[
            "last_sexual_transition_reason"
        ] = "boundary_signal_detected"

        return

    # Rejeição ou hostilidade podem causar regressão.
    if (
        signals_normalized.get(
            "rejection_signal"
        )
        or signals_normalized.get(
            "hostility_signal"
        )
    ):
        if current_level > SEXUAL_LEVEL_NONE:
            state[
                "previous_sexual_level"
            ] = current_level

            state[
                "sexual_level"
            ] = max(
                SEXUAL_LEVEL_NONE,
                current_level - 1,
            )

            state[
                "last_sexual_transition_reason"
            ] = (
                "sexual_trust_damaged"
            )

        return

    # Avanço máximo de um nível por interação.
    if target_level > current_level:
        state[
            "previous_sexual_level"
        ] = current_level

        state[
            "sexual_level"
        ] = current_level + 1

        state[
            "last_sexual_transition_reason"
        ] = (
            "sexual_requirements_reached"
        )

        return

    state[
        "sexual_level"
    ] = current_level


# ==========================================================
# RESUMO INTERNO
# ==========================================================


def montar_resumo_relacao(
    state: dict[str, Any],
) -> str:
    emotional_stage = (
        normalizar_estagio_emocional(
            state.get(
                "emotional_stage"
            )
        )
    )

    sexual_level = limitar_nivel_sexual(
        state.get(
            "sexual_level",
            0,
        )
    )

    interaction_count = safe_int(
        state.get(
            "interaction_count",
            0,
        )
    )

    familiarity = limitar_valor(
        state.get(
            "familiarity_level",
            0.0,
        )
    )

    trust = limitar_valor(
        state.get(
            "trust_level",
            0.0,
        )
    )

    affection = limitar_valor(
        state.get(
            "affection_level",
            0.0,
        )
    )

    romantic_tension = limitar_valor(
        state.get(
            "romantic_tension_level",
            0.0,
        )
    )

    return (
        f"Interações: {interaction_count}. "
        f"Estágio emocional: {emotional_stage}. "
        f"Nível sexual: {sexual_level}. "
        f"Familiaridade: {familiarity:.2f}. "
        f"Confiança: {trust:.2f}. "
        f"Afeto: {affection:.2f}. "
        f"Tensão romântica: {romantic_tension:.2f}."
    )


# ==========================================================
# MOTOR PRINCIPAL
# ==========================================================


def atualizar_estado_relacao(
    relationship_state: dict[str, Any] | None,
    *,
    signals: dict[str, Any] | None,
    incrementar_interacao: bool = True,
) -> dict[str, Any]:
    state = normalizar_estado_relacao(
        relationship_state
    )

    signals_normalized = normalizar_sinais(
        signals
    )

    if (
        incrementar_interacao
        and signals_normalized.get(
            "interaction_exists"
        )
    ):
        state[
            "interaction_count"
        ] = max(
            0,
            safe_int(
                state.get(
                    "interaction_count",
                    0,
                )
            ),
        ) + 1

    increments = calcular_incrementos_relacao(
        signals_normalized
    )

    aplicar_incrementos_relacao(
        state,
        increments,
    )

    atualizar_estagio_emocional(
        state
    )

    atualizar_nivel_sexual(
        state,
        signals_normalized,
    )

    state[
        "last_relationship_signals"
    ] = signals_normalized

    state[
        "last_relationship_increments"
    ] = increments

    state[
        "relationship_summary"
    ] = montar_resumo_relacao(
        state
    )

    state[
        "updated_at"
    ] = utc_now_iso()

    return state


# ==========================================================
# SIMULAÇÃO E DIAGNÓSTICO
# ==========================================================


def simular_atualizacao_relacao(
    relationship_state: dict[str, Any] | None,
    *,
    signals: dict[str, Any] | None,
) -> dict[str, Any]:
    current = normalizar_estado_relacao(
        relationship_state
    )

    updated = atualizar_estado_relacao(
        current,
        signals=signals,
        incrementar_interacao=True,
    )

    return {
        "before": {
            "interaction_count": current.get(
                "interaction_count"
            ),
            "emotional_stage": current.get(
                "emotional_stage"
            ),
            "sexual_level": current.get(
                "sexual_level"
            ),
            "familiarity_level": current.get(
                "familiarity_level"
            ),
            "trust_level": current.get(
                "trust_level"
            ),
            "affection_level": current.get(
                "affection_level"
            ),
            "romantic_tension_level": current.get(
                "romantic_tension_level"
            ),
        },
        "after": {
            "interaction_count": updated.get(
                "interaction_count"
            ),
            "emotional_stage": updated.get(
                "emotional_stage"
            ),
            "sexual_level": updated.get(
                "sexual_level"
            ),
            "familiarity_level": updated.get(
                "familiarity_level"
            ),
            "trust_level": updated.get(
                "trust_level"
            ),
            "affection_level": updated.get(
                "affection_level"
            ),
            "romantic_tension_level": updated.get(
                "romantic_tension_level"
            ),
        },
        "signals": normalizar_sinais(
            signals
        ),
        "increments": updated.get(
            "last_relationship_increments",
            {},
        ),
    }
