from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from repositories.scenario_session_repository import (
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


def _normalizar_texto(
    valor: Any,
) -> str:
    return str(
        valor or ""
    ).strip()


def _normalizar_user_id(
    user_id: str,
) -> str:
    user_id = _normalizar_texto(
        user_id
    )

    if not user_id:
        raise ValueError(
            "O usuário não foi identificado."
        )

    return user_id


def _normalizar_ids_desbloqueados(
    scenario_ids: Iterable[str] | None,
) -> set[str]:
    if scenario_ids is None:
        return set()

    return {
        scenario_id_normalizado
        for scenario_id in scenario_ids
        if (
            scenario_id_normalizado := _normalizar_texto(
                scenario_id
            )
        )
    }


def avaliar_acesso_cenario(
    *,
    cenario: dict[str, Any],
    unlocked_scenario_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Calcula o estado de acesso de um card."""

    if not isinstance(cenario, dict):
        raise ValueError(
            "Os dados do cenário são inválidos."
        )

    scenario_id = _normalizar_texto(
        cenario.get("scenario_id")
    )

    if not scenario_id:
        raise ValueError(
            "O cenário não possui scenario_id."
        )

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
    """Retorna o catálogo já enriquecido com o acesso do usuário."""

    _normalizar_user_id(user_id)
    cenarios = listar_cenarios_disponiveis()
    resultado: list[dict[str, Any]] = []

    for cenario in cenarios:
        acesso = avaliar_acesso_cenario(
            cenario=cenario,
            unlocked_scenario_ids=unlocked_scenario_ids,
        )
        item = deepcopy(cenario)
        item.update(acesso)
        resultado.append(item)

    return resultado


def obter_cenario_para_usuario(
    *,
    user_id: str,
    scenario_id: str,
    unlocked_scenario_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Carrega um cenário e inclui o resultado da autorização."""

    _normalizar_user_id(user_id)
    scenario_id = _normalizar_texto(scenario_id)

    if not scenario_id:
        raise ValueError(
            "O cenário não foi informado."
        )

    pacote = obter_cenario(scenario_id)
    config = pacote.get("config")

    if not isinstance(config, dict):
        raise ValueError(
            "A configuração do cenário é inválida."
        )

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
    """Autoriza, cria e persiste uma nova sessão narrativa."""

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


__all__ = [
    "ACCESS_STATUS_FREE",
    "ACCESS_STATUS_LOCKED",
    "ACCESS_STATUS_UNAVAILABLE",
    "ACCESS_STATUS_UNLOCKED",
    "ScenarioAccessError",
    "avaliar_acesso_cenario",
    "iniciar_cenario_para_usuario",
    "listar_cenarios_para_usuario",
    "obter_cenario_para_usuario",
]
