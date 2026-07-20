from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from scenarios.vizinha import (
    SCENARIO_ID as VIZINHA_SCENARIO_ID,
    obter_configuracao_vizinha,
    obter_prompt_vizinha,
)


def utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


SCENARIO_LOADERS = {
    VIZINHA_SCENARIO_ID: {
        "config_loader": obter_configuracao_vizinha,
        "prompt_loader": obter_prompt_vizinha,
    },
}


def listar_cenarios_disponiveis() -> list[dict[str, Any]]:
    cenarios: list[dict[str, Any]] = []

    for scenario_id, loaders in SCENARIO_LOADERS.items():
        config = loaders[
            "config_loader"
        ]()

        cenarios.append(
            {
                "scenario_id": scenario_id,
                "title": config.get(
                    "title",
                    scenario_id,
                ),
                "short_description": config.get(
                    "short_description",
                    "",
                ),
                "category": config.get(
                    "category",
                    "",
                ),
                "adult_only": bool(
                    config.get(
                        "adult_only",
                        False,
                    )
                ),
            }
        )

    return cenarios


def obter_cenario(
    scenario_id: str,
) -> dict[str, Any]:
    scenario_id = str(
        scenario_id or ""
    ).strip()

    loaders = SCENARIO_LOADERS.get(
        scenario_id
    )

    if loaders is None:
        raise ValueError(
            f"Cenário desconhecido: {scenario_id!r}."
        )

    config = loaders[
        "config_loader"
    ]()

    prompt = loaders[
        "prompt_loader"
    ]()

    return {
        "config": config,
        "prompt": prompt,
    }


def iniciar_instancia_cenario(
    *,
    scenario_id: str,
    user_id: str,
) -> dict[str, Any]:
    pacote = obter_cenario(
        scenario_id
    )

    config = pacote["config"]

    scene_state = deepcopy(
        config.get(
            "initial_scene_state",
            {},
        )
    )

    agora = utc_now_iso()

    return {
        "scenario_session_id": (
            f"scn_{uuid4().hex}"
        ),
        "user_id": str(
            user_id or ""
        ).strip(),
        "scenario_id": scenario_id,
        "created_at": agora,
        "updated_at": agora,
        "status": "active",
        "opening_sent": False,
        "interaction_count": 0,
        "scenario_config": config,
        "scenario_prompt": pacote[
            "prompt"
        ],
        "scene_state": scene_state,
    }
