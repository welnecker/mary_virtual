from __future__ import annotations

from typing import Any

from .beat_graph import INITIAL_BEAT, obter_beat


STORY_SYNC_VERSION = "casada-frustrada-story-sync-v3-recovery-only"


def _text(value: Any) -> str:
    return str(value or "").strip()


def reconciliar_posicao_narrativa(
    *,
    messages: list[dict[str, Any]],
    legacy_route: str,
    legacy_beat: str,
) -> dict[str, Any]:
    """Recover missing or invalid state without commanding a healthy session.

    A valid beat from beat_graph.py is authoritative. Conversation text, old
    markers and semantic guesses may not replace it. The dialogue is interpreted
    inside the current beat by the director and by Mary; it does not choose the
    route.
    """
    del messages  # intentionally ignored for progression

    requested_beat = _text(legacy_beat)
    beat = obter_beat(requested_beat)
    recovered = not bool(beat)

    if not beat:
        requested_beat = INITIAL_BEAT
        beat = obter_beat(requested_beat) or {}

    route = _text(beat.get("route")) or _text(legacy_route)
    return {
        "version": STORY_SYNC_VERSION,
        "route": route,
        "beat": requested_beat,
        "reason": "invalid_state_recovered" if recovered else "beat_graph_position_preserved",
        "legacy_route": _text(legacy_route),
        "legacy_beat": _text(legacy_beat),
        "legacy_cursor_overridden": recovered,
    }


__all__ = ["STORY_SYNC_VERSION", "reconciliar_posicao_narrativa"]
