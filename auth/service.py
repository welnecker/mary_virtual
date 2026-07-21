from __future__ import annotations

import re
from typing import Any

from google_sheets_repository import (
    GoogleSheetsRepositoryError,
)
from repositories.user_repository import (
    criar_usuario_com_credenciais,
    obter_usuario_por_email_normalizado,
    registrar_login_usuario,
)
from auth.password import (
    gerar_hash_senha,
    validar_forca_senha,
    verificar_senha,
)


EMAIL_PATTERN = re.compile(
    r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
)


class AuthenticationError(ValueError):
    """Falha de autenticação sem expor detalhes sensíveis."""


def normalizar_email(
    email: str,
) -> str:
    return str(
        email or ""
    ).strip().lower()


def validar_email(
    email: str,
) -> str:
    email_normalized = normalizar_email(
        email
    )

    if not email_normalized:
        raise ValueError(
            "Informe o email."
        )

    if len(email_normalized) > 254:
        raise ValueError(
            "O email informado é muito longo."
        )

    if not EMAIL_PATTERN.fullmatch(
        email_normalized
    ):
        raise ValueError(
            "Informe um email válido."
        )

    return email_normalized


def _usuario_publico(
    usuario: dict[str, Any],
) -> dict[str, Any]:
    resultado = dict(
        usuario
    )
    resultado.pop(
        "password_hash",
        None,
    )
    return resultado


def cadastrar_usuario(
    *,
    email: str,
    senha: str,
    confirmar_senha: str,
    name: str = "",
    preferred_name: str = "",
) -> dict[str, Any]:
    email_original = str(
        email or ""
    ).strip()

    email_normalized = validar_email(
        email_original
    )

    senha = str(
        senha or ""
    )
    confirmar_senha = str(
        confirmar_senha or ""
    )

    if senha != confirmar_senha:
        raise ValueError(
            "As senhas não coincidem."
        )

    validar_forca_senha(
        senha
    )

    usuario_existente = (
        obter_usuario_por_email_normalizado(
            email_normalized
        )
    )

    if usuario_existente is not None:
        raise ValueError(
            "Já existe uma conta cadastrada com este email."
        )

    password_hash = gerar_hash_senha(
        senha
    )

    try:
        usuario = criar_usuario_com_credenciais(
            email=email_original,
            email_normalized=email_normalized,
            password_hash=password_hash,
            name=name,
            preferred_name=preferred_name,
        )
    except GoogleSheetsRepositoryError as exc:
        raise AuthenticationError(
            str(exc)
        ) from exc

    return _usuario_publico(
        usuario
    )


def autenticar_usuario(
    *,
    email: str,
    senha: str,
) -> dict[str, Any]:
    email_normalized = validar_email(
        email
    )

    senha = str(
        senha or ""
    )

    if not senha:
        raise AuthenticationError(
            "Email ou senha inválidos."
        )

    usuario = obter_usuario_por_email_normalizado(
        email_normalized
    )

    if usuario is None:
        raise AuthenticationError(
            "Email ou senha inválidos."
        )

    status = str(
        usuario.get(
            "status",
            "",
        )
        or ""
    ).strip().lower()

    if status != "active":
        raise AuthenticationError(
            "Esta conta não está ativa."
        )

    password_hash = str(
        usuario.get(
            "password_hash",
            "",
        )
        or ""
    ).strip()

    if not verificar_senha(
        senha,
        password_hash,
    ):
        raise AuthenticationError(
            "Email ou senha inválidos."
        )

    try:
        usuario = registrar_login_usuario(
            usuario
        )
    except GoogleSheetsRepositoryError as exc:
        raise AuthenticationError(
            "Não foi possível concluir o login."
        ) from exc

    return _usuario_publico(
        usuario
    )


__all__ = [
    "AuthenticationError",
    "autenticar_usuario",
    "cadastrar_usuario",
    "normalizar_email",
    "validar_email",
]
