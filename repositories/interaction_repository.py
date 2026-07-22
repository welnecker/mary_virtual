from __future__ import annotations

from typing import Any

import streamlit as st

from google_sheets_repository import (
    INTERACTIONS_SHEET,
    atualizar_registro,
    buscar_registro,
    obter_cabecalhos,
    obter_registros_aba,
    salvar_interacao as salvar_interacao_base,
)
from repositories.scenario_session_repository import (
    salvar_instancia_cenario,
)

MAX_SCENARIO_INTERACTIONS = 50

SCENARIO_INTERACTION_COLUMNS = (
    "interaction_key",
    "scenario_id",
    "scenario_session_id",
    "user_id",
    "interaction_number",
)


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _inteiro(
    valor: Any,
    padrao: int = 0,
) -> int:
    try:
        return int(valor or padrao)
    except (TypeError, ValueError):
        return padrao


def montar_interaction_key(
    *,
    scenario_session_id: str,
    interaction_number: int,
) -> str:
    scenario_session_id = _texto(
        scenario_session_id
    )
    interaction_number = _inteiro(
        interaction_number
    )

    if (
        not scenario_session_id
        or interaction_number < 1
        or interaction_number
        > MAX_SCENARIO_INTERACTIONS
    ):
        return ""

    return (
        f"{scenario_session_id}:"
        f"{interaction_number:02d}"
    )


def _obter_instancia_cenario(
    *,
    user_id: str,
) -> dict[str, Any] | None:
    instancia = st.session_state.get(
        "scenario_instance"
    )

    if not isinstance(instancia, dict):
        return None

    scenario_user_id = _texto(
        instancia.get("user_id")
    )
    user_id = _texto(user_id)

    if (
        scenario_user_id
        and scenario_user_id != user_id
    ):
        return None

    return instancia


def _obter_contexto_cenario(
    *,
    user_id: str,
) -> tuple[str, str]:
    instancia = _obter_instancia_cenario(
        user_id=user_id
    )

    if instancia is None:
        return "", ""

    return (
        _texto(instancia.get("scenario_id")),
        _texto(
            instancia.get(
                "scenario_session_id"
            )
        ),
    )


def listar_interacoes_sessao_cenario(
    *,
    user_id: str,
    scenario_session_id: str,
    limite: int = 100,
) -> list[dict[str, Any]]:
    user_id = _texto(user_id)
    scenario_session_id = _texto(
        scenario_session_id
    )

    if not user_id or not scenario_session_id:
        return []

    registros = obter_registros_aba(
        INTERACTIONS_SHEET
    )

    resultado = [
        dict(registro)
        for registro in registros
        if (
            _texto(
                registro.get("user_id")
            ) == user_id
            and _texto(
                registro.get(
                    "scenario_session_id"
                )
            ) == scenario_session_id
        )
    ]

    resultado.sort(
        key=lambda registro: (
            _inteiro(
                registro.get(
                    "interaction_number"
                )
            ),
            _texto(
                registro.get("timestamp")
            ),
        )
    )

    limite = max(
        1,
        int(limite or 100),
    )

    return resultado[-limite:]


def contar_interacoes_sessao_cenario(
    *,
    user_id: str,
    scenario_session_id: str,
) -> int:
    return len(
        [
            registro
            for registro
            in listar_interacoes_sessao_cenario(
                user_id=user_id,
                scenario_session_id=(
                    scenario_session_id
                ),
                limite=MAX_SCENARIO_INTERACTIONS,
            )
            if not _texto(
                registro.get("error")
            )
        ]
    )


def salvar_interacao(
    *,
    interaction_id: str,
    session_id: str,
    user_id: str,
    timestamp: str,
    user_text: str,
    mary_response: str,
    model: str,
    prompt_version: str,
    response_time_ms: int | None,
    image_sent: bool,
    image_width: int | None,
    image_height: int | None,
    image_size_bytes: int | None,
    image_mime_type: str | None,
    mary_asked_name: bool,
    error: str,
    interaction_number: int | None = None,
) -> None:
    """
    Salva uma interação comum ou faz upsert da interação
    de uma sessão narrativa.

    Para cenários, a chave lógica é:
    scenario_session_id + interaction_number.
    """

    interaction_id = _texto(interaction_id)
    user_id = _texto(user_id)
    error = _texto(error)

    instancia = _obter_instancia_cenario(
        user_id=user_id
    )

    scenario_id, scenario_session_id = (
        _obter_contexto_cenario(
            user_id=user_id
        )
    )

    interaction_number = _inteiro(
        interaction_number
    )

    interaction_key = montar_interaction_key(
        scenario_session_id=(
            scenario_session_id
        ),
        interaction_number=(
            interaction_number
        ),
    )

    cabecalhos = set(
        obter_cabecalhos(
            INTERACTIONS_SHEET
        )
    )

    suporta_cluster = set(
        SCENARIO_INTERACTION_COLUMNS
    ).issubset(cabecalhos)

    # Erros não ocupam nem sobrescrevem um slot narrativo.
    usar_upsert = bool(
        suporta_cluster
        and interaction_key
        and scenario_id
        and not error
    )

    registro_completo = {
        "interaction_id": interaction_id,
        "session_id": _texto(session_id),
        "user_id": user_id,
        "timestamp": _texto(timestamp),
        "user_text": str(user_text or ""),
        "mary_response": str(
            mary_response or ""
        ),
        "model": _texto(model),
        "prompt_version": _texto(
            prompt_version
        ),
        "response_time_ms": (
            response_time_ms
        ),
        "image_sent": bool(image_sent),
        "image_width": image_width,
        "image_height": image_height,
        "image_size_bytes": (
            image_size_bytes
        ),
        "image_mime_type": _texto(
            image_mime_type
        ),
        "mary_asked_name": bool(
            mary_asked_name
        ),
        "error": error,
        "interaction_key": interaction_key,
        "scenario_id": scenario_id,
        "scenario_session_id": (
            scenario_session_id
        ),
        "interaction_number": (
            interaction_number
            if interaction_key
            else ""
        ),
    }

    existente = None

    if usar_upsert:
        existente = buscar_registro(
            INTERACTIONS_SHEET,
            coluna="interaction_key",
            valor=interaction_key,
        )

    if existente is not None:
        # Sobrescreve somente o slot lógico desta sessão.
        # Nenhuma linha de outro usuário ou sessão é tocada.
        atualizar_registro(
            INTERACTIONS_SHEET,
            coluna_chave="interaction_key",
            valor_chave=interaction_key,
            alteracoes=registro_completo,
        )
    else:
        salvar_interacao_base(
            interaction_id=interaction_id,
            session_id=session_id,
            user_id=user_id,
            timestamp=timestamp,
            user_text=user_text,
            mary_response=mary_response,
            model=model,
            prompt_version=prompt_version,
            response_time_ms=(
                response_time_ms
            ),
            image_sent=image_sent,
            image_width=image_width,
            image_height=image_height,
            image_size_bytes=(
                image_size_bytes
            ),
            image_mime_type=(
                image_mime_type
            ),
            mary_asked_name=(
                mary_asked_name
            ),
            error=error,
        )

        if suporta_cluster and scenario_id:
            atualizar_registro(
                INTERACTIONS_SHEET,
                coluna_chave="interaction_id",
                valor_chave=interaction_id,
                alteracoes={
                    "interaction_key": (
                        interaction_key
                    ),
                    "scenario_id": scenario_id,
                    "scenario_session_id": (
                        scenario_session_id
                    ),
                    "user_id": user_id,
                    "interaction_number": (
                        interaction_number
                        if interaction_key
                        else ""
                    ),
                },
            )

    if instancia is not None:
        if interaction_key and not error:
            total_real = (
                contar_interacoes_sessao_cenario(
                    user_id=user_id,
                    scenario_session_id=(
                        scenario_session_id
                    ),
                )
            )

            instancia[
                "interaction_count"
            ] = total_real

            scene_state = instancia.get(
                "scene_state"
            )

            if not isinstance(
                scene_state,
                dict,
            ):
                scene_state = {}

            scene_state = dict(scene_state)
            scene_state[
                "interaction_count"
            ] = total_real

            instancia[
                "scene_state"
            ] = scene_state

        salvar_instancia_cenario(
            instancia,
            houve_interacao=True,
        )

        st.session_state[
            "scenario_instance"
        ] = instancia


__all__ = [
    "MAX_SCENARIO_INTERACTIONS",
    "SCENARIO_INTERACTION_COLUMNS",
    "contar_interacoes_sessao_cenario",
    "listar_interacoes_sessao_cenario",
    "montar_interaction_key",
    "salvar_interacao",
]
