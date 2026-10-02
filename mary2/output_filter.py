from __future__ import annotations

import re


_THOUGHT_RE = re.compile(
    r"\[(?:PENSAMENTO|INTEN(?:C|Ç)(?:A|Ã)O)\]\s*(.*?)(?=\n\s*\[FALA\]|$)",
    flags=re.I | re.S,
)
_SPEECH_RE = re.compile(
    r"\[FALA\]\s*(.*?)(?=\n\s*\[(?:PENSAMENTO|INTEN(?:C|Ç)(?:A|Ã)O)\]|$)",
    flags=re.I | re.S,
)


def parse_mary_response(text: str) -> tuple[str, str]:
    """Separa pensamento privado curto da fala audível de Mary."""
    value = str(text or "").strip()
    if not value:
        return "", ""

    thought_match = _THOUGHT_RE.search(value)
    speech_match = _SPEECH_RE.search(value)

    intent = thought_match.group(1).strip() if thought_match else ""
    speech = speech_match.group(1).strip() if speech_match else value

    # Nunca deixa tags de protocolo vazarem para a interface.
    speech = re.sub(r"^\s*\[(?:PENSAMENTO|INTEN(?:C|Ç)(?:A|Ã)O|FALA)\]\s*", "", speech, flags=re.I)
    intent = re.sub(r"\s+", " ", intent).strip()

    # Intenção é um balão curto: uma frase, sem parágrafo.
    if intent:
        intent = intent.splitlines()[0].strip()
        if len(intent) > 180:
            intent = intent[:177].rstrip() + "..."

    return intent, speech


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
    r"^\s*Mary\s+(?:se\s+)?(?:encolhe|levanta|senta|caminha|anda|pega|segura|olha|vira|deita|aproxima|afasta|sorri|ri|suspira|chora|treme|hesita|fica|permanece)\b",
    r"^\s*(?:Ela|Mary)\s+[^\n]{0,80}\b(?:olhos?|voz|mãos?|rosto|corpo)\b",

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
    """Detecta rubrica/narração escapando para o balão de Mary."""
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
