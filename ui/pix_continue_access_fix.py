from __future__ import annotations

from functools import wraps
from typing import Any, Callable

import streamlit as st

import ui.scenario_menu as scenario_menu


PIX_CONTINUE_ACCESS_FIX_VERSION = "pix-continue-access-fix-v1-menu-reference"
PAID_SCENARIO_ID = "casada_frustrada"

_INSTALLED = False
_ORIGINAL_CONTINUE: Callable[..., Any] | None = None


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _usuario_atual_id() -> str:
    usuario = (
        st.session_state.get("persistent_user")
        or st.session_state.get("auth_user")
        or {}
    )
    if not isinstance(usuario, dict):
        return ""
    return _texto(usuario.get("user_id"))


def _cenario_pago_liberado() -> bool:
    user_id = _usuario_atual_id()
    if not user_id:
        return False

    credits = st.session_state.get("pix_mp_test_credits")
    if not isinstance(credits, dict):
        return False

    credit = credits.get(f"{user_id}:{PAID_SCENARIO_ID}")
    if not isinstance(credit, dict):
        return False

    return _texto(credit.get("status")).lower() in {"available", "in_use"}


def _adicionar_desbloqueio(kwargs: dict[str, Any]) -> dict[str, Any]:
    result = dict(kwargs)
    current = result.get("unlocked_scenario_ids")
    unlocked = set(current) if isinstance(current, (set, list, tuple)) else set()

    if _cenario_pago_liberado():
        unlocked.add(PAID_SCENARIO_ID)

    result["unlocked_scenario_ids"] = unlocked
    return result


def install_pix_continue_access_fix() -> None:
    global _INSTALLED, _ORIGINAL_CONTINUE
    if _INSTALLED:
        return

    original = getattr(scenario_menu, "continuar_cenario_para_usuario", None)
    if not callable(original):
        return
    if getattr(original, "_mary_pix_continue_access_wrapped", False):
        _INSTALLED = True
        return

    _ORIGINAL_CONTINUE = original

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        assert _ORIGINAL_CONTINUE is not None
        return _ORIGINAL_CONTINUE(*args, **_adicionar_desbloqueio(kwargs))

    wrapper._mary_pix_continue_access_wrapped = True  # type: ignore[attr-defined]
    scenario_menu.continuar_cenario_para_usuario = wrapper
    _INSTALLED = True


__all__ = [
    "PIX_CONTINUE_ACCESS_FIX_VERSION",
    "install_pix_continue_access_fix",
]
