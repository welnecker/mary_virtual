from __future__ import annotations

from copy import deepcopy
from functools import wraps
import sys
from typing import Any, Callable

import streamlit as st

from google_sheets_repository import obter_planilha
from scenarios.engine.progression import advance_session
from scenarios.engine.prompt_builder import build_story_prompt
from scenarios.engine.screenplay_repository import ScreenplayRepository
from scenarios.engine.session_engine import StorySessionEngine
from scenarios.engine.models import StorySession
from scenarios.stories_v2 import register_v2_stories
from scenarios.engine.registry import story_registry


STORY_ENGINE_RUNTIME_VERSION = "story-engine-runtime-v2-clean"
_SUPPORTED_STORIES = {"casada_frustrada"}
_INSTALLED = False


def _text(value: Any) -> str:
    return str(value or "").strip()


def _instance() -> dict[str, Any] | None:
    value = st.session_state.get("scenario_instance")
    return value if isinstance(value, dict) else None


def _scene(instance: dict[str, Any]) -> dict[str, Any]:
    value = instance.get("scene_state")
    return deepcopy(value) if isinstance(value, dict) else {}


def _chapter_id(instance: dict[str, Any]) -> str:
    progress = instance.get("story_progress")
    if isinstance(progress, dict):
        chapter_id = _text(progress.get("chapter_id"))
        if chapter_id:
            return chapter_id
    return "cap_01"


def _session_from_instance(instance: dict[str, Any]) -> StorySession:
    scene = _scene(instance)
    story_id = _text(instance.get("scenario_id"))
    chapter_id = _chapter_id(instance)
    story = story_registry.get_story(story_id)
    chapter = story.chapters[chapter_id]
    route = _text(instance.get("current_route") or scene.get("current_route"))
    beat = _text(instance.get("current_beat") or scene.get("current_beat"))
    return StorySession(
        story_id=story_id,
        chapter_id=chapter_id,
        current_route=route or chapter.initial_route,
        current_beat=beat or chapter.initial_beat,
        completed_beats=list(scene.get("completed_beats") or []),
        facts=deepcopy(scene.get("story_facts") or {}),
    )


@st.cache_data(ttl=60, show_spinner=False)
def _worksheet_records(spreadsheet_id: str, worksheet_name: str) -> list[dict[str, Any]]:
    spreadsheet = obter_planilha()
    if spreadsheet_id and spreadsheet.id != spreadsheet_id:
        # A instalação atual usa uma planilha central. O id do capítulo é validado,
        # mas a conexão compartilhada continua sendo a autoridade de credenciais.
        pass
    return spreadsheet.worksheet(worksheet_name).get_all_records()


def _prompt_for_current_beat(instance: dict[str, Any]) -> str:
    session = _session_from_instance(instance)
    story = story_registry.get_story(session.story_id)
    chapter = story.chapters[session.chapter_id]
    records = _worksheet_records(
        _text(chapter.spreadsheet_id),
        chapter.worksheet,
    )
    lines = ScreenplayRepository.from_records(records)
    selected = ScreenplayRepository.select(
        lines,
        route=session.current_route,
        beat=session.current_beat,
    )
    return build_story_prompt(
        story=story,
        chapter=chapter,
        session=session,
        lines=selected,
    )


def _persist_session(instance: dict[str, Any], session: StorySession) -> None:
    scene = _scene(instance)
    scene["current_route"] = session.current_route
    scene["current_beat"] = session.current_beat
    scene["completed_beats"] = list(session.completed_beats)
    scene["story_facts"] = deepcopy(session.facts)
    instance["current_route"] = session.current_route
    instance["current_beat"] = session.current_beat
    instance["scene_state"] = scene
    progress = instance.get("story_progress")
    progress = deepcopy(progress) if isinstance(progress, dict) else {}
    progress.update(
        {
            "engine": "clean_v2",
            "story_id": session.story_id,
            "chapter_id": session.chapter_id,
            "current_route": session.current_route,
            "current_beat": session.current_beat,
            "completed_beats": list(session.completed_beats),
        }
    )
    instance["story_progress"] = progress
    st.session_state["scenario_instance"] = instance


def _advance_current_story() -> None:
    instance = _instance()
    if not isinstance(instance, dict):
        return
    story_id = _text(instance.get("scenario_id"))
    if story_id not in _SUPPORTED_STORIES:
        return
    session = _session_from_instance(instance)
    story = story_registry.get_story(story_id)
    chapter = story.chapters[session.chapter_id]
    advanced = advance_session(session, chapter)
    _persist_session(instance, advanced)


def _patch_narrative_direction(module: Any) -> None:
    original = getattr(module, "montar_direcao_narrativa", None)
    if not callable(original) or getattr(original, "_clean_story_engine_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        base = str(original(*args, **kwargs) or "").strip()
        instance = _instance()
        if not isinstance(instance, dict):
            return base
        story_id = _text(instance.get("scenario_id"))
        if story_id not in _SUPPORTED_STORIES:
            return base
        screenplay = _prompt_for_current_beat(instance)
        return "\n\n".join(part for part in (base, screenplay) if part)

    wrapper._clean_story_engine_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "montar_direcao_narrativa", wrapper)


def _patch_process_interaction(module: Any) -> None:
    original = getattr(module, "processar_interacao", None)
    if not callable(original) or getattr(original, "_clean_story_process_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        _advance_current_story()
        return result

    wrapper._clean_story_process_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "processar_interacao", wrapper)


def aplicar_story_engine_runtime() -> None:
    register_v2_stories()
    module = sys.modules.get("__main__")
    if module is None:
        return
    _patch_narrative_direction(module)
    _patch_process_interaction(module)


def install_story_engine_runtime() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    aplicar_story_engine_runtime()
    _INSTALLED = True


__all__ = [
    "STORY_ENGINE_RUNTIME_VERSION",
    "aplicar_story_engine_runtime",
    "install_story_engine_runtime",
]
