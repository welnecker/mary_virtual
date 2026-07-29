from __future__ import annotations

from collections.abc import Iterable

from .models import ScreenplayLine, StorySession
from .progression import advance_session
from .prompt_builder import build_story_prompt
from .registry import StoryRegistry
from .screenplay_renderer import render_screenplay
from .screenplay_repository import ScreenplayRepository


class StorySessionEngine:
    def __init__(self, registry: StoryRegistry) -> None:
        self._registry = registry

    def start(self, story_id: str, chapter_id: str | None = None) -> StorySession:
        story = self._registry.get_story(story_id)
        resolved_chapter_id = chapter_id or story.initial_chapter_id
        chapter = self._registry.get_chapter(story_id, resolved_chapter_id)
        return StorySession(
            story_id=story_id,
            chapter_id=resolved_chapter_id,
            current_route=chapter.initial_route,
            current_beat=chapter.initial_beat,
        )

    def build_prompt(
        self,
        session: StorySession,
        lines: Iterable[ScreenplayLine],
        *,
        permanent_context: str = "",
    ) -> str:
        story = self._registry.get_story(session.story_id)
        chapter = self._registry.get_chapter(session.story_id, session.chapter_id)
        selected = ScreenplayRepository.select(
            lines,
            route=session.current_route,
            beat=session.current_beat,
        )
        return build_story_prompt(
            story_title=story.title,
            chapter_title=chapter.title,
            session=session,
            screenplay=render_screenplay(selected),
            permanent_context=permanent_context,
        )

    def advance(self, session: StorySession, *, gate_satisfied: bool = True) -> StorySession:
        chapter = self._registry.get_chapter(session.story_id, session.chapter_id)
        return advance_session(session, chapter, gate_satisfied=gate_satisfied)
