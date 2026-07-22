from __future__ import annotations

from copy import deepcopy
from typing import Any


ENDINGS_VERSION = "vizinha-endings-v2-compact"

ENDINGS: dict[str, Any] = {
    "satisfying_completion": {
        "requires": {
            "climax_reached": True,
            "satisfaction_detected": True,
        },
        "direction": (
            "Mary encerra com uma fala curta, satisfeita e provocante, retomando a situação "
            "da porta sem repetir toda a cena e sem criar outro conflito."
        ),
        "show_end_marker": True,
    },
    "mutual_resolution": {
        "requires": {
            "ending_ready": True,
        },
        "direction": (
            "Encerre quando a tensão principal já estiver resolvida. Mary pode deixar humor, "
            "afeto ou provocação leve, mas não abrir outro arco dentro desta experiência."
        ),
        "show_end_marker": True,
    },
    "coffee_hook": {
        "requires": {
            "current_route": "coffee_invitation",
        },
        "direction": (
            "Mary resolve a situação da porta e deixa um convite específico para outro encontro. "
            "O convite é fechamento desta história, não continuação imediata."
        ),
        "show_end_marker": True,
    },
    "boundary_respected": {
        "requires": {
            "ending_reason": "user_boundary",
        },
        "direction": (
            "Mary respeita o limite, encerra sem culpa, punição ou insistência e preserva a própria dignidade."
        ),
        "show_end_marker": True,
    },
    "early_exit": {
        "requires": {
            "user_disengaged": True,
        },
        "direction": "Mary aceita a saída do usuário e encerra de forma breve, natural e definitiva.",
        "show_end_marker": True,
    },
    "safety_limit": {
        "requires": {
            "ending_trigger": "safety_limit",
        },
        "direction": (
            "A história atingiu o teto de ritmo. Resolva o elemento central imediatamente com uma "
            "fala final coerente; não recapitule nem introduza novidade."
        ),
        "show_end_marker": True,
    },
}


def obter_encerramentos() -> dict[str, Any]:
    return deepcopy(ENDINGS)


__all__ = ["ENDINGS_VERSION", "ENDINGS", "obter_encerramentos"]
