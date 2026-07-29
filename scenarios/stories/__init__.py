from __future__ import annotations

from scenarios.engine.registry import story_registry
from scenarios.stories.casada_frustrada.story import STORY as CASADA_FRUSTRADA


def register_stories() -> None:
    registered = {story.story_id for story in story_registry.list_stories()}
    if CASADA_FRUSTRADA.story_id not in registered:
        story_registry.register(CASADA_FRUSTRADA)


__all__ = ["CASADA_FRUSTRADA", "register_stories"]
