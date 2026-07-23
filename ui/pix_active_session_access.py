from __future__ import annotations

import sys
from functools import wraps
from typing import Any, Callable

import streamlit as st

from repositories.scenario_session_repository import obter_sessao_ativa_mais_recente


PIX_ACTIVE_SESSION_ACCESS_VERSION = (
    "pix-active-session-access-v1-active-session-is-entitlement"
)

_PAID_SCENARIO_ID = "casada_frustrada"
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


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


def _possui_sessao_ativa(user_id: str, scenario_id: str) -> bool:
    if not user_id or scenario_id != _PAID_SCENARIO_ID:
        return False
    try:
        sessao = obter_sessao_ativa_mais_recente(
            user_id=user_id,
            scenario_id=scenario_id,
        )
    except Exception:
        return False
    if not isinstance(sessao, dict):
        return False
    return (
        _texto(sessao.get("status")).lower() == "active"
        and not bool(sessao.get("ending_sent"))
    )


def _adicionar_acesso_por_sessao_ativa(
    kwargs: dict[str, Any],
    *,
    user_id: str,
    scenario_id: str = "",
) -> dict[str, Any]:
    result = dict(kwargs)
    current = result.get("unlocked_scenario_ids")
    unlocked = set(current) if isinstance(current, (set, list, tuple)) else set()

    target_scenario = _texto(scenario_id) or _PAID_SCENARIO_ID
    if _possui_sessao_ativa(user_id, target_scenario):
        unlocked.add(target_scenario)

    result["unlocked_scenario_ids"] = unlocked
    return result


def _patch_access_function(module: Any, name: str) -> None:
    original = getattr(module, name, None)
    if not callable(original) or getattr(
        original,
        "_mary_pix_active_session_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        user_id = _texto(kwargs.get("user_id")) or _usuario_atual_id()
        scenario_id = _texto(kwargs.get("scenario_id"))
        patched_kwargs = _adicionar_acesso_por_sessao_ativa(
            kwargs,
            user_id=user_id,
            scenario_id=scenario_id,
        )
        return original(*args, **patched_kwargs)

    wrapper._mary_pix_active_session_wrapped = True  # type: ignore[attr-defined]
    setattr(module, name, wrapper)


def aplicar_acesso_pix_por_sessao_ativa() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return

    for function_name in (
        "listar_cenarios_para_usuario",
        "obter_cenario_para_usuario",
        "iniciar_cenario_para_usuario",
        "continuar_cenario_para_usuario",
    ):
        _patch_access_function(module, function_name)


def install_pix_active_session_access() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return

    _ORIGINAL_TITLE = st.title

    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_acesso_pix_por_sessao_ativa()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "PIX_ACTIVE_SESSION_ACCESS_VERSION",
    "aplicar_acesso_pix_por_sessao_ativa",
    "install_pix_active_session_access",
]
