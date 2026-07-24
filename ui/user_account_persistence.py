from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import wraps
import sys
from typing import Any, Callable

import streamlit as st

import auth.service as auth_service
import google_sheets_repository as sheets_repository
import repositories.user_repository as user_repository


USER_ACCOUNT_PERSISTENCE_VERSION = (
    "user-account-persistence-v2-once-per-process-bootstrap"
)
USERS_SHEET = "USERS"
MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 15

USER_COLUMNS = (
    "user_id",
    "email",
    "email_normalized",
    "password_hash",
    "created_at",
    "updated_at",
    "status",
    "name",
    "preferred_name",
    "first_access_at",
    "last_access_at",
    "last_login_at",
    "access_count",
    "profile_version",
    "adult_confirmed_at",
    "adult_confirmation_version",
    "auth_version",
    "password_changed_at",
    "failed_login_count",
    "last_failed_login_at",
    "locked_until",
    "deleted_at",
    "active",
)

_INSTALLED = False
_BOOTSTRAP_DONE = False
_SCHEMA_READY = False
_NORMALIZATION_DONE = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None
_ORIGINAL_REGISTER: Callable[..., Any] | None = None
_ORIGINAL_AUTHENTICATE: Callable[..., Any] | None = None


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _inteiro(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _booleano(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    return _texto(value).lower() in {
        "true", "1", "sim", "yes", "verdadeiro", "active", "ativo"
    }


def _parse_iso(value: Any) -> datetime | None:
    text = _texto(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _clear_caches() -> None:
    for name in ("obter_cabecalhos", "obter_registros_aba"):
        function = getattr(sheets_repository, name, None)
        clear = getattr(function, "clear", None)
        if callable(clear):
            clear()


def garantir_schema_users() -> list[str]:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return []

    worksheet = sheets_repository.obter_aba(USERS_SHEET)
    headers = list(sheets_repository.obter_cabecalhos(USERS_SHEET))
    added: list[str] = []
    for column in USER_COLUMNS:
        if column in headers:
            continue
        headers.append(column)
        worksheet.update_cell(1, len(headers), column)
        added.append(column)
    if added:
        _clear_caches()
    _SCHEMA_READY = True
    return added


def normalizar_usuarios_existentes() -> int:
    global _NORMALIZATION_DONE
    if _NORMALIZATION_DONE:
        return 0

    garantir_schema_users()
    rows = sheets_repository.obter_registros_aba(USERS_SHEET)
    updated = 0
    for row in rows:
        user_id = _texto(row.get("user_id"))
        if not user_id:
            continue
        status = (_texto(row.get("status")) or "active").lower()
        changes: dict[str, Any] = {}
        if not _texto(row.get("auth_version")):
            changes["auth_version"] = 1
        if not _texto(row.get("failed_login_count")):
            changes["failed_login_count"] = 0
        if not _texto(row.get("active")):
            changes["active"] = status == "active"
        if not _texto(row.get("password_changed_at")):
            changes["password_changed_at"] = (
                _texto(row.get("created_at")) or sheets_repository.utc_now_iso()
            )
        if changes:
            changes["updated_at"] = sheets_repository.utc_now_iso()
            sheets_repository.atualizar_registro(
                USERS_SHEET,
                coluna_chave="user_id",
                valor_chave=user_id,
                alteracoes=changes,
            )
            updated += 1
    if updated:
        _clear_caches()
    _NORMALIZATION_DONE = True
    return updated


def _registrar_falha(usuario: dict[str, Any]) -> None:
    user_id = _texto(usuario.get("user_id"))
    if not user_id:
        return
    now = datetime.now(timezone.utc)
    failures = max(0, _inteiro(usuario.get("failed_login_count"), 0)) + 1
    changes: dict[str, Any] = {
        "failed_login_count": failures,
        "last_failed_login_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    if failures >= MAX_FAILED_LOGINS:
        changes["locked_until"] = (
            now + timedelta(minutes=LOCK_MINUTES)
        ).isoformat()
    sheets_repository.atualizar_registro(
        USERS_SHEET,
        coluna_chave="user_id",
        valor_chave=user_id,
        alteracoes=changes,
    )


def _verificar_bloqueio(usuario: dict[str, Any]) -> None:
    locked_until = _parse_iso(usuario.get("locked_until"))
    if locked_until and locked_until > datetime.now(timezone.utc):
        raise auth_service.AuthenticationError(
            "Muitas tentativas de acesso. Aguarde alguns minutos e tente novamente."
        )


def _patch_authentication() -> None:
    global _ORIGINAL_REGISTER, _ORIGINAL_AUTHENTICATE

    if _ORIGINAL_REGISTER is None:
        _ORIGINAL_REGISTER = auth_service.cadastrar_usuario
    if _ORIGINAL_AUTHENTICATE is None:
        _ORIGINAL_AUTHENTICATE = auth_service.autenticar_usuario

    original_register = _ORIGINAL_REGISTER
    original_authenticate = _ORIGINAL_AUTHENTICATE

    @wraps(original_register)
    def register_wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        garantir_schema_users()
        result = original_register(*args, **kwargs)
        user_id = _texto(result.get("user_id")) if isinstance(result, dict) else ""
        if user_id:
            now = sheets_repository.utc_now_iso()
            sheets_repository.atualizar_registro(
                USERS_SHEET,
                coluna_chave="user_id",
                valor_chave=user_id,
                alteracoes={
                    "adult_confirmed_at": now,
                    "adult_confirmation_version": 1,
                    "auth_version": 1,
                    "password_changed_at": now,
                    "failed_login_count": 0,
                    "last_failed_login_at": "",
                    "locked_until": "",
                    "deleted_at": "",
                    "active": True,
                    "updated_at": now,
                },
            )
            result.update({
                "adult_confirmed_at": now,
                "adult_confirmation_version": 1,
                "auth_version": 1,
                "password_changed_at": now,
                "failed_login_count": 0,
                "active": True,
            })
        return result

    @wraps(original_authenticate)
    def authenticate_wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        garantir_schema_users()
        email = kwargs.get("email")
        if email is None and args:
            email = args[0]
        normalized = auth_service.normalizar_email(_texto(email))
        usuario = (
            user_repository.obter_usuario_por_email_normalizado(normalized)
            if normalized else None
        )
        if isinstance(usuario, dict):
            _verificar_bloqueio(usuario)
            if not _booleano(usuario.get("active"), True):
                raise auth_service.AuthenticationError("Esta conta não está ativa.")
        try:
            result = original_authenticate(*args, **kwargs)
        except auth_service.AuthenticationError:
            if isinstance(usuario, dict):
                _registrar_falha(usuario)
            raise

        user_id = _texto(result.get("user_id")) if isinstance(result, dict) else ""
        if user_id:
            now = sheets_repository.utc_now_iso()
            sheets_repository.atualizar_registro(
                USERS_SHEET,
                coluna_chave="user_id",
                valor_chave=user_id,
                alteracoes={
                    "failed_login_count": 0,
                    "last_failed_login_at": "",
                    "locked_until": "",
                    "active": True,
                    "updated_at": now,
                },
            )
            result.update({
                "failed_login_count": 0,
                "last_failed_login_at": "",
                "locked_until": "",
                "active": True,
            })
        return result

    auth_service.cadastrar_usuario = register_wrapper
    auth_service.autenticar_usuario = authenticate_wrapper

    login_module = sys.modules.get("ui.login")
    if login_module is not None:
        login_module.cadastrar_usuario = register_wrapper
        login_module.autenticar_usuario = authenticate_wrapper


def aplicar_persistencia_users() -> None:
    global _BOOTSTRAP_DONE
    if _BOOTSTRAP_DONE:
        return
    garantir_schema_users()
    normalizar_usuarios_existentes()
    _patch_authentication()
    _BOOTSTRAP_DONE = True


def install_user_account_persistence() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    original_title = st.title
    _ORIGINAL_TITLE = original_title

    @wraps(original_title)
    def title_wrapper(*args: Any, **kwargs: Any) -> Any:
        aplicar_persistencia_users()
        return original_title(*args, **kwargs)

    st.title = title_wrapper
    _INSTALLED = True


__all__ = [
    "USER_ACCOUNT_PERSISTENCE_VERSION",
    "USER_COLUMNS",
    "aplicar_persistencia_users",
    "garantir_schema_users",
    "install_user_account_persistence",
    "normalizar_usuarios_existentes",
]
