from __future__ import annotations

import re


def sanitize_mary_output(text: str) -> str:
    """Remove rubricas narrativas para manter o balão apenas com fala."""
    value = str(text or "").strip()
    if not value:
        return value

    value = re.sub(r"\([^()]*\)", "", value, flags=re.S)
    # O Diretor é o único responsável por rubricas/ações. Remove ações
    # narradas pelo modelo de diálogo entre asteriscos para evitar duplicidade.
    value = re.sub(r"\*[^*]+\*", "", value, flags=re.S)
    value = re.sub(r"\n{3,}", "\n\n", value)

    lines = [line.rstrip() for line in value.splitlines()]
    return "\n".join(lines).strip()



_ACTION_LINE_PATTERNS = [
    r"^\s*(?:eu\s+)?(?:me\s+)?levanto\b",
    r"^\s*(?:eu\s+)?sento\b",
    r"^\s*(?:eu\s+)?me\s+sento\b",
    r"^\s*(?:eu\s+)?caminho\b",
    r"^\s*(?:eu\s+)?ando\b",
    r"^\s*(?:eu\s+)?pego\b",
    r"^\s*(?:eu\s+)?agarro\b",
    r"^\s*(?:eu\s+)?seguro\b",
    r"^\s*(?:eu\s+)?olho\s+(?:para|pra)\b",
    r"^\s*(?:eu\s+)?viro\b",
    r"^\s*(?:eu\s+)?me\s+viro\b",
    r"^\s*(?:eu\s+)?deito\b",
    r"^\s*(?:eu\s+)?me\s+deito\b",
    r"^\s*(?:eu\s+)?aproximo\b",
    r"^\s*(?:eu\s+)?me\s+aproximo\b",
    r"^\s*(?:eu\s+)?afasto\b",
    r"^\s*(?:eu\s+)?me\s+afasto\b",
    r"^\s*(?:eu\s+)?fico\s+(?:olhando|parada|quieta|em silêncio)\b",
    r"^\s*não\s+me\s+mexo\b",
]


def looks_like_action_narration(text: str) -> bool:
    """Detecta rubrica corporal em primeira pessoa escapando para o balão."""
    value = str(text or "").strip()
    if not value:
        return False

    # Ações entre asteriscos são sempre rubrica.
    if re.search(r"\*[^*]+\*", value, flags=re.S):
        return True

    for raw_line in value.splitlines():
        line = raw_line.strip(" —-\t")
        if not line:
            continue
        for pattern in _ACTION_LINE_PATTERNS:
            if re.search(pattern, line, flags=re.I):
                return True

    return False
