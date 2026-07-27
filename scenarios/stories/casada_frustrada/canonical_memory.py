from __future__ import annotations

from copy import deepcopy
import re
import unicodedata
from typing import Any


CANONICAL_MEMORY_VERSION = "casada-frustrada-canonical-memory-v2-factual-meetings"

ROUTE_ORDER = {
    "supermarket_encounter": 0,
    "aisle_flirtation": 1,
    "phone_exchange": 2,
    "messages": 3,
    "hidden_call": 4,
    "secret_meeting_plan": 5,
    "secret_meeting": 6,
    "growing_tension": 7,
    "intimacy": 8,
    "climax": 9,
    "aftercare": 10,
    "future_secret": 11,
}

MEMORY_CATALOG: dict[str, dict[str, str]] = {
    "met_at_supermarket": {
        "category": "shared_origin",
        "text": "Mary conheceu o usuário em um supermercado de bairro depois de quase atingi-lo com o carrinho de compras.",
    },
    "neighbors_at_plaza": {
        "category": "shared_origin",
        "text": "Mary e o usuário descobriram no primeiro encontro que são vizinhos no Plaza.",
    },
    "helped_with_groceries": {
        "category": "shared_origin",
        "text": "O usuário ajudou Mary a levar e guardar as compras no carro.",
    },
    "exchanged_phone_numbers": {
        "category": "intimacy_milestone",
        "text": "Depois da ajuda com as compras, Mary conseguiu o número do usuário e o contato entre os dois ficou estabelecido.",
    },
    "first_private_messages": {
        "category": "intimacy_milestone",
        "text": "Mary iniciou uma conversa privada por mensagens depois de chegar em casa.",
    },
    "first_hidden_video_call": {
        "category": "intimacy_milestone",
        "text": "Mary se isolou no banheiro para fazer escondida a primeira chamada de vídeo íntima com o usuário.",
    },
    "secret_meeting_planned": {
        "category": "shared_secret",
        "text": "Mary e o usuário combinaram um encontro secreto longe do condomínio.",
    },
    "first_secret_meeting": {
        "category": "shared_secret",
        "text": "Mary e o usuário já tiveram o primeiro encontro secreto em um lugar combinado.",
    },
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _history(messages: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in messages[-80:]:
        if not isinstance(item, dict):
            continue
        role = _text(item.get("role"))
        content = _text(item.get("content"))
        if role in {"user", "assistant"} and content:
            parts.append(_normalize(content))
    return " ".join(parts)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def criar_memoria_canonica_padrao() -> dict[str, Any]:
    return {"version": CANONICAL_MEMORY_VERSION, "unlocked": [], "facts": {}}


def normalizar_memoria_canonica(value: Any) -> dict[str, Any]:
    memory = criar_memoria_canonica_padrao()
    if isinstance(value, dict):
        unlocked = value.get("unlocked")
        facts = value.get("facts")
        if isinstance(unlocked, list):
            memory["unlocked"] = [
                memory_id
                for memory_id in dict.fromkeys(_text(item) for item in unlocked)
                if memory_id in MEMORY_CATALOG
            ]
        if isinstance(facts, dict):
            memory["facts"] = {
                memory_id: deepcopy(fact)
                for memory_id, fact in facts.items()
                if memory_id in MEMORY_CATALOG and isinstance(fact, dict)
            }
    memory["version"] = CANONICAL_MEMORY_VERSION
    return memory


def _unlock(memory: dict[str, Any], memory_id: str, *, route: str, beat: str, evidence: str) -> None:
    if memory_id not in MEMORY_CATALOG:
        return
    if memory_id not in memory["unlocked"]:
        memory["unlocked"].append(memory_id)
    catalog = MEMORY_CATALOG[memory_id]
    memory["facts"][memory_id] = {
        "id": memory_id,
        "category": catalog["category"],
        "text": catalog["text"],
        "established_route": route,
        "established_beat": beat,
        "evidence": evidence,
    }


def _forget_route_only(memory: dict[str, Any], memory_id: str) -> None:
    fact = memory.get("facts", {}).get(memory_id)
    if not isinstance(fact, dict):
        return
    if fact.get("evidence") not in {"history_or_route", "route"}:
        return
    memory["unlocked"] = [item for item in memory.get("unlocked", []) if item != memory_id]
    memory.get("facts", {}).pop(memory_id, None)


def atualizar_memoria_canonica(
    value: Any,
    *,
    messages: list[dict[str, Any]],
    route: str,
    beat: str,
) -> dict[str, Any]:
    memory = normalizar_memoria_canonica(value)
    history = _history(messages)
    route = _text(route)
    beat = _text(beat)
    route_rank = ROUTE_ORDER.get(route, -1)

    met = (
        _contains_any(history, ("carrinho", "quase te atropel", "susto"))
        and _contains_any(history, ("desculpa", "mercado", "compras"))
    ) or route_rank >= ROUTE_ORDER["aisle_flirtation"]
    if met:
        _unlock(memory, "met_at_supermarket", route=route, beat=beat, evidence="history_or_route")

    if _contains_any(history, ("moro no bloco", "bloco a", "bloco b", "plaza", "somos vizinhos", "praticamente vizinho")):
        _unlock(memory, "neighbors_at_plaza", route=route, beat=beat, evidence="conversation")

    groceries_helped = (
        _contains_any(history, ("ajuda ate o carro", "ajudou com as compras", "porta malas", "banco de tras"))
        and _contains_any(history, ("sacola", "compras", "carrinho", "pacote"))
    ) or route_rank >= ROUTE_ORDER["phone_exchange"]
    if groceries_helped:
        _unlock(memory, "helped_with_groceries", route=route, beat=beat, evidence="history_or_route")

    phone_established = (
        _contains_any(history, ("me passa seu numero", "salva meu numero", "anotado", "contato", "a gente se fala"))
        and (_contains_any(history, ("numero", "celular", "telefone")) or bool(re.search(r"\b\d{7,}\b", history)))
    ) or route_rank >= ROUTE_ORDER["messages"]
    if phone_established:
        _unlock(memory, "exchanged_phone_numbers", route=route, beat=beat, evidence="history_or_route")

    private_messages = _contains_any(
        history,
        ("sou eu a mary", "por mensagem", "mandar aquele primeiro oi", "estou aqui no banheiro", "falar com voce em paz"),
    ) or route_rank >= ROUTE_ORDER["messages"]
    if private_messages:
        _unlock(memory, "first_private_messages", route=route, beat=beat, evidence="history_or_route")

    hidden_call = _contains_any(
        history,
        ("chamada de video", "pode me chamar por video", "ta me vendo", "camera ligada", "celular aqui na bancada"),
    ) or route_rank >= ROUTE_ORDER["hidden_call"]
    if hidden_call:
        _unlock(memory, "first_hidden_video_call", route=route, beat=beat, evidence="history_or_route")

    meeting_proposed = _contains_any(
        history,
        ("o que acha de um motel", "quero marcar um lugar", "vamos nos encontrar", "quero te encontrar", "motel status"),
    )
    meeting_accepted = _contains_any(
        history,
        ("combinado", "fechado", "eu topo", "pode ser", "amanha ao meio dia", "amanha meio dia", "te encontro la"),
    )
    if meeting_proposed and meeting_accepted:
        _unlock(memory, "secret_meeting_planned", route=route, beat=beat, evidence="conversation")
    else:
        _forget_route_only(memory, "secret_meeting_planned")

    meeting_happened = _contains_any(
        history,
        ("cheguei no motel", "estou no motel", "to no motel", "aqui no quarto", "peguei a suite", "entrei na suite"),
    )
    if meeting_happened:
        _unlock(memory, "first_secret_meeting", route=route, beat=beat, evidence="conversation")
    else:
        _forget_route_only(memory, "first_secret_meeting")

    return memory


def memoria_canonica_para_prompt(value: Any) -> dict[str, Any]:
    memory = normalizar_memoria_canonica(value)
    facts = [
        memory["facts"][memory_id]
        for memory_id in memory["unlocked"]
        if memory_id in memory["facts"]
    ]
    return {
        "version": CANONICAL_MEMORY_VERSION,
        "shared_past": [fact["text"] for fact in facts],
        "unlocked_ids": list(memory["unlocked"]),
        "authority": (
            "Estes fatos são passado compartilhado já vivido. Nunca tratá-los como hipótese, "
            "primeira vez ou objetivo futuro; não repetir ações usadas para estabelecê-los."
        ),
    }


__all__ = [
    "CANONICAL_MEMORY_VERSION",
    "MEMORY_CATALOG",
    "criar_memoria_canonica_padrao",
    "normalizar_memoria_canonica",
    "atualizar_memoria_canonica",
    "memoria_canonica_para_prompt",
]