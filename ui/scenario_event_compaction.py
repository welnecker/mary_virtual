from __future__ import annotations

from copy import deepcopy
from functools import wraps
from typing import Any, Callable

import ui.scenario_event_persistence as scenario_events


SCENARIO_EVENT_COMPACTION_VERSION = (
    "scenario-event-compaction-v1-small-audit-payload"
)
_INSTALLED = False
_SCHEMA_READY = False


def _text(value: Any, limit: int = 600) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def _compact_analysis(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    fields = (
        "user_action",
        "user_style",
        "recommended_phase",
        "recommended_route",
        "recommended_beat",
        "recommended_focus",
        "action_choice",
        "mary_initiative_strength",
        "scene_closing_signal",
        "story_ending_signal",
        "transition_reason",
        "sexual_scene_phase",
        "climax_signal",
        "satisfaction_signal",
    )
    result: dict[str, Any] = {}
    for field in fields:
        item = value.get(field)
        if isinstance(item, str):
            item = _text(item)
        if item not in (None, "", [], {}):
            result[field] = deepcopy(item)
    return result


def _compact_scene(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    fields = (
        "current_phase",
        "current_route",
        "current_beat",
        "active_hook",
        "interaction_count",
        "story_progress_count",
        "location",
        "time_context",
        "seduction_level",
        "sexual_scene_phase",
        "ending_ready",
        "ending_sent",
        "ending_reason",
        "last_user_action",
        "recommended_focus",
        "last_action_choice",
    )
    result: dict[str, Any] = {}
    for field in fields:
        item = value.get(field)
        if isinstance(item, str):
            item = _text(item)
        if item not in (None, "", [], {}):
            result[field] = deepcopy(item)
    analysis = _compact_analysis(value.get("last_director_analysis"))
    if analysis:
        result["last_director_analysis"] = analysis
    return result


def _install_snapshot_compaction() -> None:
    original = scenario_events._snapshot
    if getattr(original, "_mary_compact_scenario_snapshot", False):
        return

    @wraps(original)
    def wrapper(instance: Any) -> dict[str, Any]:
        result = original(instance)
        if isinstance(result, dict):
            result["scene_state"] = _compact_scene(result.get("scene_state"))
        return result

    wrapper._mary_compact_scenario_snapshot = True  # type: ignore[attr-defined]
    scenario_events._snapshot = wrapper


def _install_schema_cache() -> None:
    original = scenario_events.garantir_schema_scenario_events
    if getattr(original, "_mary_scenario_event_schema_cached", False):
        return

    @wraps(original)
    def wrapper() -> list[str]:
        global _SCHEMA_READY
        if _SCHEMA_READY:
            return []
        result = original()
        _SCHEMA_READY = True
        return result

    wrapper._mary_scenario_event_schema_cached = True  # type: ignore[attr-defined]
    scenario_events.garantir_schema_scenario_events = wrapper


def install_scenario_event_compaction() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _install_snapshot_compaction()
    _install_schema_cache()
    _INSTALLED = True


__all__ = [
    "SCENARIO_EVENT_COMPACTION_VERSION",
    "install_scenario_event_compaction",
]
