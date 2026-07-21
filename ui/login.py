from __future__ import annotations

from typing import Any

import streamlit as st

from auth.service import (
    AuthenticationError,
    autenticar_usuario,
    cadastrar_usuario,
)
from google_sheets_repository import (
    GoogleSheetsRepositoryError,
)


AUTH_ACTION_LOGIN = "login"
AUTH_ACTION_REGISTER = "register"


AuthenticationResult = dict[str, Any]


def _texto(
    valor: Any,
) -> str:
    return str(
        valor or ""
    ).strip()


def _renderizar_form_login(
) -> AuthenticationResult | None:
    with st.form(
        "auth_login_form",
        clear_on_submit=False,
    ):
        email = st.text_input(
            "Email",
            key="auth_login_email",
            autocomplete="email",
            placeholder="seuemail@exemplo.com",
        )

        senha = st.text_input(
            "Senha",
            type="password",
            key="auth_login_password",
            autocomplete="current-password",
        )

        enviar = st.form_submit_button(
            "Entrar",
            type="primary",
            use_container_width=True,
        )

    if not enviar:
        return None

    try:
        usuario = autenticar_usuario(
            email=email,
            senha=senha,
        )
    except (
        AuthenticationError,
        ValueError,
    ) as exc:
        st.error(
            str(exc)
        )
        return None
    except GoogleSheetsRepositoryError:
        st.error(
            "Não foi possível acessar sua conta agora. "
            "Tente novamente em alguns instantes."
        )
        return None

    return {
        "action": AUTH_ACTION_LOGIN,
        "authenticated": True,
        "user": usuario,
    }


def _renderizar_form_cadastro(
) -> AuthenticationResult | None:
    with st.form(
        "auth_register_form",
        clear_on_submit=False,
    ):
        email = st.text_input(
            "Email",
            key="auth_register_email",
            autocomplete="email",
            placeholder="seuemail@exemplo.com",
        )

        senha = st.text_input(
            "Crie uma senha",
            type="password",
            key="auth_register_password",
            autocomplete="new-password",
            help=(
                "Use pelo menos 8 caracteres, com letras e números."
            ),
        )

        confirmar_senha = st.text_input(
            "Confirme a senha",
            type="password",
            key="auth_register_password_confirm",
            autocomplete="new-password",
        )

        aceitar_termos = st.checkbox(
            "Confirmo que sou maior de 18 anos.",
            key="auth_register_adult_confirm",
        )

        enviar = st.form_submit_button(
            "Criar conta",
            type="primary",
            use_container_width=True,
        )

    if not enviar:
        return None

    if not aceitar_termos:
        st.error(
            "É necessário confirmar que você é maior de 18 anos."
        )
        return None

    try:
        usuario = cadastrar_usuario(
            email=email,
            senha=senha,
            confirmar_senha=confirmar_senha,
        )
    except (
        AuthenticationError,
        ValueError,
    ) as exc:
        st.error(
            str(exc)
        )
        return None
    except GoogleSheetsRepositoryError:
        st.error(
            "Não foi possível criar sua conta agora. "
            "Tente novamente em alguns instantes."
        )
        return None

    st.success(
        "Conta criada com sucesso."
    )

    return {
        "action": AUTH_ACTION_REGISTER,
        "authenticated": True,
        "user": usuario,
    }


def renderizar_tela_login(
    *,
    titulo: str = "Entre para continuar",
    descricao: str = (
        "Acesse sua conta ou crie uma nova para escolher "
        "suas histórias com Mary."
    ),
) -> AuthenticationResult | None:
    """
    Renderiza login e cadastro, retornando o usuário autenticado.

    Esta camada não grava o usuário no session_state e não inicia o app.
    A integração da sessão será feita pelo app.py na etapa seguinte.
    """

    st.markdown(
        f"## {_texto(titulo) or 'Entre para continuar'}"
    )

    if _texto(
        descricao
    ):
        st.caption(
            _texto(
                descricao
            )
        )

    aba_login, aba_cadastro = st.tabs(
        [
            "Entrar",
            "Criar conta",
        ]
    )

    resultado: AuthenticationResult | None = None

    with aba_login:
        resultado_login = _renderizar_form_login()

        if resultado_login is not None:
            resultado = resultado_login

    with aba_cadastro:
        resultado_cadastro = _renderizar_form_cadastro()

        if resultado_cadastro is not None:
            resultado = resultado_cadastro

    return resultado


__all__ = [
    "AUTH_ACTION_LOGIN",
    "AUTH_ACTION_REGISTER",
    "AuthenticationResult",
    "renderizar_tela_login",
]
