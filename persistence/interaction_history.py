from __future__ import annotations

from typing import Any

from google_sheets_repository import INTERACTIONS_SHEET, obter_registros_aba


_FALSE_LIKE = {
    "",
    "0",
    "false",
    "falso",
    "nao",
    "não",
    "none",
    "null",
    "ok",
    "success",
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value if value not in (None, "") else default))
    except (TypeError, ValueError):
        return default


def has_real_error(value: Any) -> bool:
    """Aceita FALSE/0/vazio vindos do Google Sheets como ausência de erro."""
    if value is None or value is False:
        return False
    if value is True:
        return True
    return _text(value).casefold() not in _FALSE_LIKE


def interaction_sort_key(row: dict[str, Any]) -> tuple[int, str, str]:
    return (
        _int(row.get("interaction_number"), 0),
        _text(row.get("timestamp") or row.get("updated_at")),
        _text(row.get("interaction_id")),
    )


def interaction_rows_for_session(
    *,
    scenario_session_id: str,
    user_id: str = "",
) -> list[dict[str, Any]]:
    """Lê as linhas válidas de uma execução usando scenario_session_id como vínculo principal."""
    scenario_session_id = _text(scenario_session_id)
    user_id = _text(user_id)
    if not scenario_session_id:
        return []

    selected: list[dict[str, Any]] = []
    for raw in obter_registros_aba(INTERACTIONS_SHEET):
        row = dict(raw)
        if _text(row.get("scenario_session_id")) != scenario_session_id:
            continue

        interaction_user_id = _text(row.get("user_id"))
        if user_id and interaction_user_id and interaction_user_id != user_id:
            continue
        if has_real_error(row.get("error")):
            continue
        if not _text(row.get("user_text")) and not _text(row.get("mary_response")):
            continue
        selected.append(row)

    selected.sort(key=interaction_sort_key)
    return selected


def load_story_messages(
    *,
    user_id: str,
    scenario_session_id: str,
    limit: int = 100,
) -> list[dict[str, str]]:
    rows = interaction_rows_for_session(
        scenario_session_id=scenario_session_id,
        user_id=user_id,
    )
    messages: list[dict[str, str]] = []
    for row in rows[-max(1, int(limit or 100)):]:
        user_text = _text(row.get("user_text"))
        mary_response = _text(row.get("mary_response"))
        if user_text:
            messages.append({"role": "user", "content": user_text})
        if mary_response:
            messages.append({"role": "assistant", "content": mary_response})
    return messages


def latest_interaction_for_session(
    *,
    scenario_session_id: str,
    user_id: str = "",
) -> dict[str, Any] | None:
    rows = interaction_rows_for_session(
        scenario_session_id=scenario_session_id,
        user_id=user_id,
    )
    return rows[-1] if rows else None


__all__ = [
    "has_real_error",
    "interaction_rows_for_session",
    "interaction_sort_key",
    "latest_interaction_for_session",
    "load_story_messages",
]
