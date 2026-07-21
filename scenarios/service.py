from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from repositories.interaction_repository import (
    listar_interacoes_sessao_cenario,
)
from repositories.scenario_session_repository import (
    listar_sessoes_cenario_usuario,
    marcar_sessao_cenario_reiniciada,
    obter_sessao_ativa_mais_recente,
    obter_sessao_cenario,
    salvar_instancia_cenario,
)
from scenarios.registry import (
    iniciar_instancia_cenario,
    listar_cenarios_disponiveis,
    obter_cenario,
)
from scenarios.schema import (
    ACCESS_TYPE_FREE,
    ACCESS_TYPE_PAID,
)

ACCESS_STATUS_FREE = "free"
ACCESS_STATUS_UNLOCKED = "unlocked"
ACCESS_STATUS_LOCKED = "locked"
ACCESS_STATUS_UNAVAILABLE = "unavailable"


class ScenarioAccessError(PermissionError):
    """O usuário não possui acesso à historinha solicitada."""


def _normalizar_texto(valor: Any) -> str:
    return str(valor or "").strip()


def _normalizar_user_id(user_id: str) -> str:
    user_id = _normalizar_texto(user_id)
    if not user_id:
        raise ValueError("O usuário não foi identificado.")
    return user_id


def _normalizar_ids_desbloqueados(
    scenario_ids: Iterable[str] | None,
) -> set[str]:
    if scenario_ids is None:
        return set()
    return {
        normalizado
        for scenario_id in scenario_ids
        if (normalizado := _normalizar_texto(scenario_id))
    }


def avaliar_acesso_cenario(
    *,
    cenario: dict[str, Any],
    unlocked_scenario_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(cenario, dict):
        raise ValueError("Os dados do cenário são inválidos.")

    scenario_id = _normalizar_texto(cenario.get("scenario_id"))
    if not scenario_id:
        raise ValueError("O cenário não possui scenario_id.")

    commerce = cenario.get("commerce")
    if not isinstance(commerce, dict):
        commerce = {}

    access_type = _normalizar_texto(
        commerce.get("access_type")
        or cenario.get("access_type")
        or ACCESS_TYPE_PAID
    ).lower()
    price_cents = int(
        commerce.get(
            "price_cents",
            cenario.get("price_cents", 0),
        )
        or 0
    )
    currency = _normalizar_texto(
        commerce.get("currency")
        or cenario.get("currency")
        or "BRL"
    ).upper()
    product_id = _normalizar_texto(
        commerce.get("product_id")
        or cenario.get("product_id")
    )
    unlocked_ids = _normalizar_ids_desbloqueados(
        unlocked_scenario_ids
    )

    if access_type == ACCESS_TYPE_FREE:
        return {
            "allowed": True,
            "access_status": ACCESS_STATUS_FREE,
            "access_reason": "free_scenario",
            "access_type": ACCESS_TYPE_FREE,
            "price_cents": 0,
            "currency": currency,
            "product_id": "",
        }
    if access_type != ACCESS_TYPE_PAID:
        return {
            "allowed": False,
            "access_status": ACCESS_STATUS_UNAVAILABLE,
            "access_reason": "invalid_access_type",
            "access_type": access_type,
            "price_cents": price_cents,
            "currency": currency,
            "product_id": product_id,
        }
    if scenario_id in unlocked_ids:
        return {
            "allowed": True,
            "access_status": ACCESS_STATUS_UNLOCKED,
            "access_reason": "user_entitlement",
            "access_type": ACCESS_TYPE_PAID,
            "price_cents": price_cents,
            "currency": currency,
            "product_id": product_id,
        }
    return {
        "allowed": False,
        "access_status": ACCESS_STATUS_LOCKED,
        "access_reason": "purchase_required",
        "access_type": ACCESS_TYPE_PAID,
        "price_cents": price_cents,
        "currency": currency,
        "product_id": product_id,
    }


def listar_cenarios_para_usuario(
    *,
    user_id: str,
    unlocked_scenario_ids: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    user_id = _normalizar_user_id(user_id)
    cenarios = listar_cenarios_disponiveis()
    resultado: list[dict[str, Any]] = []

    for cenario in cenarios:
        acesso = avaliar_acesso_cenario(
            cenario=cenario,
            unlocked_scenario_ids=unlocked_scenario_ids,
        )
        item = deepcopy(cenario)
        item.update(acesso)

        scenario_id = _normalizar_texto(
            item.get("scenario_id")
        )
        sessao_ativa = obter_sessao_ativa_mais_recente(
            user_id=user_id,
            scenario_id=scenario_id,
        )
        item["active_session"] = deepcopy(sessao_ativa)
        item["can_continue"] = bool(
            sessao_ativa and acesso.get("allowed")
        )
        if sessao_ativa:
            item["interaction_count"] = int(
                sessao_ativa.get("interaction_count", 0) or 0
            )
            item["last_interaction_at"] = _normalizar_texto(
                sessao_ativa.get("last_interaction_at")
                or sessao_ativa.get("updated_at")
            )
        resultado.append(item)

    return resultado


def listar_historias_iniciadas_usuario(
    *,
    user_id: str,
    status: str | None = None,
) -> list[dict[str, Any]]:
    user_id = _normalizar_user_id(user_id)
    sessoes = listar_sessoes_cenario_usuario(
        user_id,
        status=status,
    )
    catalogo = {
        _normalizar_texto(item.get("scenario_id")): item
        for item in listar_cenarios_disponiveis()
    }
    resultado: list[dict[str, Any]] = []

    for sessao in sessoes:
        scenario_id = _normalizar_texto(sessao.get("scenario_id"))
        cenario = catalogo.get(scenario_id, {})
        item = deepcopy(sessao)
        item["title"] = (
            _normalizar_texto(cenario.get("title"))
            or scenario_id
        )
        item["short_description"] = _normalizar_texto(
            cenario.get("short_description")
        )
        item["card"] = deepcopy(
            cenario.get("card")
            if isinstance(cenario.get("card"), dict)
            else {}
        )
        item["duration"] = deepcopy(
            cenario.get("duration")
            if isinstance(cenario.get("duration"), dict)
            else {}
        )
        item["scenario_available"] = bool(cenario)
        item["can_continue"] = (
            _normalizar_texto(sessao.get("status")).lower()
            == "active"
            and bool(cenario)
        )
        resultado.append(item)
    return resultado


def obter_cenario_para_usuario(
    *,
    user_id: str,
    scenario_id: str,
    unlocked_scenario_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    _normalizar_user_id(user_id)
    scenario_id = _normalizar_texto(scenario_id)
    if not scenario_id:
        raise ValueError("O cenário não foi informado.")

    pacote = obter_cenario(scenario_id)
    config = pacote.get("config")
    if not isinstance(config, dict):
        raise ValueError("A configuração do cenário é inválida.")

    acesso = avaliar_acesso_cenario(
        cenario=config,
        unlocked_scenario_ids=unlocked_scenario_ids,
    )
    resultado = deepcopy(pacote)
    resultado["access"] = acesso
    return resultado


def iniciar_cenario_para_usuario(
    *,
    user_id: str,
    scenario_id: str,
    unlocked_scenario_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    user_id = _normalizar_user_id(user_id)
    pacote_usuario = obter_cenario_para_usuario(
        user_id=user_id,
        scenario_id=scenario_id,
        unlocked_scenario_ids=unlocked_scenario_ids,
    )
    acesso = pacote_usuario["access"]
    if not bool(acesso.get("allowed", False)):
        raise ScenarioAccessError(
            "Esta historinha precisa ser desbloqueada antes de iniciar."
        )

    instancia = iniciar_instancia_cenario(
        scenario_id=scenario_id,
        user_id=user_id,
    )
    instancia["access_status"] = acesso["access_status"]
    instancia["access_reason"] = acesso["access_reason"]
    salvar_instancia_cenario(instancia)
    return instancia


def continuar_cenario_para_usuario(
    *,
    user_id: str,
    scenario_session_id: str,
    unlocked_scenario_ids: Iterable[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    user_id = _normalizar_user_id(user_id)
    sessao = obter_sessao_cenario(scenario_session_id)
    if sessao is None:
        raise ValueError("A sessão narrativa não foi encontrada.")
    if _normalizar_texto(sessao.get("user_id")) != user_id:
        raise ValueError("A sessão narrativa não pertence ao usuário atual.")
    if _normalizar_texto(sessao.get("status")).lower() != "active":
        raise ValueError("Esta sessão narrativa não está ativa.")

    scenario_id = _normalizar_texto(sessao.get("scenario_id"))
    pacote_usuario = obter_cenario_para_usuario(
        user_id=user_id,
        scenario_id=scenario_id,
        unlocked_scenario_ids=unlocked_scenario_ids,
    )
    acesso = pacote_usuario["access"]
    if not bool(acesso.get("allowed", False)):
        raise ScenarioAccessError(
            "Esta historinha não está disponível para esta conta."
        )

    instancia = iniciar_instancia_cenario(
        scenario_id=scenario_id,
        user_id=user_id,
    )
    for campo in (
        "scenario_session_id", "scenario_version", "created_at",
        "updated_at", "last_interaction_at", "completed_at", "status",
        "interaction_count", "opening_sent", "current_phase",
        "current_route", "current_beat", "active_hook",
        "climax_reached", "satisfaction_detected", "ending_ready",
        "ending_sent", "ending_type", "ending_reason", "input_locked",
        "show_return_to_menu", "summary",
    ):
        if campo in sessao:
            instancia[campo] = deepcopy(sessao[campo])

    if isinstance(sessao.get("scene_state"), dict):
        instancia["scene_state"] = deepcopy(sessao["scene_state"])
    if isinstance(sessao.get("story_progress"), dict):
        instancia["story_progress"] = deepcopy(
            sessao["story_progress"]
        )

    instancia["access_status"] = acesso["access_status"]
    instancia["access_reason"] = acesso["access_reason"]

    interacoes = listar_interacoes_sessao_cenario(
        user_id=user_id,
        scenario_session_id=scenario_session_id,
        limite=100,
    )
    mensagens: list[dict[str, Any]] = []
    for interacao in interacoes:
        if _normalizar_texto(interacao.get("error")):
            continue
        texto_usuario = _normalizar_texto(interacao.get("user_text"))
        resposta_mary = _normalizar_texto(
            interacao.get("mary_response")
        )
        if texto_usuario:
            mensagens.append({"role": "user", "content": texto_usuario})
        if resposta_mary:
            mensagens.append(
                {"role": "assistant", "content": resposta_mary}
            )

    return instancia, mensagens


def reiniciar_cenario_para_usuario(
    *,
    user_id: str,
    scenario_session_id: str,
) -> None:
    user_id = _normalizar_user_id(user_id)
    marcar_sessao_cenario_reiniciada(
        scenario_session_id=scenario_session_id,
        user_id=user_id,
    )


__all__ = [
    "ACCESS_STATUS_FREE",
    "ACCESS_STATUS_LOCKED",
    "ACCESS_STATUS_UNAVAILABLE",
    "ACCESS_STATUS_UNLOCKED",
    "ScenarioAccessError",
    "avaliar_acesso_cenario",
    "continuar_cenario_para_usuario",
    "iniciar_cenario_para_usuario",
    "listar_cenarios_para_usuario",
    "listar_historias_iniciadas_usuario",
    "obter_cenario_para_usuario",
    "reiniciar_cenario_para_usuario",
]
