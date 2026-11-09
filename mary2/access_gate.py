"""Portão de acesso do Mary Core 2.

Credenciais vêm somente de Streamlit Secrets, nunca do repositório,
das interações, ou do estado narrativo.
"""
from __future__ import annotations

import hashlib
import hmac


def password_fingerprint(password: str) -> str:
    """Identificador não reversível da senha configurada (para a sessão atual)."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def password_matches(candidate: str, configured_password: str) -> bool:
    """Compara em tempo constante sem armazenar a tentativa na sessão."""
    if not configured_password:
        return False
    return hmac.compare_digest(
        password_fingerprint(candidate),
        password_fingerprint(configured_password),
    )
