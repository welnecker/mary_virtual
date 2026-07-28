from __future__ import annotations

from typing import Any

from .beat_graph import obter_beat, proximo_beat_padrao
from .canonical_screenplay import linhas_canonicas_do_beat


SCREENPLAY_EXECUTOR_VERSION = "casada-frustrada-screenplay-lock-v4-canonical-only"


def _text(value: Any) -> str:
    return str(value or "").strip()


def construir_trava_de_roteiro(beat_id: str) -> dict[str, Any]:
    beat = obter_beat(beat_id) or {}
    canonical_lines = linhas_canonicas_do_beat(beat_id)
    return {
        "version": SCREENPLAY_EXECUTOR_VERSION,
        "current_beat": beat_id,
        "canonical_lines": canonical_lines,
        "mandatory_objective": "\n".join(canonical_lines),
        "canonical_text_must_be_preserved": True,
        "current_route": _text(beat.get("route")),
        "gate": _text(beat.get("gate")),
        "next_beat_locked": proximo_beat_padrao(beat_id),
        "rule": (
            "Interprete somente as canonical_lines do beat atual. Responda ao improviso "
            "do usuário com uma ponte curta e natural, sem alterar, repetir desnecessariamente "
            "ou antecipar linhas do roteiro."
        ),
    }


__all__ = ["SCREENPLAY_EXECUTOR_VERSION", "construir_trava_de_roteiro"]
