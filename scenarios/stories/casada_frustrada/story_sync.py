from __future__ import annotations

import re
import unicodedata
from typing import Any

from .beat_graph import obter_beat


STORY_SYNC_VERSION = "casada-frustrada-story-sync-v2-semantic-functions"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _history(messages: list[dict[str, Any]], *, role: str = "") -> str:
    parts: list[str] = []
    for item in messages[-24:]:
        if not isinstance(item, dict):
            continue
        item_role = _text(item.get("role"))
        content = _text(item.get("content"))
        if item_role not in {"user", "assistant"} or not content:
            continue
        if role and item_role != role:
            continue
        parts.append(_normalize(content))
    return " ".join(parts)


def _latest(messages: list[dict[str, Any]], role: str) -> str:
    for item in reversed(messages):
        if not isinstance(item, dict):
            continue
        if _text(item.get("role")) == role:
            return _normalize(item.get("content"))
    return ""


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _resolve_aisle_beat(messages: list[dict[str, Any]], legacy_beat: str) -> str:
    assistant_history = _history(messages, role="assistant")
    latest_assistant = _latest(messages, "assistant")

    # A posição corresponde à função que ainda aguarda resposta ou ao próximo
    # movimento não realizado; não ao último identificador persistido.
    if _contains_any(
        latest_assistant,
        ("voce me espera", "preciso de ajuda ate o carro", "ajudinha ate o carro"),
    ):
        return "ask_wait_help_car"
    if _contains_any(
        assistant_history,
        ("e sua vez no caixa", "passa suas compras", "colocar as coisas na esteira"),
    ):
        return "ask_wait_help_car"
    if _contains_any(
        assistant_history,
        ("na minha casa e cerveja e futebol", "cerveja e futebol todo fim de semana"),
    ):
        return "checkout_turn"
    if _contains_any(
        latest_assistant,
        (
            "isso e tipico de solteiro",
            "carrinho de solteiro",
            "voce mora sozinho",
            "e solteiro",
            "passei longe do palpite",
        ),
    ):
        return "cart_single_guess"
    if _contains_any(
        assistant_history,
        ("mercado ta cheio", "mercado esta cheio", "fila do caixa ta desanimadora"),
    ):
        return "cart_single_guess"
    if _contains_any(
        assistant_history,
        ("recuperado do susto", "cruzei com voce de novo", "te encontrei de novo"),
    ):
        return "market_crowded"
    if _contains_any(
        assistant_history,
        ("a gente se ve por la", "vou terminar minhas compras", "tchauzinho"),
    ):
        return "second_encounter"
    return legacy_beat or "second_encounter"


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
    if video_offered or attraction_admitted:
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
    elif route == "aisle_flirtation" or beat_id in {
        "second_encounter",
        "market_crowded",
        "cart_single_guess",
        "home_weekend_routine",
        "checkout_turn",
        "ask_wait_help_car",
    }:
        resolved = _resolve_aisle_beat(messages, beat_id)
        if resolved != beat_id:
            beat_id = resolved
            reason = "conversation_confirms_completed_aisle_functions"

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
