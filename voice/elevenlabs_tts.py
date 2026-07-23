from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st


ELEVENLABS_TTS_VERSION = "elevenlabs-tts-v2-diagnostic-secrets"
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"
ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"
ELEVENLABS_OUTPUT_FORMAT = "mp3_44100_128"
CACHE_DIR = Path(".cache") / "mary_voice"

VOICE_SETTINGS: dict[str, dict[str, float | bool]] = {
    "Quente": {
        "stability": 0.38,
        "similarity_boost": 0.78,
        "style": 0.22,
        "use_speaker_boost": True,
        "speed": 0.94,
    },
    "Viva": {
        "stability": 0.34,
        "similarity_boost": 0.76,
        "style": 0.30,
        "use_speaker_boost": True,
        "speed": 1.02,
    },
    "Suave": {
        "stability": 0.48,
        "similarity_boost": 0.80,
        "style": 0.12,
        "use_speaker_boost": True,
        "speed": 0.93,
    },
    "Natural": {
        "stability": 0.44,
        "similarity_boost": 0.78,
        "style": 0.10,
        "use_speaker_boost": True,
        "speed": 0.98,
    },
}


class ElevenLabsTTSError(RuntimeError):
    """Erro seguro de síntese, sem expor a chave da API."""


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _ler_secret(nome: str) -> str:
    try:
        return _texto(st.secrets[nome])
    except Exception:
        return ""


def obter_credenciais_com_origem() -> tuple[str, str, str]:
    """Lê secrets planos ou agrupados e informa a origem do voice_id."""

    api_key = _ler_secret("ELEVENLABS_API_KEY")
    voice_id = _ler_secret("ELEVENLABS_VOICE_ID")
    origem = "secret plano" if voice_id else ""

    try:
        grouped = st.secrets["elevenlabs"]
    except Exception:
        grouped = {}

    if hasattr(grouped, "get"):
        if not api_key:
            api_key = _texto(grouped.get("api_key", ""))
        if not voice_id:
            voice_id = _texto(grouped.get("voice_id", ""))
            if voice_id:
                origem = "seção [elevenlabs]"

    return api_key, voice_id, origem


def obter_credenciais() -> tuple[str, str]:
    api_key, voice_id, _ = obter_credenciais_com_origem()
    return api_key, voice_id


def obter_status_configuracao() -> dict[str, Any]:
    api_key, voice_id, origem = obter_credenciais_com_origem()
    return {
        "api_key_encontrada": bool(api_key),
        "voice_id_encontrado": bool(voice_id),
        "voice_id_origem": origem or "não encontrado",
        "voice_id_final": voice_id[-6:] if voice_id else "",
    }


def elevenlabs_configurada() -> bool:
    api_key, voice_id = obter_credenciais()
    return bool(api_key and voice_id)


def _settings_for(profile_name: str) -> dict[str, float | bool]:
    return dict(VOICE_SETTINGS.get(profile_name, VOICE_SETTINGS["Quente"]))


def _cache_path(*, text: str, voice_id: str, profile_name: str) -> Path:
    material = "|".join(
        (
            ELEVENLABS_MODEL_ID,
            ELEVENLABS_OUTPUT_FORMAT,
            voice_id,
            profile_name,
            text,
        )
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.mp3"


def _read_cache(path: Path) -> bytes | None:
    try:
        if path.is_file() and path.stat().st_size > 0:
            return path.read_bytes()
    except OSError:
        return None
    return None


def _write_cache(path: Path, audio: bytes) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(audio)
        temporary.replace(path)
    except OSError:
        return


def _formatar_detalhe_api(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        message = value.get("message") or value.get("detail") or value.get("status")
        if message:
            return _texto(message)
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return _texto(value)
    if isinstance(value, list):
        return "; ".join(filter(None, (_formatar_detalhe_api(item) for item in value)))
    return _texto(value)


def sintetizar_fala(
    *,
    text: str,
    profile_name: str = "Quente",
    timeout_seconds: float = 45.0,
) -> bytes:
    clean_text = _texto(text)
    if not clean_text:
        raise ElevenLabsTTSError("Não há fala de Mary para sintetizar.")

    api_key, voice_id, origem = obter_credenciais_com_origem()
    if not api_key or not voice_id:
        ausentes = []
        if not api_key:
            ausentes.append("ELEVENLABS_API_KEY")
        if not voice_id:
            ausentes.append("ELEVENLABS_VOICE_ID")
        raise ElevenLabsTTSError(
            "Secrets ausentes: " + ", ".join(ausentes) + "."
        )

    cache_path = _cache_path(
        text=clean_text,
        voice_id=voice_id,
        profile_name=profile_name,
    )
    cached = _read_cache(cache_path)
    if cached is not None:
        return cached

    endpoint = (
        f"{ELEVENLABS_API_BASE}/text-to-speech/{voice_id}"
        f"?output_format={ELEVENLABS_OUTPUT_FORMAT}"
    )
    payload = {
        "text": clean_text,
        "model_id": ELEVENLABS_MODEL_ID,
        "voice_settings": _settings_for(profile_name),
    }
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            audio = response.read()
    except HTTPError as exc:
        detail = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
            parsed = json.loads(body)
            detail = _formatar_detalhe_api(
                parsed.get("detail") or parsed.get("message") or parsed
            )
        except Exception:
            detail = ""
        message = (
            f"ElevenLabs HTTP {exc.code}. Voice ID lido de {origem}; "
            f"final ...{voice_id[-6:]}."
        )
        if detail:
            message += f" Motivo: {detail[:500]}"
        raise ElevenLabsTTSError(message) from exc
    except (URLError, TimeoutError) as exc:
        raise ElevenLabsTTSError(
            f"Falha de conexão com a ElevenLabs: {type(exc).__name__}."
        ) from exc
    except Exception as exc:
        raise ElevenLabsTTSError(
            f"Erro inesperado ao gerar a voz: {type(exc).__name__}: {exc}"
        ) from exc

    if not audio:
        raise ElevenLabsTTSError("A ElevenLabs retornou um áudio vazio.")

    _write_cache(cache_path, audio)
    return audio


__all__ = [
    "ELEVENLABS_TTS_VERSION",
    "ELEVENLABS_MODEL_ID",
    "ElevenLabsTTSError",
    "VOICE_SETTINGS",
    "elevenlabs_configurada",
    "obter_credenciais",
    "obter_credenciais_com_origem",
    "obter_status_configuracao",
    "sintetizar_fala",
]
