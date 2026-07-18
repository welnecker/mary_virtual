from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


RELATIONSHIP_STATE_VERSION = "relationship-state-v1"


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
    "sexual_state": {
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
    },
    "created_at": "",
    "updated_at": "",
}


def utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def criar_estado_relacao_padrao() -> dict[str, Any]:
    state = deepcopy(
        DEFAULT_RELATIONSHIP_STATE
    )

    agora = utc_now_iso()

    state["created_at"] = agora
    state["updated_at"] = agora

    return state


def normalizar_estado_relacao(
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = criar_estado_relacao_padrao()

    if not isinstance(
        state,
        dict,
    ):
        return normalized

    for key in (
        "state_version",
        "emotional_stage",
        "previous_emotional_stage",
        "sexual_level",
        "previous_sexual_level",
        "trust_level",
        "affection_level",
        "familiarity_level",
        "romantic_tension_level",
        "interaction_count",
        "relationship_summary",
        "created_at",
        "updated_at",
    ):
        if key in state:
            normalized[key] = state[key]

    sexual_state = state.get(
        "sexual_state"
    )

    if isinstance(
        sexual_state,
        dict,
    ):
        normalized[
            "sexual_state"
        ].update(
            sexual_state
        )

    if not normalized.get(
        "created_at"
    ):
        normalized[
            "created_at"
        ] = utc_now_iso()

    normalized[
        "updated_at"
    ] = utc_now_iso()

    return normalized
