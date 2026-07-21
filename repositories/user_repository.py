from __future__ import annotations

from typing import Any

from google_sheets_repository import (
    GoogleSheetsRepositoryError,
    USERS_SHEET,
    adicionar_registro,
    atualizar_registro,
    buscar_registro,
    gerar_id,
    utc_now_iso,
)


def obter_usuario_por_email_normalizado(
    email_normalized: str,
) -> dict[str, Any] | None:
    email_normalized = str(
        email_normalized or ""
    ).strip().lower()

    if not email_normalized:
        return None

    return buscar_registro(
        USERS_SHEET,
        coluna="email_normalized",
        valor=email_normalized,
    )


def criar_usuario_com_credenciais(
    *,
    email: str,
    email_normalized: str,
    password_hash: str,
    name: str = "",
    preferred_name: str = "",
) -> dict[str, Any]:
    email = str(
        email or ""
    ).strip()

    email_normalized = str(
        email_normalized or ""
    ).strip().lower()

    password_hash = str(
        password_hash or ""
    ).strip()

    if not email:
        raise ValueError(
            "O email não foi informado."
        )

    if not email_normalized:
        raise ValueError(
            "O email normalizado não foi informado."
        )

    if not password_hash:
        raise ValueError(
            "O hash da senha não foi informado."
        )

    usuario_existente = (
        obter_usuario_por_email_normalizado(
            email_normalized
        )
    )

    if usuario_existente is not None:
        raise GoogleSheetsRepositoryError(
            "Já existe uma conta cadastrada com este email."
        )

    agora = utc_now_iso()

    usuario: dict[str, Any] = {
        "user_id": gerar_id("usr"),
        "email": email,
        "email_normalized": email_normalized,
        "password_hash": password_hash,
        "created_at": agora,
        "updated_at": agora,
        "status": "active",
        "name": str(name or "").strip(),
        "preferred_name": str(
            preferred_name or ""
        ).strip(),
        "first_access_at": agora,
        "last_access_at": agora,
        "last_login_at": agora,
        "access_count": 1,
        "profile_version": 1,
    }

    adicionar_registro(
        USERS_SHEET,
        usuario,
    )

    return dict(
        usuario
    )


def registrar_login_usuario(
    usuario: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(
        usuario,
        dict,
    ):
        raise ValueError(
            "Os dados do usuário são inválidos."
        )

    user_id = str(
        usuario.get(
            "user_id",
            "",
        )
        or ""
    ).strip()

    if not user_id:
        raise GoogleSheetsRepositoryError(
            "O usuário não possui user_id."
        )

    try:
        access_count = int(
            usuario.get(
                "access_count",
                0,
            )
            or 0
        )
    except (
        TypeError,
        ValueError,
    ):
        access_count = 0

    agora = utc_now_iso()

    alteracoes = {
        "updated_at": agora,
        "last_access_at": agora,
        "last_login_at": agora,
        "access_count": access_count + 1,
    }

    atualizado = atualizar_registro(
        USERS_SHEET,
        coluna_chave="user_id",
        valor_chave=user_id,
        alteracoes=alteracoes,
    )

    if not atualizado:
        raise GoogleSheetsRepositoryError(
            "Não foi possível localizar o usuário para registrar o login."
        )

    usuario_atualizado = dict(
        usuario
    )
    usuario_atualizado.update(
        alteracoes
    )

    return usuario_atualizado


__all__ = [
    "criar_usuario_com_credenciais",
    "obter_usuario_por_email_normalizado",
    "registrar_login_usuario",
]
