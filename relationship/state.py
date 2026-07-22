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
from relationship.sexual_engine import (
    DEFAULT_SEXUAL_STATE as SEXUAL_ENGINE_DEFAULT_STATE,
    normalizar_estado_sexual as normalizar_estado_sexual_engine,
)


RELATIONSHIP_STATE_VERSION = "relationship-state-v3-responsive-preserving"

EMOTIONAL_STAGES = {
    "first_contact",
    "acquaintance",
    "connection",
    "intimacy",
    "deep_bond",
}

DEFAULT_SEXUAL_STATE: dict[str, Any] = deepcopy(
    SEXUAL_ENGINE_DEFAULT_STATE
)

DEFAULT_RELATIONSHIP_STATE: dict[str, Any] = {
    "state_version": RELATIONSHIP_STATE_VERSION,
    "emotional_stage": "first_contact",
    "previous_emotional_stage": "",
    "sexual_level": 0,
    "previous_sexual_level": 0,
    "trust_level": 0.0,
    "affection_level": 0.0,
    "familiarity_level": 0.0,
    "romantic_tension_level": 0.0,
    "interaction_count": 0,
    "relationship_summary": "",
    "sexual_state": deepcopy(DEFAULT_SEXUAL_STATE),
    "mary_internal_state": deepcopy(DEFAULT_MARY_INTERNAL_STATE),
    "experience_state": deepcopy(DEFAULT_EXPERIENCE_STATE),
    "voice_state": deepcopy(DEFAULT_VOICE_STATE),
    "current_turn_intent": {},
    "current_turn_direction": {},
    "last_turn_intent": {},
    "last_turn_direction": {},
    "last_relationship_signals": {},
    "last_sexual_validation": {},
    "last_relationship_increments": {},
    "last_emotional_transition_reason": "",
    "last_sexual_transition_reason": "",
    "created_at": "",
    "updated_at": "",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def normalizar_dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


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


def normalizar_texto(value: Any, *, default: str = "") -> str:
    return default if value is None else str(value).strip()


def criar_estado_sexual_padrao() -> dict[str, Any]:
    return deepcopy(DEFAULT_SEXUAL_STATE)


def normalizar_estado_sexual(
    value: dict[str, Any] | None,
) -> dict[str, Any]:
    return normalizar_estado_sexual_engine(value)


def criar_estado_relacao_padrao() -> dict[str, Any]:
    state = deepcopy(DEFAULT_RELATIONSHIP_STATE)
    now = utc_now_iso()
    state["created_at"] = now
    state["updated_at"] = now
    return state


def normalizar_intencao_turno(
    value: dict[str, Any] | None,
    *,
    permitir_vazio: bool = True,
) -> dict[str, Any]:
    if permitir_vazio and not value:
        return {}
    result = deepcopy(DEFAULT_TURN_INTENT)
    if isinstance(value, dict):
        result.update(deepcopy(value))
    return result


def normalizar_direcao_turno(
    value: dict[str, Any] | None,
    *,
    permitir_vazio: bool = True,
) -> dict[str, Any]:
    if permitir_vazio and not value:
        return {}
    result = deepcopy(DEFAULT_TURN_DIRECTION)
    if isinstance(value, dict):
        result.update(deepcopy(value))
    result["voice_state"] = normalizar_estado_voz(
        result.get("voice_state")
    )
    return result


def _primeiro_valor(
    state: dict[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    for key in keys:
        if key in state and state[key] is not None:
            return state[key]
    return default


def _normalizar_estagio(value: Any) -> str:
    stage = normalizar_texto(value, default="first_contact").lower()
    return stage if stage in EMOTIONAL_STAGES else "first_contact"


def normalizar_estado_relacao(
    state: dict[str, Any] | None,
    *,
    tocar_updated_at: bool = False,
) -> dict[str, Any]:
    """Normaliza o núcleo sem descartar campos novos ou extensões.

    Estados antigos continuam aceitos por aliases. Campos desconhecidos são
    preservados para que novos motores possam evoluir sem serem apagados por
    uma versão anterior deste módulo.
    """

    if isinstance(state, dict):
        normalized = deepcopy(state)
    else:
        normalized = {}

    defaults = criar_estado_relacao_padrao()
    for key, value in defaults.items():
        normalized.setdefault(key, deepcopy(value))

    normalized["state_version"] = RELATIONSHIP_STATE_VERSION

    normalized["emotional_stage"] = _normalizar_estagio(
        _primeiro_valor(
            normalized,
            "emotional_stage",
            "stage",
            default="first_contact",
        )
    )

    previous_stage = normalizar_texto(
        _primeiro_valor(
            normalized,
            "previous_emotional_stage",
            "previous_stage",
            default="",
        )
    ).lower()
    normalized["previous_emotional_stage"] = (
        previous_stage if previous_stage in EMOTIONAL_STAGES else ""
    )

    normalized["sexual_level"] = max(
        0,
        min(
            5,
            safe_int(
                _primeiro_valor(
                    normalized,
                    "sexual_level",
                    "sexual_intimacy",
                    default=0,
                )
            ),
        ),
    )
    normalized["previous_sexual_level"] = max(
        0,
        min(5, safe_int(normalized.get("previous_sexual_level"), 0)),
    )

    aliases = {
        "trust_level": ("trust_level", "trust"),
        "affection_level": ("affection_level", "affection"),
        "familiarity_level": ("familiarity_level", "familiarity"),
        "romantic_tension_level": (
            "romantic_tension_level",
            "romantic_tension",
        ),
    }
    for canonical, names in aliases.items():
        normalized[canonical] = limitar_valor(
            _primeiro_valor(normalized, *names, default=0.0)
        )

    normalized["interaction_count"] = max(
        0,
        safe_int(normalized.get("interaction_count"), 0),
    )
    normalized["relationship_summary"] = normalizar_texto(
        normalized.get("relationship_summary")
    )

    normalized["sexual_state"] = normalizar_estado_sexual(
        normalized.get("sexual_state")
    )
    normalized["mary_internal_state"] = normalizar_estado_interno_mary(
        normalized.get("mary_internal_state")
    )
    normalized["experience_state"] = normalizar_estado_experiencia(
        normalized.get("experience_state")
    )
    normalized["voice_state"] = normalizar_estado_voz(
        normalized.get("voice_state")
    )

    normalized["current_turn_intent"] = normalizar_intencao_turno(
        normalized.get("current_turn_intent"),
        permitir_vazio=True,
    )
    normalized["current_turn_direction"] = normalizar_direcao_turno(
        normalized.get("current_turn_direction"),
        permitir_vazio=True,
    )
    normalized["last_turn_intent"] = normalizar_intencao_turno(
        normalized.get("last_turn_intent"),
        permitir_vazio=True,
    )
    normalized["last_turn_direction"] = normalizar_direcao_turno(
        normalized.get("last_turn_direction"),
        permitir_vazio=True,
    )

    for key in (
        "last_relationship_signals",
        "last_sexual_validation",
        "last_relationship_increments",
    ):
        normalized[key] = normalizar_dict(normalized.get(key))

    for key in (
        "last_emotional_transition_reason",
        "last_sexual_transition_reason",
    ):
        normalized[key] = normalizar_texto(normalized.get(key))

    created_at = normalizar_texto(normalized.get("created_at"))
    updated_at = normalizar_texto(normalized.get("updated_at"))
    normalized["created_at"] = created_at or defaults["created_at"]
    normalized["updated_at"] = updated_at or defaults["updated_at"]

    if tocar_updated_at:
        normalized["updated_at"] = utc_now_iso()

    return normalized


def marcar_estado_relacao_atualizado(
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = normalizar_estado_relacao(state)
    normalized["updated_at"] = utc_now_iso()
    return normalized


def limpar_planejamento_turno(
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = normalizar_estado_relacao(state)
    normalized["current_turn_intent"] = {}
    normalized["current_turn_direction"] = {}
    normalized["updated_at"] = utc_now_iso()
    return normalized


def preparar_estado_para_persistencia(
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    return normalizar_estado_relacao(state, tocar_updated_at=False)


def montar_resumo_estado_relacao(
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = normalizar_estado_relacao(state)
    internal = normalized["mary_internal_state"]
    experience = normalized["experience_state"]
    voice = normalized["voice_state"]
    sexual = normalized["sexual_state"]
    intent = normalized["current_turn_intent"]
    direction = normalized["current_turn_direction"]

    return {
        "state_version": normalized["state_version"],
        "emotional_stage": normalized["emotional_stage"],
        "sexual_level": normalized["sexual_level"],
        "interaction_count": normalized["interaction_count"],
        "trust_level": normalized["trust_level"],
        "affection_level": normalized["affection_level"],
        "familiarity_level": normalized["familiarity_level"],
        "romantic_tension_level": normalized["romantic_tension_level"],
        "sexual_phase": sexual.get("scene_phase", "idle"),
        "mary_pre_orgasm_announced": bool(
            sexual.get("mary_pre_orgasm_announced", False)
        ),
        "mary_mood": internal.get("current_mood", "neutral"),
        "mary_desire": internal.get("current_desire", 0.0),
        "mary_curiosity": internal.get("current_curiosity", 0.0),
        "mary_initiative_drive": internal.get("initiative_drive", 0.0),
        "experience_mode": experience.get(
            "current_mode", "natural_conversation"
        ),
        "surprise_budget": experience.get("surprise_budget", 0.0),
        "voice_register": (
            direction.get("voice_register")
            or experience.get("last_voice_register")
            or "natural"
        ),
        "sexual_explicitness": voice.get("sexual_explicitness", 0.0),
        "vulgarity": voice.get("vulgarity", 0.0),
        "current_turn_mode": intent.get("turn_mode", ""),
        "current_experience_mode": direction.get("experience_mode", ""),
        "open_thread_count": len(
            [
                thread
                for thread in experience.get("open_threads", [])
                if isinstance(thread, dict) and not thread.get("resolved", False)
            ]
        ),
        "created_at": normalized["created_at"],
        "updated_at": normalized["updated_at"],
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
