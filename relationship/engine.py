from __future__ import annotations

from typing import Any

from relationship.signals import DEFAULT_RELATIONSHIP_SIGNALS
from relationship.state import normalizar_estado_relacao, utc_now_iso


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

SEXUAL_LEVEL_NONE = 0
SEXUAL_LEVEL_ATTRACTION = 1
SEXUAL_LEVEL_FLIRT = 2
SEXUAL_LEVEL_DESIRE = 3
SEXUAL_LEVEL_INTIMACY = 4
SEXUAL_LEVEL_DEEP_INTIMACY = 5
SEXUAL_LEVEL_MIN = SEXUAL_LEVEL_NONE
SEXUAL_LEVEL_MAX = SEXUAL_LEVEL_DEEP_INTIMACY


# Estes valores orientam diagnóstico e compatibilidade. Não são mais uma
# escada rígida baseada apenas em contagem de interações.
EMOTIONAL_STAGE_REQUIREMENTS: dict[str, dict[str, Any]] = {
    EMOTIONAL_STAGE_FIRST_CONTACT: {
        "min_interactions": 0,
        "min_familiarity": 0.0,
        "min_trust": 0.0,
        "min_affection": 0.0,
    },
    EMOTIONAL_STAGE_ACQUAINTANCE: {
        "min_interactions": 1,
        "min_familiarity": 0.08,
        "min_trust": 0.02,
        "min_affection": 0.0,
    },
    EMOTIONAL_STAGE_CONNECTION: {
        "min_interactions": 3,
        "min_familiarity": 0.20,
        "min_trust": 0.12,
        "min_affection": 0.08,
    },
    EMOTIONAL_STAGE_INTIMACY: {
        "min_interactions": 7,
        "min_familiarity": 0.38,
        "min_trust": 0.28,
        "min_affection": 0.22,
    },
    EMOTIONAL_STAGE_DEEP_BOND: {
        "min_interactions": 16,
        "min_familiarity": 0.62,
        "min_trust": 0.52,
        "min_affection": 0.48,
    },
}

SEXUAL_LEVEL_REQUIREMENTS: dict[int, dict[str, Any]] = {
    SEXUAL_LEVEL_NONE: {
        "min_interactions": 0,
        "min_familiarity": 0.0,
        "min_trust": 0.0,
        "min_affection": 0.0,
        "min_romantic_tension": 0.0,
        "min_emotional_stage": EMOTIONAL_STAGE_FIRST_CONTACT,
    },
    SEXUAL_LEVEL_ATTRACTION: {
        "min_interactions": 0,
        "min_familiarity": 0.0,
        "min_trust": 0.0,
        "min_affection": 0.0,
        "min_romantic_tension": 0.08,
        "min_emotional_stage": EMOTIONAL_STAGE_FIRST_CONTACT,
    },
    SEXUAL_LEVEL_FLIRT: {
        "min_interactions": 1,
        "min_familiarity": 0.05,
        "min_trust": 0.0,
        "min_affection": 0.0,
        "min_romantic_tension": 0.16,
        "min_emotional_stage": EMOTIONAL_STAGE_FIRST_CONTACT,
    },
    SEXUAL_LEVEL_DESIRE: {
        "min_interactions": 2,
        "min_familiarity": 0.10,
        "min_trust": 0.04,
        "min_affection": 0.02,
        "min_romantic_tension": 0.28,
        "min_emotional_stage": EMOTIONAL_STAGE_ACQUAINTANCE,
    },
    SEXUAL_LEVEL_INTIMACY: {
        "min_interactions": 3,
        "min_familiarity": 0.16,
        "min_trust": 0.10,
        "min_affection": 0.06,
        "min_romantic_tension": 0.42,
        "min_emotional_stage": EMOTIONAL_STAGE_ACQUAINTANCE,
    },
    SEXUAL_LEVEL_DEEP_INTIMACY: {
        "min_interactions": 8,
        "min_familiarity": 0.34,
        "min_trust": 0.26,
        "min_affection": 0.20,
        "min_romantic_tension": 0.62,
        "min_emotional_stage": EMOTIONAL_STAGE_CONNECTION,
    },
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


def normalizar_estagio_emocional(stage: Any) -> str:
    normalized = str(stage or "").strip().lower()
    return (
        normalized
        if normalized in EMOTIONAL_STAGE_ORDER
        else EMOTIONAL_STAGE_FIRST_CONTACT
    )


def obter_indice_estagio_emocional(stage: Any) -> int:
    return EMOTIONAL_STAGE_ORDER.index(normalizar_estagio_emocional(stage))


def limitar_nivel_sexual(level: Any) -> int:
    return max(SEXUAL_LEVEL_MIN, min(SEXUAL_LEVEL_MAX, safe_int(level)))


def normalizar_sinais(signals: dict[str, Any] | None) -> dict[str, Any]:
    normalized = dict(DEFAULT_RELATIONSHIP_SIGNALS)
    if isinstance(signals, dict):
        normalized.update(signals)
    return normalized


def _forca(signals: dict[str, Any], name: str) -> float:
    return limitar_valor(signals.get(name, 0.0))


def calcular_incrementos_relacao(
    signals: dict[str, Any] | None,
    relationship_state: dict[str, Any] | None = None,
) -> dict[str, float]:
    s = normalizar_sinais(signals)
    state = relationship_state if isinstance(relationship_state, dict) else {}

    familiarity = 0.020 if s.get("interaction_exists") else 0.0
    trust = 0.0
    affection = 0.0
    romantic = 0.0

    affection_strength = _forca(s, "affection_strength")
    romantic_strength = _forca(s, "romantic_strength")
    sexual_strength = _forca(s, "sexual_strength")
    trust_strength = _forca(s, "trust_strength")
    negative_strength = _forca(s, "negative_strength")

    if s.get("repeated_interaction"):
        familiarity += 0.006
    if s.get("user_returned"):
        familiarity += 0.018
        affection += 0.006
    if s.get("continuity_signal"):
        familiarity += 0.024
        trust += 0.012
    if s.get("personal_disclosure"):
        familiarity += 0.032
        trust += 0.022
    if s.get("emotional_disclosure"):
        trust += 0.036
        affection += 0.024
    if s.get("trust_signal"):
        trust += 0.034 + trust_strength * 0.038
        affection += trust_strength * 0.010
    if s.get("affection_signal"):
        affection += 0.034 + affection_strength * 0.038
        trust += 0.008 + affection_strength * 0.010
        romantic += affection_strength * 0.010
    if s.get("romantic_signal"):
        romantic += 0.050 + romantic_strength * 0.050
        affection += 0.020 + romantic_strength * 0.020
        trust += romantic_strength * 0.008
    if s.get("sexual_signal"):
        romantic += 0.060 + sexual_strength * 0.070
        familiarity += 0.012
    if s.get("explicit_sexual_signal"):
        romantic += 0.070 + sexual_strength * 0.080
        familiarity += 0.010
    if s.get("respect_signal"):
        trust += 0.026
        affection += 0.008
    if s.get("image_shared"):
        familiarity += 0.016
        trust += 0.006

    internal = state.get("mary_internal_state")
    if not isinstance(internal, dict):
        internal = {}
    mary_desire = limitar_valor(internal.get("current_desire", 0.0))
    initiative = limitar_valor(internal.get("initiative_drive", 0.0))
    if mary_desire >= 0.45:
        romantic += min(0.035, mary_desire * 0.035)
    if initiative >= 0.55 and s.get("interaction_exists"):
        familiarity += 0.006

    # Limite é direção do momento, não rejeição da pessoa.
    if s.get("boundary_signal"):
        romantic -= 0.025 + negative_strength * 0.015
    if s.get("rejection_signal"):
        romantic -= 0.050 + negative_strength * 0.030
        affection -= 0.012 + negative_strength * 0.010
    if s.get("hostility_signal"):
        trust -= 0.080 + negative_strength * 0.050
        affection -= 0.060 + negative_strength * 0.040
        romantic -= 0.080 + negative_strength * 0.050

    return {
        "familiarity_delta": familiarity,
        "trust_delta": trust,
        "affection_delta": affection,
        "romantic_tension_delta": romantic,
    }


def aplicar_incrementos_relacao(
    state: dict[str, Any],
    increments: dict[str, float],
) -> None:
    mapping = {
        "familiarity_level": "familiarity_delta",
        "trust_level": "trust_delta",
        "affection_level": "affection_delta",
        "romantic_tension_level": "romantic_tension_delta",
    }
    for field, delta in mapping.items():
        state[field] = limitar_valor(
            safe_float(state.get(field, 0.0))
            + safe_float(increments.get(delta, 0.0))
        )


def requisitos_estagio_emocional_atendidos(
    state: dict[str, Any],
    target_stage: str,
) -> bool:
    target = normalizar_estagio_emocional(target_stage)
    req = EMOTIONAL_STAGE_REQUIREMENTS[target]
    count = safe_int(state.get("interaction_count", 0))
    familiarity = limitar_valor(state.get("familiarity_level", 0.0))
    trust = limitar_valor(state.get("trust_level", 0.0))
    affection = limitar_valor(state.get("affection_level", 0.0))

    metrics_ready = (
        familiarity >= req["min_familiarity"]
        and trust >= req["min_trust"]
        and affection >= req["min_affection"]
    )
    # Sinais fortes podem antecipar vínculo; contagem é referência, não veto.
    close_enough = count >= max(0, req["min_interactions"] - 2)
    return metrics_ready and close_enough


def calcular_estagio_emocional_maximo(state: dict[str, Any]) -> str:
    maximum = EMOTIONAL_STAGE_FIRST_CONTACT
    for stage in EMOTIONAL_STAGE_ORDER:
        if requisitos_estagio_emocional_atendidos(state, stage):
            maximum = stage
    return maximum


def atualizar_estagio_emocional(state: dict[str, Any]) -> None:
    current = normalizar_estagio_emocional(state.get("emotional_stage"))
    target = calcular_estagio_emocional_maximo(state)
    current_index = obter_indice_estagio_emocional(current)
    target_index = obter_indice_estagio_emocional(target)

    if target_index > current_index:
        state["previous_emotional_stage"] = current
        # Permite até dois estágios quando o contexto realmente convergiu.
        new_index = min(target_index, current_index + 2)
        state["emotional_stage"] = EMOTIONAL_STAGE_ORDER[new_index]
        state["last_emotional_transition_reason"] = "relationship_context_converged"
        return

    trust = limitar_valor(state.get("trust_level", 0.0))
    affection = limitar_valor(state.get("affection_level", 0.0))
    if target_index < current_index and trust < 0.08 and affection < 0.06:
        state["previous_emotional_stage"] = current
        state["emotional_stage"] = EMOTIONAL_STAGE_ORDER[max(0, current_index - 1)]
        state["last_emotional_transition_reason"] = "significant_relationship_damage"


def obter_estado_interno_mary(state: dict[str, Any]) -> dict[str, Any]:
    value = state.get("mary_internal_state")
    return value if isinstance(value, dict) else {}


def obter_desejo_mary(state: dict[str, Any]) -> float:
    return limitar_valor(obter_estado_interno_mary(state).get("current_desire", 0.0))


def obter_iniciativa_mary(state: dict[str, Any]) -> float:
    return limitar_valor(obter_estado_interno_mary(state).get("initiative_drive", 0.0))


def calcular_tensao_sexual_efetiva(state: dict[str, Any]) -> float:
    romantic = limitar_valor(state.get("romantic_tension_level", 0.0))
    mary_component = limitar_valor(
        obter_desejo_mary(state) * 0.78
        + obter_iniciativa_mary(state) * 0.22
    )
    return max(romantic, mary_component)


def existe_bloqueio_sexual_no_turno(
    signals: dict[str, Any] | None,
) -> bool:
    s = normalizar_sinais(signals)
    return bool(
        s.get("boundary_signal")
        or s.get("rejection_signal")
        or s.get("hostility_signal")
    )


def requisitos_nivel_sexual_atendidos(
    state: dict[str, Any],
    target_level: int,
    signals: dict[str, Any] | None = None,
) -> bool:
    level = limitar_nivel_sexual(target_level)
    if level == SEXUAL_LEVEL_NONE:
        return True
    if existe_bloqueio_sexual_no_turno(signals):
        return False

    req = SEXUAL_LEVEL_REQUIREMENTS[level]
    count = safe_int(state.get("interaction_count", 0))
    familiarity = limitar_valor(state.get("familiarity_level", 0.0))
    trust = limitar_valor(state.get("trust_level", 0.0))
    affection = limitar_valor(state.get("affection_level", 0.0))
    tension = calcular_tensao_sexual_efetiva(state)
    desire = obter_desejo_mary(state)
    initiative = obter_iniciativa_mary(state)
    stage_index = obter_indice_estagio_emocional(state.get("emotional_stage"))
    required_stage = obter_indice_estagio_emocional(req["min_emotional_stage"])

    metrics_ready = (
        familiarity >= req["min_familiarity"]
        and trust >= req["min_trust"]
        and affection >= req["min_affection"]
        and tension >= req["min_romantic_tension"]
        and stage_index >= required_stage
    )
    count_ready = count >= max(0, req["min_interactions"] - 2)

    # Desejo explícito e reciprocidade podem substituir parte da espera.
    s = normalizar_sinais(signals)
    strong_reciprocity = bool(
        s.get("explicit_sexual_signal")
        or _forca(s, "sexual_strength") >= 0.70
    )

    if level <= SEXUAL_LEVEL_FLIRT:
        return metrics_ready or tension >= req["min_romantic_tension"]
    if level == SEXUAL_LEVEL_DESIRE:
        return (metrics_ready and count_ready) or (strong_reciprocity and desire >= 0.34)
    if level == SEXUAL_LEVEL_INTIMACY:
        return (
            metrics_ready
            and (count_ready or strong_reciprocity)
            and desire >= 0.42
            and initiative >= 0.30
        )
    return (
        metrics_ready
        and count_ready
        and desire >= 0.60
        and initiative >= 0.48
    )


def calcular_nivel_sexual_maximo(
    state: dict[str, Any],
    signals: dict[str, Any] | None = None,
) -> int:
    maximum = SEXUAL_LEVEL_NONE
    for level in range(SEXUAL_LEVEL_MIN, SEXUAL_LEVEL_MAX + 1):
        if requisitos_nivel_sexual_atendidos(state, level, signals):
            maximum = level
    return maximum


def atualizar_nivel_sexual(
    state: dict[str, Any],
    signals: dict[str, Any] | None = None,
) -> None:
    s = normalizar_sinais(signals)
    current = limitar_nivel_sexual(state.get("sexual_level", 0))

    if s.get("boundary_signal"):
        state["last_sexual_transition_reason"] = "boundary_signal_detected"
        return

    if s.get("hostility_signal"):
        state["previous_sexual_level"] = current
        state["sexual_level"] = max(SEXUAL_LEVEL_NONE, current - 1)
        state["last_sexual_transition_reason"] = "sexual_trust_damaged"
        return

    if s.get("rejection_signal"):
        # Recusa encerra o rumo atual, não apaga toda atração acumulada.
        state["last_sexual_transition_reason"] = "sexual_direction_refused"
        return

    target = calcular_nivel_sexual_maximo(state, s)
    if target > current:
        state["previous_sexual_level"] = current
        strong = bool(
            s.get("explicit_sexual_signal")
            or _forca(s, "sexual_strength") >= 0.75
        )
        max_step = 2 if strong else 1
        state["sexual_level"] = min(target, current + max_step)
        state["last_sexual_transition_reason"] = "sexual_context_converged"
        return

    state["sexual_level"] = current


def montar_resumo_relacao(state: dict[str, Any]) -> str:
    return (
        f"Interações: {safe_int(state.get('interaction_count', 0))}. "
        f"Estágio emocional: {normalizar_estagio_emocional(state.get('emotional_stage'))}. "
        f"Nível sexual: {limitar_nivel_sexual(state.get('sexual_level', 0))}. "
        f"Familiaridade: {limitar_valor(state.get('familiarity_level', 0.0)):.2f}. "
        f"Confiança: {limitar_valor(state.get('trust_level', 0.0)):.2f}. "
        f"Afeto: {limitar_valor(state.get('affection_level', 0.0)):.2f}. "
        f"Tensão romântica: {limitar_valor(state.get('romantic_tension_level', 0.0)):.2f}."
    )


def atualizar_estado_relacao(
    relationship_state: dict[str, Any] | None,
    *,
    signals: dict[str, Any] | None,
    incrementar_interacao: bool = True,
) -> dict[str, Any]:
    state = normalizar_estado_relacao(relationship_state)
    s = normalizar_sinais(signals)

    if incrementar_interacao and s.get("interaction_exists"):
        state["interaction_count"] = max(
            0,
            safe_int(state.get("interaction_count", 0)),
        ) + 1

    increments = calcular_incrementos_relacao(s, relationship_state=state)
    aplicar_incrementos_relacao(state, increments)
    atualizar_estagio_emocional(state)
    atualizar_nivel_sexual(state, s)

    state["last_relationship_signals"] = s
    state["last_relationship_increments"] = increments
    state["relationship_summary"] = montar_resumo_relacao(state)
    state["updated_at"] = utc_now_iso()
    return state


def simular_atualizacao_relacao(
    relationship_state: dict[str, Any] | None,
    *,
    signals: dict[str, Any] | None,
) -> dict[str, Any]:
    current = normalizar_estado_relacao(relationship_state)
    updated = atualizar_estado_relacao(
        current,
        signals=signals,
        incrementar_interacao=True,
    )
    fields = (
        "interaction_count",
        "emotional_stage",
        "sexual_level",
        "familiarity_level",
        "trust_level",
        "affection_level",
        "romantic_tension_level",
    )
    return {
        "before": {field: current.get(field) for field in fields},
        "after": {field: updated.get(field) for field in fields},
        "signals": normalizar_sinais(signals),
        "increments": updated.get("last_relationship_increments", {}),
    }


__all__ = [
    "EMOTIONAL_STAGE_REQUIREMENTS",
    "SEXUAL_LEVEL_REQUIREMENTS",
    "aplicar_incrementos_relacao",
    "atualizar_estado_relacao",
    "atualizar_estagio_emocional",
    "atualizar_nivel_sexual",
    "calcular_estagio_emocional_maximo",
    "calcular_incrementos_relacao",
    "calcular_nivel_sexual_maximo",
    "montar_resumo_relacao",
    "requisitos_estagio_emocional_atendidos",
    "requisitos_nivel_sexual_atendidos",
    "simular_atualizacao_relacao",
]
