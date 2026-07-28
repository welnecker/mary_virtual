from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping

from .story_models import GateDecision


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


_REJECTION_MARKERS = (
    "nao",
    "não",
    "nem pensar",
    "prefiro nao",
    "prefiro não",
    "de jeito nenhum",
    "vou embora",
    "tchau",
)

_GATE_ACCEPTANCE: Mapping[str, tuple[str, ...]] = {
    "wellbeing_confirmation": (
        "to bem", "estou bem", "tudo bem", "sem problema", "foi so um susto",
        "foi só um susto", "nao machucou", "não machucou", "tranquilo",
    ),
    "plaza_answer": (
        "moro", "plaza", "bloco", "mudei", "sou vizinho", "sou vizinha",
    ),
    "relationship_answer": (
        "solteiro", "casado", "namorando", "separado", "divorciado", "sozinho",
    ),
    "accept_help_car": (
        "espero", "ajudo", "vou ajudar", "claro", "pode deixar", "vamos",
    ),
    "phone_acceptance": (
        "anota", "meu numero", "meu número", "pode pegar", "te passo", "claro",
    ),
}


def classify_gate(gate: str, user_text: str) -> GateDecision:
    """Classifica somente o gate atual; nunca escolhe rota ou beat."""

    normalized = _normalize(user_text)
    if not normalized:
        return GateDecision.UNCLEAR

    if any(_normalize(marker) in normalized for marker in _REJECTION_MARKERS):
        return GateDecision.REJECTED

    markers = _GATE_ACCEPTANCE.get(str(gate or "").strip(), ())
    if any(_normalize(marker) in normalized for marker in markers):
        return GateDecision.ACCEPTED

    return GateDecision.UNCLEAR


__all__ = ["classify_gate"]
