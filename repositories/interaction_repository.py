from __future__ import annotations

from typing import Any

import streamlit as st

from google_sheets_repository import (
    INTERACTIONS_SHEET,
    atualizar_registro,
    obter_cabecalhos,
    obter_registros_aba,
    salvar_interacao as salvar_interacao_base,
)
from repositories.scenario_session_repository import (
    salvar_instancia_cenario,
)

SCENARIO_INTERACTION_COLUMNS = (
    "scenario_id",
    "scenario_session_id",
)


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _obter_instancia_cenario(
    *,
    user_id: str,
) -> dict[str, Any] | None:
    instancia = st.session_state.get("scenario_instance")
    if not isinstance(instancia, dict):
        return None

    scenario_user_id = _texto(instancia.get("user_id"))
    user_id = _texto(user_id)
    if scenario_user_id and scenario_user_id != user_id:
        return None
    return instancia


def _obter_contexto_cenario(
    *,
    user_id: str,
) -> tuple[str, str]:
    instancia = _obter_instancia_cenario(user_id=user_id)
    if instancia is None:
        return "", ""
    return (
        _texto(instancia.get("scenario_id")),
        _texto(instancia.get("scenario_session_id")),
    )


def listar_interacoes_sessao_cenario(
    *,
    user_id: str,
    scenario_session_id: str,
    limite: int = 100,
) -> list[dict[str, Any]]:
    user_id = _texto(user_id)
    scenario_session_id = _texto(scenario_session_id)
    if not user_id or not scenario_session_id:
        return []

    registros = obter_registros_aba(INTERACTIONS_SHEET)
    resultado = [
        dict(registro)
        for registro in registros
        if (
            _texto(registro.get("user_id")) == user_id
            and _texto(registro.get("scenario_session_id"))
            == scenario_session_id
        )
    ]
    resultado.sort(
        key=lambda registro: _texto(registro.get("timestamp"))
    )
    limite = max(1, int(limite or 100))
    return resultado[-limite:]


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
) -> None:
    """Salva a interação, seu cenário e o estado narrativo atual."""

    salvar_interacao_base(
        interaction_id=interaction_id,
        session_id=session_id,
        user_id=user_id,
        timestamp=timestamp,
        user_text=user_text,
        mary_response=mary_response,
        model=model,
        prompt_version=prompt_version,
        response_time_ms=response_time_ms,
        image_sent=image_sent,
        image_width=image_width,
        image_height=image_height,
        image_size_bytes=image_size_bytes,
        image_mime_type=image_mime_type,
        mary_asked_name=mary_asked_name,
        error=error,
    )

    instancia = _obter_instancia_cenario(user_id=user_id)
    scenario_id, scenario_session_id = _obter_contexto_cenario(
        user_id=user_id
    )

    if not scenario_id or not scenario_session_id:
        return

    cabecalhos = set(obter_cabecalhos(INTERACTIONS_SHEET))
    if set(SCENARIO_INTERACTION_COLUMNS).issubset(cabecalhos):
        atualizar_registro(
            INTERACTIONS_SHEET,
            coluna_chave="interaction_id",
            valor_chave=interaction_id,
            alteracoes={
                "scenario_id": scenario_id,
                "scenario_session_id": scenario_session_id,
            },
        )

    if instancia is not None:
        salvar_instancia_cenario(instancia, houve_interacao=True)
        st.session_state["scenario_instance"] = instancia


__all__ = [
    "SCENARIO_INTERACTION_COLUMNS",
    "listar_interacoes_sessao_cenario",
    "salvar_interacao",
]
