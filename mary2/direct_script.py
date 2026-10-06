from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

import gspread


DIRECT_HEADERS = {
    "ordem": "order",
    "roteiro": "script_name",
    "tipo": "type",
    "fala-guia": "speech_guide",
    "estilo / atitude": "style",
    "pré-condição": "precondition",
    "pre-condição": "precondition",
    "vestimenta atual": "wardrobe",
    "ação física / encenação": "physical_action",
    "acao fisica / encenacao": "physical_action",
    "tipo de conclusão": "completion_type",
    "tipo de conclusao": "completion_type",
    "memória recente para roteiro": "recent_memory",
    "memoria recente para roteiro": "recent_memory",
    "memória instantânea": "instant_memory",
    "memoria instantanea": "instant_memory",
    "memória permanente": "permanent_memory",
    "memoria permanente": "permanent_memory",
    "descrição inicial": "initial_description",
    "descricao inicial": "initial_description",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _resolve_placeholders(text: str, *, character_name: str) -> str:
    value = _clean(text)
    name = _clean(character_name)
    if name.lower() in {"", "personal", "personagem", "personagem_da_cena"}:
        name = ""
    value = value.replace("{usuario}", name)
    value = re.sub(r"\s+,", ",", value)
    value = re.sub(r",\s*,", ",", value)
    value = re.sub(r"\s{2,}", " ", value)
    return value.strip(" ,")


def load_direct_script_rows(
    *,
    service_account_info: dict,
    spreadsheet_id: str,
    worksheet_name: str,
    script_name: str,
) -> list[dict]:
    """Lê o roteiro autoral sem reinterpretar ou enriquecer seus campos."""
    if not service_account_info:
        raise ValueError("service_account_info ausente para roteiro direto")
    if not _clean(spreadsheet_id):
        raise ValueError("spreadsheet_id ausente para roteiro direto")

    client = gspread.service_account_from_dict(service_account_info)
    worksheet = client.open_by_key(_clean(spreadsheet_id)).worksheet(
        _clean(worksheet_name) or "MINHA_SUGESTAO"
    )
    values = worksheet.get_all_values()
    if not values:
        return []

    header_index = -1
    headers: list[str] = []
    for idx, source in enumerate(values):
        normalized = [_clean(cell).lower() for cell in source]
        if "ordem" in normalized and "fala-guia" in normalized:
            header_index = idx
            headers = normalized
            break
    if header_index < 0:
        raise ValueError("cabeçalho do roteiro direto não encontrado")

    rows: list[dict] = []
    for source_row in values[header_index + 1 :]:
        if not any(_clean(cell) for cell in source_row):
            continue

        record: dict[str, Any] = {}
        for index, header in enumerate(headers):
            key = DIRECT_HEADERS.get(header)
            if key:
                record[key] = _clean(
                    source_row[index] if index < len(source_row) else ""
                )

        if _clean(record.get("script_name")).casefold() != _clean(script_name).casefold():
            continue
        try:
            record["order"] = int(float(_clean(record.get("order"))))
        except Exception:
            continue
        if not _clean(record.get("speech_guide")):
            continue

        record["line_id"] = f"linha_{record['order']:02d}"
        rows.append(record)

    rows.sort(key=lambda item: int(item.get("order", 0) or 0))
    return rows


def ensure_direct_state(narrative: dict, rows: list[dict]) -> dict:
    state = narrative.get("direct_script")
    if not isinstance(state, dict) or state.get("engine") != "direct_sheet_v1":
        state = {
            "engine": "direct_sheet_v1",
            "index": 0,
            "current_order": int(rows[0].get("order", 0) or 0) if rows else 0,
            "awaiting_reply_order": 0,
            "completed_orders": [],
            "completed": not bool(rows),
        }
        narrative["direct_script"] = state

    if not isinstance(state.get("completed_orders"), list):
        state["completed_orders"] = []
    state["index"] = max(0, int(state.get("index", 0) or 0))
    state["awaiting_reply_order"] = max(
        0, int(state.get("awaiting_reply_order", 0) or 0)
    )
    state["completed"] = bool(state.get("completed", False))
    return state


def register_direct_user_reply(
    state: dict,
    rows: list[dict],
    user_text: str,
) -> dict:
    """A fala seguinte do usuário encerra a linha que Mary acabou de emitir."""
    before = deepcopy(state)
    awaiting = int(state.get("awaiting_reply_order", 0) or 0)
    if awaiting and _clean(user_text):
        completed = {
            int(value)
            for value in (state.get("completed_orders", []) or [])
            if str(value).strip()
        }
        completed.add(awaiting)
        state["completed_orders"] = sorted(completed)
        state["awaiting_reply_order"] = 0
        state["index"] = min(int(state.get("index", 0) or 0) + 1, len(rows))
        if state["index"] >= len(rows):
            state["current_order"] = 0
            state["completed"] = True
        else:
            state["current_order"] = int(rows[state["index"]].get("order", 0) or 0)

    return {"state_before": before, "state_after": deepcopy(state)}


def current_direct_row(rows: list[dict], state: dict) -> dict:
    if not rows or bool(state.get("completed", False)):
        return {}
    index = max(0, min(int(state.get("index", 0) or 0), len(rows) - 1))
    return dict(rows[index])


def mark_direct_line_emitted(state: dict, row: dict) -> None:
    order = int(row.get("order", 0) or 0)
    if order:
        state["awaiting_reply_order"] = order
        state["current_order"] = order


def direct_script_ready_for_choice(state: dict) -> bool:
    return bool(state.get("completed", False))


def build_direct_writer_prompt(
    *,
    row: dict,
    user_text: str,
    character_name: str = "",
) -> str:
    """Entrega a linha autoral ao Redator sem camada narrativa intermediária."""
    if not row:
        return (
            "FALA DO USUÁRIO\n"
            f"{_clean(user_text) or '(sem fala verbal)'}\n\n"
            "ROTEIRO CONCLUÍDO\n"
            "A última linha autoral já foi concluída. Responda brevemente apenas ao que o "
            "usuário acabou de dizer, sem abrir novo assunto, plano ou etapa narrativa.\n\n"
            "FORMATO\n"
            "Use exatamente:\n[FALA] fala de Mary\n[PENSAMENTO] uma frase curta em primeira pessoa."
        )

    speech_guide = _resolve_placeholders(
        row.get("speech_guide", ""),
        character_name=character_name,
    )

    return (
        "DESCRIÇÃO INICIAL\n"
        f"{_clean(row.get('initial_description')) or '(não informada nesta linha)'}\n\n"
        "MEMÓRIA PERMANENTE\n"
        f"{_clean(row.get('permanent_memory')) or '(não informada nesta linha)'}\n\n"
        "MEMÓRIA RECENTE PARA ROTEIRO\n"
        f"{_clean(row.get('recent_memory')) or '(não informada nesta linha)'}\n\n"
        "MEMÓRIA INSTANTÂNEA\n"
        f"{_clean(row.get('instant_memory')) or '(não informada nesta linha)'}\n\n"
        "FALA DO USUÁRIO\n"
        f"{_clean(user_text) or '(sem fala verbal)'}\n\n"
        "FALA-GUIA\n"
        f"{speech_guide}\n\n"
        "ESTILO / ATITUDE\n"
        f"{_clean(row.get('style')) or '(natural)'}\n\n"
        "VESTIMENTA ATUAL\n"
        f"{_clean(row.get('wardrobe')) or '(não informada nesta linha)'}\n\n"
        "AÇÃO FÍSICA / ENCENAÇÃO\n"
        f"{_clean(row.get('physical_action')) or '(nenhuma orientação adicional)'}\n\n"
        "HIERARQUIA DE DESENVOLVIMENTO\n"
        "1. DESCRIÇÃO INICIAL, MEMÓRIA PERMANENTE, MEMÓRIA RECENTE, MEMÓRIA INSTANTÂNEA, "
        "VESTIMENTA e AÇÃO FÍSICA / ENCENAÇÃO são CONTEXTO. Servem para Mary compreender "
        "a situação e manter coerência. Não devem ser recitados, explicados nem transformados "
        "em assunto por iniciativa própria.\n"
        "2. FALA DO USUÁRIO é o único acontecimento verbal que acabou de ocorrer. Antes de escrever, "
        "interprete silenciosamente o que essa fala significa neste contexto: intenção, subtexto, "
        "tom social e emocional, e o que ela pede de Mary como reação humana. A fala pode ser seca, "
        "brincalhona, provocadora, evasiva, carinhosa, apressada, absurda, confusa ou inesperada.\n"
        "3. Mary deve reagir primeiro ao significado interpretado da FALA DO USUÁRIO, como uma pessoa "
        "real reagiria naquela situação. Essa reação pode incluir humor, estranhamento, provocação, "
        "curiosidade, correção, ironia, afeto ou desconforto, conforme o contexto.\n"
        "4. FALA-GUIA é uma MISSÃO AUTORAL para a resposta de Mary. Não é uma fala anterior, "
        "não foi dita pelo usuário e não deve ser tratada como pergunta recebida. Depois da reação "
        "ao usuário, conduza organicamente a conversa para o conteúdo da FALA-GUIA.\n\n"
        "INSTRUÇÃO DE RESPOSTA\n"
        "Faça mentalmente esta sequência antes de escrever: INTERPRETAR O USUÁRIO -> REAGIR COMO MARY -> "
        "DESENVOLVER A FALA-GUIA. Não exponha essa análise.\n"
        "Não responda apenas às palavras literais do usuário quando o contexto indicar um subtexto claro. "
        "Interprete pragmaticamente a fala. Se o usuário disser algo curto como 'pronto', 'então tá', "
        "'entra', 'só isso?' ou algo esdrúxulo, trate essa fala como comunicação humana e devolva uma "
        "reação coerente antes de seguir a missão da linha.\n"
        "A FALA-GUIA orienta para onde a conversa deve caminhar, mas não deve apagar nem atropelar a "
        "reação de Mary ao usuário. Se a fala do usuário já abrir naturalmente o caminho para a FALA-GUIA, "
        "integre as duas coisas sem repetição mecânica.\n"
        "Use as memórias apenas para evitar contradições e compreender o contexto. Não puxe delas "
        "informações que o usuário não pediu e que a FALA-GUIA não exige. Não transforme memória em "
        "explicação, justificativa ou retrospectiva.\n"
        "Quando o tipo for INTERPRETADA, preserve a intenção e o conteúdo da FALA-GUIA, mas escreva "
        "com naturalidade. Não invente fatos, passado, propriedade, ações, sentimentos ou intenções "
        "do usuário. Não abra um novo rumo narrativo além do necessário para reagir ao usuário e cumprir "
        "a FALA-GUIA.\n\n"
        "FORMATO\n"
        "Use exatamente dois blocos nesta ordem:\n"
        "[FALA] fala de Mary em primeira pessoa\n"
        "[PENSAMENTO] uma frase curta em primeira pessoa."
    )
