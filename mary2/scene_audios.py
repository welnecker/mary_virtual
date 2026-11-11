"""Optional local MP3 playback keyed to the authored script order.

A recording is usable only when the MP3 AND literal transcript are present.
Partial configurations fail closed instead of silently changing the scene.
"""
from __future__ import annotations

from pathlib import Path
import re

SCENE_AUDIO_DIR = Path(__file__).resolve().parent / "assets" / "audios"


def scene_audio_filename(script_name: str, order: int) -> str:
    name = str(script_name or "").strip()
    try:
        number = int(order or 0)
    except (TypeError, ValueError):
        return ""
    if not name or number <= 0 or name in {".", ".."}:
        return ""
    if ".." in name or any(c in name for c in '/\\\x00') or re.search(r'[<>:"|?*]', name):
        return ""
    return f"{name}_{number:03d}.mp3"


def resolve_scene_audio(
    script_name: str,
    order: int,
    transcript: str,
    *,
    folder: Path = SCENE_AUDIO_DIR,
) -> Path | None:
    """Return a valid MP3 path, or None for a completely unconfigured line.

    A half-configured recording must not advance a scripted turn or fabricate
    speech. Never call this for an emotional loop replacing the authored line.
    """
    speech = str(transcript or "").strip()
    filename = scene_audio_filename(script_name, order)
    path = folder / filename if filename else None
    exists = bool(path and path.is_file())
    if not speech and not exists:
        return None
    if not filename:
        raise ValueError("FALA GRAVADA: ROTEIRO/ORDEM inválidos.")
    if not speech:
        raise ValueError(f"FALA GRAVADA: falta transcrição para {filename}.")
    if not exists:
        raise ValueError(f"FALA GRAVADA: arquivo MP3 ausente: {filename}.")
    return path
