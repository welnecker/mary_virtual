from __future__ import annotations

import hashlib
import re
from typing import Any, Callable

import streamlit as st

import ui.professional_experience as professional_experience
from voice.elevenlabs_tts import (
    ELEVENLABS_MODEL_ID,
    ElevenLabsTTSError,
    elevenlabs_configurada,
    obter_status_configuracao,
    sintetizar_fala,
)


ELEVENLABS_VOICE_INTEGRATION_VERSION = (
    "elevenlabs-voice-integration-v3-visible-safe-diagnostics"
)

_INSTALLED = False
_ORIGINAL_RENDER_VOICE_PLAYER: Callable[..., Any] | None = None


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _component_key(key_seed: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", _texto(key_seed))[-48:]
    return cleaned or "mary"


def _profile_name() -> str:
    profile = _texto(st.session_state.get("mary_voice_profile", "Quente"))
    return profile if profile in professional_experience.VOICE_PROFILES else "Quente"


def _latest_assistant_speech() -> str:
    messages = st.session_state.get("messages")
    if not isinstance(messages, list):
        return ""

    for message in reversed(messages):
        if not isinstance(message, dict):
            continue
        if _texto(message.get("role")).casefold() not in {"assistant", "ai"}:
            continue
        _, speech = professional_experience.separar_resposta_mary(
            _texto(message.get("content"))
        )
        return speech
    return ""


def _is_latest_speech(text: str) -> bool:
    return bool(text and text == _latest_assistant_speech())


def _autoplay_token(*, text: str, profile_name: str) -> str:
    material = f"{ELEVENLABS_MODEL_ID}|{profile_name}|{text}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _render_browser_fallback(
    text: str,
    *,
    autoplay: bool,
    key_seed: str,
) -> None:
    if _ORIGINAL_RENDER_VOICE_PLAYER is None:
        return
    _ORIGINAL_RENDER_VOICE_PLAYER(
        text,
        autoplay=autoplay,
        key_seed=key_seed,
    )


def _render_configuration_problem() -> None:
    status = obter_status_configuracao()
    missing = []
    if not status["api_key_encontrada"]:
        missing.append("ELEVENLABS_API_KEY")
    if not status["voice_id_encontrado"]:
        missing.append("ELEVENLABS_VOICE_ID")

    if missing:
        st.warning(
            "Voz neural não configurada. Secret ausente: " + ", ".join(missing)
        )


def _render_neural_voice_player(
    text: str,
    *,
    autoplay: bool,
    key_seed: str,
) -> None:
    clean_text = _texto(text)
    if not clean_text or not st.session_state.get("mary_voice_enabled", True):
        return

    if not elevenlabs_configurada():
        _render_configuration_problem()
        _render_browser_fallback(
            clean_text,
            autoplay=autoplay,
            key_seed=key_seed,
        )
        return

    profile_name = _profile_name()
    component_key = _component_key(key_seed)
    audio_state_key = f"_mary_neural_audio_{component_key}_{profile_name}"
    error_state_key = f"_mary_neural_audio_error_{component_key}_{profile_name}"

    should_autoplay = bool(autoplay and _is_latest_speech(clean_text))
    autoplay_key = _autoplay_token(text=clean_text, profile_name=profile_name)
    autoplay_done = st.session_state.get("_mary_neural_autoplay_done") == autoplay_key

    play_clicked = st.button(
        f"▶ Ouvir Mary · {profile_name}",
        key=f"mary_neural_voice_{component_key}_{profile_name}",
        help="Voz neural em português pela ElevenLabs.",
    )

    should_generate = bool(play_clicked or (should_autoplay and not autoplay_done))
    audio = st.session_state.get(audio_state_key)

    if should_generate and not isinstance(audio, bytes):
        try:
            with st.spinner("Preparando a voz de Mary..."):
                audio = sintetizar_fala(
                    text=clean_text,
                    profile_name=profile_name,
                )
            st.session_state[audio_state_key] = audio
            st.session_state.pop(error_state_key, None)
        except ElevenLabsTTSError as exc:
            st.session_state[error_state_key] = str(exc)
            audio = None

    if should_autoplay and should_generate:
        st.session_state["_mary_neural_autoplay_done"] = autoplay_key

    if isinstance(audio, bytes) and audio:
        st.audio(
            audio,
            format="audio/mpeg",
            autoplay=bool(should_autoplay and should_generate),
        )
        return

    error_message = _texto(st.session_state.get(error_state_key))
    if error_message:
        st.error("A voz neural não pôde ser gerada.")
        with st.expander("Ver diagnóstico da ElevenLabs", expanded=True):
            st.code(error_message, language=None)
            status = obter_status_configuracao()
            st.caption(
                "API key encontrada: "
                + ("sim" if status["api_key_encontrada"] else "não")
                + " · Voice ID encontrado: "
                + ("sim" if status["voice_id_encontrado"] else "não")
                + " · Origem: "
                + status["voice_id_origem"]
                + (
                    " · Final do ID: ..." + status["voice_id_final"]
                    if status["voice_id_final"]
                    else ""
                )
            )
        st.caption("Usando temporariamente a voz do navegador.")
        _render_browser_fallback(
            clean_text,
            autoplay=bool(should_autoplay and should_generate),
            key_seed=key_seed,
        )


def install_elevenlabs_voice_integration() -> None:
    global _INSTALLED, _ORIGINAL_RENDER_VOICE_PLAYER
    if _INSTALLED:
        return

    professional_experience.install_professional_experience()

    original = getattr(professional_experience, "_render_voice_player", None)
    if not callable(original):
        return

    _ORIGINAL_RENDER_VOICE_PLAYER = original
    professional_experience._render_voice_player = _render_neural_voice_player
    _INSTALLED = True


__all__ = [
    "ELEVENLABS_VOICE_INTEGRATION_VERSION",
    "install_elevenlabs_voice_integration",
]
