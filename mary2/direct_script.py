from __future__ import annotations

import json
import re
import time
from copy import deepcopy
from typing import Any

import gspread

from openrouter_client import chat


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
    "memória instantânea-local": "instant_memory",
    "memoria instantanea-local": "instant_memory",
    "memória permanente": "permanent_memory",
    "memoria permanente": "permanent_memory",
    "memória permanente-global": "permanent_memory",
    "memoria permanente-global": "permanent_memory",
    "memória física": "physical_memory",
    "memoria fisica": "physical_memory",
    "memória física-global": "physical_memory",
    "memoria fisica-global": "physical_memory",
    "descrição inicial": "initial_description",
    "descricao inicial": "initial_description",
    "descrição inicial-cena": "initial_description",
    "descricao inicial-cena": "initial_description",
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

    # Memórias marcadas como GLOBAL são autoradas uma única vez na planilha,
    # mas precisam acompanhar todas as linhas entregues ao Redator.
    permanent_memory_global = next(
        (_clean(item.get("permanent_memory")) for item in rows if _clean(item.get("permanent_memory"))),
        "",
    )
    physical_memory_global = next(
        (_clean(item.get("physical_memory")) for item in rows if _clean(item.get("physical_memory"))),
        "",
    )
    for item in rows:
        item["permanent_memory"] = permanent_memory_global
        item["physical_memory"] = physical_memory_global

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

    completed = sorted({
        int(value)
        for value in state.get("completed_orders", [])
        if str(value).strip()
    })
    state["completed_orders"] = completed

    index = max(0, int(state.get("index", 0) or 0))
    while (
        index < len(rows)
        and int(rows[index].get("order", 0) or 0) in completed
    ):
        index += 1

    state["index"] = min(index, len(rows))
    state["awaiting_reply_order"] = max(
        0, int(state.get("awaiting_reply_order", 0) or 0)
    )

    if state["index"] >= len(rows):
        state["current_order"] = 0
        state["completed"] = True
    else:
        current_order = int(rows[state["index"]].get("order", 0) or 0)
        if current_order in completed:
            raise RuntimeError(
                "direct_script inválido: tentativa de regressão para linha já concluída"
            )
        state["current_order"] = current_order
        state["completed"] = bool(state.get("completed", False)) and not rows

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



def validate_direct_line_completion(
    *,
    api_key: str,
    model: str,
    fallback_model: str | None,
    row: dict,
    mary_text: str,
) -> dict:
    """Diretor semântico: verifica apenas se os elementos essenciais da fala-guia foram satisfeitos."""
    speech_guide = _clean(row.get("speech_guide"))
    if not speech_guide:
        return {
            "fulfilled": True,
            "missing": "",
            "reason": "linha sem fala-guia",
            "elements": [],
            "model": model,
            "duration_ms": 0.0,
            "input_payload": "",
            "raw_response": "",
            "parsed_response": {
                "elementos": [],
                "cumpriu": True,
                "faltou": "",
                "motivo": "linha sem fala-guia",
            },
            "parse_error": "",
        }

    payload = (
        "FALA-GUIA DA LINHA\n"
        + speech_guide
        + "\n\nRESPOSTA DE MARY\n"
        + _clean(mary_text)
        + "\n\n"
        "TAREFA DE VALIDAÇÃO\n"
        "1. Decomponha mentalmente a FALA-GUIA em elementos semânticos essenciais distintos. "
        "Considere quem pratica a ação, sobre quem/que ela recai e qual intenção verbal precisa ocorrer. "
        "Perguntas diferentes, pedidos diferentes e afirmações essenciais diferentes contam como elementos separados. "
        "2. Para cada elemento, procure evidência semântica real na RESPOSTA DE MARY. Não exija as mesmas palavras. "
        "3. Um assunto apenas mencionado NÃO satisfaz uma ação específica. Exemplo: falar de um clube não equivale "
        "a pedir que alguém a leve ao clube. "
        "4. Preserve sujeito e papéis. Se a fala-guia pede que Mary pergunte onde o usuário mora, uma resposta sobre "
        "onde Mary mora NÃO satisfaz esse elemento. "
        "5. Avalie atos de fala, não execução física. Se a fala-guia diz 'anota meu número', basta Mary pedir ao outro "
        "personagem que registre o contato; não exija que Mary anote algo fisicamente. "
        "6. Nunca exija dado concreto que a FALA-GUIA não fornece. Se não há número, endereço ou valor explícito, "
        "não reprove por ausência desse dado. "
        "7. Não avalie estilo, profundidade, simpatia, resposta ao usuário, personalidade ou qualidade literária. "
        "8. CUMPRIU só pode ser true quando TODOS os elementos essenciais estiverem presentes. "
        "Retorne apenas JSON no formato: "
        '{"elementos":[{"requisito":"texto curto","encontrado":true,"evidencia":"trecho curto"}],'
        '"cumpriu":true,"faltou":"","motivo":"curto"}.'
    )
    system_prompt = (
        "Você é um Diretor validador estritamente limitado. "
        "Não escreve cenas, não inventa fatos, não altera o roteiro e não sugere novos rumos. "
        "Sua única função é validar semanticamente se Mary cumpriu todos os elementos essenciais da FALA-GUIA, "
        "preservando sujeito, ação e intenção."
    )

    started_at = time.perf_counter()
    raw = chat(
        api_key=api_key,
        model=model,
        fallback_model=fallback_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": payload},
        ],
        temperature=0.0,
        max_tokens=360,
    )
    duration_ms = round((time.perf_counter() - started_at) * 1000.0, 1)

    parse_error = ""
    parsed: dict = {}
    try:
        text = str(raw or "").strip()
        text = re.sub(r"^\\s*```(?:json)?\\s*", "", text, flags=re.I)
        text = re.sub(r"\\s*```\\s*$", "", text)
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= start:
            text = text[start : end + 1]
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("resposta do Diretor não é objeto JSON")
    except Exception as exc:
        parse_error = str(exc)
        parsed = {}

    elements = parsed.get("elementos", [])
    if not isinstance(elements, list):
        elements = []

    normalized_elements: list[dict] = []
    for item in elements:
        if not isinstance(item, dict):
            continue
        normalized_elements.append(
            {
                "requirement": _clean(item.get("requisito")),
                "found": bool(item.get("encontrado", False)),
                "evidence": _clean(item.get("evidencia")),
            }
        )

    all_elements_found = bool(normalized_elements) and all(
        bool(item.get("found", False)) for item in normalized_elements
    )
    claimed_fulfilled = bool(parsed.get("cumpriu", False))
    fulfilled = (
        claimed_fulfilled and all_elements_found
        if not parse_error
        else False
    )

    missing_requirements = [
        item.get("requirement", "")
        for item in normalized_elements
        if not bool(item.get("found", False)) and item.get("requirement")
    ]
    missing = _clean(parsed.get("faltou"))
    if not missing and missing_requirements:
        missing = "; ".join(missing_requirements)
    reason = _clean(parsed.get("motivo"))

    return {
        "fulfilled": fulfilled,
        "missing": missing,
        "reason": reason,
        "elements": normalized_elements,
        "model": model,
        "duration_ms": duration_ms,
        "input_payload": payload,
        "raw_response": raw,
        "parsed_response": parsed,
        "parse_error": parse_error,
    }


def direct_line_correction_prompt(row: dict, evaluation: dict) -> str:
    """Corrige só a lacuna apontada, preservando personalidade, continuidade e espontaneidade."""
    guide = _clean(row.get("speech_guide"))
    missing = _clean(evaluation.get("missing"))
    elements = evaluation.get("elements", [])
    unmet = [
        _clean(item.get("requirement"))
        for item in elements
        if isinstance(item, dict)
        and not bool(item.get("found", False))
        and _clean(item.get("requirement"))
    ]
    detail = "; ".join(unmet) or missing or "o conteúdo essencial da FALA-GUIA"
    return (
        "CORREÇÃO CIRÚRGICA DA MESMA LINHA. Preserve personalidade, continuidade e espontaneidade. "
        "A primeira resposta pode conter partes naturais e válidas: não reinicie tudo do zero e não reescreva "
        "o que já funciona sem necessidade. Faça a menor alteração necessária para acrescentar os elementos ausentes. "
        f"Elementos ainda não satisfeitos: {detail}. "
        f"A FALA-GUIA continua sendo: {guide}. "
        "Reaja ao significado da fala atual do usuário sem repeti-la ou parafraseá-la mecanicamente. "
        "Não copie literalmente a FALA-GUIA se puder cumprir a mesma intenção com naturalidade. "
        "Não invente fatos, dados, ações ou informações para compensar a falha. "
        "Não explique a correção. Mantenha exatamente o formato [FALA] seguido de [PENSAMENTO]."
    )


def build_direct_writer_prompt(
    *,
    row: dict,
    user_text: str,
    previous_mary_text: str = "",
    character_name: str = "",
) -> str:
    """Formata a linha autoral final para o Redator, separando GLOBAL, CENA e LOCAL."""
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
    line_order = int(row.get("order", 0) or 0)
    initial_description_block = (
        "DESCRIÇÃO INICIAL-CENA\n"
        f"{_clean(row.get('initial_description')) or '(não informada)'}\n\n"
        if line_order == 1
        else ""
    )

    return (
        "PAPÉIS INVARIÁVEIS\n"
        "Você é Mary. Toda [FALA] e todo [PENSAMENTO] pertencem sempre a Mary. "
        "O usuário interpreta o outro personagem da cena, neste roteiro o personal. "
        "Nunca fale pelo usuário, nunca troque motorista e passageira, nunca atribua a Mary "
        "moradia, ações, falas, intenções ou propriedades que pertencem ao usuário.\n\n"

        "MEMÓRIA PERMANENTE-GLOBAL\n"
        f"{_clean(row.get('permanent_memory')) or '(não informada)'}\n\n"

        "MEMÓRIA FÍSICA-GLOBAL\n"
        f"{_clean(row.get('physical_memory')) or '(não informada)'}\n\n"

        + initial_description_block

        + "MEMÓRIA INSTANTÂNEA-LOCAL\n"
        f"{_clean(row.get('instant_memory')) or '(não informada)'}\n\n"

        "CONTINUIDADE IMEDIATA\n"
        "ÚLTIMA FALA DE MARY:\n"
        f"{_clean(previous_mary_text) or '(primeira interação desta cena)'}\n\n"
        "FALA ATUAL DO USUÁRIO:\n"
        f"{_clean(user_text) or '(sem fala verbal)'}\n\n"

        "MISSÃO AUTORAL DESTA LINHA\n"
        "FALA-GUIA:\n"
        f"{speech_guide}\n\n"
        "ESTILO / ATITUDE:\n"
        f"{_clean(row.get('style')) or '(natural)'}\n\n"

        "COMO USAR CADA BLOCO\n"
        "1. MEMÓRIA PERMANENTE-GLOBAL contém fatos estáveis da vida de Mary. É autoridade factual, "
        "mas não é assunto obrigatório. Use um fato somente quando a fala do usuário ou a FALA-GUIA "
        "torná-lo relevante. Nunca invente uma explicação quando a memória já contém a resposta.\n"
        "2. MEMÓRIA FÍSICA-GLOBAL contém aparência e autopercepção física estáveis. Serve para coerência; "
        "não descreva o corpo, a beleza ou a aparência de Mary espontaneamente só porque essa memória existe.\n"
        "3. DESCRIÇÃO INICIAL-CENA, quando presente, define o ponto de partida e o contexto de entrada da cena. "
        "Ela não substitui o estado atual e não deve ser recitada.\n"
        "4. MEMÓRIA INSTANTÂNEA-LOCAL é o estado factual no INÍCIO desta linha. Ela tem precedência para "
        "posição, deslocamento, local, papéis e situação física atual. Não antecipe como fato algo que a própria "
        "FALA-GUIA ainda precisa fazer acontecer.\n"
        "5. ÚLTIMA FALA DE MARY existe apenas para continuidade e resolução de referências. Não reutilize, "
        "complete, reescreva ou repita essa fala mecanicamente. Se houver erro antigo nela, não o perpetue.\n"
        "6. FALA ATUAL DO USUÁRIO deve ser compreendida antes de qualquer desenvolvimento do roteiro. Interprete "
        "quem falou, a que fala anterior ele está reagindo, intenção, subtexto, humor e direção da ação. Responda "
        "ao significado; não repita nem parafraseie a fala apenas para mostrar compreensão.\n"
        "7. FALA-GUIA é a obrigação semântica da linha. Preserve sujeito, ação, destinatário e intenção. "
        "Ela não precisa ser copiada literalmente e não autoriza trocar os papéis.\n"
        "8. ESTILO / ATITUDE define somente a maneira de Mary se expressar nesta passagem. Não cria fatos, "
        "ações obrigatórias, passado novo ou mudança de estado.\n\n"

        "SEQUÊNCIA MENTAL OBRIGATÓRIA\n"
        "Antes de escrever, faça silenciosamente: "
        "ENTENDER QUEM DISSE O QUÊ -> IDENTIFICAR O ESTADO LOCAL -> REAGIR HUMANAMENTE AO USUÁRIO -> "
        "CUMPRIR A FALA-GUIA -> VERIFICAR PAPÉIS E FATOS. Não exponha essa análise.\n\n"

        "REGRAS DE REDAÇÃO\n"
        "- Personalidade + continuidade + espontaneidade.\n"
        "- Reaja primeiro à fala atual do usuário; depois faça a missão autoral caber naturalmente na mesma resposta.\n"
        "- Não trate a FALA-GUIA como uma resposta pré-escrita. Preserve o sentido e escreva Mary de forma natural.\n"
        "- Não invente fatos, passado, relações, lugares, objetos, motivos ou informações ausentes dos blocos acima.\n"
        "- Não transforme Mary em dona do carro, motorista, moradora de outro lugar ou autora de uma ação do usuário.\n"
        "- Não faça retrospectiva nem explique memórias sem necessidade.\n"
        "- Não abra assunto de linha futura e não antecipe acontecimentos posteriores.\n"
        "- Pequenos gestos podem ser implícitos no tom, mas não escreva narração externa ou rubrica de encenação.\n"
        "- Se a fala do usuário corrigir, negar ou esclarecer algo sobre ELE MESMO, aceite essa informação como "
        "parte da conversa atual, desde que não contradiga um fato autoral explícito sobre Mary.\n\n"

        "FORMATO\n"
        "Use exatamente dois blocos nesta ordem:\n"
        "[FALA] fala de Mary em primeira pessoa\n"
        "[PENSAMENTO] uma frase curta em primeira pessoa."
    )

