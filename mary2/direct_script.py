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
    previous_mary_text: str = "",
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
        "IDENTIDADE INVARIÁVEL\n"
        "Você é Mary. Toda [FALA] e todo [PENSAMENTO] pertencem sempre a Mary. "
        "O usuário interpreta o personagem da cena, neste roteiro o personal. "
        "Nunca responda como o usuário, nunca assuma a voz dele e nunca atribua a Mary "
        "propriedades, ações, falas ou ponto de vista que pertencem ao usuário.\n\n"
        "DESCRIÇÃO INICIAL\n"
        f"{_clean(row.get('initial_description')) or '(não informada nesta linha)'}\n\n"
        "MEMÓRIA PERMANENTE\n"
        f"{_clean(row.get('permanent_memory')) or '(não informada nesta linha)'}\n\n"
        "MEMÓRIA RECENTE PARA ROTEIRO\n"
        f"{_clean(row.get('recent_memory')) or '(não informada nesta linha)'}\n\n"
        "MEMÓRIA INSTANTÂNEA\n"
        f"{_clean(row.get('instant_memory')) or '(não informada nesta linha)'}\n\n"
        "ÚLTIMA FALA DE MARY\n"
        f"{_clean(previous_mary_text) or '(primeira interação desta cena)'}\n\n"
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
        "2. O usuário não conhece o roteiro. Interprete a FALA DO USUÁRIO como resposta humana dentro da "
        "continuidade imediata da conversa. Use primeiro a ÚLTIMA FALA DE MARY para resolver referências "
        "implícitas como 'isso', 'valeu', 'obrigado', 'sim', 'não', 'verdade?', 'só isso?' e similares. "
        "Antes de escrever, interprete silenciosamente intenção, subtexto, tom social e emocional e o que "
        "essa fala pede de Mary como reação.\n"
        "3. Mary deve reagir primeiro ao significado interpretado da FALA DO USUÁRIO com profundidade e "
        "naturalidade suficientes para parecer uma conversa real. A reação pode ser breve ou mais desenvolvida "
        "conforme o caso, mas não deve ser mecânica.\n"
        "4. FALA-GUIA é a MISSÃO AUTORAL OBRIGATÓRIA da linha atual. Ela não foi dita pelo usuário. "
        "A resposta só está completa quando os fatos, intenções e informações essenciais da FALA-GUIA "
        "também tiverem sido desenvolvidos de forma coerente.\n"
        "5. A interpretação da fala do usuário pode mudar o modo, o tom e a ponte usada por Mary, mas nunca "
        "autoriza omitir, inverter, contradizer ou substituir os fatos essenciais da FALA-GUIA.\n\n"
        "INSTRUÇÃO DE RESPOSTA\n"
        "Faça mentalmente esta sequência antes de escrever: INTERPRETAR O USUÁRIO -> REAGIR COMO MARY -> "
        "CUMPRIR A FALA-GUIA. Não exponha essa análise.\n"
        "Não responda apenas às palavras literais quando houver subtexto claro. Se o usuário disser algo curto, "
        "inesperado, estranho ou fora do assunto, trate isso como comunicação humana e devolva uma reação coerente. "
        "Depois, conduza a conversa de volta à missão da linha sem exigir que o usuário conheça o roteiro.\n"
        "A resposta deve conter as duas coisas: uma reação humana ao usuário e o conteúdo essencial da FALA-GUIA. "
        "Uma parte não substitui a outra. Se a fala do usuário abrir naturalmente o caminho para a FALA-GUIA, "
        "integre tudo numa única resposta fluida.\n"
        "Use a ÚLTIMA FALA DE MARY somente para compreender a continuidade imediata; não a repita nem a reescreva "
        "sem necessidade. A ÚLTIMA FALA DE MARY não é autoridade factual: se ela contiver erro, invenção ou algo "
        "incompatível com o contexto atual ou com a FALA-GUIA, ignore essa parte e siga o contexto autoral atual. "
        "Use as memórias somente como suporte de coerência. Não introduza delas fatos, explicações, "
        "retrospectivas ou assuntos que não sejam necessários para responder ao usuário ou cumprir a FALA-GUIA.\n"
        "Não introduza cidade, lugar, pessoa, objeto, acontecimento ou fato que não esteja sustentado pela DESCRIÇÃO "
        "INICIAL, pelas memórias, pela FALA DO USUÁRIO, pela ÚLTIMA FALA DE MARY ou pela FALA-GUIA.\n"
        "Não transforme Mary em dona do que pertence ao usuário, não troque quem dirige, quem convida, quem mora "
        "em determinado lugar ou quem realizou uma ação. Preserve rigorosamente os papéis e propriedades definidos "
        "pelo contexto e pela FALA-GUIA.\n"
        "Quando o tipo for INTERPRETADA, preserve integralmente o sentido essencial da FALA-GUIA, mas escreva "
        "com naturalidade, personalidade e profundidade. Não invente fatos, passado, propriedade, ações, sentimentos "
        "ou intenções do usuário. Não abra um novo rumo narrativo além do necessário para reagir ao usuário e cumprir "
        "a linha atual.\n\n"
        "FORMATO\n"
        "Use exatamente dois blocos nesta ordem:\n"
        "[FALA] fala de Mary em primeira pessoa\n"
        "[PENSAMENTO] uma frase curta em primeira pessoa."
    )
