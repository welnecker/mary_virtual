from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable


STORY_STATE_VERSION = "casada-frustrada-story-state-v1"

DEFAULT_STORY_STATE: dict[str, Any] = {
    "version": STORY_STATE_VERSION,
    "current_scene": "supermarket_encounter",
    "dramatic_zone": "primeiro contato acidental",
    "confirmed_facts": [],
    "active_tensions": [],
    "completed_functions": [],
    "blocked_movements": [],
    "progress": {
        "meaningful_turns": 0,
        "repetition_score": 0.0,
        "transition_readiness": 0.0,
        "pressure": 0.0,
    },
    "last_observation": {},
}


def _unique_texts(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def criar_estado_narrativo_padrao() -> dict[str, Any]:
    return deepcopy(DEFAULT_STORY_STATE)


def normalizar_estado_narrativo(value: Any) -> dict[str, Any]:
    state = criar_estado_narrativo_padrao()
    if isinstance(value, dict):
        for key, incoming in value.items():
            if key == "progress" and isinstance(incoming, dict):
                state["progress"].update(deepcopy(incoming))
            else:
                state[key] = deepcopy(incoming)

    state["version"] = STORY_STATE_VERSION
    state["current_scene"] = str(state.get("current_scene") or "supermarket_encounter").strip()
    state["dramatic_zone"] = str(state.get("dramatic_zone") or "").strip()
    for key in (
        "confirmed_facts",
        "active_tensions",
        "completed_functions",
        "blocked_movements",
    ):
        values = state.get(key)
        state[key] = _unique_texts(values if isinstance(values, list) else [])

    progress = state.get("progress")
    if not isinstance(progress, dict):
        progress = {}
    state["progress"] = {
        "meaningful_turns": max(0, int(progress.get("meaningful_turns", 0) or 0)),
        "repetition_score": min(1.0, max(0.0, float(progress.get("repetition_score", 0.0) or 0.0))),
        "transition_readiness": min(1.0, max(0.0, float(progress.get("transition_readiness", 0.0) or 0.0))),
        "pressure": min(1.0, max(0.0, float(progress.get("pressure", 0.0) or 0.0))),
    }
    if not isinstance(state.get("last_observation"), dict):
        state["last_observation"] = {}
    return state


def adicionar_fatos(state: dict[str, Any], *facts: str) -> dict[str, Any]:
    state["confirmed_facts"] = _unique_texts([
        *state.get("confirmed_facts", []),
        *facts,
    ])
    return state


def concluir_funcoes(state: dict[str, Any], *functions: str) -> dict[str, Any]:
    state["completed_functions"] = _unique_texts([
        *state.get("completed_functions", []),
        *functions,
    ])
    return state


def bloquear_movimentos(state: dict[str, Any], *movements: str) -> dict[str, Any]:
    state["blocked_movements"] = _unique_texts([
        *state.get("blocked_movements", []),
        *movements,
    ])
    return state


__all__ = [
    "STORY_STATE_VERSION",
    "DEFAULT_STORY_STATE",
    "criar_estado_narrativo_padrao",
    "normalizar_estado_narrativo",
    "adicionar_fatos",
    "concluir_funcoes",
    "bloquear_movimentos",
]
