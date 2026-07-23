from __future__ import annotations

import re
from typing import Any


ONOMATOPOEIA_VERSION = "onomatopoeia-v2-controlled-laughter-and-sounds"


ONOMATOPOEIA_ACTIONS: dict[str, dict[str, Any]] = {
    "KKK": {
        "action": "gargalhada",
        "description": "gargalhada aberta, espontânea ou debochada",
        "sexual": False,
        "explicit": False,
        "tone": "open_laughter",
    },
    "RSRS": {
        "action": "riso_contido",
        "description": "riso contido, tímido, provocador ou incrédulo",
        "sexual": False,
        "explicit": False,
        "tone": "contained_laughter",
    },
    "SNIFF": {
        "action": "cheirar",
        "description": "som curto de inspirar pelo nariz ou cheirar algo ou alguém",
        "sexual": False,
        "explicit": False,
        "tone": "smell",
    },
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
    r"(?<![\w])(?:K{3,}|(?:RS){2,}|SNI+F+|CHU+P|SLU+P|SU+CK|PO+P|FLO+P|GLU+B|HU+N+F+|PLA+F|NHA+M|FA+P)(?![\w])",
    flags=re.IGNORECASE,
)


CONTROLLED_USAGE_PROMPT = """
USO CONTROLADO DE RISOS E ONOMATOPEIAS

- Mary pode usar onomatopeias curtas dentro da própria fala quando o som realmente estiver acontecendo no instante.
- “kkkk”, “kkkkk” ou “kkkkkk” representam gargalhada aberta, espontânea, debochada ou divertida.
- “rsrs”, “rsrsrs” ou “rsrsrsrs” representam riso contido, tímido, provocador ou incrédulo.
- “sniff!” representa uma inspiração curta pelo nariz ou o ato de cheirar; combine com algo concreto que Mary percebe.
- CHUP, SLUP, SUCK, POP, FLOP, GLUB, HUNFF, PLAF, NHAM e FAP representam os sons físicos correspondentes ao ato atual.
- Use no máximo uma família de onomatopeia por resposta comum e, em cena física intensa, no máximo duas ocorrências curtas da mesma família.
- Não comece toda resposta com som. Não repita o mesmo som em turnos consecutivos sem motivo real.
- O som deve vir colado a uma fala natural de Mary, nunca sozinho e nunca como legenda de roteiro.
- Risos só aparecem quando algo foi engraçado, absurdo, provocador, embaraçoso ou deliciosamente inesperado.
- Onomatopeias sexuais só aparecem quando o ato correspondente já está acontecendo ou foi claramente iniciado na cena.
- Não use uma onomatopeia para inventar ação do usuário. Mary pode produzir o próprio som, reagir ao ato confirmado ou pedir continuidade.
- Preserve oralidade. Prefira exemplos como “kkkkk... você não tem jeito”, “rsrsrs... tá brincando, né?”, “sniff! Você tem um cheiro tão bom” ou “GLUB... engoli tudinho”.
- Evite explicar o som depois de usá-lo. A fala seguinte deve expressar desejo, humor, sensação ou reação imediata.
""".strip()


def _canonicalize(token: str) -> str:
    text = str(token or "").upper()
    if re.fullmatch(r"K{3,}", text):
        return "KKK"
    if re.fullmatch(r"(?:RS){2,}", text):
        return "RSRS"
    if text.startswith("SNI"):
        return "SNIFF"
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
    lines = [CONTROLLED_USAGE_PROMPT]

    if not detected:
        return "\n".join(lines)

    lines.extend(
        [
            "",
            "INTERPRETAÇÃO DE ONOMATOPEIAS DO TURNO DO USUÁRIO:",
            "Trate os sons abaixo como ações ou tons realmente expressos no turno, não como palavras aleatórias.",
        ]
    )

    for item in detected:
        lines.append(
            f"- {item['token']}: {item['description']} (ação: {item['action']})."
        )

    lines.extend(
        [
            "Mary deve reagir ao gesto, ao humor e à parte do corpo já estabelecida pela continuidade da cena.",
            "Ela pode ecoar o riso do usuário quando isso soar espontâneo, mas não deve copiar mecanicamente todos os sons.",
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

    if any(item.get("tone") == "open_laughter" for item in detected):
        result["user_laughed"] = True
        result["laughter_style"] = "open"

    if any(item.get("tone") == "contained_laughter" for item in detected):
        result["user_laughed"] = True
        result["laughter_style"] = "contained"

    if any(item.get("tone") == "smell" for item in detected):
        result["smell_action"] = True

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
    "CONTROLLED_USAGE_PROMPT",
    "detectar_onomatopeias",
    "montar_contexto_onomatopeias",
    "enriquecer_sinais_com_onomatopeias",
]
