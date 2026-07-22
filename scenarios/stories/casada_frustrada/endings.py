from __future__ import annotations

from copy import deepcopy
from typing import Any


ENDINGS_VERSION = "casada-frustrada-endings-v1"

ENDINGS: dict[str, Any] = {
    "satisfying_completion": {
        "requires": {
            "climax_reached": True,
            "satisfaction_detected": True,
        },
        "direction": (
            "Mary encerra satisfeita, ainda consciente do segredo, com uma fala curta "
            "que reconhece o prazer e deixa ou não um próximo contato, sem abrir nova cena."
        ),
        "show_end_marker": True,
    },
    "future_secret": {
        "requires": {
            "current_route": "future_secret",
        },
        "direction": (
            "Mary define uma regra discreta para o próximo contato e encerra esta história. "
            "O gancho não inicia outro encontro agora."
        ),
        "show_end_marker": True,
    },
    "mutual_resolution": {
        "requires": {
            "ending_ready": True,
        },
        "direction": (
            "Encerre quando a tensão central estiver resolvida. Mary pode terminar com "
            "desejo, consequência ou provocação, mas não recapitular toda a história."
        ),
        "show_end_marker": True,
    },
    "boundary_respected": {
        "requires": {
            "ending_reason": "user_boundary",
        },
        "direction": (
            "Mary respeita o limite sem insistir, atacar ou usar o casamento como culpa. "
            "Ela encerra com dignidade e clareza."
        ),
        "show_end_marker": True,
    },
    "early_exit": {
        "requires": {
            "user_disengaged": True,
        },
        "direction": (
            "Mary aceita a saída do usuário e encerra de forma breve, natural e definitiva."
        ),
        "show_end_marker": True,
    },
    "safety_limit": {
        "requires": {
            "ending_trigger": "safety_limit",
        },
        "direction": (
            "A história atingiu 28 interações. Resolva imediatamente a pendência atual "
            "com uma fala final coerente, sem introduzir novo encontro, conflito ou ato."
        ),
        "show_end_marker": True,
    },
}


def obter_encerramentos() -> dict[str, Any]:
    return deepcopy(ENDINGS)


__all__ = ["ENDINGS_VERSION", "ENDINGS", "obter_encerramentos"]
