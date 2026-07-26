from __future__ import annotations

from copy import deepcopy
from functools import wraps
import re
import sys
import unicodedata
from typing import Any

import streamlit as st

from repositories.scenario_session_repository import salvar_instancia_cenario


FAILURE_GUARD_VERSION = "casada-frustrada-failure-guard-v2-dynamic-duration"
_TERMINAL_MESSAGE = (
    "Você não está sendo apropriado com Mary. Tente novamente — ela está te esperando."
)
_INSTALLED = False

_HOSTILE_PATTERNS = (
    "vou te bater",
    "vou te machucar",
    "vou te matar",
    "cala a boca",
    "vai se foder",
    "vai tomar no cu",
    "sua puta",
    "sua vagabunda",
    "sua idiota",
    "sua imbecil",
    "te odeio",
    "some daqui",
    "nao enche",
)
_PHONE_REFUSALS = (
    "nao vou te passar meu numero",
    "nao te dou meu numero",
    "nao quero te dar meu numero",
    "nao quero trocar telefone",
    "nao quero seu numero",
    "nao me liga",
)
_CALL_REFUSALS = (
    "nao vou atender",
    "nao quero atender",
    "nao quero chamada",
    "nao quero falar por video",
    "nao quero video",
    "nao me chama por video",
    "nao vou entrar na chamada",
    "desliga e nao liga mais",
)
_MEETING_REFUSALS = (
    "nao vou te encontrar",
    "nao quero te encontrar",
    "nao vou ao motel",
    "nao quero ir ao motel",
    "nao vou aparecer",
    "nao apareco",
    "vou te dar bolo",
    "nao fui",
    "nao compareci",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _scenario_instance() -> dict[str, Any] | None:
    value = st.session_state.get("scenario_instance")
    return value if isinstance(value, dict) else None


def _current_route(instance: dict[str, Any]) -> str:
    scene = instance.get("scene_state")
    scene = scene if isinstance(scene, dict) else {}
    return _text(instance.get("current_route") or scene.get("current_route"))


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for pattern in patterns)


def _terminal_reason(prompt: Any, route: str) -> str:
    text = _normalize(prompt)
    if not text:
        return ""
    if _contains_any(text, _HOSTILE_PATTERNS):
        return "hostile_or_aggressive_treatment"
    if route == "phone_exchange" and _contains_any(text, _PHONE_REFUSALS):
        return "phone_exchange_rejected"
    if route in {"messages", "hidden_call"} and _contains_any(text, _CALL_REFUSALS):
        return "private_call_rejected"
    if route in {"secret_meeting_plan", "secret_meeting"} and _contains_any(
        text, _MEETING_REFUSALS
    ):
        return "secret_meeting_rejected_or_abandoned"
    return ""


def _finish_story(prompt: Any, reason: str) -> None:
    instance = _scenario_instance()
    if not isinstance(instance, dict):
        return
    instance = deepcopy(instance)
    scene = instance.get("scene_state")
    scene = deepcopy(scene) if isinstance(scene, dict) else {}
    scene.update(
        {
            "status": "completed",
            "current_phase": "ending",
            "ending_ready": True,
            "ending_sent": True,
            "ending_type": "incompatible_user_response",
            "ending_reason": reason,
            "input_locked": True,
            "show_return_to_menu": True,
            "scene_active": False,
            "last_user_action": _text(prompt),
            "last_mary_response": _TERMINAL_MESSAGE,
        }
    )
    instance.update(
        {
            "status": "completed",
            "current_phase": "ending",
            "ending_ready": True,
            "ending_sent": True,
            "ending_type": "incompatible_user_response",
            "ending_reason": reason,
            "input_locked": True,
            "show_return_to_menu": True,
            "summary": _TERMINAL_MESSAGE,
            "scene_state": scene,
        }
    )
    messages = st.session_state.get("messages")
    if not isinstance(messages, list):
        messages = []
    messages.append({"role": "user", "content": _text(prompt)})
    messages.append(
        {
            "role": "assistant",
            "content": f"> **História interrompida**\n\n{_TERMINAL_MESSAGE}",
        }
    )
    st.session_state["messages"] = messages
    st.session_state["scenario_instance"] = instance
    try:
        salvar_instancia_cenario(instance, houve_interacao=True)
    except Exception:
        pass
    st.rerun()


def _apply_duration_to_main(module: Any) -> None:
    instance = _scenario_instance()
    if not isinstance(instance, dict):
        return
    if _text(instance.get("scenario_id")) != "casada_frustrada":
        return
    setattr(module, "ENDING_COUNTDOWN_START", 90)
    setattr(module, "ENDING_INTERACTION_LIMIT", 95)


def _patch_process(module: Any) -> None:
    current = getattr(module, "processar_interacao", None)
    if not callable(current) or getattr(current, "_mary_failure_guard", False):
        return

    @wraps(current)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        instance = _scenario_instance()
        if isinstance(instance, dict) and _text(instance.get("scenario_id")) == "casada_frustrada":
            # O cenário pode ter sido escolhido depois da instalação do plugin.
            # Reaplicar aqui garante que a política 90/95 esteja ativa antes da
            # contagem e da geração da resposta deste turno.
            _apply_duration_to_main(module)
            prompt = kwargs.get("prompt")
            if prompt is None and args:
                prompt = args[0]
            reason = _terminal_reason(prompt, _current_route(instance))
            if reason:
                _finish_story(prompt, reason)
                return None
        return current(*args, **kwargs)

    wrapper._mary_failure_guard = True  # type: ignore[attr-defined]
    setattr(module, "processar_interacao", wrapper)


def install_casada_frustrada_failure_guard() -> None:
    global _INSTALLED
    module = sys.modules.get("__main__")
    if module is None:
        return
    _apply_duration_to_main(module)
    _patch_process(module)
    _INSTALLED = True


__all__ = [
    "FAILURE_GUARD_VERSION",
    "install_casada_frustrada_failure_guard",
]
