from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

from scenarios.stories.casada_frustrada.beat_graph import (
    INITIAL_BEAT,
    obter_beat,
    proximo_beat_padrao,
)


BEAT_ENGINE_VERSION = "casada-frustrada-beat-engine-v1"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _truth(value: Any) -> bool:
    return value is True or _text(value).lower() in {"true", "1", "sim", "yes"}


def _message_hash(text: str) -> str:
    return hashlib.sha256(_text(text).encode("utf-8")).hexdigest()[:20]


def _facts(scene_state: dict[str, Any], sexual_state: dict[str, Any]) -> set[str]:
    facts: set[str] = set()
    completed = scene_state.get("completed_story_facts")
    if isinstance(completed, list):
        facts.update(_text(item) for item in completed if _text(item))

    for key in (
        "phone_numbers_exchanged",
        "privacy_established",
        "video_call_established",
        "camera_positioned",
        "secret_meeting_arranged",
        "user_arrived_secret_meeting",
    ):
        if _truth(scene_state.get(key)):
            facts.add(key)

    if _truth(sexual_state.get("mary_orgasm_allowed")):
        facts.add("mary_orgasm_allowed")
    if _truth(sexual_state.get("mary_orgasm_done")):
        facts.add("mary_orgasm_done")
    if _truth(sexual_state.get("user_orgasm_done")):
        facts.add("user_orgasm_confirmed")
    return facts


def inicializar_estado_beats(scene_state: dict[str, Any] | None) -> dict[str, Any]:
    state = deepcopy(scene_state) if isinstance(scene_state, dict) else {}
    beat_state = state.get("beat_state")
    if not isinstance(beat_state, dict):
        beat_state = {}

    current = _text(beat_state.get("current") or state.get("current_beat"))
    if not obter_beat(current):
        current = INITIAL_BEAT

    beat_state.setdefault("current", current)
    beat_state.setdefault("completed", [])
    beat_state.setdefault("last_response_hash", "")
    beat_state.setdefault("version", BEAT_ENGINE_VERSION)
    state["beat_state"] = beat_state

    beat = obter_beat(current)
    if beat:
        state["current_beat"] = current
        state["current_route"] = beat.get("route") or state.get("current_route")
    return state


def beat_disponivel(
    beat_id: str,
    *,
    scene_state: dict[str, Any],
    sexual_state: dict[str, Any],
) -> bool:
    beat = obter_beat(beat_id)
    if not beat:
        return False
    facts = _facts(scene_state, sexual_state)
    return all(_text(item) in facts for item in beat.get("requires", []))


def sincronizar_beat_apos_resposta(
    *,
    scene_state: dict[str, Any] | None,
    sexual_state: dict[str, Any] | None,
    last_mary_response: str,
) -> dict[str, Any]:
    state = inicializar_estado_beats(scene_state)
    sexual = deepcopy(sexual_state) if isinstance(sexual_state, dict) else {}
    beat_state = deepcopy(state.get("beat_state") or {})
    current = _text(beat_state.get("current"))
    beat = obter_beat(current)
    response = _text(last_mary_response)
    response_hash = _message_hash(response) if response else ""

    if not beat or not response_hash or response_hash == _text(beat_state.get("last_response_hash")):
        return state

    completed = beat_state.get("completed")
    completed = list(completed) if isinstance(completed, list) else []
    if current not in completed:
        completed.append(current)

    story_facts = state.get("completed_story_facts")
    story_facts = list(story_facts) if isinstance(story_facts, list) else []
    for fact in beat.get("completes", []):
        fact = _text(fact)
        if fact and fact not in story_facts:
            story_facts.append(fact)
        if fact in {
            "phone_numbers_exchanged",
            "privacy_established",
            "video_call_established",
            "camera_positioned",
            "secret_meeting_arranged",
            "user_arrived_secret_meeting",
        }:
            state[fact] = True

    next_beat = proximo_beat_padrao(current)
    if next_beat and beat_disponivel(next_beat, scene_state={**state, "completed_story_facts": story_facts}, sexual_state=sexual):
        beat_state["current"] = next_beat
    elif next_beat:
        beat_state["pending"] = next_beat

    pending = _text(beat_state.get("pending"))
    if pending and beat_disponivel(pending, scene_state={**state, "completed_story_facts": story_facts}, sexual_state=sexual):
        beat_state["current"] = pending
        beat_state.pop("pending", None)

    beat_state["completed"] = completed[-40:]
    beat_state["last_response_hash"] = response_hash
    state["completed_story_facts"] = story_facts[-60:]
    state["beat_state"] = beat_state

    active = obter_beat(_text(beat_state.get("current")))
    if active:
        state["current_beat"] = active["id"]
        state["current_route"] = active["route"]
        state["current_phase"] = (
            "intimacy"
            if active.get("sexual_phase") == "active"
            else "climax"
            if active.get("sexual_phase") == "climax"
            else "aftercare"
            if active.get("sexual_phase") == "aftercare"
            else state.get("current_phase", "familiarity")
        )
    return state


def obter_beat_atual(scene_state: dict[str, Any] | None) -> dict[str, Any]:
    state = inicializar_estado_beats(scene_state)
    beat_state = state.get("beat_state") or {}
    return obter_beat(_text(beat_state.get("current")))


__all__ = [
    "BEAT_ENGINE_VERSION",
    "beat_disponivel",
    "inicializar_estado_beats",
    "obter_beat_atual",
    "sincronizar_beat_apos_resposta",
]
