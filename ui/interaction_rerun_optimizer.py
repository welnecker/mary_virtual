from __future__ import annotations

import sys
from functools import wraps
from typing import Any, Callable

import streamlit as st


INTERACTION_RERUN_OPTIMIZER_VERSION = (
    "interaction-rerun-optimizer-v1-safe-final-rerun"
)

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _should_preserve_final_rerun() -> bool:
    """Mantém o rerun quando a nova tela precisa mudar estruturalmente."""
    if bool(st.session_state.get("show_name_form", False)):
        return True

    instance = st.session_state.get("scenario_instance")
    if not isinstance(instance, dict):
        return False

    status = str(instance.get("status") or "active").strip().lower()
    if status == "completed":
        return True

    if bool(instance.get("input_locked", False)):
        return True

    if bool(instance.get("show_return_to_menu", False)):
        return True

    return False


def _patch_processar_interacao(module: Any) -> None:
    original = getattr(module, "processar_interacao", None)
    if not callable(original):
        return
    if getattr(original, "_mary_rerun_optimized", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        original_rerun = st.rerun
        suppressed = False

        def conditional_rerun(*rerun_args: Any, **rerun_kwargs: Any) -> Any:
            nonlocal suppressed

            # O rerun final ocorre depois que a resposta já foi desenhada,
            # adicionada ao session_state e persistida. Ele só é necessário
            # quando a estrutura da tela mudou (fim da história ou formulário).
            if _should_preserve_final_rerun():
                return original_rerun(*rerun_args, **rerun_kwargs)

            suppressed = True
            return None

        st.rerun = conditional_rerun
        try:
            result = original(*args, **kwargs)
        finally:
            st.rerun = original_rerun

        if suppressed:
            st.session_state["_mary_last_interaction_rerun_suppressed"] = True

        return result

    wrapper._mary_rerun_optimized = True  # type: ignore[attr-defined]
    setattr(module, "processar_interacao", wrapper)


def aplicar_otimizacao_rerun() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return
    _patch_processar_interacao(module)


def install_interaction_rerun_optimizer() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return

    _ORIGINAL_TITLE = st.title

    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_otimizacao_rerun()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "INTERACTION_RERUN_OPTIMIZER_VERSION",
    "aplicar_otimizacao_rerun",
    "install_interaction_rerun_optimizer",
]
