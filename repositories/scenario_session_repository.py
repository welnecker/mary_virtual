from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from google_sheets_repository import (
    adicionar_registro,
    atualizar_registro,
    buscar_registro,
    obter_registros_aba,
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
        "true", "1", "sim", "yes", "verdadeiro"
    }


def _desserializar_json(valor: Any) -> dict[str, Any]:
    if isinstance(valor, dict):
        return dict(valor)
    texto = _texto(valor)
    if not texto:
        return {}
    try:
        resultado = json.loads(texto)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return resultado if isinstance(resultado, dict) else {}


def _hidratar_registro_sessao(
    registro: dict[str, Any],
) -> dict[str, Any]:
    resultado = dict(registro)
    resultado["scenario_version"] = _inteiro(
        resultado.get("scenario_version"), 1
    )
    resultado["interaction_count"] = _inteiro(
        resultado.get("interaction_count"), 0
    )
    for campo in (
        "opening_sent", "climax_reached", "satisfaction_detected",
        "ending_ready", "ending_sent", "input_locked",
        "show_return_to_menu",
    ):
        resultado[campo] = _booleano(resultado.get(campo))
    resultado["scene_state"] = _desserializar_json(
        resultado.get("scene_state_json")
    )
    resultado["story_progress"] = _desserializar_json(
        resultado.get("story_progress_json")
    )
    resultado["relationship_state"] = _desserializar_json(
        resultado.get("relationship_state_json")
    )
    return resultado


def montar_registro_sessao_cenario(
    instancia: dict[str, Any],
    *,
    houve_interacao: bool = False,
) -> dict[str, Any]:
    if not isinstance(instancia, dict):
        raise ValueError("A instância do cenário é inválida.")

    scenario_session_id = _texto(instancia.get("scenario_session_id"))
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
    last_interaction_at = _texto(instancia.get("last_interaction_at"))
    if houve_interacao:
        last_interaction_at = agora

    scene_state = instancia.get("scene_state")
    if not isinstance(scene_state, dict):
        scene_state = {}
    story_progress = instancia.get("story_progress")
    if not isinstance(story_progress, dict):
        story_progress = {}
    relationship_state = instancia.get("relationship_state")
    if not isinstance(relationship_state, dict):
        relationship_state = {}

    return {
        "scenario_session_id": scenario_session_id,
        "user_id": user_id,
        "scenario_id": scenario_id,
        "scenario_version": _inteiro(
            instancia.get("scenario_version"), 1
        ),
        "created_at": created_at,
        "updated_at": agora,
        "last_interaction_at": last_interaction_at,
        "completed_at": _texto(instancia.get("completed_at")),
        "status": _texto(instancia.get("status")) or "active",
        "interaction_count": _inteiro(
            instancia.get("interaction_count"), 0
        ),
        "opening_sent": _booleano(instancia.get("opening_sent")),
        "current_phase": _texto(instancia.get("current_phase")),
        "current_route": _texto(instancia.get("current_route")),
        "current_beat": _texto(instancia.get("current_beat")),
        "active_hook": _texto(instancia.get("active_hook")),
        "climax_reached": _booleano(instancia.get("climax_reached")),
        "satisfaction_detected": _booleano(
            instancia.get("satisfaction_detected")
        ),
        "ending_ready": _booleano(instancia.get("ending_ready")),
        "ending_sent": _booleano(instancia.get("ending_sent")),
        "ending_type": _texto(instancia.get("ending_type")),
        "ending_reason": _texto(instancia.get("ending_reason")),
        "input_locked": _booleano(instancia.get("input_locked")),
        "show_return_to_menu": _booleano(
            instancia.get("show_return_to_menu")
        ),
        "scene_state_json": serializar_json(scene_state),
        "story_progress_json": serializar_json(story_progress),
        "relationship_state_json": serializar_json(relationship_state),
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
        adicionar_registro(SCENARIO_SESSIONS_SHEET, registro)
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
    instancia["last_interaction_at"] = registro["last_interaction_at"]
    return registro


def obter_sessao_cenario(
    scenario_session_id: str,
) -> dict[str, Any] | None:
    scenario_session_id = _texto(scenario_session_id)
    if not scenario_session_id:
        return None
    registro = buscar_registro(
        SCENARIO_SESSIONS_SHEET,
        coluna="scenario_session_id",
        valor=scenario_session_id,
    )
    if registro is None:
        return None
    return _hidratar_registro_sessao(dict(registro))


def listar_sessoes_cenario_usuario(
    user_id: str,
    *,
    status: str | None = None,
    scenario_id: str | None = None,
) -> list[dict[str, Any]]:
    user_id = _texto(user_id)
    if not user_id:
        raise ValueError("O usuário não foi identificado.")

    status_normalizado = _texto(status).lower()
    scenario_id_normalizado = _texto(scenario_id)
    registros = obter_registros_aba(SCENARIO_SESSIONS_SHEET)
    resultado: list[dict[str, Any]] = []

    for registro in registros:
        if _texto(registro.get("user_id")) != user_id:
            continue
        if (
            status_normalizado
            and _texto(registro.get("status")).lower()
            != status_normalizado
        ):
            continue
        if (
            scenario_id_normalizado
            and _texto(registro.get("scenario_id"))
            != scenario_id_normalizado
        ):
            continue
        resultado.append(_hidratar_registro_sessao(dict(registro)))

    resultado.sort(
        key=lambda item: (
            _texto(item.get("updated_at")),
            _texto(item.get("created_at")),
        ),
        reverse=True,
    )
    return resultado


def obter_sessao_ativa_mais_recente(
    *,
    user_id: str,
    scenario_id: str,
) -> dict[str, Any] | None:
    sessoes = listar_sessoes_cenario_usuario(
        user_id,
        status="active",
        scenario_id=scenario_id,
    )
    return sessoes[0] if sessoes else None


def marcar_sessao_cenario_reiniciada(
    *,
    scenario_session_id: str,
    user_id: str,
) -> bool:
    sessao = obter_sessao_cenario(scenario_session_id)
    if sessao is None:
        return False
    if _texto(sessao.get("user_id")) != _texto(user_id):
        raise ValueError("A sessão narrativa não pertence ao usuário atual.")
    return atualizar_registro(
        SCENARIO_SESSIONS_SHEET,
        coluna_chave="scenario_session_id",
        valor_chave=scenario_session_id,
        alteracoes={
            "status": "restarted",
            "updated_at": utc_now_iso(),
        },
    )


__all__ = [
    "SCENARIO_SESSIONS_SHEET",
    "listar_sessoes_cenario_usuario",
    "marcar_sessao_cenario_reiniciada",
    "montar_registro_sessao_cenario",
    "obter_sessao_ativa_mais_recente",
    "obter_sessao_cenario",
    "salvar_instancia_cenario",
]
