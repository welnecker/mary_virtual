from __future__ import annotations

from copy import deepcopy
from typing import Any

from google_sheets_repository import (
    GoogleSheetsRepositoryError,
    INTERACTIONS_SHEET,
    obter_aba,
    obter_cabecalhos,
    obter_registros_aba,
)
from repositories.scenario_session_repository import (
    obter_sessao_cenario,
    salvar_instancia_cenario,
)


SCENARIO_ROLLBACK_VERSION = "scenario-rollback-v1-synchronized-turns"


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _inteiro(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def listar_interacoes_sessao_cenario_sem_cache(
    *,
    user_id: str,
    scenario_session_id: str,
) -> list[dict[str, Any]]:
    user_id = _texto(user_id)
    scenario_session_id = _texto(scenario_session_id)
    if not user_id or not scenario_session_id:
        return []

    worksheet = obter_aba(INTERACTIONS_SHEET)
    headers = [str(item).strip() for item in worksheet.row_values(1)]
    values = worksheet.get_all_values()
    if not values or not headers:
        return []

    result: list[dict[str, Any]] = []
    for row_number, row in enumerate(values[1:], start=2):
        record = {
            header: row[index] if index < len(row) else ""
            for index, header in enumerate(headers)
            if header
        }
        if _texto(record.get("user_id")) != user_id:
            continue
        if _texto(record.get("scenario_session_id")) != scenario_session_id:
            continue
        record["_row_number"] = row_number
        result.append(record)

    result.sort(
        key=lambda item: (
            _inteiro(item.get("interaction_number")),
            _texto(item.get("timestamp")),
            _inteiro(item.get("_row_number")),
        )
    )
    return result


def _limpar_estado_encerramento(state: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(state)
    result.update(
        {
            "ending_ready": False,
            "ending_sent": False,
            "ending_forced": False,
            "ending_type": "",
            "ending_reason": "",
            "ending_trigger": "",
            "ending_trigger_interaction": 0,
            "ending_requested_by_user": False,
            "ending_requested_at_interaction": 0,
            "ending_countdown_visible": False,
            "ending_countdown_remaining": 0,
            "ending_pressure": "",
            "seek_narrative_resolution": False,
            "input_locked": False,
            "show_return_to_menu": False,
            "user_disengaged": False,
        }
    )
    return result


def apagar_ultimos_turnos_cenario(
    *,
    user_id: str,
    scenario_session_id: str,
    quantidade: int,
) -> dict[str, Any]:
    """Apaga os últimos turnos e reconcilia INTERACTIONS e SCENARIO_SESSIONS."""

    user_id = _texto(user_id)
    scenario_session_id = _texto(scenario_session_id)
    quantidade = max(1, min(20, _inteiro(quantidade, 1)))

    if not user_id:
        raise ValueError("O usuário não foi identificado.")
    if not scenario_session_id:
        raise ValueError("A sessão narrativa não foi identificada.")

    interactions = listar_interacoes_sessao_cenario_sem_cache(
        user_id=user_id,
        scenario_session_id=scenario_session_id,
    )
    valid = [item for item in interactions if not _texto(item.get("error"))]
    if not valid:
        return {
            "deleted_turns": 0,
            "remaining_turns": 0,
            "scenario_session_id": scenario_session_id,
            "messages": [],
        }

    targets = valid[-quantidade:]
    target_rows = sorted(
        {_inteiro(item.get("_row_number")) for item in targets if _inteiro(item.get("_row_number")) >= 2},
        reverse=True,
    )

    worksheet = obter_aba(INTERACTIONS_SHEET)
    try:
        for row_number in target_rows:
            worksheet.delete_rows(row_number)
        obter_registros_aba.clear()
        obter_cabecalhos.clear()
    except Exception as exc:
        raise GoogleSheetsRepositoryError(
            f"Não foi possível apagar os turnos da história: {exc}"
        ) from exc

    remaining = listar_interacoes_sessao_cenario_sem_cache(
        user_id=user_id,
        scenario_session_id=scenario_session_id,
    )
    remaining_valid = [item for item in remaining if not _texto(item.get("error"))]
    total_real = len(remaining_valid)

    session = obter_sessao_cenario(scenario_session_id)
    if session is None:
        raise GoogleSheetsRepositoryError(
            "A sessão narrativa não foi encontrada para sincronização."
        )
    if _texto(session.get("user_id")) != user_id:
        raise ValueError("A sessão narrativa não pertence ao usuário atual.")

    scene_state = session.get("scene_state")
    if not isinstance(scene_state, dict):
        scene_state = {}
    scene_state = _limpar_estado_encerramento(scene_state)
    scene_state["interaction_count"] = total_real
    scene_state["interaction_number"] = total_real + 1
    scene_state["story_progress_count"] = min(
        total_real,
        max(0, _inteiro(scene_state.get("story_progress_count"))),
    )
    scene_state["turns_since_story_advance"] = 0
    scene_state["same_activity_turns"] = 0
    scene_state["repeated_turns"] = 0
    scene_state["stalled_turns"] = 0

    last = remaining_valid[-1] if remaining_valid else {}
    scene_state["last_user_action"] = _texto(last.get("user_text"))
    scene_state["last_mary_response"] = _texto(last.get("mary_response"))

    session.update(
        {
            "status": "active",
            "completed_at": "",
            "interaction_count": total_real,
            "ending_ready": False,
            "ending_sent": False,
            "ending_type": "",
            "ending_reason": "",
            "input_locked": False,
            "show_return_to_menu": False,
            "scene_state": scene_state,
        }
    )
    salvar_instancia_cenario(session, houve_interacao=False)

    messages: list[dict[str, str]] = []
    for record in remaining_valid:
        user_text = _texto(record.get("user_text"))
        mary_response = _texto(record.get("mary_response"))
        if user_text:
            messages.append({"role": "user", "content": user_text})
        if mary_response:
            messages.append({"role": "assistant", "content": mary_response})

    return {
        "deleted_turns": len(targets),
        "remaining_turns": total_real,
        "scenario_session_id": scenario_session_id,
        "session": session,
        "messages": messages,
    }


__all__ = [
    "SCENARIO_ROLLBACK_VERSION",
    "apagar_ultimos_turnos_cenario",
    "listar_interacoes_sessao_cenario_sem_cache",
]
