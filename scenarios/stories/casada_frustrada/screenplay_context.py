from __future__ import annotations

from typing import Any

from .immersive_screenplay import (
    HIDDEN_CALL_DIALOGUE,
    IMMERSIVE_SCREENPLAY_VERSION,
    MESSAGES_DIALOGUE,
    SECRET_MEETING_DIALOGUE,
    SECRET_MEETING_PLAN_DIALOGUE,
    SUPERMARKET_DIALOGUE,
)


SCREENPLAY_CONTEXT_VERSION = "casada-frustrada-screenplay-context-v1"


def _between(text: str, start: str, end: str | None = None) -> str:
    marker = f"\n{start}\n"
    position = text.find(marker)
    if position < 0:
        if text.startswith(f"{start}\n"):
            position = -1
            marker = f"{start}\n"
        else:
            return ""
    content_start = position + len(marker)
    if not end:
        return text[content_start:].strip()
    end_marker = f"\n{end}\n"
    content_end = text.find(end_marker, content_start)
    if content_end < 0:
        return text[content_start:].strip()
    return text[content_start:content_end].strip()


def _join_sections(*sections: str) -> str:
    return "\n\n".join(section.strip() for section in sections if section.strip())


def obter_trecho_roteiro(route: str) -> dict[str, Any]:
    route_id = str(route or "").strip()

    if route_id == "supermarket_encounter":
        excerpt = _join_sections(
            _between(SUPERMARKET_DIALOGUE, "PRIMEIRO CONTATO", "PENSAMENTO APÓS A PRIMEIRA DESPEDIDA"),
            _between(SUPERMARKET_DIALOGUE, "PENSAMENTO APÓS A PRIMEIRA DESPEDIDA", "REENCONTRO"),
        )
        block = "primeiro contato no supermercado"
    elif route_id == "aisle_flirtation":
        excerpt = _join_sections(
            _between(SUPERMARKET_DIALOGUE, "REENCONTRO", "ATÉ O CARRO"),
        )
        block = "reencontro e aproximação no supermercado"
    elif route_id == "phone_exchange":
        excerpt = _join_sections(
            _between(SUPERMARKET_DIALOGUE, "ATÉ O CARRO", "PENSAMENTO DEPOIS DA TROCA"),
            _between(SUPERMARKET_DIALOGUE, "PENSAMENTO DEPOIS DA TROCA", "REGRAS DO BLOCO"),
        )
        block = "até o carro, contato e despedida"
    elif route_id == "messages":
        excerpt = MESSAGES_DIALOGUE.strip()
        block = "casa e primeiras mensagens"
    elif route_id == "hidden_call":
        excerpt = HIDDEN_CALL_DIALOGUE.strip()
        block = "chamada de vídeo escondida"
    elif route_id == "secret_meeting_plan":
        excerpt = SECRET_MEETING_PLAN_DIALOGUE.strip()
        block = "madrugada e encontro marcado"
    elif route_id in {
        "secret_meeting",
        "growing_tension",
        "intimacy",
        "climax",
        "aftercare",
        "future_secret",
    }:
        excerpt = SECRET_MEETING_DIALOGUE.strip()
        block = "encontro secreto"
    else:
        excerpt = ""
        block = ""

    return {
        "version": SCREENPLAY_CONTEXT_VERSION,
        "source_version": IMMERSIVE_SCREENPLAY_VERSION,
        "route": route_id,
        "block": block,
        "excerpt": excerpt,
        "usage": (
            "Trecho oficial do roteiro. Interpretar seus movimentos com naturalidade; "
            "não recitar linhas, não executar tudo de uma vez e não antecipar outro bloco."
        ),
    }


__all__ = [
    "SCREENPLAY_CONTEXT_VERSION",
    "obter_trecho_roteiro",
]
