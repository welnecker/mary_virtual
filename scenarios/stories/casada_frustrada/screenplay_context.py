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
from .screenplay_sheet_repository import (
    SCREENPLAY_SOURCE_VERSION,
    ScreenplaySheetError,
    carregar_trecho_por_rota,
)


SCREENPLAY_CONTEXT_VERSION = "casada-frustrada-screenplay-context-v2-google-sheets"


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


def _obter_trecho_local(route_id: str) -> tuple[str, str]:
    if route_id == "supermarket_encounter":
        return (
            _join_sections(
                _between(SUPERMARKET_DIALOGUE, "PRIMEIRO CONTATO", "PENSAMENTO APÓS A PRIMEIRA DESPEDIDA"),
                _between(SUPERMARKET_DIALOGUE, "PENSAMENTO APÓS A PRIMEIRA DESPEDIDA", "REENCONTRO"),
            ),
            "primeiro contato no supermercado",
        )
    if route_id == "aisle_flirtation":
        return (
            _between(SUPERMARKET_DIALOGUE, "REENCONTRO", "ATÉ O CARRO"),
            "reencontro e aproximação no supermercado",
        )
    if route_id == "phone_exchange":
        return (
            _join_sections(
                _between(SUPERMARKET_DIALOGUE, "ATÉ O CARRO", "PENSAMENTO DEPOIS DA TROCA"),
                _between(SUPERMARKET_DIALOGUE, "PENSAMENTO DEPOIS DA TROCA", "REGRAS DO BLOCO"),
            ),
            "até o carro, contato e despedida",
        )
    if route_id == "messages":
        return MESSAGES_DIALOGUE.strip(), "casa e primeiras mensagens"
    if route_id == "hidden_call":
        return HIDDEN_CALL_DIALOGUE.strip(), "chamada de vídeo escondida"
    if route_id == "secret_meeting_plan":
        return SECRET_MEETING_PLAN_DIALOGUE.strip(), "madrugada e encontro marcado"
    if route_id in {
        "secret_meeting",
        "growing_tension",
        "intimacy",
        "climax",
        "aftercare",
        "future_secret",
    }:
        return SECRET_MEETING_DIALOGUE.strip(), "encontro secreto"
    return "", ""


def obter_trecho_roteiro(route: str, current_beat: str = "") -> dict[str, Any]:
    route_id = str(route or "").strip()
    beat_id = str(current_beat or "").strip()

    try:
        remote = carregar_trecho_por_rota(route_id, beat_id)
        excerpt = str(remote.get("excerpt", "")).strip()
        if excerpt:
            return {
                "version": SCREENPLAY_CONTEXT_VERSION,
                "source_version": SCREENPLAY_SOURCE_VERSION,
                "source": "google_sheets",
                "spreadsheet_id": remote.get("spreadsheet_id", ""),
                "worksheet": remote.get("worksheet", ""),
                "route": route_id,
                "current_beat": beat_id,
                "block": route_id,
                "excerpt": excerpt,
                "rows": remote.get("rows", 0),
                "usage": (
                    "Trecho oficial do roteiro carregado da planilha. Interpretar seus movimentos "
                    "com naturalidade; não recitar linhas, não executar tudo de uma vez e não "
                    "antecipar outro bloco. Campos de condição, função dramática e próxima rota "
                    "orientam a atuação, mas não devem aparecer literalmente na resposta."
                ),
            }
    except ScreenplaySheetError:
        pass

    excerpt, block = _obter_trecho_local(route_id)
    return {
        "version": SCREENPLAY_CONTEXT_VERSION,
        "source_version": IMMERSIVE_SCREENPLAY_VERSION,
        "source": "local_fallback",
        "route": route_id,
        "current_beat": beat_id,
        "block": block,
        "excerpt": excerpt,
        "usage": (
            "Fallback local do roteiro. Interpretar seus movimentos com naturalidade; "
            "não recitar linhas, não executar tudo de uma vez e não antecipar outro bloco."
        ),
    }


__all__ = [
    "SCREENPLAY_CONTEXT_VERSION",
    "obter_trecho_roteiro",
]
