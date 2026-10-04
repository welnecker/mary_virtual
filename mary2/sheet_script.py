from __future__ import annotations

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


def _clean(value: Any) -> str:
    return str(value or "").strip()


def load_sheet_script(
    *,
    service_account_info: dict,
    spreadsheet_id: str,
    worksheet_name: str,
    script_name: str,
) -> list[dict]:
    """Read the authored script once; caller owns caching.

    Only the selected script rows are returned. Future rows stay in memory at
    runtime but are never included in the prompt until selected.
    """
    if not service_account_info:
        raise ValueError("service_account_info ausente para roteiro em planilha")
    if not _clean(spreadsheet_id):
        raise ValueError("spreadsheet_id ausente para roteiro em planilha")

    client = gspread.service_account_from_dict(service_account_info)
    worksheet = client.open_by_key(_clean(spreadsheet_id)).worksheet(
        _clean(worksheet_name) or "ROTEIRO_REDATOR"
    )
    values = worksheet.get_all_values()
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
        record: dict[str, str] = {}
        for index, header in enumerate(headers):
            key = SCRIPT_HEADERS.get(header)
            if not key:
                continue
            record[key] = _clean(source_row[index] if index < len(source_row) else "")

        if _clean(record.get("script_name")).lower() != _clean(script_name).lower():
            continue
        try:
            order = int(float(_clean(record.get("order"))))
        except Exception:
            continue
        record["order"] = order
        rows.append(record)

    rows.sort(key=lambda item: int(item.get("order", 0) or 0))
    return rows


def script_line(rows: list[dict], order: int) -> dict:
    target = max(1, int(order or 1))
    for row in rows:
        if int(row.get("order", 0) or 0) == target:
            return dict(row)
    return {}


def build_line_prompt(row: dict, *, line_order: int) -> str:
    if not row:
        return (
            "ROTEIRO POR LINHA\n"
            f"linha_atual={int(line_order)}\n"
            "Nenhuma linha roteirizada foi encontrada. Reaja somente ao usuário e à CENA ATUAL, "
            "sem inventar acontecimentos futuros."
        )

    parts = [
        "ROTEIRO POR LINHA — SOMENTE ESTA INTERAÇÃO",
        f"linha_atual={int(row.get('order', line_order) or line_order)}",
        f"tipo={_clean(row.get('type')) or 'INTERPRETADA'}",
        "",
        "REGRA CENTRAL",
        "Tudo nesta resposta deve orbitar esta única linha. Linhas futuras não estão disponíveis.",
        "FALA-GUIA é direção dramática, não texto literal, salvo quando tipo=EXATA.",
        "Em INTERPRETADA, varie palavras e ritmo sem diluir, inverter ou enfraquecer o núcleo semântico.",
        "Responda primeiro ao que o usuário acabou de dizer; preserve a intenção desta linha sem ignorar a interação real.",
    ]

    fields = [
        ("FALA-GUIA", "speech_guide"),
        ("ESTILO / ATITUDE", "style"),
        ("SENTIDO INTERPRETATIVO", "interpretive_meaning"),
        ("NÚCLEO SEMÂNTICO OBRIGATÓRIO", "semantic_core"),
        ("ATMOSFERA", "atmosphere"),
        ("FATO LIBERADO NESTA LINHA", "released_fact"),
        ("PRÉ-CONDIÇÃO EDITORIAL", "precondition"),
        ("VESTIMENTA ATUAL", "wardrobe"),
        ("AÇÃO FÍSICA / ENCENAÇÃO", "physical_action"),
        ("LIMITES DO REDATOR", "writer_limits"),
        ("RESULTADO ESPERADO", "expected_result"),
    ]
    for title, key in fields:
        value = _clean(row.get(key))
        if value:
            parts.extend(["", title, value])

    parts.extend([
        "",
        "PROTEÇÃO CRONOLÓGICA",
        "Não use fatos, falas, locais, convites, decisões ou desfechos de linhas posteriores.",
        "Perguntas, hipóteses e convites do usuário não viram fatos sem confirmação.",
        "Não decida falas, ações ou escolhas do personagem controlado pelo usuário.",
    ])
    return "\n".join(parts)


def line_for_interaction(*, chapter_turn: int, opening_consumes_line_one: bool = True) -> int:
    """Map the current user interaction to the authored line.

    Carona uses line 1 as the fixed Mary opening, so user turn 1 receives line 2.
    """
    turn = max(1, int(chapter_turn or 1))
    return turn + 1 if opening_consumes_line_one else turn
