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




def interpret_direct_turn(
    *,
    api_key: str,
    model: str,
    fallback_model: str | None,
    row: dict,
    user_text: str,
    previous_mary_text: str = "",
) -> dict:
    """Intérprete: transforma a fala atual em situação compreendida antes da redação."""
    speech_guide = _clean(row.get("speech_guide"))
    payload = (
        "MEMÓRIA PERMANENTE-GLOBAL\n"
        + (_clean(row.get("permanent_memory")) or "(não informada)")
        + "\n\nMEMÓRIA FÍSICA-GLOBAL\n"
        + (_clean(row.get("physical_memory")) or "(não informada)")
        + "\n\nMEMÓRIA INSTANTÂNEA-LOCAL\n"
        + (_clean(row.get("instant_memory")) or "(não informada)")
        + "\n\nÚLTIMA FALA DE MARY\n"
        + (_clean(previous_mary_text) or "(primeira interação)")
        + "\n\nFALA ATUAL DO USUÁRIO\n"
        + (_clean(user_text) or "(sem fala verbal)")
        + "\n\nFALA-GUIA\n"
        + speech_guide
        + "\n\nTAREFA\n"
        "Interprete a situação para um Redator de diálogo. Não escreva a fala final de Mary. "
        "SEPARAÇÃO ABSOLUTA DE FONTES: a FALA ATUAL DO USUÁRIO contém apenas o que o usuário realmente disse. "
        "A FALA-GUIA contém apenas o que MARY deve fazer nesta linha. Nunca atribua ao usuário pergunta, intenção, pedido ou informação que exista apenas na FALA-GUIA. "
        "Identifique: (1) o que o usuário realmente quis dizer, usando somente a FALA ATUAL DO USUÁRIO e a continuidade; "
        "se a fala for apenas uma exclamação curta, palavrão, reação vaga ou frase ambígua sem referente claro, NÃO force uma interpretação temática: marque o sentido como reação vaga e o subtexto como vazio; "
        "(2) subtexto somente quando houver evidência real na fala atual ou continuidade; "
        "(3) se existe obrigação conversacional criada pelo USUÁRIO e o que Mary precisa responder/reconhecer; "
        "(4) quais fatos das memórias são diretamente relevantes agora; "
        "(5) qual ponte natural pode unir a resposta ao usuário à missão autoral, mas somente se essa ponte puder ser feita sem atribuir ao usuário algo que ele não disse. Se não houver ponte segura, deixe vazio. "
        "Nunca invente fatos pessoais, motivos ou emoções. "
        "Se a pergunta do usuário toca um fato presente na memória, use esse fato como base obrigatória. "
        "Retorne apenas JSON: "
        '{"sentido_usuario":"", "subtexto":"", '
        '"obrigacao_conversacional":{"existe":true,"requisito":""}, '
        '"fatos_relevantes":[""], "ponte_natural":""}.'
    )
    raw = chat(
        api_key=api_key,
        model=model,
        fallback_model=fallback_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um Intérprete de diálogo. Sua função é compreender o turno antes da escrita. "
                    "O usuário é sempre o PERSONAGEM DA CENA; Mary é sempre Mary. "
                    "Nunca troque sujeito, nunca transforme a FALA-GUIA em algo dito pelo usuário e nunca transforme a fala do usuário em fala de Mary. "
                    "Não use a FALA-GUIA para adivinhar o significado de uma fala vaga do usuário. "
                    "Não escreve falas de Mary, não cria fatos e não embeleza."
                ),
            },
            {"role": "user", "content": payload},
        ],
        temperature=0.0,
        max_tokens=420,
    )
    parsed: dict = {}
    parse_error = ""
    try:
        text = str(raw or "").strip()
        text = re.sub(r"^\s*\`\`\`(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*\`\`\`\s*$", "", text)
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= start:
            text = text[start:end + 1]
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("interpretação não é objeto JSON")
    except Exception as exc:
        parse_error = str(exc)
        parsed = {}

    obligation = parsed.get("obrigacao_conversacional", {})
    if not isinstance(obligation, dict):
        obligation = {}
    facts = parsed.get("fatos_relevantes", [])
    if not isinstance(facts, list):
        facts = []
    return {
        "user_meaning": _clean(parsed.get("sentido_usuario")),
        "subtext": _clean(parsed.get("subtexto")),
        "user_obligation": {
            "exists": bool(obligation.get("existe", False)),
            "requirement": _clean(obligation.get("requisito")),
        },
        "relevant_facts": [_clean(x) for x in facts if _clean(x)],
        "guide_requirements": [],
        "natural_bridge": _clean(parsed.get("ponte_natural")),
        "raw_response": raw,
        "input_payload": payload,
        "parse_error": parse_error,
    }


def validate_direct_line_completion(
    *,
    api_key: str,
    model: str,
    fallback_model: str | None,
    row: dict,
    interpretation: dict,
    mary_text: str,
) -> dict:
    """Diretor semântico: verifica apenas se os elementos essenciais da fala-guia foram satisfeitos."""
    user_obligation = interpretation.get("user_obligation", {}) if isinstance(interpretation, dict) else {}
    if not isinstance(user_obligation, dict):
        user_obligation = {}
    speech_guide = _clean(row.get("speech_guide"))
    obligation_text = _clean(user_obligation.get("requirement"))
    obligation_exists = bool(user_obligation.get("exists", False))

    payload = (
        "OBRIGAÇÃO CONVERSACIONAL\n"
        + (obligation_text if obligation_exists else "(nenhuma)")
        + "\n\nFALA-GUIA ORIGINAL\n"
        + (speech_guide or "(nenhuma)")
        + "\n\nRESPOSTA DE MARY\n"
        + _clean(mary_text)
        + "\n\nTAREFA\n"
        "Valide APENAS a RESPOSTA DE MARY contra a obrigação conversacional e a FALA-GUIA ORIGINAL. "
        "Decomponha a FALA-GUIA ORIGINAL em todos os atos semânticos essenciais, preservando sujeito, ação e destinatário. "
        "Você não possui acesso à fala original do usuário. "
        "Para cada requisito, cite como evidência somente trecho que esteja literalmente presente na RESPOSTA DE MARY. "
        "Se não houver evidência na resposta, marque como não atendido. "
        "Não avalie estilo ou qualidade literária. "
        "Retorne apenas JSON: "
        '{"obrigacao_usuario":{"existe":true,"requisito":"","atendida":true,"evidencia":""},'
        '"elementos_guia":[{"requisito":"","encontrado":true,"evidencia":""}],'
        '"cumpriu":true,"faltou":"","motivo":""}.'
    )
    system_prompt = (
        "Você é um Validador isolado. Só pode usar a RESPOSTA DE MARY como fonte de evidência. "
        "Nunca trate textos dos requisitos como se fossem evidência."
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

    elements = parsed.get("elementos_guia", [])
    if not isinstance(elements, list):
        elements = []
    normalized_elements: list[dict] = []
    response_text = _clean(mary_text)
    response_norm = response_text.casefold()
    for item in elements:
        if not isinstance(item, dict):
            continue
        evidence = _clean(item.get("evidencia"))
        evidence_valid = bool(evidence) and evidence.casefold() in response_norm
        found = bool(item.get("encontrado", False)) and evidence_valid
        normalized_elements.append({
            "requirement": _clean(item.get("requisito")),
            "found": found,
            "evidence": evidence if evidence_valid else "",
        })

    obligation_raw = parsed.get("obrigacao_usuario", {})
    if not isinstance(obligation_raw, dict):
        obligation_raw = {}
    obligation_evidence = _clean(obligation_raw.get("evidencia"))
    obligation_evidence_valid = bool(obligation_evidence) and obligation_evidence.casefold() in response_norm
    normalized_obligation = {
        "exists": obligation_exists,
        "requirement": obligation_text,
        "satisfied": (
            True if not obligation_exists
            else bool(obligation_raw.get("atendida", False)) and obligation_evidence_valid
        ),
        "evidence": obligation_evidence if obligation_evidence_valid else "",
    }

    all_guide_found = (
        True if not speech_guide
        else bool(normalized_elements) and all(bool(item.get("found")) for item in normalized_elements)
    )
    fulfilled = (
        not parse_error
        and normalized_obligation["satisfied"]
        and all_guide_found
        and bool(parsed.get("cumpriu", False))
    )

    missing_parts: list[str] = []
    if obligation_exists and not normalized_obligation["satisfied"]:
        missing_parts.append(obligation_text or "responder à obrigação conversacional")
    for item in normalized_elements:
        if not item["found"] and item["requirement"]:
            missing_parts.append(item["requirement"])
    missing = "; ".join(missing_parts) or _clean(parsed.get("faltou"))
    reason = _clean(parsed.get("motivo"))

    return {
        "fulfilled": fulfilled,
        "missing": missing,
        "reason": reason,
        "elements": normalized_elements,
        "user_obligation": normalized_obligation,
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
    user_obligation = evaluation.get("user_obligation", {})
    unmet = [
        _clean(item.get("requirement"))
        for item in elements
        if isinstance(item, dict)
        and not bool(item.get("found", False))
        and _clean(item.get("requirement"))
    ]
    if isinstance(user_obligation, dict) and bool(user_obligation.get("exists", False)) and not bool(user_obligation.get("satisfied", False)):
        user_requirement = _clean(user_obligation.get("requirement")) or "responder diretamente à fala atual do usuário"
        unmet.insert(0, user_requirement)
    detail = "; ".join(unmet) or missing or "as obrigações do turno"
    return (
        "CORREÇÃO CIRÚRGICA DA MESMA LINHA. Preserve personalidade, continuidade e espontaneidade. "
        "A primeira resposta pode conter partes naturais e válidas: não reinicie tudo do zero e não reescreva "
        "o que já funciona sem necessidade. Faça a menor alteração necessária para acrescentar os elementos ausentes. "
        f"Elementos ainda não satisfeitos: {detail}. "
        f"A FALA-GUIA continua sendo: {guide}. "
        "Se a lacuna for uma obrigação conversacional trazida pelo usuário, responda primeiro a ela de forma natural; use as memórias autoritativas quando a obrigação for factual. "
        "Depois preserve e cumpra a FALA-GUIA na mesma resposta, de modo natural. "
        "Reaja ao significado da fala atual do usuário sem repeti-la ou parafraseá-la mecanicamente. "
        "Não copie literalmente a FALA-GUIA se puder cumprir a mesma intenção com naturalidade. "
        "Não invente fatos, dados, ações ou informações para compensar a falha. "
        "Não explique a correção. Mantenha exatamente o formato [FALA] seguido de [PENSAMENTO]."
    )


def build_direct_writer_prompt(
    *,
    row: dict,
    user_text: str,
    interpretation: dict | None = None,
    previous_mary_text: str = "",
    character_name: str = "",
) -> str:
    """Monta o prompt do Redator em blocos semânticos separados."""
    if not row:
        return (
            "FALA ATUAL DO USUÁRIO\n"
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
    initial_description = _clean(row.get("initial_description"))
    interpretation = interpretation or {}

    obligation = interpretation.get("user_obligation", {}) if isinstance(interpretation, dict) else {}
    if not isinstance(obligation, dict):
        obligation = {}
    obligation_text = (
        _clean(obligation.get("requirement"))
        if obligation.get("exists")
        else "(nenhuma obrigação direta)"
    )

    facts = interpretation.get("relevant_facts", []) if isinstance(interpretation, dict) else []
    if not isinstance(facts, list):
        facts = []

    understanding_lines = [
        "Significado: " + (
            _clean(interpretation.get("literal_meaning"))
            or _clean(interpretation.get("user_meaning"))
            or "(não determinado)"
        ),
        "Referência: " + (_clean(interpretation.get("reference")) or "(não determinada)"),
        "Intenção: " + (_clean(interpretation.get("intent")) or "(não determinada)"),
        "Reação emocional observável: " + (
            _clean(interpretation.get("emotional_reaction")) or "(nenhuma claramente observável)"
        ),
        "Subtexto sustentado: " + (_clean(interpretation.get("subtext")) or "(nenhum)"),
        "Ambiguidade: " + ("sim" if bool(interpretation.get("ambiguity", False)) else "não"),
        "Ponto incerto: " + (_clean(interpretation.get("unclear_point")) or "(nenhum)"),
        "Reação adequada de Mary: " + (
            _clean(interpretation.get("expected_mary_reaction")) or "(livre, conforme a conversa)"
        ),
        "Obrigação conversacional criada pelo usuário: " + obligation_text,
        "Fatos relevantes agora: " + (
            "; ".join(_clean(value) for value in facts if _clean(value)) or "(nenhum)"
        ),
    ]

    initial_description_block = ""
    if line_order == 1:
        initial_description_block = (
            "==================================================\n"
            "DESCRIÇÃO INICIAL-CENA\n"
            "==================================================\n"
            + (initial_description or "(não informada)")
            + "\n\n"
        )

    return (
        "VOCÊ É MARY.\n"
        "Escreva como uma mulher real dentro desta situação, não como narradora nem como assistente.\n\n"
        "==================================================\n"
        "MEMÓRIA PERMANENTE-GLOBAL\n"
        "==================================================\n"
        + (_clean(row.get("permanent_memory")) or "(não informada)")
        + "\n\n"
        "==================================================\n"
        "MEMÓRIA FÍSICA-GLOBAL\n"
        "==================================================\n"
        + (_clean(row.get("physical_memory")) or "(não informada)")
        + "\n\n"
        + initial_description_block
        + "==================================================\n"
        "MEMÓRIA INSTANTÂNEA-LOCAL\n"
        "==================================================\n"
        + (_clean(row.get("instant_memory")) or "(não informada)")
        + "\n\n"
        "==================================================\n"
        "CONTINUIDADE REAL\n"
        "==================================================\n"
        "Última fala de Mary:\n"
        + (_clean(previous_mary_text) or "(primeira interação da cena)")
        + "\n\n"
        "A última fala de Mary serve para resolver referências e continuidade. "
        "Não repita a mesma informação, piada, justificativa ou observação apenas porque ela aparece aqui, "
        "a menos que o usuário retome explicitamente esse assunto.\n\n"
        "==================================================\n"
        "FALA ATUAL DO USUÁRIO\n"
        "==================================================\n"
        + (_clean(user_text) or "(sem fala verbal)")
        + "\n\n"
        "==================================================\n"
        "COMPREENSÃO ISOLADA DO USUÁRIO\n"
        "==================================================\n"
        + "\n".join(understanding_lines)
        + "\n\n"
        "Esta compreensão foi produzida sem acesso à FALA-GUIA. "
        "Ela descreve somente o que o usuário realmente disse dentro do contexto já ocorrido.\n\n"
        "==================================================\n"
        "FALA-GUIA DA LINHA ATUAL\n"
        "==================================================\n"
        + (speech_guide or "(nenhuma)")
        + "\n\n"
        "A FALA-GUIA pertence à autoria do roteiro. Ela indica o movimento semântico que Mary deve tentar desenvolver. "
        "Ela NÃO é uma fala, pergunta, intenção ou informação do usuário. "
        "Não precisa ser repetida literalmente.\n\n"
        "==================================================\n"
        "ESTILO / ATITUDE\n"
        "==================================================\n"
        + (_clean(row.get("style")) or "natural")
        + "\n\n"
        "==================================================\n"
        "REGRAS DE REDAÇÃO\n"
        "==================================================\n"
        "1. Priorize a fala atual do usuário e responda ao que realmente aconteceu na conversa.\n"
        "2. Preserve os fatos e sujeitos das memórias. O que pertence a Mary continua pertencendo a Mary; "
        "o que pertence ao usuário continua pertencendo ao usuário.\n"
        "3. Depois de responder ao usuário, desenvolva a FALA-GUIA se houver oportunidade natural.\n"
        "4. Se a FALA-GUIA ficar artificial nesta resposta, não a force. A linha pode continuar ativa por outras interações.\n"
        "5. Enquanto a linha estiver ativa, a FALA-GUIA continua pendente até ser realmente realizada; "
        "não a abandone apenas porque o usuário abriu outro assunto.\n"
        "6. Nunca transforme a FALA-GUIA em algo que o usuário teria dito, perguntado, desejado ou pensado.\n"
        "7. Não invente fatos pessoais sobre o usuário. Mary pode enriquecer ambiente, formulação e pequenos detalhes próprios "
        "quando compatíveis com as memórias e sem contradizer fatos estabelecidos.\n"
        "8. Não antecipe conteúdo de linhas futuras.\n"
        "9. Não trate a missão como checklist e não faça confirmação mecânica de leitura.\n"
        "10. O pensamento deve ser curto, íntimo e situacional; não diagnostique psicologicamente o usuário nem invente "
        "olhar, gesto, desejo, ansiedade, timidez ou atração sem evidência.\n\n"
        "FORMATO\n"
        "[FALA] fala de Mary em primeira pessoa\n"
        "[PENSAMENTO] uma frase curta, íntima e situacional em primeira pessoa."
    )

