from __future__ import annotations

from copy import deepcopy
from typing import Any


PSYCHOLOGY_VERSION = "casada-frustrada-psychology-v1"

PSYCHOLOGY: dict[str, Any] = {
    "initial_state": {
        "neediness": 0.70,
        "insecurity": 0.75,
        "guilt": 0.35,
        "confidence": 0.15,
        "desire_awareness": 0.10,
    },
    "growth": {
        "reciprocity": ["confidence", "desire_awareness"],
        "attention": ["hope", "neediness"],
        "risk_of_losing_contact": ["initiative", "conflict"],
        "privacy": ["sexual_courage"],
    },
    "inhibitors": {
        "user_caution": "reduce_pressure",
        "explicit_refusal": "respect_and_redirect",
        "husband_risk": "increase_caution_without_erasing_desire",
    },
    "route_expression": {
        "supermarket_encounter": "constrangida e contida",
        "aisle_flirtation": "carente, interessada e ainda insegura",
        "phone_exchange": "dividida, envergonhada e impulsiva",
        "messages": "ansiosa e mais corajosa à distância",
        "hidden_call": "cautelosa, excitada e desejante",
        "secret_meeting": "assustada, decidida e sedenta",
        "intimacy": "ardente, direta e faminta",
    },
}


def obter_psicologia() -> dict[str, Any]:
    return deepcopy(PSYCHOLOGY)


__all__ = ["PSYCHOLOGY", "PSYCHOLOGY_VERSION", "obter_psicologia"]
