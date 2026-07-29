from __future__ import annotations

from .models import ChapterDefinition, StorySession


def advance_session(
    session: StorySession,
    chapter: ChapterDefinition,
    *,
    gate_satisfied: bool = True,
) -> StorySession:
    beat = chapter.beats.get(session.current_beat)
    if beat is None:
        raise KeyError(f"Beat inexistente: {session.current_beat}")
    if beat.gate and not gate_satisfied:
        return session
    if not beat.next_beat:
        return session

    next_beat = chapter.beats.get(beat.next_beat)
    if next_beat is None:
        raise KeyError(f"Próximo beat inexistente: {beat.next_beat}")

    if session.current_beat not in session.completed_beats:
        session.completed_beats.append(session.current_beat)
    session.current_beat = next_beat.beat_id
    session.current_route = next_beat.route
    return session
