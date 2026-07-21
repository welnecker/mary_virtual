from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google_sheets_repository import (
    adicionar_registro,
    atualizar_registro,
    buscar_registro,
    serializar_json,
)

SCENARIO_SESSIONS_SHEET = "SCENARIO_SESSIONS"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _inteiro(valor: Any, padrao: int = 0) -> int:
    try:
        return int(valor or padrao)
    except (TypeError, ValueError):
        return padrao


def _booleano(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    return _texto(valor).lower() in {
        "true",
        "1",
        "sim",
        "yes",
        "verdadeiro",
    }


def montar_registro_sessao_cenario(
    instancia: dict[str, Any],
    *,
    houve_interacao: bool = False,
) -> dict[str, Any]:
    if not isinstance(instancia, dict):
        raise ValueError("A instância do cenário é inválida.")

    scenario_session_id = _texto(
        instancia.get("scenario_session_id")
    )
    user_id = _texto(instancia.get("user_id"))
    scenario_id = _texto(instancia.get("scenario_id"))

    if not scenario_session_id:
        raise ValueError("A sessão narrativa não possui identificador.")
    if not user_id:
        raise ValueError("A sessão narrativa não possui usuário.")
    if not scenario_id:
        raise ValueError("A sessão narrativa não possui cenário.")

    agora = utc_now_iso()
    created_at = _texto(instancia.get("created_at")) or agora
    updated_at = agora

    last_interaction_at = _texto(
        instancia.get("last_interaction_at")
    )
    if houve_interacao:
        last_interaction_at = agora

    scene_state = instancia.get("scene_state")
    if not isinstance(scene_state, dict):
        scene_state = {}

    story_progress = instancia.get("story_progress")
    if not isinstance(story_progress, dict):
        story_progress = {}

    return {
        "scenario_session_id": scenario_session_id,
        "user_id": user_id,
        "scenario_id": scenario_id,
        "scenario_version": _inteiro(
            instancia.get("scenario_version"),
            1,
        ),
        "created_at": created_at,
        "updated_at": updated_at,
        "last_interaction_at": last_interaction_at,
        "completed_at": _texto(instancia.get("completed_at")),
        "status": _texto(instancia.get("status")) or "active",
        "interaction_count": _inteiro(
            instancia.get("interaction_count"),
            0,
        ),
        "opening_sent": _booleano(
            instancia.get("opening_sent")
        ),
        "current_phase": _texto(
            instancia.get("current_phase")
        ),
        "current_route": _texto(
            instancia.get("current_route")
        ),
        "current_beat": _texto(
            instancia.get("current_beat")
        ),
        "active_hook": _texto(
            instancia.get("active_hook")
        ),
        "climax_reached": _booleano(
            instancia.get("climax_reached")
        ),
        "satisfaction_detected": _booleano(
            instancia.get("satisfaction_detected")
        ),
        "ending_ready": _booleano(
            instancia.get("ending_ready")
        ),
        "ending_sent": _booleano(
            instancia.get("ending_sent")
        ),
        "ending_type": _texto(
            instancia.get("ending_type")
        ),
        "ending_reason": _texto(
            instancia.get("ending_reason")
        ),
        "input_locked": _booleano(
            instancia.get("input_locked")
        ),
        "show_return_to_menu": _booleano(
            instancia.get("show_return_to_menu")
        ),
        "scene_state_json": serializar_json(scene_state),
        "story_progress_json": serializar_json(story_progress),
        "summary": _texto(instancia.get("summary")),
    }


def salvar_instancia_cenario(
    instancia: dict[str, Any],
    *,
    houve_interacao: bool = False,
) -> dict[str, Any]:
    registro = montar_registro_sessao_cenario(
        instancia,
        houve_interacao=houve_interacao,
    )

    scenario_session_id = registro["scenario_session_id"]
    existente = buscar_registro(
        SCENARIO_SESSIONS_SHEET,
        coluna="scenario_session_id",
        valor=scenario_session_id,
    )

    if existente is None:
        adicionar_registro(
            SCENARIO_SESSIONS_SHEET,
            registro,
        )
    else:
        alteracoes = dict(registro)
        alteracoes.pop("scenario_session_id", None)
        alteracoes.pop("created_at", None)
        atualizar_registro(
            SCENARIO_SESSIONS_SHEET,
            coluna_chave="scenario_session_id",
            valor_chave=scenario_session_id,
            alteracoes=alteracoes,
        )

    instancia["updated_at"] = registro["updated_at"]
    instancia["last_interaction_at"] = registro[
        "last_interaction_at"
    ]
    return registro


__all__ = [
    "SCENARIO_SESSIONS_SHEET",
    "montar_registro_sessao_cenario",
    "salvar_instancia_cenario",
]
