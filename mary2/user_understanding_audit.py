from __future__ import annotations

import json
import re

from openrouter_client import chat
from persistence import _audit_cell, _ensure_worksheet, _now, open_or_create_book


SHEET = "USER_UNDERSTANDING_AUDIT"
HEADERS = [
    "created_at",
    "run_id",
    "chapter_id",
    "chapter_instance_id",
    "chapter_turn",
    "line_id",
    "line_order",
    "user_text",
    "previous_mary_text",
    "literal_meaning",
    "reference",
    "intent",
    "emotional_reaction",
    "subtext",
    "ambiguity",
    "confidence",
    "unclear_point",
    "expected_mary_reaction",
    "raw_interpreter_json",
    "parse_error",
]


def analyze_user_understanding(
    *,
    api_key: str,
    model: str,
    fallback_model: str | None,
    user_text: str,
    previous_mary_text: str = "",
    recent_messages: list[dict] | None = None,
    instant_memory: str = "",
    permanent_memory: str = "",
    physical_memory: str = "",
    initial_description: str = "",
) -> dict:
    """Compreende a fala do usuário sem receber fala-guia ou roteiro futuro."""
    recent_lines: list[str] = []
    for message in (recent_messages or [])[-6:]:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "") or "").strip().lower()
        content = str(message.get("content", "") or "").strip()
        if not content:
            continue
        speaker = "MARY" if role == "assistant" else "USUÁRIO"
        recent_lines.append(f"{speaker}: {content}")
    recent_context = "\n".join(recent_lines).strip()

    payload = (
        "CONTEXTO ESTÁVEL SOBRE MARY\n"
        + (str(permanent_memory or "").strip() or "(não informado)")
        + "\n\nCONTEXTO FÍSICO ESTÁVEL\n"
        + (str(physical_memory or "").strip() or "(não informado)")
        + "\n\nDESCRIÇÃO INICIAL DA CENA\n"
        + (str(initial_description or "").strip() or "(não informada)")
        + "\n\nESTADO OBJETIVO ATUAL\n"
        + (str(instant_memory or "").strip() or "(não informado)")
        + "\n\nCONTEXTO RECENTE REAL\n"
        + (recent_context or "(nenhuma interação anterior relevante)")
        + "\n\nÚLTIMA FALA DE MARY\n"
        + (str(previous_mary_text or "").strip() or "(nenhuma)")
        + "\n\nFALA ATUAL DO USUÁRIO\n"
        + (str(user_text or "").strip() or "(sem fala verbal)")
        + "\n\nHIERARQUIA DE VERDADE\n"
        "1. MEMÓRIA PERMANENTE-GLOBAL\n"
        "2. MEMÓRIA FÍSICA-GLOBAL\n"
        "3. ESTADO OBJETIVO ATUAL / MEMÓRIA INSTANTÂNEA-LOCAL\n"
        "4. DESCRIÇÃO INICIAL DA CENA\n"
        "5. CONTEXTO RECENTE REAL E FALAS ANTERIORES\n"
        "Se uma fala anterior de Mary contradizer qualquer fonte autoritativa acima, trate a fala anterior como erro de continuidade. "
        "Não a transforme em fato consolidado e não a use para reinterpretar a realidade.\n"
        + "\nTAREFA\n"
        "Compreenda SOMENTE a fala atual do usuário à luz do passado e do presente já estabelecidos. "
        "Você não conhece a fala-guia, a missão da linha nem qualquer acontecimento futuro. "
        "Não escreva a resposta de Mary e não tente avançar o roteiro. "
        "Não invente intenção escondida. Não converta gentileza, humor, atenção ou disponibilidade em atração, interesse romântico/sexual ou intenção futura sem evidência explícita. Se houver ambiguidade real, declare-a. "
        "Preserve rigorosamente sujeito, posse, posição e papel: não transfira para o usuário fatos de Mary nem para Mary fatos do usuário. "
        "Quando a fala atual reagir a um erro anterior de Mary, reconheça que existe conflito com a memória autoritativa e baseie a compreensão na memória, não no erro. "
        "Use as memórias apenas para resolver referências e fatos já estabelecidos. "
        "ESTADO JÁ RESOLVIDO: se uma decisão, acordo, posse, destino, relação ou condição já estiver estabelecida nas fontes autoritativas, "
        "não a reabra como escolha pendente só porque a fala atual toca nesse assunto. Interprete apenas o novo movimento conversacional. "
        "PRINCÍPIO DA ENTIDADE MÍNIMA: resolva pronomes, possessivos e referências ('meu', 'seu', 'dele', 'ela', 'isso', 'aquele') "
        "contra entidades já existentes sempre que isso produzir leitura coerente. Não crie uma segunda pessoa, objeto, lugar ou evento "
        "quando a entidade já estabelecida explica a fala. Só introduza nova entidade quando o usuário ou a memória a distinguirem explicitamente. "
        "REFERÊNCIA GEOGRÁFICA NÃO CRIA PROGRAMA: um lugar citado como trajeto, ponto de passagem, direção, bairro, referência espacial "
        "ou estimativa de tempo não se torna automaticamente destino final, parada, atividade, convite ou plano de lazer. "
        "Só atribua atividade ao local quando o usuário, a memória ou a cena a estabelecerem explicitamente. "
        "Informe: significado literal/contextual; referência; intenção conversacional; reação emocional observável; "
        "subtexto somente quando sustentado; ambiguidade; confiança de 0 a 1; ponto incerto; "
        "tipo de reação adequada de Mary; se há conflito factual entre fala anterior e memória autoritativa; qual é a correção factual; "
        "se a fala cria uma obrigação conversacional direta para Mary; "
        "qual é essa obrigação; e quais fatos fornecidos são diretamente relevantes. "
        "Retorne somente JSON com as chaves: "
        "literal_meaning, reference, intent, emotional_reaction, subtext, ambiguity, confidence, "
        "unclear_point, expected_mary_reaction, factual_conflict, factual_correction, requires_response, response_requirement, relevant_facts."
    )

    raw = chat(
        api_key=api_key,
        model=model,
        fallback_model=fallback_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é o módulo de compreensão conversacional. "
                    "Seu trabalho é entender o que o usuário realmente disse dentro do contexto já ocorrido. "
                    "Você nunca recebe nem tenta adivinhar o roteiro futuro. "
                    "Não escreve por Mary, não inventa fatos e não troca sujeitos. "
                    "Não reabra decisões já resolvidas e preserve a menor quantidade de entidades compatível com os fatos."
                ),
            },
            {"role": "user", "content": payload},
        ],
        temperature=0.0,
        max_tokens=420,
    )

    def _parse_understanding(value: str) -> tuple[dict, str]:
        try:
            text = str(value or "").strip()
            text = re.sub(r"^\s*\x60\x60\x60(?:json)?\s*", "", text, flags=re.I)
            text = re.sub(r"\s*\x60\x60\x60\s*$", "", text)
            json_start = text.find("{")
            json_end = text.rfind("}")
            if json_start >= 0 and json_end >= json_start:
                text = text[json_start : json_end + 1]
            parsed_value = json.loads(text)
            if not isinstance(parsed_value, dict):
                raise ValueError("understanding response is not a JSON object")
            return parsed_value, ""
        except Exception as exc:
            return {}, str(exc)

    parsed, parse_error = _parse_understanding(raw)
    if parse_error:
        repair_raw = chat(
            api_key=api_key,
            model=model,
            fallback_model=fallback_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Repita a mesma compreensão e retorne SOMENTE JSON válido, curto e completo. "
                        "Não escreva por Mary. Não invente fatos, intenções ou atividades."
                    ),
                },
                {"role": "user", "content": payload},
            ],
            temperature=0.0,
            max_tokens=420,
        )
        repaired, repair_error = _parse_understanding(repair_raw)
        if not repair_error:
            raw = repair_raw
            parsed = repaired
            parse_error = ""
        else:
            parse_error = parse_error + " | retry: " + repair_error

    relevant_facts = parsed.get("relevant_facts", [])
    if not isinstance(relevant_facts, list):
        relevant_facts = []

    raw_ambiguity = parsed.get("ambiguity", False)
    if isinstance(raw_ambiguity, bool):
        ambiguity = raw_ambiguity
    else:
        ambiguity_text = str(raw_ambiguity or "").strip().casefold()
        ambiguity = ambiguity_text in {
            "true", "sim", "yes", "1", "ambíguo", "ambiguo", "há ambiguidade", "ha ambiguidade"
        }

    raw_requires_response = parsed.get("requires_response", False)
    if isinstance(raw_requires_response, bool):
        requires_response = raw_requires_response
    else:
        requires_response = str(raw_requires_response or "").strip().casefold() in {
            "true", "sim", "yes", "1"
        }
    response_requirement = str(parsed.get("response_requirement", "") or "").strip()

    raw_factual_conflict = parsed.get("factual_conflict", False)
    if isinstance(raw_factual_conflict, bool):
        factual_conflict = raw_factual_conflict
    else:
        factual_conflict = str(raw_factual_conflict or "").strip().casefold() in {
            "true", "sim", "yes", "1"
        }

    result = {
        "literal_meaning": str(parsed.get("literal_meaning", "") or "").strip(),
        "reference": str(parsed.get("reference", "") or "").strip(),
        "intent": str(parsed.get("intent", "") or "").strip(),
        "emotional_reaction": str(parsed.get("emotional_reaction", "") or "").strip(),
        "subtext": str(parsed.get("subtext", "") or "").strip(),
        "ambiguity": ambiguity,
        "confidence": parsed.get("confidence", ""),
        "unclear_point": str(parsed.get("unclear_point", "") or "").strip(),
        "expected_mary_reaction": str(parsed.get("expected_mary_reaction", "") or "").strip(),
        "factual_conflict": factual_conflict,
        "factual_correction": str(parsed.get("factual_correction", "") or "").strip(),
        "relevant_facts": [
            str(value or "").strip() for value in relevant_facts if str(value or "").strip()
        ],
        "user_obligation": {
            "exists": requires_response,
            "requirement": response_requirement,
        },
        # Compatibilidade com o Redator e o Diretor atuais.
        "user_meaning": str(parsed.get("literal_meaning", "") or "").strip(),
        "natural_bridge": "",
        "guide_requirements": [],
        "raw_response": raw,
        "input_payload": payload,
        "parse_error": parse_error,
    }
    return result


def save_user_understanding_audit(
    *,
    service_account_info: dict,
    spreadsheet_id: str,
    spreadsheet_title: str,
    owner_email: str,
    run_id: str,
    chapter_id: str,
    chapter_instance_id: str,
    chapter_turn: int,
    row: dict,
    user_text: str,
    previous_mary_text: str,
    audit: dict,
) -> None:
    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    ws = _ensure_worksheet(book, SHEET, HEADERS)
    ws.append_row(
        [
            _now(),
            run_id,
            chapter_id,
            chapter_instance_id,
            int(chapter_turn or 0),
            str(row.get("line_id", "") or ""),
            int(row.get("order", 0) or 0),
            _audit_cell(user_text),
            _audit_cell(previous_mary_text),
            _audit_cell(audit.get("literal_meaning", "")),
            _audit_cell(audit.get("reference", "")),
            _audit_cell(audit.get("intent", "")),
            _audit_cell(audit.get("emotional_reaction", "")),
            _audit_cell(audit.get("subtext", "")),
            bool(audit.get("ambiguity", False)),
            audit.get("confidence", ""),
            _audit_cell(audit.get("unclear_point", "")),
            _audit_cell(audit.get("expected_mary_reaction", "")),
            _audit_cell(audit.get("raw_response", "")),
            str(audit.get("parse_error", "") or ""),
        ],
        value_input_option="RAW",
    )
