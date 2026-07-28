from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from core.story_models import StorySession
from google_sheets_repository import (
    INTERACTIONS_SHEET,
    SESSIONS_SHEET,
    adicionar_registro,
    atualizar_registro,
    buscar_registro,
    obter_registros_aba,
    serializar_json,
)
from repositories.scenario_session_repository import salvar_instancia_cenario

SCENARIOS_SHEET = "SCENARIOS"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value if value not in (None, "") else default))
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = _text(value).lower()
    if text in {"true", "1", "sim", "yes", "ativo", "active"}:
        return True
    if text in {"false", "0", "nao", "não", "no", "inativo", "inactive"}:
        return False
    return default


def load_catalog_overrides() -> dict[str, dict[str, Any]]:
    rows = obter_registros_aba(SCENARIOS_SHEET)
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        scenario_id = _text(row.get("scenario_id"))
        if not scenario_id:
            continue
        status = (_text(row.get("status")) or "active").lower()
        if status not in {"active", "ativo", "published", "publicado"}:
            continue
        if not _bool(row.get("active"), True) or not _bool(row.get("published"), True):
            continue
        result[scenario_id] = dict(row)
    return result


def create_runtime_session(
    *,
    user_id: str,
    model: str,
    prompt_version: str,
    app_version: str,
    client_type: str = "streamlit",
    runtime_id: str = "story-runtime-v2",
) -> dict[str, Any]:
    now = _now()
    record = {
        "session_id": f"ses_{uuid4().hex}",
        "user_id": _text(user_id),
        "started_at": now,
        "last_activity_at": now,
        "ended_at": "",
        "updated_at": now,
        "model": _text(model),
        "prompt_version": _text(prompt_version),
        "app_version": _text(app_version),
        "status": "active",
        "end_reason": "",
        "interaction_count": 0,
        "last_scenario_id": "",
        "last_scenario_session_id": "",
        "client_type": _text(client_type),
        "runtime_id": _text(runtime_id),
        "duration_seconds": "",
        "active": True,
    }
    adicionar_registro(SESSIONS_SHEET, record)
    return record


def finish_runtime_session(session_id: str, *, reason: str) -> None:
    now = _now()
    atualizar_registro(
        SESSIONS_SHEET,
        coluna_chave="session_id",
        valor_chave=_text(session_id),
        alteracoes={
            "last_activity_at": now,
            "ended_at": now,
            "updated_at": now,
            "status": "ended",
            "end_reason": _text(reason) or "ended",
            "active": False,
        },
    )


def create_story_session(
    *,
    engine_session: StorySession,
    user_id: str,
    scenario_version: int,
    opening_sent: bool,
) -> dict[str, Any]:
    scenario_session_id = f"scn_{uuid4().hex}"
    engine_session.access_id = scenario_session_id
    instance = {
        "scenario_session_id": scenario_session_id,
        "user_id": _text(user_id),
        "scenario_id": engine_session.story_id,
        "scenario_version": max(1, int(scenario_version or 1)),
        "status": engine_session.status,
        "interaction_count": engine_session.turn_count,
        "opening_sent": bool(opening_sent),
        "current_phase": engine_session.chapter_id,
        "current_route": "",
        "current_beat": engine_session.current_beat,
        "active_hook": "",
        "climax_reached": False,
        "satisfaction_detected": False,
        "ending_ready": False,
        "ending_sent": False,
        "ending_type": "",
        "ending_reason": engine_session.ending_reason,
        "input_locked": not engine_session.is_active,
        "show_return_to_menu": not engine_session.is_active,
        "scene_state": {
            "current_beat_emitted": engine_session.current_beat_emitted,
        },
        "story_progress": {
            "chapter_id": engine_session.chapter_id,
            "completed_beats": list(engine_session.completed_beats),
            "completed_facts": list(engine_session.completed_facts),
            "access_id": engine_session.access_id,
            "engine": asdict(engine_session),
        },
        "relationship_state": {},
        "summary": "",
        "chapter_number": 1,
        "parent_session_id": "",
        "root_session_id": scenario_session_id,
        "continuation_mode": "single_paid_story",
        "history_session_ids": [],
    }
    salvar_instancia_cenario(instance)
    return instance


def persist_story_session(
    *,
    instance: dict[str, Any],
    engine_session: StorySession,
    route: str = "",
    interaction_happened: bool = False,
) -> dict[str, Any]:
    instance["status"] = engine_session.status
    instance["interaction_count"] = engine_session.turn_count
    instance["current_phase"] = engine_session.chapter_id
    instance["current_route"] = _text(route)
    instance["current_beat"] = engine_session.current_beat
    instance["ending_reason"] = engine_session.ending_reason
    instance["ending_sent"] = not engine_session.is_active
    instance["ending_ready"] = not engine_session.is_active
    instance["input_locked"] = not engine_session.is_active
    instance["show_return_to_menu"] = not engine_session.is_active
    instance["scene_state"] = {
        "current_beat_emitted": engine_session.current_beat_emitted,
    }
    instance["story_progress"] = {
        "chapter_id": engine_session.chapter_id,
        "completed_beats": list(engine_session.completed_beats),
        "completed_facts": list(engine_session.completed_facts),
        "access_id": engine_session.access_id,
        "engine": asdict(engine_session),
    }
    return salvar_instancia_cenario(instance, houve_interacao=interaction_happened)


def persist_interaction(
    *,
    runtime_session_id: str,
    user_id: str,
    scenario_instance: dict[str, Any],
    user_text: str,
    mary_response: str,
    model: str,
    prompt_version: str,
    app_version: str,
    response_time_ms: int,
    scenario_beat: str,
    scenario_route: str,
    scenario_status: str,
    scenario_completed: bool,
    error: str = "",
    error_type: str = "",
    error_stage: str = "",
    retry_count: int = 0,
) -> dict[str, Any]:
    now = _now()
    scenario_session_id = _text(scenario_instance.get("scenario_session_id"))
    interaction_number = max(1, _int(scenario_instance.get("interaction_count"), 0))
    interaction_key = f"{scenario_session_id}:{interaction_number:02d}"
    interaction_id = f"int_{uuid4().hex}"
    record = {
        "interaction_id": interaction_id,
        "session_id": _text(runtime_session_id),
        "user_id": _text(user_id),
        "timestamp": now,
        "updated_at": now,
        "user_text": str(user_text or ""),
        "mary_response": str(mary_response or ""),
        "model": _text(model),
        "prompt_version": _text(prompt_version),
        "app_version": _text(app_version),
        "response_time_ms": max(0, int(response_time_ms or 0)),
        "image_sent": False,
        "image_width": "",
        "image_height": "",
        "image_size_bytes": "",
        "image_mime_type": "",
        "mary_asked_name": False,
        "error": _text(error),
        "error_type": _text(error_type),
        "error_stage": _text(error_stage),
        "retry_count": max(0, int(retry_count or 0)),
        "scenario_session_id": scenario_session_id,
        "scenario_id": _text(scenario_instance.get("scenario_id")),
        "scenario_version": max(1, _int(scenario_instance.get("scenario_version"), 1)),
        "scenario_phase": _text(scenario_instance.get("current_phase")),
        "scenario_route": _text(scenario_route),
        "scenario_beat": _text(scenario_beat),
        "scenario_status": _text(scenario_status),
        "interaction_number": interaction_number,
        "scenario_completed": bool(scenario_completed),
        "interaction_key": interaction_key,
    }
    existing = buscar_registro(
        INTERACTIONS_SHEET,
        coluna="interaction_key",
        valor=interaction_key,
    )
    if existing is None:
        adicionar_registro(INTERACTIONS_SHEET, record)
    else:
        atualizar_registro(
            INTERACTIONS_SHEET,
            coluna_chave="interaction_key",
            valor_chave=interaction_key,
            alteracoes=record,
        )

    session_row = buscar_registro(SESSIONS_SHEET, coluna="session_id", valor=runtime_session_id) or {}
    total = max(0, _int(session_row.get("interaction_count"), 0)) + (0 if existing else 1)
    atualizar_registro(
        SESSIONS_SHEET,
        coluna_chave="session_id",
        valor_chave=_text(runtime_session_id),
        alteracoes={
            "last_activity_at": now,
            "updated_at": now,
            "interaction_count": total,
            "last_scenario_id": record["scenario_id"],
            "last_scenario_session_id": scenario_session_id,
            "active": True,
        },
    )
    return record


def load_story_messages(*, user_id: str, scenario_session_id: str, limit: int = 100) -> list[dict[str, str]]:
    rows = obter_registros_aba(INTERACTIONS_SHEET)
    selected = [
        row
        for row in rows
        if _text(row.get("user_id")) == _text(user_id)
        and _text(row.get("scenario_session_id")) == _text(scenario_session_id)
        and not _text(row.get("error"))
    ]
    selected.sort(key=lambda row: (_int(row.get("interaction_number"), 0), _text(row.get("timestamp"))))
    messages: list[dict[str, str]] = []
    for row in selected[-max(1, int(limit or 100)):]:
        user_text = str(row.get("user_text") or "").strip()
        mary_response = str(row.get("mary_response") or "").strip()
        if user_text:
            messages.append({"role": "user", "content": user_text})
        if mary_response:
            messages.append({"role": "assistant", "content": mary_response})
    return messages
