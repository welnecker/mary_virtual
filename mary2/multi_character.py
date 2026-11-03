"""Opt-in multi-character authoring for DIRECT_SHEET rows.

Three authorial columns remain the source of truth. Explicit 'NOME:' clauses
in each column authorize only that character and that component.
Unlabelled legacy guide text still belongs to Mary.
"""
from __future__ import annotations

import re
import unicodedata

_CHANNELS = ("action_guide", "thought_guide", "speech_guide")
_RESERVED = frozenset({"interpretar", "adaptar", "objetivo", "contexto", "descricao", "pensamento", "fala", "tom", "estilo", "nota", "observacao", "direcao", "revelacao", "atitude"})
_COMPONENT = {"action_guide": "AÇÃO", "thought_guide": "PENSAMENTO",
              "speech_guide": "FALA"}
_GUIDE_LABEL = re.compile(r"(?m)(?:^|[\n;])\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ' -]{1,40})\s*:\s*")
_OUTPUT_TAG = re.compile(r"\[(AÇÃO|ACAO|FALA|PENSAMENTO)(?:\s*:\s*([^\]\n]+))?\]", re.I)


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or "").strip().casefold())
    return "".join(c for c in text if not unicodedata.combining(c))


def _label(text: str) -> str:
    text = " ".join(str(text or "").strip().split())
    if text.upper() == "MARY":
        return "Mary"
    return text


def guide_characters(row: dict) -> dict[str, set[str]]:
    """Parse structured authorial clauses, not incidental character mentions.

    Format: 'SILVIA: ...\nMARY: ...'. Names must start a line or follow ';'.
    The function does not infer authorizations from narrative prose.
    """
    mapping: dict[str, set[str]] = {}
    for key in _CHANNELS:
        content = str(row.get(key, "") or "")
        matches = list(_GUIDE_LABEL.finditer(content))
        # Opt in only when the value starts with a speaker label. Ignore ordinary
        # mentions such as 'Silvia: ...' embedded in a natural sentence.
        if not matches or content[:matches[0].start()].strip():
            continue
        for match in matches:
            name = _label(match.group(1))
            if not name or _fold(name) in _RESERVED:
                continue
            mapping.setdefault(_fold(name), set()).add(_COMPONENT[key])
    return mapping


def multi_character_contract(row: dict, *, user_speaker: str = "") -> str:
    mapping = guide_characters(row)
    if not mapping or all(name == "mary" for name in mapping):
        return ""
    entries = []
    for person, kinds in mapping.items():
        if person != "mary":
            entries.append(person.upper() + ": " + ", ".join(sorted(kinds)))
    return (
        "CONTRATO MULTIPERSONAGEM — SOMENTE LINHA ATIVA\\n"
        "As rubricas NOME: nos três guias autorizam APENAS aquele componente "
        "para aquele personagem. Guias sem rubrica são da Mary. "
        "Fale e pense em nome de coadjuvantes apenas quando a rubrica autorizar. "
        "Use [AÇÃO: NOME], [FALA: NOME], [PENSAMENTO: NOME] conforme indicado. "
        "Para Mary use [AÇÃO: MARY], [FALA: MARY], [PENSAMENTO: MARY]. "
        "Gere os blocos na ordem causal da cena; não transfira ações ou "
        "palavras de Silvia para Mary. "
        "Não invente fala ou pensamento de quem está sendo interpretado pelo usuário. "
        "Não reproduza rubricas de personagens não autorizados. "
        "Coadjuvantes autorizados: " + "; ".join(entries) + ". "
        + ("Interlocutor atual indicado: " + user_speaker + ". " if user_speaker else "")
    )


def parsed_character_blocks(raw: str) -> list[dict[str, str]]:
    value = str(raw or "")
    matches = list(_OUTPUT_TAG.finditer(value))
    blocks = []
    for i, match in enumerate(matches):
        kind = _fold(match.group(1)).upper()
        if kind == "ACAO":
            kind = "ACAO"
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(value)
        body = value[start:end].strip()
        if body:
            blocks.append({"kind": kind, "speaker": _label(match.group(2) or "Mary"),
                           "text": body})
    return blocks


def verify_character_blocks(raw: str, row: dict, *, user_speaker: str = "") -> tuple[bool, str]:
    """Hard check of explicitly required speech and ownership; no LLM needed."""
    mapping = guide_characters(row)
    extra = {name: kinds for name, kinds in mapping.items() if name != "mary"}
    if not extra:
        return True, ""
    blocks = parsed_character_blocks(raw)
    if not blocks:
        return False, "Sem blocos identificados por personagem."
    allowed = set(mapping) | {"mary"}
    for block in blocks:
        who = _fold(block["speaker"])
        if who not in allowed:
            return False, "Personagem sem autorização: " + block["speaker"]
        if user_speaker and who == _fold(user_speaker):
            return False, "O modelo tentou falar pelo usuário: " + block["speaker"]
        if who != "mary" and _normalize_component(block["kind"]) not in mapping.get(who, set()):
            return False, "Componente não autorizado: " + block["kind"] + " de " + block["speaker"]
    for name, kinds in extra.items():
        if user_speaker and name == _fold(user_speaker):
            continue
        for kind in kinds:
            if not any(_fold(b["speaker"]) == name and _normalize_component(b["kind"]) == kind for b in blocks):
                return False, "Faltou " + kind + " do personagem " + name
    return True, ""


def _normalize_component(value: str) -> str:
    if _fold(value) in {"acao"}:
        return "AÇÃO"
    return _fold(value).upper()


def formatted_components(raw: str, row: dict) -> dict[str, str]:
    """Present attributed blocks via legacy action/thought/speech fields.

    Speaker labels persist in INTERACTIONS and are not mistaken for Mary's voice.
    """
    parts = {"action": [], "thought": [], "speech": []}
    for block in parsed_character_blocks(raw):
        key = {"ACAO": "action", "FALA": "speech", "PENSAMENTO": "thought"}[block["kind"]]
        parts[key].append("**" + block["speaker"] + ":** " + block["text"])
    return {key: "\n\n".join(value) for key, value in parts.items()}
