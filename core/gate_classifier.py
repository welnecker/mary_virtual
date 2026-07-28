from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping

from .story_models import GateDecision


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


_GLOBAL_REJECTION_MARKERS = (
    "nem pensar",
    "prefiro nao",
    "de jeito nenhum",
    "nao quero continuar",
    "quero encerrar",
    "vou embora",
    "para por aqui",
    "pode encerrar",
    "nao aceito",
    "nao quero",
    "nao vou",
)

_GENERIC_ACCEPTANCE_MARKERS = (
    "sim",
    "claro",
    "com certeza",
    "pode",
    "vamos",
    "aceito",
    "quero",
    "tudo bem",
    "ta bom",
    "beleza",
    "por que nao",
    "pode deixar",
    "feito",
    "pronto",
    "cheguei",
    "estou aqui",
)

_GATE_ACCEPTANCE: Mapping[str, tuple[str, ...]] = {
    "wellbeing_confirmation": (
        "to bem", "estou bem", "tudo bem", "ta tudo bem", "sem problema",
        "sem problemas", "foi so um susto", "nao machucou", "nao me machucou",
        "nao doeu", "tranquilo", "ta tranquilo", "ta de boa", "tenho certeza",
        "tenho sim", "sim",
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
        "anota", "meu numero", "pode pegar", "te passo", "claro",
    ),
}

_GATE_REJECTION: Mapping[str, tuple[str, ...]] = {
    "plaza_answer": ("nao moro", "nao conheco o plaza"),
    "accept_help_car": ("nao vou esperar", "nao posso ajudar", "nao vou ajudar"),
    "phone_acceptance": (
        "nao passo meu numero", "nao quero passar meu numero", "nao quero trocar telefone",
    ),
}


def classify_gate(gate: str, user_text: str) -> GateDecision:
    """Classifica somente a resposta ao gate atual; nunca escolhe rota ou beat."""

    normalized = _normalize(user_text)
    if not normalized:
        return GateDecision.UNCLEAR

    gate_id = str(gate or "").strip()

    acceptance_markers = _GATE_ACCEPTANCE.get(gate_id, ())
    if any(_normalize(marker) in normalized for marker in acceptance_markers):
        return GateDecision.ACCEPTED

    rejection_markers = _GATE_REJECTION.get(gate_id, ())
    if any(_normalize(marker) in normalized for marker in rejection_markers):
        return GateDecision.REJECTED

    if any(_normalize(marker) in normalized for marker in _GLOBAL_REJECTION_MARKERS):
        return GateDecision.REJECTED

    if gate_id and any(_normalize(marker) in normalized for marker in _GENERIC_ACCEPTANCE_MARKERS):
        return GateDecision.ACCEPTED

    return GateDecision.UNCLEAR


__all__ = ["classify_gate"]
