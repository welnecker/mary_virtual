"""Histórias baseadas no motor narrativo v2.

Esta pasta é temporária enquanto `scenarios/stories/` ainda contém o runtime
legado. Após a migração, ela deverá assumir o nome definitivo `stories`.
"""

from scenarios.engine.registry import story_registry
from scenarios.stories_v2.casada_frustrada.story import STORY as CASADA_FRUSTRADA


def register_v2_stories() -> None:
    registered = {story.story_id for story in story_registry.list_stories()}
    if CASADA_FRUSTRADA.story_id not in registered:
        story_registry.register(CASADA_FRUSTRADA)


__all__ = ["CASADA_FRUSTRADA", "register_v2_stories"]
