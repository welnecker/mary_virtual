from __future__ import annotations

import re
import unicodedata
from typing import Any

from .beat_graph import obter_beat


STORY_SYNC_VERSION = "casada-frustrada-story-sync-v1"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _history(messages: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in messages[-24:]:
        if not isinstance(item, dict):
            continue
        role = _text(item.get("role"))
        content = _text(item.get("content"))
        if role in {"user", "assistant"} and content:
            parts.append(_normalize(content))
    return " ".join(parts)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _resolve_messages_beat(history: str) -> str:
    video_accepted = _contains_any(
        history,
        (
            "pode me chamar por video",
            "pode chamar por video",
            "chama por video",
            "liga a camera",
            "aceito a chamada",
        ),
    )
    video_offered = _contains_any(
        history,
        (
            "posso te chamar por video",
            "quero te ver de verdade",
            "chamada de video",
            "te chamar por video",
        ),
    )
    attraction_admitted = _contains_any(
        history,
        (
            "te achei muito atraente",
            "eu te achei atraente",
            "voce me atrai",
            "estou atraida por voce",
            "to atraida por voce",
            "voce e muito atraente",
        ),
    )
    neediness_admitted = _contains_any(
        history,
        (
            "deve me achar muito carente",
            "me achar carente",
            "pareco carente",
            "louca talvez",
            "estou carente",
            "to carente",
        ),
    )
    privacy_established = _contains_any(
        history,
        (
            "estou aqui no banheiro",
            "to aqui no banheiro",
            "esconderijo no banheiro",
            "indo ao banheiro",
            "conversar mais a vontade",
            "falar com voce em paz",
        ),
    )

    if video_accepted:
        return "camera_setup"
    if video_offered:
        return "offer_video"
    if attraction_admitted:
        return "offer_video"
    if neediness_admitted:
        return "admit_attraction"
    if privacy_established:
        return "admit_neediness"
    return "home_first_message"


def reconciliar_posicao_narrativa(
    *,
    messages: list[dict[str, Any]],
    legacy_route: str,
    legacy_beat: str,
) -> dict[str, Any]:
    history = _history(messages)
    route = _text(legacy_route)
    beat_id = _text(legacy_beat)
    reason = "legacy_cursor_consistent"

    message_channel_established = _contains_any(
        history,
        (
            "sou eu a mary",
            "salva meu numero",
            "por mensagem",
            "conversando por mensagens",
            "estou aqui no banheiro",
            "to aqui no banheiro",
            "esconderijo no banheiro",
            "falar com voce em paz",
        ),
    )
    video_context_established = _contains_any(
        history,
        (
            "ta me vendo",
            "esta me vendo",
            "colocar o celular aqui na bancada",
            "camera ligada",
            "na chamada de video",
        ),
    )

    if video_context_established:
        route = "hidden_call"
        beat_id = "camera_setup"
        reason = "conversation_confirms_video_call"
    elif message_channel_established:
        route = "messages"
        beat_id = _resolve_messages_beat(history)
        reason = "conversation_confirms_private_messages"

    beat = obter_beat(beat_id) or {}
    if beat:
        route = _text(beat.get("route")) or route

    return {
        "version": STORY_SYNC_VERSION,
        "route": route,
        "beat": beat_id,
        "reason": reason,
        "legacy_route": _text(legacy_route),
        "legacy_beat": _text(legacy_beat),
        "legacy_cursor_overridden": (
            route != _text(legacy_route) or beat_id != _text(legacy_beat)
        ),
    }


__all__ = [
    "STORY_SYNC_VERSION",
    "reconciliar_posicao_narrativa",
]
