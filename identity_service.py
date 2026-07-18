from __future__ import annotations

from typing import Any

import streamlit as st

from google_sheets_repository import (
    GoogleSheetsRepositoryError,
    criar_usuario_anonimo,
    obter_usuario_por_token,
    registrar_novo_acesso_usuario,
)


QUERY_PARAM_USER_TOKEN = "u"


def obter_token_url() -> str:
    valor = st.query_params.get(
        QUERY_PARAM_USER_TOKEN,
        "",
    )

    if isinstance(valor, list):
        valor = valor[0] if valor else ""

    return str(valor or "").strip()


def gravar_token_url(token: str) -> None:
    st.query_params[
        QUERY_PARAM_USER_TOKEN
    ] = token

def remover_token_url() -> None:
    """
    Remove da URL o token do usuário atual.

    Deve ser chamado depois que o cadastro do usuário
    for excluído da planilha.
    """

    if QUERY_PARAM_USER_TOKEN in st.query_params:
        del st.query_params[
            QUERY_PARAM_USER_TOKEN
        ]


def obter_ou_criar_usuario_atual(
) -> dict[str, Any]:
    if st.session_state.get(
        "persistent_user"
    ):
        return st.session_state[
            "persistent_user"
        ]

    token = obter_token_url()

    if token:
        usuario = obter_usuario_por_token(
            token
        )

        if usuario is not None:
            usuario = registrar_novo_acesso_usuario(
                usuario
            )

            st.session_state[
                "persistent_user"
            ] = usuario

            st.session_state[
                "persistent_user_token"
            ] = token

            return usuario

    usuario, novo_token = criar_usuario_anonimo()

    st.session_state[
        "persistent_user"
    ] = usuario

    st.session_state[
        "persistent_user_token"
    ] = novo_token

    gravar_token_url(
        novo_token
    )

    return usuario
