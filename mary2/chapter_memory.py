from __future__ import annotations

import json
import re


MEMORY_KEYS = (
    "facts",
    "about_user_character",
    "mary_perceptions",
    "references",
    "open_items",
    "do_not_assume",
)


def build_recent_memory_prompt(source_chapter_id: str, records: list[dict], structural_facts: list[str] | None = None) -> str:
    dialogue = []
    for record in records[-24:]:
        user_text = str(record.get("user_text", "") or "").strip()
        mary_text = str(record.get("mary_text", "") or "").strip()
        if user_text:
            dialogue.append(f"USUARIO: {user_text}")
        if mary_text:
            dialogue.append(f"MARY: {mary_text}")

    facts = [str(item or "").strip() for item in (structural_facts or []) if str(item or "").strip()]
    lines = [
        "Voce e um RESUMIDOR DE MEMORIA NARRATIVA.",
        "Este resumo e gerado uma unica vez no fechamento do capitulo.",
        "Guarde apenas informacoes que podem mudar a interpretacao do capitulo seguinte.",
        "Nao copie o dialogo.",
        "So registre como fato algo explicitamente dito, realizado ou confirmado.",
        "Perguntas, hipoteses, brincadeiras e convites nao confirmados nao viram fatos.",
        "Preserve autoria e nao invente intencoes, planos, preferencias ou reciprocidade.",
        "Responda somente JSON com as chaves: facts, about_user_character, mary_perceptions, references, open_items, do_not_assume.",
        f"CAPITULO_ORIGEM: {source_chapter_id}",
        "FATOS_ESTRUTURAIS:",
    ]
    lines.extend([f"- {item}" for item in facts] if facts else ["(nenhum)"])
    lines.append("INTERACOES:")
    lines.extend(dialogue if dialogue else ["(nenhuma)"])
    return "\n".join(lines)


def parse_recent_memory(text: str) -> dict:
    value = str(text or "").strip()
    try:
        data = json.loads(value)
    except Exception:
        match = re.search(r"\{.*\}", value, flags=re.S)
        if not match:
            return {}
        try:
            data = json.loads(match.group(0))
        except Exception:
            return {}

    if not isinstance(data, dict):
        return {}

    result = {}
    for key in MEMORY_KEYS:
        raw_items = data.get(key, [])
        if not isinstance(raw_items, list):
            raw_items = []
        items = []
        for item in raw_items[:10]:
            cleaned = re.sub(r"\s+", " ", str(item or "")).strip()
            if len(cleaned) > 260:
                cleaned = cleaned[:257].rstrip() + "..."
            if cleaned and cleaned not in items:
                items.append(cleaned)
        result[key] = items
    return result


def recent_memory_text(memory: dict | None) -> str:
    if not isinstance(memory, dict) or not any(memory.values()):
        return ""

    labels = {
        "facts": "FATOS RECENTES CONFIRMADOS",
        "about_user_character": "SOBRE O PERSONAGEM DO USUARIO",
        "mary_perceptions": "PERCEPCOES RECENTES DE MARY",
        "references": "REFERENCIAS UTEIS",
        "open_items": "PENDENCIAS",
        "do_not_assume": "NAO ASSUMIR",
    }
    parts = [
        "MEMORIA RECENTE DA EXECUCAO",
        "Resumo consolidado do capitulo imediatamente anterior. Nao reconstrua o dialogo original.",
    ]
    for key, label in labels.items():
        items = memory.get(key, [])
        if not items:
            continue
        parts.extend(["", label])
        parts.extend(f"- {item}" for item in items)
    return "\n".join(parts)
