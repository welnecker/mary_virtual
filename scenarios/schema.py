from __future__ import annotations

from copy import deepcopy
from typing import Any


SCENARIO_STATUS_ACTIVE = "active"
SCENARIO_STATUS_INACTIVE = "inactive"

ACCESS_TYPE_FREE = "free"
ACCESS_TYPE_PAID = "paid"

DEFAULT_TARGET_INTERACTIONS = 48
DEFAULT_SOFT_ENDING_START = 40
DEFAULT_HARD_ENDING_LIMIT = 58
DEFAULT_ENDING_TURNS = 2

REQUIRED_CONFIG_FIELDS = {
    "scenario_id",
    "scenario_version",
    "category",
    "title",
    "short_description",
    "adult_only",
    "status",
    "roles",
    "opening_message",
    "initial_state",
    "initial_scene_state",
    "phases",
    "card",
    "duration",
    "commerce",
}

REQUIRED_ROLE_FIELDS = {
    "mary",
    "user",
}

REQUIRED_CARD_FIELDS = {
    "title",
    "subtitle",
    "image",
    "badge",
    "button_label_free",
    "button_label_locked",
    "button_label_unlocked",
}

REQUIRED_DURATION_FIELDS = {
    "target_interactions",
    "soft_ending_start",
    "hard_ending_limit",
    "ending_turns",
}

REQUIRED_COMMERCE_FIELDS = {
    "access_type",
    "price_cents",
    "currency",
    "product_id",
}

REQUIRED_PHASES = {
    "opening",
    "familiarity",
    "tension",
    "intimacy",
    "climax",
    "aftercare",
    "ending",
}


class ScenarioConfigError(ValueError):
    """Erro de configuração de uma historinha."""


def _normalizar_texto(
    valor: Any,
) -> str:
    return str(
        valor or ""
    ).strip()


def _normalizar_inteiro(
    valor: Any,
    *,
    campo: str,
    minimo: int | None = None,
) -> int:
    try:
        numero = int(
            valor
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ScenarioConfigError(
            f"O campo {campo!r} deve ser um número inteiro."
        ) from exc

    if (
        minimo is not None
        and numero < minimo
    ):
        raise ScenarioConfigError(
            f"O campo {campo!r} deve ser maior ou igual a {minimo}."
        )

    return numero


def _exigir_dict(
    valor: Any,
    *,
    campo: str,
) -> dict[str, Any]:
    if not isinstance(
        valor,
        dict,
    ):
        raise ScenarioConfigError(
            f"O campo {campo!r} deve ser um dicionário."
        )

    return valor


def _validar_campos_obrigatorios(
    dados: dict[str, Any],
    campos: set[str],
    *,
    contexto: str,
) -> None:
    ausentes = campos - set(
        dados
    )

    if not ausentes:
        return

    raise ScenarioConfigError(
        f"Campos obrigatórios ausentes em {contexto}: "
        + ", ".join(
            sorted(
                ausentes
            )
        )
    )


def normalizar_duration(
    duration: dict[str, Any] | None,
) -> dict[str, int]:
    duration = deepcopy(
        duration
        if isinstance(
            duration,
            dict,
        )
        else {}
    )

    target = _normalizar_inteiro(
        duration.get(
            "target_interactions",
            DEFAULT_TARGET_INTERACTIONS,
        ),
        campo="duration.target_interactions",
        minimo=1,
    )

    soft_start = _normalizar_inteiro(
        duration.get(
            "soft_ending_start",
            DEFAULT_SOFT_ENDING_START,
        ),
        campo="duration.soft_ending_start",
        minimo=1,
    )

    hard_limit = _normalizar_inteiro(
        duration.get(
            "hard_ending_limit",
            DEFAULT_HARD_ENDING_LIMIT,
        ),
        campo="duration.hard_ending_limit",
        minimo=1,
    )

    ending_turns = _normalizar_inteiro(
        duration.get(
            "ending_turns",
            DEFAULT_ENDING_TURNS,
        ),
        campo="duration.ending_turns",
        minimo=1,
    )

    if soft_start > target:
        raise ScenarioConfigError(
            "duration.soft_ending_start não pode ser maior que "
            "duration.target_interactions."
        )

    if hard_limit < target:
        raise ScenarioConfigError(
            "duration.hard_ending_limit não pode ser menor que "
            "duration.target_interactions."
        )

    return {
        "target_interactions": target,
        "soft_ending_start": soft_start,
        "hard_ending_limit": hard_limit,
        "ending_turns": ending_turns,
    }


def normalizar_card(
    card: dict[str, Any] | None,
    *,
    fallback_title: str,
) -> dict[str, str]:
    card = deepcopy(
        card
        if isinstance(
            card,
            dict,
        )
        else {}
    )

    title = _normalizar_texto(
        card.get(
            "title"
        )
    ) or fallback_title

    return {
        "title": title,
        "subtitle": _normalizar_texto(
            card.get(
                "subtitle"
            )
        ),
        "image": _normalizar_texto(
            card.get(
                "image"
            )
        ),
        "badge": _normalizar_texto(
            card.get(
                "badge"
            )
        ),
        "button_label_free": (
            _normalizar_texto(
                card.get(
                    "button_label_free"
                )
            )
            or "Jogar gratuitamente"
        ),
        "button_label_locked": (
            _normalizar_texto(
                card.get(
                    "button_label_locked"
                )
            )
            or "Desbloquear"
        ),
        "button_label_unlocked": (
            _normalizar_texto(
                card.get(
                    "button_label_unlocked"
                )
            )
            or "Jogar"
        ),
    }


def normalizar_commerce(
    commerce: dict[str, Any] | None,
) -> dict[str, Any]:
    commerce = deepcopy(
        commerce
        if isinstance(
            commerce,
            dict,
        )
        else {}
    )

    access_type = _normalizar_texto(
        commerce.get(
            "access_type",
            ACCESS_TYPE_PAID,
        )
    ).lower()

    if access_type not in {
        ACCESS_TYPE_FREE,
        ACCESS_TYPE_PAID,
    }:
        raise ScenarioConfigError(
            "commerce.access_type deve ser 'free' ou 'paid'."
        )

    price_cents = _normalizar_inteiro(
        commerce.get(
            "price_cents",
            0,
        ),
        campo="commerce.price_cents",
        minimo=0,
    )

    currency = (
        _normalizar_texto(
            commerce.get(
                "currency",
                "BRL",
            )
        )
        or "BRL"
    ).upper()

    product_id = _normalizar_texto(
        commerce.get(
            "product_id"
        )
    )

    if access_type == ACCESS_TYPE_FREE:
        price_cents = 0
        product_id = ""

    elif price_cents <= 0:
        raise ScenarioConfigError(
            "Uma historinha paga deve possuir commerce.price_cents maior que zero."
        )

    return {
        "access_type": access_type,
        "price_cents": price_cents,
        "currency": currency,
        "product_id": product_id,
    }


def validar_config_cenario(
    config: dict[str, Any],
) -> None:
    config = _exigir_dict(
        config,
        campo="config",
    )

    _validar_campos_obrigatorios(
        config,
        REQUIRED_CONFIG_FIELDS,
        contexto="SCENARIO_CONFIG",
    )

    scenario_id = _normalizar_texto(
        config.get(
            "scenario_id"
        )
    )

    if not scenario_id:
        raise ScenarioConfigError(
            "scenario_id não pode ficar vazio."
        )

    if " " in scenario_id:
        raise ScenarioConfigError(
            "scenario_id não pode conter espaços."
        )

    _normalizar_inteiro(
        config.get(
            "scenario_version"
        ),
        campo="scenario_version",
        minimo=1,
    )

    for campo in (
        "category",
        "title",
        "short_description",
        "opening_message",
    ):
        if not _normalizar_texto(
            config.get(
                campo
            )
        ):
            raise ScenarioConfigError(
                f"O campo {campo!r} não pode ficar vazio."
            )

    status = _normalizar_texto(
        config.get(
            "status"
        )
    ).lower()

    if status not in {
        SCENARIO_STATUS_ACTIVE,
        SCENARIO_STATUS_INACTIVE,
    }:
        raise ScenarioConfigError(
            "status deve ser 'active' ou 'inactive'."
        )

    roles = _exigir_dict(
        config.get(
            "roles"
        ),
        campo="roles",
    )

    _validar_campos_obrigatorios(
        roles,
        REQUIRED_ROLE_FIELDS,
        contexto="roles",
    )

    for role_name in REQUIRED_ROLE_FIELDS:
        if not _normalizar_texto(
            roles.get(
                role_name
            )
        ):
            raise ScenarioConfigError(
                f"roles.{role_name} não pode ficar vazio."
            )

    initial_state = _exigir_dict(
        config.get(
            "initial_state"
        ),
        campo="initial_state",
    )

    initial_scene_state = _exigir_dict(
        config.get(
            "initial_scene_state"
        ),
        campo="initial_scene_state",
    )

    phases = _exigir_dict(
        config.get(
            "phases"
        ),
        campo="phases",
    )

    missing_phases = REQUIRED_PHASES - set(
        phases
    )

    if missing_phases:
        raise ScenarioConfigError(
            "Fases obrigatórias ausentes: "
            + ", ".join(
                sorted(
                    missing_phases
                )
            )
        )

    for phase_name in REQUIRED_PHASES:
        phase = _exigir_dict(
            phases.get(
                phase_name
            ),
            campo=(
                "phases."
                + phase_name
            ),
        )

        if not _normalizar_texto(
            phase.get(
                "objective"
            )
        ):
            raise ScenarioConfigError(
                f"phases.{phase_name}.objective não pode ficar vazio."
            )

    card = _exigir_dict(
        config.get(
            "card"
        ),
        campo="card",
    )

    _validar_campos_obrigatorios(
        card,
        REQUIRED_CARD_FIELDS,
        contexto="card",
    )

    duration = _exigir_dict(
        config.get(
            "duration"
        ),
        campo="duration",
    )

    _validar_campos_obrigatorios(
        duration,
        REQUIRED_DURATION_FIELDS,
        contexto="duration",
    )

    commerce = _exigir_dict(
        config.get(
            "commerce"
        ),
        campo="commerce",
    )

    _validar_campos_obrigatorios(
        commerce,
        REQUIRED_COMMERCE_FIELDS,
        contexto="commerce",
    )

    normalizar_duration(
        duration
    )

    normalizar_card(
        card,
        fallback_title=_normalizar_texto(
            config.get(
                "title"
            )
        ),
    )

    normalizar_commerce(
        commerce
    )

    if not isinstance(
        initial_state.get(
            "interaction_count",
            0,
        ),
        int,
    ):
        raise ScenarioConfigError(
            "initial_state.interaction_count deve ser inteiro."
        )

    if not isinstance(
        initial_scene_state.get(
            "scene_active",
            True,
        ),
        bool,
    ):
        raise ScenarioConfigError(
            "initial_scene_state.scene_active deve ser booleano."
        )


def normalizar_config_cenario(
    config: dict[str, Any],
) -> dict[str, Any]:
    validar_config_cenario(
        config
    )

    result = deepcopy(
        config
    )

    result[
        "scenario_id"
    ] = _normalizar_texto(
        result.get(
            "scenario_id"
        )
    )

    result[
        "scenario_version"
    ] = int(
        result.get(
            "scenario_version",
            1,
        )
        or 1
    )

    result[
        "category"
    ] = _normalizar_texto(
        result.get(
            "category"
        )
    )

    result[
        "title"
    ] = _normalizar_texto(
        result.get(
            "title"
        )
    )

    result[
        "short_description"
    ] = _normalizar_texto(
        result.get(
            "short_description"
        )
    )

    result[
        "status"
    ] = _normalizar_texto(
        result.get(
            "status"
        )
    ).lower()

    result[
        "adult_only"
    ] = bool(
        result.get(
            "adult_only",
            True,
        )
    )

    result[
        "display_order"
    ] = _normalizar_inteiro(
        result.get(
            "display_order",
            999,
        ),
        campo="display_order",
        minimo=0,
    )

    result[
        "card"
    ] = normalizar_card(
        result.get(
            "card"
        ),
        fallback_title=result[
            "title"
        ],
    )

    result[
        "duration"
    ] = normalizar_duration(
        result.get(
            "duration"
        )
    )

    result[
        "commerce"
    ] = normalizar_commerce(
        result.get(
            "commerce"
        )
    )

    # Campo temporário para manter compatibilidade com o registry atual.
    result[
        "max_interactions"
    ] = result[
        "duration"
    ][
        "hard_ending_limit"
    ]

    return result


__all__ = [
    "ACCESS_TYPE_FREE",
    "ACCESS_TYPE_PAID",
    "DEFAULT_ENDING_TURNS",
    "DEFAULT_HARD_ENDING_LIMIT",
    "DEFAULT_SOFT_ENDING_START",
    "DEFAULT_TARGET_INTERACTIONS",
    "REQUIRED_CONFIG_FIELDS",
    "SCENARIO_STATUS_ACTIVE",
    "SCENARIO_STATUS_INACTIVE",
    "ScenarioConfigError",
    "normalizar_card",
    "normalizar_commerce",
    "normalizar_config_cenario",
    "normalizar_duration",
    "validar_config_cenario",
]
