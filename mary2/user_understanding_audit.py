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
    recent_user_facts: list[str] | None = None,
    active_interlocutor: str = "",
    previous_conversation_state: dict | None = None,
    instant_memory: str = "",
    permanent_memory: str = "",
    physical_memory: str = "",
    initial_description: str = "",
    revelation_policy: str = "",
) -> dict:
    """Compreende a fala do usuário sem receber fala-guia ou roteiro futuro."""
    recent_lines: list[str] = []
    for message in (recent_messages or [])[-14:]:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "") or "").strip().lower()
        content = str(message.get("content", "") or "").strip()
        if not content:
            continue
        speaker = "MARY" if role == "assistant" else "USUÁRIO"
        recent_lines.append(f"{speaker}: {content}")
    recent_context = "\n".join(recent_lines).strip()
    grounded_recent_facts = [
        str(value or "").strip()
        for value in (recent_user_facts or [])
        if str(value or "").strip()
    ][-16:]
    recent_facts_text = "\n".join(f"- {value}" for value in grounded_recent_facts)
    previous_state_text = json.dumps(
        previous_conversation_state if isinstance(previous_conversation_state, dict) else {},
        ensure_ascii=False,
    )

    payload = (
        "CONTEXTO ESTÁVEL SOBRE MARY\n"
        + (str(permanent_memory or "").strip() or "(não informado)")
        + "\n\nCONTEXTO FÍSICO ESTÁVEL\n"
        + (str(physical_memory or "").strip() or "(não informado)")
        + "\n\nDESCRIÇÃO INICIAL DA CENA\n"
        + (str(initial_description or "").strip() or "(não informada)")
        + "\n\nREGRA DE REVELAÇÃO DA LINHA ATUAL\n"
        + (str(revelation_policy or "").strip() or "(sem restrição autoral específica)")
        + "\n\nINTERLOCUTOR ATIVO\n"
        + (str(active_interlocutor or "").strip() or "(não especificado)")
        + "\n\nESTADO CONVERSACIONAL ANTERIOR — INTERPRETAÇÃO DO ÚLTIMO MOVIMENTO DE MARY\n"
        + (previous_state_text or "{}")
        + "\n\nESTADO OBJETIVO ATUAL\n"
        + (str(instant_memory or "").strip() or "(não informado)")
        + "\n\nFATOS/DECISÕES RECENTES DO USUÁRIO — TRECHOS LITERAIS\n"
        + (recent_facts_text or "(nenhum fato estruturado)")
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
        "5. FATOS/DECISÕES RECENTES DO USUÁRIO — trechos literais; os mais recentes vencem conflitos anteriores\n"
        "6. CONTEXTO RECENTE REAL E FALAS ANTERIORES\n"
        "Se uma fala anterior de Mary contradizer qualquer fonte autoritativa acima, trate a fala anterior como erro de continuidade. "
        "Não a transforme em fato consolidado e não a use para reinterpretar a realidade.\n"
        + "\nTAREFA\n"
        "Compreenda SOMENTE a fala atual do usuário à luz do passado e do presente já estabelecidos. "
        "A REGRA DE REVELAÇÃO DA LINHA ATUAL limita o que Mary pode verbalizar agora, mesmo quando a DESCRIÇÃO INICIAL DA CENA contém fatos completos que Mary conhece. "
        "Conhecimento de Mary não equivale a autorização de revelação. "
        "Se o usuário pedir diretamente um fato marcado como NÃO PODE, NÃO transforme isso em obrigação de revelar o conteúdo reservado. "
        "A obrigação deve ser reagir adequadamente à pergunta sem mentir, sem inventar e sem antecipar: Mary pode reconhecer a pressão, hesitar, prometer contar ou preparar a revelação. "
        "O ESTADO CONVERSACIONAL ANTERIOR é a interpretação semântica do que Mary acabou de fazer na conversa; "
        "use-o para determinar COMO a fala atual do usuário se relaciona ao turno anterior, em vez de apenas justapor textos. "
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
        "ANCORAGEM RELACIONAL: quando o papel já conhecido do interlocutor estiver diretamente ligado à fala atual ou ao acontecimento recente, "
        "a reação adequada de Mary deve usar essa relação concreta. Evite sugerir resposta social genérica e não trate o interlocutor como se estivesse sendo conhecido agora. "
        "VOCATIVO NÃO MUDA IDENTIDADE: adjetivo, apelido ou vocativo que o usuário dirige a Mary descreve Mary naquele ato de fala, não o usuário. "
        "Não devolva automaticamente ao usuário o mesmo adjetivo/apelido e nunca use isso para inferir gênero, papel ou identidade dele. "
        "Se o gênero do interlocutor não estiver explicitamente estabelecido nas fontes, prefira formulações sem marcação de gênero, como 'a gente' ou 'nós'. "
        "Justificativas improvisadas de Mary após um erro — por exemplo dizer que está distraída, confusa ou com a cabeça longe — "
        "não são traços psicológicos autoritativos e não devem ser consolidadas como verdade sobre Mary sem apoio nas memórias. "
        "Retorne somente JSON curto com estas oito chaves: "
        "{\"relation_to_previous\":\"\",\"move\":\"\",\"meaning\":\"\",\"reference\":\"\",\"obligation\":\"\",\"state_changes\":[],\"conflict\":\"\",\"reaction\":\"\"}. "
        "relation_to_previous descreve a relação causal/conversacional com o último movimento de Mary: responde, devolve brincadeira, corrige, aceita, recusa, muda de assunto, continua ação etc. "
        "move descreve o ato conversacional atual do usuário. "
        "state_changes deve conter SOMENTE mudanças persistentes explicitamente estabelecidas pela fala atual: fato novo, decisão, aceite, recusa, limite ou correção; não inclua perguntas, vocativos, brincadeiras ou comandos efêmeros. "
        "obligation deve ser uma frase curta apenas quando a fala atual exige resposta, esclarecimento ou reconhecimento direto; caso contrário, vazio. "
        "conflict deve conter somente a correção factual necessária quando houver conflito com fonte autoritativa; caso contrário, vazio. "
        "reaction descreve de forma curta o tipo de reação adequada de Mary, sem escrever a fala final."
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
                    "Não reabra decisões já resolvidas e preserve a menor quantidade de entidades compatível com os fatos. "
                    "Quando houver relação ativa conhecida, interprete a fala a partir dela e do acontecimento recente pertinente."
                ),
            },
            {"role": "user", "content": payload},
        ],
        temperature=0.0,
        max_tokens=520,
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
                        "Retorne SOMENTE JSON válido e completo no formato mínimo: "
                        "{\"relation_to_previous\":\"\",\"move\":\"\",\"meaning\":\"\",\"reference\":\"\",\"obligation\":\"\",\"state_changes\":[],\"conflict\":\"\",\"reaction\":\"\"}. "
                        "Preserve apenas fatos sustentados pelo contexto. Não escreva por Mary e não invente fatos, intenções ou atividades."
                    ),
                },
                {"role": "user", "content": payload},
            ],
            temperature=0.0,
            max_tokens=520,
        )
        repaired, repair_error = _parse_understanding(repair_raw)
        if not repair_error:
            raw = repair_raw
            parsed = repaired
            parse_error = ""
        else:
            parse_error = parse_error + " | retry: " + repair_error

    fallback_used = False
    if parse_error:
        # Falha dupla de JSON nunca pode apagar a compreensão do turno.
        # O fallback é deliberadamente conservador: preserva a fala literal
        # e só cria obrigação quando há pergunta explícita ou pedido de clareza.
        fallback_used = True
        user_value = str(user_text or "").strip()
        normalized_user = user_value.casefold()
        repair_markers = (
            "não entendi",
            "nao entendi",
            "explique",
            "esclareça",
            "esclareca",
            "você está confusa",
            "voce esta confusa",
            "você está confundindo",
            "voce esta confundindo",
        )
        obligation = (
            "Responder diretamente e esclarecer a fala atual do usuário."
            if "?" in user_value or any(marker in normalized_user for marker in repair_markers)
            else ""
        )
        parsed = {
            "relation_to_previous": "",
            "move": "",
            "meaning": user_value,
            "reference": "",
            "obligation": obligation,
            "state_changes": [],
            "conflict": "",
            "reaction": (
                "Responder de forma simples, factual e sem inventar continuidade."
                if user_value
                else ""
            ),
        }

    state_changes = parsed.get("state_changes", [])
    if not isinstance(state_changes, list):
        state_changes = []
    state_changes = [
        str(value or "").strip()
        for value in state_changes
        if str(value or "").strip()
    ][:8]

    # Não promova automaticamente fragmentos da fala atual para memória persistente.
    # Perguntas, brincadeiras, vocativos e comandos pertencem ao movimento conversacional,
    # não a uma lista genérica de "fatos recentes".
    combined_recent_facts = list(grounded_recent_facts)[-16:]

    meaning = str(parsed.get("meaning", "") or "").strip()
    reference = str(parsed.get("reference", "") or "").strip()
    obligation = str(parsed.get("obligation", "") or "").strip()
    conflict = str(parsed.get("conflict", "") or "").strip()
    reaction = str(parsed.get("reaction", "") or "").strip()

    result = {
        "relation_to_previous": str(parsed.get("relation_to_previous", "") or "").strip(),
        "move": str(parsed.get("move", "") or "").strip(),
        "literal_meaning": meaning,
        "reference": reference,
        "intent": "",
        "emotional_reaction": "",
        "subtext": "",
        "ambiguity": False,
        "confidence": "",
        "unclear_point": "",
        "expected_mary_reaction": reaction,
        "factual_conflict": bool(conflict),
        "factual_correction": conflict,
        "relevant_facts": state_changes,
        "state_changes": state_changes,
        "recent_user_facts": combined_recent_facts,
        "user_obligation": {
            "exists": bool(obligation),
            "requirement": obligation,
        },
        # Compatibilidade com o Redator e o Diretor atuais.
        "user_meaning": meaning,
        "natural_bridge": "",
        "guide_requirements": [],
        "raw_response": raw,
        "input_payload": payload,
        "parse_error": parse_error,
        "fallback_used": fallback_used,
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
