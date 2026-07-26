from __future__ import annotations

from functools import wraps
from typing import Any

import streamlit as st

import scenarios.card_runtime as card_runtime
import ui.card_runtime_integration as card_integration


CALL_PROMPT_GUARD_VERSION = "casada-frustrada-call-prompt-guard-v1-no-restart"
_INSTALLED = False


def _text(value: Any) -> str:
    return str(value or "").strip()


def _video_call_established() -> bool:
    instance = st.session_state.get("scenario_instance")
    if not isinstance(instance, dict):
        return False
    if _text(instance.get("scenario_id")) != "casada_frustrada":
        return False
    scene = instance.get("scene_state")
    return isinstance(scene, dict) and bool(scene.get("video_call_established"))


def _patch_screenplay_window() -> None:
    original = card_runtime.montar_janela_roteiro
    if getattr(original, "_mary_established_call_prompt", False):
        return

    @wraps(original)
    def wrapper(scenario_id: str, route: str) -> str:
        base = _text(original(scenario_id, route))
        if scenario_id != "casada_frustrada" or route != "hidden_call":
            return base
        if not _video_call_established():
            return base
        guard = """
[CONTINUIDADE INEGOCIÁVEL — CHAMADA DE VÍDEO JÁ ESTABELECIDA]
- A câmera já está ligada e os dois já se veem. Não pedir autorização para ligar,
  não perguntar se pode chamar por vídeo e não iniciar outra chamada.
- Não repetir “tá me vendo?”, não apoiar ou posicionar o celular novamente e não
  voltar à apresentação visual inicial.
- Preserve exatamente o último estado confirmado de roupas, exposição, excitação,
  posição e ação corporal de Mary.
- Continue pelo próximo movimento ainda não realizado do roteiro da chamada.
- Se a interação sexual já começou, mantenha linguagem direta, explícita, corporal
  e intensa. Não reduza para ansiedade contida, romance abstrato ou conversa preparatória.
- Mary conduz por reação, pedido, comando ou iniciativa. Evite pergunta; nunca use
  mais de uma pergunta no turno.
- Não repita uma etapa concluída apenas porque ela aparece no início do bloco lexical.
""".strip()
        return "\n\n".join(part for part in (base, guard) if part)

    wrapper._mary_established_call_prompt = True  # type: ignore[attr-defined]
    card_runtime.montar_janela_roteiro = wrapper
    card_integration.montar_janela_roteiro = wrapper


def install_casada_frustrada_call_prompt_guard() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _patch_screenplay_window()
    _INSTALLED = True


__all__ = [
    "CALL_PROMPT_GUARD_VERSION",
    "install_casada_frustrada_call_prompt_guard",
]
