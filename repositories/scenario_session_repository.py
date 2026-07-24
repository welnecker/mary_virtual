from __future__ import annotations

import hashlib
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
        return int(float(valor if valor not in (None, "") else padrao))
    except (TypeError, ValueError):
        return padrao


def _booleano(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return bool(valor)
    return _texto(valor).lower() in {
        "true", "1", "sim", "yes", "verdadeiro", "active", "ativo"
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


def _desserializar_lista(valor: Any) -> list[Any]:
    if isinstance(valor, list):
        return list(valor)
    texto = _texto(valor)
    if not texto:
        return []
    try:
        resultado = json.loads(texto)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return resultado if isinstance(resultado, list) else []


def _normalizar_lista_ids(valor: Any) -> list[str]:
    itens = valor if isinstance(valor, list) else _desserializar_lista(valor)
    resultado: list[str] = []
    vistos: set[str] = set()
    for item in itens:
        texto = _texto(item)
        if not texto or texto in vistos:
            continue
        vistos.add(texto)
        resultado.append(texto)
    return resultado


def _checksum_estado(*partes: str) -> str:
    payload = "\n".join(partes).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _hidratar_registro_sessao(
    registro: dict[str, Any],
) -> dict[str, Any]:
    resultado = dict(registro)
    resultado["scenario_version"] = max(
        1, _inteiro(resultado.get("scenario_version"), 1)
    )
    resultado["interaction_count"] = max(
        0, _inteiro(resultado.get("interaction_count"), 0)
    )
    resultado["chapter_number"] = max(
        1, _inteiro(resultado.get("chapter_number"), 1)
    )
    resultado["save_revision"] = max(
        1, _inteiro(resultado.get("save_revision"), 1)
    )
    for campo in (
        "opening_sent", "climax_reached", "satisfaction_detected",
        "ending_ready", "ending_sent", "input_locked",
        "show_return_to_menu", "active",
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
    resultado["history_session_ids"] = _normalizar_lista_ids(
        resultado.get("history_session_ids_json")
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

    status = _texto(instancia.get("status")) or "active"
    ending_sent = _booleano(instancia.get("ending_sent"))
    completed = status.lower() == "completed" or ending_sent
    completed_at = _texto(instancia.get("completed_at"))
    if completed and not completed_at:
        completed_at = agora

    chapter_number = max(
        1,
        _inteiro(
            instancia.get("chapter_number")
            or story_progress.get("chapter_number"),
            1,
        ),
    )
    parent_session_id = _texto(
        instancia.get("parent_session_id")
        or story_progress.get("parent_session_id")
    )
    root_session_id = _texto(
        instancia.get("root_session_id")
        or story_progress.get("root_session_id")
    )
    if not root_session_id:
        root_session_id = parent_session_id or scenario_session_id
    continuation_mode = _texto(
        instancia.get("continuation_mode")
        or story_progress.get("continuation_mode")
    )
    history_session_ids = _normalizar_lista_ids(
        instancia.get("history_session_ids")
        or story_progress.get("history_session_ids")
    )
    if parent_session_id and parent_session_id not in history_session_ids:
        history_session_ids.append(parent_session_id)

    scene_state_json = serializar_json(scene_state)
    story_progress_json = serializar_json(story_progress)
    relationship_state_json = serializar_json(relationship_state)

    return {
        "scenario_session_id": scenario_session_id,
        "user_id": user_id,
        "scenario_id": scenario_id,
        "scenario_version": max(
            1, _inteiro(instancia.get("scenario_version"), 1)
        ),
        "created_at": created_at,
        "updated_at": agora,
        "last_interaction_at": last_interaction_at,
        "completed_at": completed_at,
        "status": "completed" if completed else status,
        "interaction_count": max(
            0, _inteiro(instancia.get("interaction_count"), 0)
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
        "ending_sent": ending_sent,
        "ending_type": _texto(instancia.get("ending_type")),
        "ending_reason": _texto(instancia.get("ending_reason")),
        "input_locked": _booleano(instancia.get("input_locked")),
        "show_return_to_menu": _booleano(
            instancia.get("show_return_to_menu")
        ),
        "scene_state_json": scene_state_json,
        "story_progress_json": story_progress_json,
        "relationship_state_json": relationship_state_json,
        "summary": _texto(instancia.get("summary")),
        "chapter_number": chapter_number,
        "parent_session_id": parent_session_id,
        "root_session_id": root_session_id,
        "continuation_mode": continuation_mode,
        "history_session_ids_json": serializar_json(history_session_ids),
        "state_checksum": _checksum_estado(
            scene_state_json,
            story_progress_json,
            relationship_state_json,
        ),
        "active": not completed and status.lower() == "active",
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
    revisao_atual = (
        max(0, _inteiro(existente.get("save_revision"), 0))
        if isinstance(existente, dict)
        else 0
    )
    registro["save_revision"] = revisao_atual + 1

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

    for campo in (
        "updated_at", "last_interaction_at", "completed_at", "status",
        "chapter_number", "parent_session_id", "root_session_id",
        "continuation_mode", "state_checksum", "save_revision", "active",
    ):
        instancia[campo] = registro.get(campo)
    instancia["history_session_ids"] = _normalizar_lista_ids(
        registro.get("history_session_ids_json")
    )
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
            _texto(item.get("last_interaction_at") or item.get("updated_at")),
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
    for sessao in sessoes:
        if sessao.get("active", True):
            return sessao
    return None


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
    agora = utc_now_iso()
    return atualizar_registro(
        SCENARIO_SESSIONS_SHEET,
        coluna_chave="scenario_session_id",
        valor_chave=scenario_session_id,
        alteracoes={
            "status": "restarted",
            "active": False,
            "updated_at": agora,
            "completed_at": _texto(sessao.get("completed_at")) or agora,
            "ending_reason": _texto(sessao.get("ending_reason")) or "restarted",
            "save_revision": max(1, _inteiro(sessao.get("save_revision"), 1)) + 1,
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
