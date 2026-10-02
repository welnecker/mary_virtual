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
