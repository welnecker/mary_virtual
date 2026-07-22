from __future__ import annotations

import re
from typing import Any


ONOMATOPOEIA_VERSION = "onomatopoeia-v1-action-markers"


ONOMATOPOEIA_ACTIONS: dict[str, dict[str, Any]] = {
    "CHUP": {
        "action": "chupada",
        "description": "som de chupada ou sucção com a boca",
        "sexual": True,
        "explicit": True,
    },
    "SLUP": {
        "action": "lambida",
        "description": "som úmido de lambida",
        "sexual": True,
        "explicit": True,
    },
    "SUCK": {
        "action": "sucção",
        "description": "sucção contínua com a boca",
        "sexual": True,
        "explicit": True,
    },
    "POP": {
        "action": "sucção_liberada",
        "description": "som de a boca ou sucção sendo liberada",
        "sexual": True,
        "explicit": True,
    },
    "FLOP": {
        "action": "penetracao_ritmica",
        "description": "som de penetração ou movimento de entra e sai",
        "sexual": True,
        "explicit": True,
    },
    "GLUB": {
        "action": "engolir",
        "description": "som de engolir",
        "sexual": False,
        "explicit": False,
    },
    "HUNFF": {
        "action": "abraco_apertado",
        "description": "som corporal de abraço ou aperto forte",
        "sexual": False,
        "explicit": False,
    },
    "PLAF": {
        "action": "tapa",
        "description": "som de tapa ou palmada",
        "sexual": False,
        "explicit": False,
    },
    "NHAM": {
        "action": "mordiscada",
        "description": "mordida leve ou mordiscada",
        "sexual": False,
        "explicit": False,
    },
    "FAP": {
        "action": "masturbacao_manual",
        "description": "movimento manual repetido de masturbação",
        "sexual": True,
        "explicit": True,
    },
}


_TOKEN_PATTERN = re.compile(
    r"(?<![\w])(?:CHU+P|SLU+P|SU+CK|PO+P|FLO+P|GLU+B|HU+N+F+|PLA+F|NHA+M|FA+P)(?![\w])",
    flags=re.IGNORECASE,
)


def _canonicalize(token: str) -> str:
    text = str(token or "").upper()
    if text.startswith("CH"):
        return "CHUP"
    if text.startswith("SL"):
        return "SLUP"
    if text.startswith("SU"):
        return "SUCK"
    if text.startswith("PO"):
        return "POP"
    if text.startswith("FL"):
        return "FLOP"
    if text.startswith("GL"):
        return "GLUB"
    if text.startswith("HU"):
        return "HUNFF"
    if text.startswith("PL"):
        return "PLAF"
    if text.startswith("NH"):
        return "NHAM"
    if text.startswith("FA"):
        return "FAP"
    return text


def _pop_is_sound(text: str, match: re.Match[str]) -> bool:
    """Evita interpretar 'música pop' ou 'cultura pop' como efeito sonoro."""
    before = text[max(0, match.start() - 16):match.start()].lower()
    after = text[match.end():match.end() + 16].lower()
    lexical_context = (
        "musica", "música", "cultura", "artista", "cantora", "cantor",
        "rock", "genero", "gênero", "estilo",
    )
    if any(term in before or term in after for term in lexical_context):
        return False
    token = match.group(0)
    trailing = text[match.end():match.end() + 2]
    return token.isupper() or bool(re.search(r"[!.*~]", trailing))


def detectar_onomatopeias(texto: str) -> list[dict[str, Any]]:
    text = str(texto or "")
    detected: list[dict[str, Any]] = []

    for match in _TOKEN_PATTERN.finditer(text):
        canonical = _canonicalize(match.group(0))
        if canonical == "POP" and not _pop_is_sound(text, match):
            continue

        definition = ONOMATOPOEIA_ACTIONS.get(canonical)
        if not definition:
            continue

        detected.append(
            {
                "token": match.group(0),
                "canonical": canonical,
                **definition,
            }
        )

    return detected


def montar_contexto_onomatopeias(texto: str) -> str:
    detected = detectar_onomatopeias(texto)
    if not detected:
        return ""

    lines = [
        "INTERPRETAÇÃO DE ONOMATOPEIAS DO TURNO:",
        "Trate os sons abaixo como ações realizadas ou descritas pelo usuário, não como palavras aleatórias.",
    ]

    for item in detected:
        lines.append(
            f"- {item['token']}: {item['description']} (ação: {item['action']})."
        )

    lines.extend(
        [
            "Mary deve reagir ao gesto e à parte do corpo já estabelecida pela continuidade da cena.",
            "Não repetir mecanicamente todas as onomatopeias na resposta; use-as apenas quando soarem naturais.",
            "Não inventar penetração, tapa ou ato sexual se a continuidade e o consentimento da cena não sustentarem essa leitura.",
        ]
    )
    return "\n".join(lines)


def enriquecer_sinais_com_onomatopeias(
    signals: dict[str, Any] | None,
    texto: str,
) -> dict[str, Any]:
    result = dict(signals) if isinstance(signals, dict) else {}
    detected = detectar_onomatopeias(texto)
    if not detected:
        result.setdefault("onomatopoeia_actions", [])
        return result

    actions = [str(item["action"]) for item in detected]
    result["onomatopoeia_actions"] = actions
    result["onomatopoeia_tokens"] = [str(item["token"]) for item in detected]

    if any(bool(item.get("sexual")) for item in detected):
        result["sexual_signal"] = True
        result["sexual_strength"] = max(
            0.65,
            float(result.get("sexual_strength", 0.0) or 0.0),
        )

    if any(bool(item.get("explicit")) for item in detected):
        result["explicit_sexual_signal"] = True
        result["sexual_strength"] = max(
            0.78,
            float(result.get("sexual_strength", 0.0) or 0.0),
        )

    matched = result.get("matched_user_terms")
    if not isinstance(matched, dict):
        matched = {}
    matched = dict(matched)
    matched["onomatopoeia_actions"] = [str(item["canonical"]) for item in detected]
    result["matched_user_terms"] = matched
    return result


__all__ = [
    "ONOMATOPOEIA_VERSION",
    "ONOMATOPOEIA_ACTIONS",
    "detectar_onomatopeias",
    "montar_contexto_onomatopeias",
    "enriquecer_sinais_com_onomatopeias",
]
