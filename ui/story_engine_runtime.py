from __future__ import annotations

from copy import deepcopy
from functools import wraps
import re
import sys
from typing import Any, Callable

import gspread
import streamlit as st

from scenarios.engine.models import ScreenplayLine, StorySession
from scenarios.engine.progression import advance_session
from scenarios.engine.registry import story_registry
from scenarios.engine.screenplay_repository import ScreenplayRepository
from scenarios.stories import register_stories


STORY_ENGINE_RUNTIME_VERSION = "story-engine-runtime-v2-strict-authoritative-screenplay"
_SUPPORTED_STORIES = {"casada_frustrada"}
_OPENING_CONDITION = "abertura da história"
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _key(value: Any) -> str:
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
        value = _text(progress.get("chapter_id"))
        if value:
            return value
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
        route = chapter.initial_route
        beat = chapter.initial_beat

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


def _consumed_orders(instance: dict[str, Any]) -> set[int]:
    progress = instance.get("story_progress")
    values = progress.get("consumed_line_orders") if isinstance(progress, dict) else []
    result: set[int] = set()
    for value in values or []:
        try:
            result.add(int(value))
        except (TypeError, ValueError):
            continue
    return result


def _route_rules(session: StorySession) -> list[ScreenplayLine]:
    return [
        line
        for line in _selected_lines(session)
        if _key(line.kind) == "regra" and not _text(line.beat)
    ]


def _next_movement_line(instance: dict[str, Any]) -> ScreenplayLine:
    session = _session_from_instance(instance)
    consumed = _consumed_orders(instance)
    candidates = [
        line
        for line in _selected_lines(session)
        if (
            line.route == session.current_route
            and line.beat == session.current_beat
            and _key(line.kind) != "regra"
            and line.order not in consumed
            and _key(line.condition) != _OPENING_CONDITION
        )
    ]
    if not candidates:
        raise RuntimeError(
            "O beat atual não possui movimento executável. "
            f"rota={session.current_route!r}, beat={session.current_beat!r}, "
            f"ordens_consumidas={sorted(consumed)}."
        )
    return min(candidates, key=lambda line: line.order)


def _strict_prompt(instance: dict[str, Any]) -> str:
    session = _session_from_instance(instance)
    movement = _next_movement_line(instance)
    rules = _route_rules(session)

    progress = instance.get("story_progress")
    progress = deepcopy(progress) if isinstance(progress, dict) else {}
    progress.update(
        {
            "engine": "clean_v2_strict",
            "pending_line_order": movement.order,
            "pending_line_content": movement.content,
            "pending_line_route": movement.route,
            "pending_line_beat": movement.beat,
        }
    )
    instance["story_progress"] = progress
    st.session_state["scenario_instance"] = instance

    rule_text = "\n".join(
        f"- {line.content}" for line in rules if _text(line.content)
    )
    if not rule_text:
        rule_text = "- Não invente movimentos fora da linha obrigatória."

    return (
        "MODO DE ROTEIRO ESTRITO — ESTA SEÇÃO TEM PRIORIDADE SOBRE TODAS AS "
        "ORIENTAÇÕES ANTERIORES.\n\n"
        f"ROTA: {session.current_route}\n"
        f"BEAT: {session.current_beat}\n"
        f"ORDEM: {movement.order}\n"
        f"TIPO: {movement.kind}\n\n"
        "MOVIMENTO OBRIGATÓRIO DESTE TURNO:\n"
        f"{movement.content}\n\n"
        "REGRAS DA ROTA:\n"
        f"{rule_text}\n\n"
        "EXECUÇÃO OBRIGATÓRIA:\n"
        "- Reaja à mensagem mais recente do usuário somente dentro desse movimento.\n"
        "- Execute apenas esse movimento narrativo.\n"
        "- Não introduza outro assunto, pergunta, despedida, ação ou transição.\n"
        "- Não antecipe outra linha, outro beat ou outra rota.\n"
        "- Não explique o roteiro.\n"
        "- Produza somente a fala final de Mary."
    )


def _meaningful_tokens(value: str) -> set[str]:
    stop = {
        "a", "as", "o", "os", "de", "da", "das", "do", "dos", "e", "em",
        "um", "uma", "pra", "para", "que", "eu", "você", "voce", "me", "te",
        "tá", "ta", "tô", "to", "não", "nao", "com", "por", "se", "isso",
    }
    return {
        token
        for token in re.findall(r"[a-záàâãéêíóôõúç]+", _key(value))
        if len(token) >= 3 and token not in stop
    }


def _response_follows_movement(response: str, movement: str) -> bool:
    expected = _meaningful_tokens(movement)
    actual = _meaningful_tokens(response)
    if not expected:
        return bool(_text(response))
    required = 1 if len(expected) <= 3 else 2
    return len(expected & actual) >= required


def _last_assistant_message() -> dict[str, Any] | None:
    messages = st.session_state.get("messages")
    if not isinstance(messages, list):
        return None
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("role") == "assistant":
            return message
    return None


def _enforce_pending_movement(instance: dict[str, Any]) -> None:
    progress = instance.get("story_progress")
    if not isinstance(progress, dict):
        raise RuntimeError("O estado do roteiro não existe após a resposta.")

    movement = _text(progress.get("pending_line_content"))
    if not movement:
        raise RuntimeError("A linha pendente do roteiro não possui conteúdo.")

    assistant_message = _last_assistant_message()
    if assistant_message is None:
        raise RuntimeError("A interação terminou sem resposta de Mary.")

    response = _text(assistant_message.get("content"))
    if not _response_follows_movement(response, movement):
        assistant_message["content"] = movement
        assistant_message["screenplay_fallback"] = True

    assistant_message["screenplay_order"] = progress.get("pending_line_order")
    assistant_message["screenplay_route"] = progress.get("pending_line_route")
    assistant_message["screenplay_beat"] = progress.get("pending_line_beat")


def _persist_session(instance: dict[str, Any], session: StorySession) -> None:
    scene = _scene(instance)
    scene.update(
        {
            "current_route": session.current_route,
            "current_beat": session.current_beat,
            "completed_beats": list(session.completed_beats),
            "story_facts": deepcopy(session.facts),
        }
    )
    instance["current_route"] = session.current_route
    instance["current_beat"] = session.current_beat
    instance["scene_state"] = scene

    progress = instance.get("story_progress")
    progress = deepcopy(progress) if isinstance(progress, dict) else {}
    progress.update(
        {
            "engine": "clean_v2_strict",
            "story_id": session.story_id,
            "chapter_id": session.chapter_id,
            "current_route": session.current_route,
            "current_beat": session.current_beat,
            "completed_beats": list(session.completed_beats),
        }
    )
    instance["story_progress"] = progress
    st.session_state["scenario_instance"] = instance


def _consume_pending_and_advance() -> None:
    instance = _instance()
    if not isinstance(instance, dict):
        return
    if _text(instance.get("scenario_id")) not in _SUPPORTED_STORIES:
        return

    progress = instance.get("story_progress")
    progress = deepcopy(progress) if isinstance(progress, dict) else {}
    pending = progress.get("pending_line_order")
    if pending is None:
        raise RuntimeError("A resposta terminou sem ordem pendente do roteiro.")

    consumed = _consumed_orders(instance)
    consumed.add(int(pending))
    progress["consumed_line_orders"] = sorted(consumed)
    for field in (
        "pending_line_order",
        "pending_line_content",
        "pending_line_route",
        "pending_line_beat",
    ):
        progress.pop(field, None)
    instance["story_progress"] = progress

    session = _session_from_instance(instance)
    remaining = [
        line
        for line in _selected_lines(session)
        if (
            line.route == session.current_route
            and line.beat == session.current_beat
            and _key(line.kind) != "regra"
            and line.order not in consumed
            and _key(line.condition) != _OPENING_CONDITION
        )
    ]

    if remaining:
        _persist_session(instance, session)
        return

    story = story_registry.get_story(session.story_id)
    chapter = story.chapters[session.chapter_id]
    _persist_session(instance, advance_session(session, chapter))


def _prepare_new_instance(instance: dict[str, Any]) -> dict[str, Any]:
    if _text(instance.get("scenario_id")) not in _SUPPORTED_STORIES:
        return instance

    progress = instance.get("story_progress")
    progress = deepcopy(progress) if isinstance(progress, dict) else {}
    progress.update(
        {
            "engine": "clean_v2_strict",
            "consumed_line_orders": [],
        }
    )
    for field in list(progress):
        if field.startswith("opening_line_") or field.startswith("pending_line_"):
            progress.pop(field, None)

    instance["story_progress"] = progress
    instance["opening_message"] = ""
    instance["opening_sent"] = True
    scene = _scene(instance)
    scene["opening_sent"] = True
    instance["scene_state"] = scene
    return instance


def _disable_initial_message() -> None:
    instance = _instance()
    if not isinstance(instance, dict):
        return
    if _text(instance.get("scenario_id")) not in _SUPPORTED_STORIES:
        return

    messages = st.session_state.get("messages")
    messages = list(messages) if isinstance(messages, list) else []
    messages = [
        message
        for message in messages
        if not (
            isinstance(message, dict)
            and message.get("role") == "assistant"
            and (
                message.get("source") == "screenplay_opening"
                or not _text(message.get("content"))
            )
        )
    ]
    st.session_state["messages"] = messages
    st.session_state["initial_message_created"] = True


def _patch_start_scenario(module: Any) -> None:
    original = getattr(module, "iniciar_cenario_para_usuario", None)
    if not callable(original) or getattr(original, "_strict_story_start_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        instance = original(*args, **kwargs)
        return _prepare_new_instance(instance) if isinstance(instance, dict) else instance

    wrapper._strict_story_start_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "iniciar_cenario_para_usuario", wrapper)


def _patch_initial_message(module: Any) -> None:
    original = getattr(module, "criar_mensagem_inicial_cenario", None)
    if not callable(original) or getattr(original, "_strict_no_opening_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        instance = _instance()
        if isinstance(instance, dict) and _text(instance.get("scenario_id")) in _SUPPORTED_STORIES:
            _disable_initial_message()
            return None
        return original(*args, **kwargs)

    wrapper._strict_no_opening_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "criar_mensagem_inicial_cenario", wrapper)


def _patch_narrative_direction(module: Any) -> None:
    original = getattr(module, "montar_direcao_narrativa", None)
    if not callable(original) or getattr(original, "_strict_screenplay_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        instance = _instance()
        if isinstance(instance, dict) and _text(instance.get("scenario_id")) in _SUPPORTED_STORIES:
            return _strict_prompt(instance)
        return str(original(*args, **kwargs) or "").strip()

    wrapper._strict_screenplay_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "montar_direcao_narrativa", wrapper)


def _patch_process_interaction(module: Any) -> None:
    original = getattr(module, "processar_interacao", None)
    if not callable(original) or getattr(original, "_strict_story_process_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        instance = _instance()
        if isinstance(instance, dict) and _text(instance.get("scenario_id")) in _SUPPORTED_STORIES:
            _enforce_pending_movement(instance)
            _consume_pending_and_advance()
        return result

    wrapper._strict_story_process_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "processar_interacao", wrapper)


def aplicar_story_engine_runtime() -> None:
    register_stories()
    module = sys.modules.get("__main__")
    if module is None:
        return
    _patch_start_scenario(module)
    _patch_initial_message(module)
    _patch_narrative_direction(module)
    _patch_process_interaction(module)


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
