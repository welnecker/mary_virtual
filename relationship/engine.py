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
        "min_interactions": 2,
        "min_familiarity": 0.08,
        "min_trust": 0.02,
        "min_affection": 0.01,
        "min_romantic_tension": 0.08,
        "min_emotional_stage": (
            EMOTIONAL_STAGE_FIRST_CONTACT
        ),
    },

    SEXUAL_LEVEL_FLIRT: {
        "min_interactions": 4,
        "min_familiarity": 0.16,
        "min_trust": 0.08,
        "min_affection": 0.06,
        "min_romantic_tension": 0.20,
        "min_emotional_stage": (
            EMOTIONAL_STAGE_ACQUAINTANCE
        ),
    },

    SEXUAL_LEVEL_DESIRE: {
        "min_interactions": 7,
        "min_familiarity": 0.26,
        "min_trust": 0.16,
        "min_affection": 0.12,
        "min_romantic_tension": 0.36,
        "min_emotional_stage": (
            EMOTIONAL_STAGE_ACQUAINTANCE
        ),
    },

    SEXUAL_LEVEL_INTIMACY: {
        "min_interactions": 11,
        "min_familiarity": 0.40,
        "min_trust": 0.28,
        "min_affection": 0.22,
        "min_romantic_tension": 0.54,
        "min_emotional_stage": (
            EMOTIONAL_STAGE_CONNECTION
        ),
    },

    SEXUAL_LEVEL_DEEP_INTIMACY: {
        "min_interactions": 24,
        "min_familiarity": 0.68,
        "min_trust": 0.58,
        "min_affection": 0.52,
        "min_romantic_tension": 0.74,
        "min_emotional_stage": (
            EMOTIONAL_STAGE_INTIMACY
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
    relationship_state: dict[str, Any] | None = None,
) -> dict[str, float]:
    signals_normalized = normalizar_sinais(
        signals
    )

    state = (
        relationship_state
        if isinstance(
            relationship_state,
            dict,
        )
        else {}
    )

    familiarity_delta = 0.0
    trust_delta = 0.0
    affection_delta = 0.0
    romantic_delta = 0.0

    affection_strength = limitar_valor(
        signals_normalized.get(
            "affection_strength",
            0.0,
        )
    )

    romantic_strength = limitar_valor(
        signals_normalized.get(
            "romantic_strength",
            0.0,
        )
    )

    sexual_strength = limitar_valor(
        signals_normalized.get(
            "sexual_strength",
            0.0,
        )
    )

    trust_strength = limitar_valor(
        signals_normalized.get(
            "trust_strength",
            0.0,
        )
    )

    negative_strength = limitar_valor(
        signals_normalized.get(
            "negative_strength",
            0.0,
        )
    )

    # Uma interação real aumenta familiaridade,
    # mas não cria automaticamente amor ou confiança.
    if signals_normalized.get(
        "interaction_exists"
    ):
        familiarity_delta += 0.018

    # Conversas recorrentes geram familiaridade suave.
    if signals_normalized.get(
        "repeated_interaction"
    ):
        familiarity_delta += 0.004

    # Retorno real depois de uma ausência ou nova sessão.
    if signals_normalized.get(
        "user_returned"
    ):
        familiarity_delta += 0.012
        affection_delta += 0.004

    # Retomada concreta de assunto ou memória.
    if signals_normalized.get(
        "continuity_signal"
    ):
        familiarity_delta += 0.018
        trust_delta += 0.008

    if signals_normalized.get(
        "personal_disclosure"
    ):
        familiarity_delta += 0.022
        trust_delta += 0.016

    if signals_normalized.get(
        "emotional_disclosure"
    ):
        trust_delta += 0.026
        affection_delta += 0.016

    if signals_normalized.get(
        "trust_signal"
    ):
        trust_delta += (
            0.030
            + trust_strength * 0.025
        )

        affection_delta += (
            0.006
            + trust_strength * 0.008
        )

    if signals_normalized.get(
        "affection_signal"
    ):
        affection_delta += (
            0.026
            + affection_strength * 0.026
        )

        trust_delta += (
            0.005
            + affection_strength * 0.008
        )

        romantic_delta += (
            affection_strength * 0.006
        )

    if signals_normalized.get(
        "romantic_signal"
    ):
        romantic_delta += (
            0.032
            + romantic_strength * 0.030
        )

        affection_delta += (
            0.016
            + romantic_strength * 0.016
        )

        trust_delta += (
            0.005
            + romantic_strength * 0.006
        )

    if signals_normalized.get(
        "sexual_signal"
    ):
        romantic_delta += (
            0.026
            + sexual_strength * 0.024
        )

        affection_delta += (
            0.006
            + sexual_strength * 0.008
        )

        familiarity_delta += 0.008

    if signals_normalized.get(
        "explicit_sexual_signal"
    ):
        romantic_delta += (
            0.020
            + sexual_strength * 0.022
        )

        familiarity_delta += 0.006

    if signals_normalized.get(
        "respect_signal"
    ):
        trust_delta += 0.022
        affection_delta += 0.006

    if signals_normalized.get(
        "image_shared"
    ):
        familiarity_delta += 0.012
        trust_delta += 0.004

    # A iniciativa de Mary também faz parte da tensão construída.
    # Isso usa a decisão interna do sistema, não o texto gerado por Mary.
    mary_internal_state = state.get(
        "mary_internal_state"
    )

    if not isinstance(
        mary_internal_state,
        dict,
    ):
        mary_internal_state = {}

    mary_desire = limitar_valor(
        mary_internal_state.get(
            "current_desire",
            0.0,
        )
    )

    current_direction = state.get(
        "current_turn_direction"
    )

    if not isinstance(
        current_direction,
        dict,
    ) or not current_direction:
        current_direction = state.get(
            "last_turn_direction"
        )

    if not isinstance(
        current_direction,
        dict,
    ):
        current_direction = {}

    experience_mode = str(
        current_direction.get(
            "experience_mode",
            "",
        )
        or ""
    ).strip().lower()

    mary_romantic_modes = {
        "gentle_provocation",
        "bold_provocation",
        "romantic_escalation",
        "sexual_tension",
        "sexual_initiative",
        "continue_shared_fantasy",
    }

    if experience_mode in mary_romantic_modes:
        romantic_delta += min(
            0.010,
            mary_desire * 0.012,
        )

    # Limites não significam automaticamente perda de afeto.
    # Eles interrompem principalmente a tensão daquele momento.
    if signals_normalized.get(
        "boundary_signal"
    ):
        romantic_delta -= (
            0.025
            + negative_strength * 0.020
        )

    if signals_normalized.get(
        "rejection_signal"
    ):
        trust_delta -= (
            0.050
            + negative_strength * 0.035
        )

        affection_delta -= (
            0.055
            + negative_strength * 0.035
        )

        romantic_delta -= (
            0.080
            + negative_strength * 0.050
        )

    if signals_normalized.get(
        "hostility_signal"
    ):
        trust_delta -= (
            0.085
            + negative_strength * 0.050
        )

        affection_delta -= (
            0.070
            + negative_strength * 0.045
        )

        romantic_delta -= (
            0.095
            + negative_strength * 0.055
        )

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

def obter_estado_interno_mary(
    state: dict[str, Any],
) -> dict[str, Any]:
    internal_state = state.get(
        "mary_internal_state"
    )

    if isinstance(
        internal_state,
        dict,
    ):
        return internal_state

    return {}


def obter_desejo_mary(
    state: dict[str, Any],
) -> float:
    internal_state = obter_estado_interno_mary(
        state
    )

    return limitar_valor(
        internal_state.get(
            "current_desire",
            0.0,
        )
    )


def obter_iniciativa_mary(
    state: dict[str, Any],
) -> float:
    internal_state = obter_estado_interno_mary(
        state
    )

    return limitar_valor(
        internal_state.get(
            "initiative_drive",
            0.0,
        )
    )


def calcular_tensao_sexual_efetiva(
    state: dict[str, Any],
) -> float:
    """
    Combina a tensão construída pelo usuário com o desejo autônomo de Mary.

    A tensão da relação não depende exclusivamente de uma fala sexual do
    usuário, mas o desejo de Mary também não substitui completamente vínculo,
    confiança e familiaridade.
    """

    romantic_tension = limitar_valor(
        state.get(
            "romantic_tension_level",
            0.0,
        )
    )

    mary_desire = obter_desejo_mary(
        state
    )

    mary_initiative = obter_iniciativa_mary(
        state
    )

    mary_component = limitar_valor(
        mary_desire * 0.72
        + mary_initiative * 0.18
    )

    return max(
        romantic_tension,
        mary_component,
    )


def existe_bloqueio_sexual_no_turno(
    signals: dict[str, Any] | None,
) -> bool:
    signals_normalized = normalizar_sinais(
        signals
    )

    return bool(
        signals_normalized.get(
            "boundary_signal"
        )
        or signals_normalized.get(
            "rejection_signal"
        )
        or signals_normalized.get(
            "hostility_signal"
        )
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

    effective_romantic_tension = (
        calcular_tensao_sexual_efetiva(
            state
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

    if existe_bloqueio_sexual_no_turno(
        signals
    ):
        return False

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
        and effective_romantic_tension
        >= requirements[
            "min_romantic_tension"
        ]
        and emotional_stage_index
        >= required_stage_index
    )

    if not basic_requirements:
        return False

    mary_desire = obter_desejo_mary(
        state
    )

    mary_initiative = obter_iniciativa_mary(
        state
    )

    # Atração pode surgir principalmente de Mary.
    if level == SEXUAL_LEVEL_ATTRACTION:
        return bool(
            effective_romantic_tension >= 0.08
        )

    # Flerte exige alguma disposição ativa de pelo menos um dos lados.
    if level == SEXUAL_LEVEL_FLIRT:
        return bool(
            effective_romantic_tension >= 0.20
            and (
                mary_desire >= 0.20
                or limitar_valor(
                    state.get(
                        "romantic_tension_level",
                        0.0,
                    )
                ) >= 0.16
            )
        )

    # Desejo pode ser iniciado por Mary.
    if level == SEXUAL_LEVEL_DESIRE:
        return bool(
            effective_romantic_tension >= 0.36
            and mary_desire >= 0.34
        )

    # Intimidade exige desejo e segurança.
    if level == SEXUAL_LEVEL_INTIMACY:
        return bool(
            effective_romantic_tension >= 0.54
            and mary_desire >= 0.48
            and mary_initiative >= 0.34
            and trust >= 0.28
        )

    # Intimidade profunda continua exigente.
    if level == SEXUAL_LEVEL_DEEP_INTIMACY:
        return bool(
            effective_romantic_tension >= 0.74
            and mary_desire >= 0.68
            and mary_initiative >= 0.54
            and trust >= 0.58
            and affection >= 0.52
        )

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
        signals_normalized,
        relationship_state=state,
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
