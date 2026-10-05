from __future__ import annotations

import json
import re
from typing import Any

import gspread


SCRIPT_HEADERS = {
    "ordem": "order",
    "roteiro": "script_name",
    "tipo": "type",
    "fala-guia": "speech_guide",
    "estilo / atitude": "style",
    "sentido interpretativo": "interpretive_meaning",
    "núcleo semântico obrigatório": "semantic_core",
    "atmosfera": "atmosphere",
    "fato liberado nesta linha": "released_fact",
    "pré-condição": "precondition",
    "vestimenta atual": "wardrobe",
    "ação física / encenação": "physical_action",
    "limites do redator": "writer_limits",
    "resultado esperado": "expected_result",
}

MEMORY_HEADERS = {
    "roteiro": "script_name",
    "categoria": "category",
    "memória": "memory",
    "memoria": "memory",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _sheet_values(
    *,
    service_account_info: dict,
    spreadsheet_id: str,
    worksheet_name: str,
) -> list[list[str]]:
    if not service_account_info:
        raise ValueError("service_account_info ausente para roteiro em planilha")
    if not _clean(spreadsheet_id):
        raise ValueError("spreadsheet_id ausente para roteiro em planilha")
    client = gspread.service_account_from_dict(service_account_info)
    worksheet = client.open_by_key(_clean(spreadsheet_id)).worksheet(
        _clean(worksheet_name)
    )
    return worksheet.get_all_values()


def load_sheet_script(
    *,
    service_account_info: dict,
    spreadsheet_id: str,
    worksheet_name: str,
    script_name: str,
) -> list[dict]:
    """Load authored beats once; caller owns caching."""
    values = _sheet_values(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        worksheet_name=_clean(worksheet_name) or "ROTEIRO_REDATOR",
    )
    if not values:
        return []

    header_index = -1
    headers: list[str] = []
    for idx, row in enumerate(values):
        normalized = [_clean(cell).lower() for cell in row]
        if "ordem" in normalized and "fala-guia" in normalized:
            header_index = idx
            headers = normalized
            break
    if header_index < 0:
        raise ValueError("cabeçalho do roteiro não encontrado")

    rows: list[dict] = []
    for source_row in values[header_index + 1 :]:
        if not any(_clean(cell) for cell in source_row):
            continue
        record: dict[str, Any] = {}
        for index, header in enumerate(headers):
            key = SCRIPT_HEADERS.get(header)
            if key:
                record[key] = _clean(
                    source_row[index] if index < len(source_row) else ""
                )
        if _clean(record.get("script_name")).lower() != _clean(script_name).lower():
            continue
        try:
            record["order"] = int(float(_clean(record.get("order"))))
        except Exception:
            continue
        rows.append(record)

    rows.sort(key=lambda item: int(item.get("order", 0) or 0))
    return rows


def load_script_memory(
    *,
    service_account_info: dict,
    spreadsheet_id: str,
    worksheet_name: str,
    script_name: str,
) -> list[dict]:
    """Load concise authored continuity; never raw prior dialogue."""
    values = _sheet_values(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        worksheet_name=_clean(worksheet_name) or "ROTEIRO_MEMORIA",
    )
    if not values:
        return []

    header_index = -1
    headers: list[str] = []
    for idx, row in enumerate(values):
        normalized = [_clean(cell).lower() for cell in row]
        if "roteiro" in normalized and ("memória" in normalized or "memoria" in normalized):
            header_index = idx
            headers = normalized
            break
    if header_index < 0:
        raise ValueError("cabeçalho da memória do roteiro não encontrado")

    memories: list[dict] = []
    for source_row in values[header_index + 1 :]:
        record: dict[str, str] = {}
        for index, header in enumerate(headers):
            key = MEMORY_HEADERS.get(header)
            if key:
                record[key] = _clean(
                    source_row[index] if index < len(source_row) else ""
                )
        if _clean(record.get("script_name")).lower() != _clean(script_name).lower():
            continue
        if _clean(record.get("memory")):
            memories.append(record)
    return memories


def script_line(rows: list[dict], order: int) -> dict:
    target = max(1, int(order or 1))
    for row in rows:
        if int(row.get("order", 0) or 0) == target:
            return dict(row)
    return {}


def max_script_order(rows: list[dict]) -> int:
    return max([int(row.get("order", 0) or 0) for row in rows] or [0])


def build_memory_prompt(memories: list[dict]) -> str:
    if not memories:
        return ""
    groups: dict[str, list[str]] = {}
    for item in memories:
        category = _clean(item.get("category")) or "CONTEXTO"
        groups.setdefault(category.upper(), []).append(_clean(item.get("memory")))
    parts = [
        "MEMÓRIA DE ENTRADA — CONTINUIDADE AUTORAL",
        "Use apenas como contexto consolidado. Não reconstrua nem cite conversas anteriores.",
    ]
    for category, items in groups.items():
        parts.extend(["", category])
        parts.extend(f"- {item}" for item in items if item)
    return "\n".join(parts)


def build_line_prompt(row: dict, *, line_order: int) -> str:
    if not row:
        return (
            "BEAT ATUAL DO ROTEIRO\n"
            f"ordem={int(line_order)}\n"
            "Beat não encontrado. Reaja somente ao usuário e à cena atual; não invente futuro."
        )

    parts = [
        "BEAT ATUAL DO ROTEIRO — SOMENTE ESTE BEAT",
        f"ordem={int(row.get('order', line_order) or line_order)}",
        f"tipo={_clean(row.get('type')) or 'INTERPRETADA'}",
        "",
        "CONTRATO DO REDATOR",
        "Responda primeiro ao usuário. Execute este beat quando couber naturalmente.",
        "INTERPRETADA permite variar palavras, ritmo, humor e intensidade; não permite mudar o sentido.",
        "Não crie nova logística, rota, destino, plano, alternativa ou consequência estrutural.",
        "Não assuma ações, escolhas ou respostas do personagem do usuário.",
        "Não use conteúdo de beats futuros.",
    ]

    fields = [
        ("FALA-GUIA", "speech_guide"),
        ("ESTILO / ATITUDE", "style"),
        ("SENTIDO INTERPRETATIVO", "interpretive_meaning"),
        ("NÚCLEO SEMÂNTICO OBRIGATÓRIO", "semantic_core"),
        ("ATMOSFERA", "atmosphere"),
        ("FATO LIBERADO NESTE BEAT", "released_fact"),
        ("PRÉ-CONDIÇÃO", "precondition"),
        ("VESTIMENTA ATUAL DE MARY", "wardrobe"),
        ("AÇÃO FÍSICA / ENCENAÇÃO", "physical_action"),
        ("LIMITES DO REDATOR", "writer_limits"),
        ("RESULTADO ESPERADO", "expected_result"),
    ]
    for title, key in fields:
        value = _clean(row.get(key))
        if value:
            parts.extend(["", title, value])
            if key == "wardrobe":
                parts.append(
                    "A vestimenta descreve exclusivamente Mary; nunca a transfira ao personagem do usuário."
                )

    return "\n".join(parts)


def build_hold_prompt(row: dict, *, line_order: int) -> str:
    """Keep a physical gate pending without repeating the authored beat."""
    parts = [
        "BEAT ATUAL — AGUARDANDO CONDIÇÃO FÍSICA",
        f"ordem={int(line_order)}",
        "O conteúdo verbal deste beat já foi apresentado.",
        "Responda naturalmente sem repeti-lo e sem avançar para beats futuros.",
    ]
    precondition = _clean(row.get("precondition"))
    if precondition:
        parts.extend(["", "CONDIÇÃO AINDA PENDENTE", precondition])
    return "\n".join(parts)


def build_beat_validator_prompt(
    *,
    row: dict,
    user_text: str,
    mary_text: str,
    recent_dialogue: list[dict] | None = None,
) -> str:
    """Independent controller prompt. The Redator never decides progression."""
    recent = []
    for item in (recent_dialogue or [])[-6:]:
        role = _clean(item.get("role"))
        content = _clean(item.get("content"))
        if content:
            recent.append(f"{role.upper()}: {content}")
    return "\n".join([
        "Você é um VALIDADOR DE BEAT narrativo, não um escritor.",
        "Decida apenas se o beat ativo foi concretamente cumprido nesta interação.",
        "Considere a fala atual do usuário e a resposta atual de Mary.",
        "Um desvio humano legítimo, desculpa, esclarecimento ou assunto lateral NÃO conclui o beat.",
        "Não exija literalidade: preserve o núcleo semântico e o resultado esperado.",
        "A fala do usuário sozinha só pode concluir o beat quando o RESULTADO ESPERADO for obter/revelar uma resposta, decisão, reação ou informação do usuário.",
        "Se o beat exige que Mary apresente, pergunte, proponha, convide, alerte, reconheça ou revele algo, a resposta de Mary precisa executar isso para o beat ser concluído.",
        "Responda SOMENTE JSON: {\"completed\": true|false, \"reason\": \"curto\"}.",
        "",
        f"ORDEM: {int(row.get('order', 0) or 0)}",
        f"FALA-GUIA: {_clean(row.get('speech_guide'))}",
        f"NÚCLEO: {_clean(row.get('semantic_core'))}",
        f"PRÉ-CONDIÇÃO: {_clean(row.get('precondition'))}",
        f"RESULTADO ESPERADO: {_clean(row.get('expected_result'))}",
        "",
        "CONTEXTO RECENTE:",
        *(recent or ["(nenhum)"]),
        "",
        f"USUÁRIO AGORA: {_clean(user_text)}",
        f"MARY AGORA: {_clean(mary_text)}",
    ])


def parse_beat_validation(text: str) -> bool:
    value = _clean(text)
    try:
        data = json.loads(value)
        return bool(data.get("completed", False))
    except Exception:
        match = re.search(r'"completed"\s*:\s*(true|false)', value, flags=re.I)
        return bool(match and match.group(1).lower() == "true")


def line_for_interaction(*, chapter_turn: int, opening_consumes_line_one: bool = True) -> int:
    turn = max(1, int(chapter_turn or 1))
    return turn + 1 if opening_consumes_line_one else turn
