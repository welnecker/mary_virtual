from __future__ import annotations

from copy import deepcopy
from functools import wraps
import sys
from typing import Any, Callable

import gspread
import streamlit as st

from scenarios.engine.models import ScreenplayLine, StorySession
from scenarios.engine.progression import advance_session
from scenarios.engine.prompt_builder import build_story_prompt
from scenarios.engine.registry import story_registry
from scenarios.engine.screenplay_repository import ScreenplayRepository
from scenarios.stories import register_stories


STORY_ENGINE_RUNTIME_VERSION = "story-engine-runtime-v2-explicit-opening-event"
_SUPPORTED_STORIES = {"casada_frustrada"}
_OPENING_CONDITION = "abertura da história"
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _condition_key(value: Any) -> str:
    return " ".join(_text(value).casefold().split())


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
    story = story_registry.get_story(story_id)
    requested_chapter = _chapter_id(instance)
    chapter = story.chapters.get(requested_chapter) or story.chapters[
        story.initial_chapter_id
    ]
    route = _text(instance.get("current_route") or scene.get("current_route"))
    beat = _text(instance.get("current_beat") or scene.get("current_beat"))
    if beat not in chapter.beats:
        beat = chapter.initial_beat
        route = chapter.initial_route
    return StorySession(
        story_id=story_id,
        chapter_id=chapter.chapter_id,
        current_route=route or chapter.initial_route,
        current_beat=beat or chapter.initial_beat,
        completed_beats=list(scene.get("completed_beats") or []),
        facts=deepcopy(scene.get("story_facts") or {}),
    )


@st.cache_data(ttl=60, show_spinner=False)
def _worksheet_records(
    spreadsheet_id: str,
    worksheet_name: str,
) -> list[dict[str, Any]]:
    if not spreadsheet_id:
        raise ValueError("O capítulo não possui spreadsheet_id configurado.")
    credentials = dict(st.secrets["gcp_service_account"])
    client = gspread.service_account_from_dict(credentials)
    spreadsheet = client.open_by_key(spreadsheet_id)
    return spreadsheet.worksheet(worksheet_name).get_all_records()


def _chapter_lines(session: StorySession) -> tuple[ScreenplayLine, ...]:
    story = story_registry.get_story(session.story_id)
    chapter = story.chapters[session.chapter_id]
    records = _worksheet_records(
        _text(chapter.spreadsheet_id),
        chapter.worksheet,
    )
    return ScreenplayRepository.from_records(records)


def _selected_lines(session: StorySession) -> tuple[ScreenplayLine, ...]:
    return ScreenplayRepository.select(
        _chapter_lines(session),
        route=session.current_route,
        beat=session.current_beat,
    )


def _opening_line(instance: dict[str, Any]) -> ScreenplayLine:
    session = _session_from_instance(instance)
    story = story_registry.get_story(session.story_id)
    chapter = story.chapters[session.chapter_id]
    candidates = tuple(
        line
        for line in _chapter_lines(session)
        if (
            line.route == session.current_route
            and line.beat == session.current_beat
            and _condition_key(line.condition) == _OPENING_CONDITION
        )
    )

    if not candidates:
        raise RuntimeError(
            "A abertura do roteiro não foi encontrada. "
            f"Aba={chapter.worksheet!r}, "
            f"rota esperada={session.current_route!r}, "
            f"beat esperado={session.current_beat!r}, "
            f"condicao esperada={_OPENING_CONDITION!r}. "
            "É obrigatória exatamente uma linha ativa com conteudo preenchido."
        )

    if len(candidates) > 1:
        orders = ", ".join(str(line.order) for line in candidates)
        raise RuntimeError(
            "Existem múltiplas linhas de abertura para o mesmo beat. "
            f"Aba={chapter.worksheet!r}, "
            f"rota={session.current_route!r}, "
            f"beat={session.current_beat!r}, "
            f"condicao={_OPENING_CONDITION!r}, "
            f"ordens encontradas=[{orders}]."
        )

    line = candidates[0]
    if not _text(line.content):
        raise RuntimeError(
            "A linha de abertura possui conteudo vazio. "
            f"Aba={chapter.worksheet!r}, ordem={line.order}, "
            f"rota={line.route!r}, beat={line.beat!r}."
        )
    return line


def _apply_sheet_opening(
    instance: dict[str, Any],
    *,
    force_new: bool = False,
) -> dict[str, Any]:
    story_id = _text(instance.get("scenario_id"))
    if story_id not in _SUPPORTED_STORIES:
        return instance

    progress = instance.get("story_progress")
    progress = deepcopy(progress) if isinstance(progress, dict) else {}
    line = _opening_line(instance)
    session = _session_from_instance(instance)

    consumed = list(progress.get("consumed_line_orders") or [])
    consumed = [int(value) for value in consumed if str(value).strip()]
    if line.order not in consumed:
        consumed.append(line.order)

    progress.update(
        {
            "engine": "clean_v2",
            "story_id": story_id,
            "chapter_id": session.chapter_id,
            "opening_line_order": line.order,
            "opening_line_content": line.content,
            "opening_line_route": line.route,
            "opening_line_beat": line.beat,
            "opening_line_condition": _OPENING_CONDITION,
            "consumed_line_orders": consumed,
        }
    )

    instance["opening_message"] = ""
    if force_new:
        instance["opening_sent"] = False
        scene = _scene(instance)
        scene["opening_sent"] = False
        instance["scene_state"] = scene

    instance["story_progress"] = progress
    return instance


def _ensure_opening_visible() -> None:
    instance = _instance()
    if not isinstance(instance, dict):
        return
    if _text(instance.get("scenario_id")) not in _SUPPORTED_STORIES:
        return
    if bool(instance.get("opening_sent", False)):
        return

    instance = _apply_sheet_opening(instance)
    progress = instance.get("story_progress")
    if not isinstance(progress, dict):
        raise RuntimeError("O estado da abertura não foi criado corretamente.")

    content = _text(progress.get("opening_line_content"))
    if not content:
        raise RuntimeError("O conteúdo da abertura não foi registrado.")

    messages = st.session_state.get("messages")
    if not isinstance(messages, list):
        messages = []

    opening_order = int(progress["opening_line_order"])
    already_present = any(
        isinstance(message, dict)
        and message.get("role") == "assistant"
        and message.get("source") == "screenplay_opening"
        and int(message.get("order", -1)) == opening_order
        for message in messages
    )

    if not already_present:
        messages.insert(
            0,
            {
                "role": "assistant",
                "content": content,
                "source": "screenplay_opening",
                "route": progress.get("opening_line_route", ""),
                "beat": progress.get("opening_line_beat", ""),
                "order": opening_order,
            },
        )

    instance["opening_sent"] = True
    scene = _scene(instance)
    scene["opening_sent"] = True
    instance["scene_state"] = scene

    st.session_state["messages"] = messages
    st.session_state["scenario_instance"] = instance
    st.session_state["initial_message_created"] = True


def _prompt_for_current_beat(instance: dict[str, Any]) -> str:
    session = _session_from_instance(instance)
    story = story_registry.get_story(session.story_id)
    chapter = story.chapters[session.chapter_id]
    selected = list(_selected_lines(session))

    progress = instance.get("story_progress")
    consumed_orders: set[int] = set()
    if isinstance(progress, dict):
        for value in progress.get("consumed_line_orders") or []:
            try:
                consumed_orders.add(int(value))
            except (TypeError, ValueError):
                continue

    selected = [line for line in selected if line.order not in consumed_orders]

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
    _persist_session(instance, advance_session(session, chapter))


def _patch_start_scenario(module: Any) -> None:
    original = getattr(module, "iniciar_cenario_para_usuario", None)
    if not callable(original) or getattr(
        original,
        "_strict_story_start_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        instance = original(*args, **kwargs)
        if isinstance(instance, dict):
            instance = _apply_sheet_opening(instance, force_new=True)
        return instance

    wrapper._strict_story_start_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "iniciar_cenario_para_usuario", wrapper)


def _patch_narrative_direction(module: Any) -> None:
    original = getattr(module, "montar_direcao_narrativa", None)
    if not callable(original) or getattr(
        original,
        "_clean_story_engine_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        base = str(original(*args, **kwargs) or "").strip()
        instance = _instance()
        if not isinstance(instance, dict):
            return base
        if _text(instance.get("scenario_id")) not in _SUPPORTED_STORIES:
            return base
        screenplay = _prompt_for_current_beat(instance)
        return "\n\n".join(part for part in (base, screenplay) if part)

    wrapper._clean_story_engine_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "montar_direcao_narrativa", wrapper)


def _patch_process_interaction(module: Any) -> None:
    original = getattr(module, "processar_interacao", None)
    if not callable(original) or getattr(
        original,
        "_clean_story_process_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        _advance_current_story()
        return result

    wrapper._clean_story_process_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "processar_interacao", wrapper)


def aplicar_story_engine_runtime() -> None:
    register_stories()
    module = sys.modules.get("__main__")
    if module is None:
        return
    _patch_start_scenario(module)
    _patch_narrative_direction(module)
    _patch_process_interaction(module)
    _ensure_opening_visible()


def install_story_engine_runtime() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    register_stories()
    _ORIGINAL_TITLE = st.title

    @wraps(_ORIGINAL_TITLE)
    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_story_engine_runtime()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "STORY_ENGINE_RUNTIME_VERSION",
    "aplicar_story_engine_runtime",
    "install_story_engine_runtime",
]
