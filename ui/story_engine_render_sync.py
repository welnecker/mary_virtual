from __future__ import annotations

from copy import deepcopy
from functools import wraps
import sys
from typing import Any, Callable

import streamlit as st


RENDER_SYNC_VERSION = "story-engine-render-sync-v1-local-only"
_SUPPORTED_STORIES = {"casada_frustrada"}
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _patch_render_sync(module: Any) -> None:
    original = getattr(module, "sincronizar_contagem_cenario_com_historico", None)
    if not callable(original) or getattr(original, "_clean_story_render_sync_wrapped", False):
        return

    @wraps(original)
    def wrapper(*, instancia_cenario: dict[str, Any], mensagens: list[dict[str, Any]]) -> dict[str, Any]:
        scenario_id = _text(
            instancia_cenario.get("scenario_id")
            if isinstance(instancia_cenario, dict)
            else ""
        )
        if scenario_id not in _SUPPORTED_STORIES:
            return original(
                instancia_cenario=instancia_cenario,
                mensagens=mensagens,
            )

        instancia = deepcopy(instancia_cenario)
        total_real = sum(
            1
            for mensagem in mensagens
            if (
                isinstance(mensagem, dict)
                and mensagem.get("role") == "user"
                and _text(mensagem.get("content"))
            )
        )

        # Nesta arquitetura, renderizar a tela nunca persiste a sessão.
        # A persistência ocorre na criação da sessão e no fechamento de cada interação.
        instancia["interaction_count"] = total_real
        scene_state = instancia.get("scene_state")
        scene_state = deepcopy(scene_state) if isinstance(scene_state, dict) else {}
        scene_state["interaction_count"] = total_real
        instancia["scene_state"] = scene_state
        return instancia

    wrapper._clean_story_render_sync_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "sincronizar_contagem_cenario_com_historico", wrapper)


def aplicar_render_sync_runtime() -> None:
    module = sys.modules.get("__main__")
    if module is not None:
        _patch_render_sync(module)


def install_render_sync_runtime() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return

    _ORIGINAL_TITLE = st.title

    @wraps(_ORIGINAL_TITLE)
    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_render_sync_runtime()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "RENDER_SYNC_VERSION",
    "aplicar_render_sync_runtime",
    "install_render_sync_runtime",
]
