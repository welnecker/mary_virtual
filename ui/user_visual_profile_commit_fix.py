from __future__ import annotations

import sys
from functools import wraps
from typing import Any, Callable

import streamlit as st

import google_sheets_repository as sheets_repository
from ui.user_visual_profile_persistence import (
    obter_perfil_visual_ativo,
    persistir_nova_referencia_visual,
)


USER_VISUAL_PROFILE_COMMIT_FIX_VERSION = (
    "user-visual-profile-commit-fix-v1-before-rerun"
)

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _patch_app(module: Any) -> None:
    original = getattr(module, "confirmar_referencia_visual", None)
    if not callable(original) or getattr(original, "_visual_commit_wrapped", False):
        return

    @wraps(original)
    def wrapper(profile: dict[str, Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
        updated = original(profile, *args, **kwargs)
        user = (
            st.session_state.get("persistent_user")
            or st.session_state.get("auth_user")
            or {}
        )
        user_id = _texto(user.get("user_id")) if isinstance(user, dict) else ""
        if not user_id:
            return updated

        visual = updated.get("visual_profile") if isinstance(updated, dict) else {}
        visual = visual if isinstance(visual, dict) else {}
        current_hash = _texto(
            visual.get("image_hash") or visual.get("reference_image_id")
        )
        active = obter_perfil_visual_ativo(user_id)
        active_hash = _texto(
            active.get("image_hash") or active.get("reference_image_id")
        ) if isinstance(active, dict) else ""

        if current_hash and current_hash != active_hash:
            persisted = persistir_nova_referencia_visual(
                user_id=user_id,
                profile=updated,
            )
            st.session_state["user_visual_profile"] = persisted
        return updated

    wrapper._visual_commit_wrapped = True  # type: ignore[attr-defined]
    module.confirmar_referencia_visual = wrapper


def aplicar_commit_perfil_visual() -> None:
    module = sys.modules.get("__main__")
    if module is not None:
        _patch_app(module)


def install_user_visual_profile_commit_fix() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    original_title = st.title
    _ORIGINAL_TITLE = original_title

    @wraps(original_title)
    def title_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            aplicar_commit_perfil_visual()
        except sheets_repository.GoogleSheetsRepositoryError as exc:
            st.warning(
                "A referência visual foi confirmada localmente, mas não pôde "
                f"ser persistida: {exc}"
            )
        return original_title(*args, **kwargs)

    st.title = title_wrapper
    _INSTALLED = True


__all__ = [
    "USER_VISUAL_PROFILE_COMMIT_FIX_VERSION",
    "aplicar_commit_perfil_visual",
    "install_user_visual_profile_commit_fix",
]
