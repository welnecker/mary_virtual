from __future__ import annotations

import json
import re
import time

from openrouter_client import chat


def _clean(value) -> str:
    return str(value or "").strip()


def _evidence_source(evidence: str, entries: list[tuple[str, str]]) -> str:
    """Determina a autoria pela conversa real, nunca pelo rótulo produzido pelo LLM.

    Aceita uma citação literal contínua ou uma citação abreviada por reticências,
    desde que TODOS os fragmentos substantivos existam literalmente na MESMA fala.
    Isso evita falso negativo quando o Diretor encurta uma evidência real sem
    permitir que uma paráfrase inventada conte como prova.
    """
    needle = _clean(evidence).casefold()
    if not needle:
        return ""

    for source, content in entries:
        haystack = _clean(content).casefold()
        if needle in haystack:
            return source

    # O Diretor às vezes cita dois trechos reais da mesma fala unidos por "..."
    # ou "(...)". Valide somente se todos os fragmentos relevantes forem literais
    # e pertencerem ao mesmo enunciado.
    fragments = [
        _clean(part).casefold().strip(" .,!?:;()[]{}-—")
        for part in re.split(r"(?:\.\.\.|…|\(\.\.\.\)|\[…\])", evidence)
    ]
    fragments = [part for part in fragments if len(part) >= 8]
    if len(fragments) < 2:
        return ""

    for source, content in entries:
        haystack = _clean(content).casefold()
        if all(fragment in haystack for fragment in fragments):
            return source
    return ""


def validate_direct_semantic_turn(
    *,
    api_key: str,
    model: str,
    fallback_model: str | None,
    row: dict,
    interpretation: dict,
    mary_text: str,
    mary_thought: str = "",
    user_text: str = "",
    user_scene_direction: str = "",
    line_dialogue: list[dict] | None = None,
) -> dict:
    """Valida em uma só chamada: finalidade da linha + consistência factual dura."""
    obligation = interpretation.get("user_obligation", {}) if isinstance(interpretation, dict) else {}
    if not isinstance(obligation, dict):
        obligation = {}
    obligation_exists = bool(obligation.get("exists", False))
    obligation_text = _clean(obligation.get("requirement"))
    speech_guide = _clean(row.get("speech_guide"))
    revelation_policy = _clean(row.get("revelation_policy"))
    interaction_mode = _clean(row.get("interaction_mode")).casefold()
    automatic_row = interaction_mode in {"automatico", "automático", "automatic"}

    recent_user_facts = interpretation.get("recent_user_facts", []) if isinstance(interpretation, dict) else []
    if not isinstance(recent_user_facts, list):
        recent_user_facts = []
    grounded_recent_facts = [
        _clean(value) for value in recent_user_facts if _clean(value)
    ][-16:]

    history: list[str] = []
    conversation_entries: list[tuple[str, str]] = [
        ("USUÁRIO", value) for value in grounded_recent_facts
    ]
    for message in (line_dialogue or [])[-10:]:
        if not isinstance(message, dict):
            continue
        role = _clean(message.get("role")).lower()
        content = _clean(message.get("content"))
        if not content:
            continue
        source = "MARY" if role == "assistant" else "USUÁRIO"
        conversation_entries.append((source, content))
        history.append(source + ": " + content)
    if _clean(user_scene_direction):
        conversation_entries.append(("USUÁRIO", _clean(user_scene_direction)))
        history.append("DIREÇÃO/ENCENAÇÃO DO USUÁRIO: " + _clean(user_scene_direction))
    if _clean(user_text):
        conversation_entries.append(("USUÁRIO", _clean(user_text)))
        history.append("FALA DO USUÁRIO: " + _clean(user_text))
    if _clean(mary_text):
        conversation_entries.append(("MARY", _clean(mary_text)))
        history.append("MARY: " + _clean(mary_text))
    if automatic_row and _clean(mary_thought):
        conversation_entries.append(("MARY", _clean(mary_thought)))
        history.append("PENSAMENTO DE MARY: " + _clean(mary_thought))
    conversation = "\n".join(history) or "(sem histórico da linha)"

    authoritative = (
        "MEMÓRIA PERMANENTE-GLOBAL\n"
        + (_clean(row.get("permanent_memory")) or "(não informada)")
        + "\n\nMEMÓRIA FÍSICA-GLOBAL\n"
        + (_clean(row.get("physical_memory")) or "(não informada)")
        + "\n\nMEMÓRIA INSTANTÂNEA-LOCAL\n"
        + (_clean(row.get("instant_memory")) or "(não informada)")
        + "\n\nDESCRIÇÃO INICIAL-CENA\n"
        + (_clean(row.get("initial_description")) or "(não informada)")
    )

    understanding = (
        "Relação com o movimento anterior: "
        + (_clean(interpretation.get("relation_to_previous")) or "(não determinada)")
        + "\nMovimento atual do usuário: "
        + (_clean(interpretation.get("move")) or "(não determinado)")
        + "\nSignificado: "
        + (_clean(interpretation.get("literal_meaning")) or _clean(interpretation.get("user_meaning")) or "(não determinado)")
        + "\nReferência: " + (_clean(interpretation.get("reference")) or "(não determinada)")
        + "\nIntenção: " + (_clean(interpretation.get("intent")) or "(não determinada)")
        + "\nSubtexto: " + (_clean(interpretation.get("subtext")) or "(nenhum)")
    )

    payload = (
        "FONTES AUTORITATIVAS\n"
        + authoritative
        + "\n\nFALA-GUIA ORIGINAL\n"
        + (speech_guide or "(nenhuma)")
        + "\n\nREGRA DE REVELAÇÃO DA LINHA ATUAL\n"
        + (revelation_policy or "(sem restrição autoral específica)")
        + "\n\nCOMPREENSÃO DA ENTRADA ATUAL\n"
        + understanding
        + "\n\nOBRIGAÇÃO CONVERSACIONAL ATUAL\n"
        + (obligation_text if obligation_exists else "(nenhuma)")
        + "\n\nFATOS/DECISÕES RECENTES DO USUÁRIO — TRECHOS LITERAIS ATERRADOS\n"
        + ("\n".join(f"- {value}" for value in grounded_recent_facts) or "(nenhum)")
        + "\n\nCONVERSA DA LINHA ATIVA\n"
        + conversation
        + "\n\nRESPOSTA ATUAL DE MARY\n"
        + _clean(mary_text)
        + (
            "\n\nPENSAMENTO ATUAL DE MARY\n" + _clean(mary_thought)
            if automatic_row and _clean(mary_thought)
            else ""
        )
        + "\n\nTAREFA\n"
        "Faça quatro validações independentes. "
        "A) FINALIDADE DA LINHA: primeiro decomponha EXCLUSIVAMENTE a FALA-GUIA ORIGINAL nos ATOS CONVERSACIONAIS que Mary deve realizar. "
        + (
            "Esta linha é AUTOMÁTICA: o PENSAMENTO ATUAL DE MARY também é saída válida e pode cumprir a FALA-GUIA, especialmente quando a linha é introspectiva. "
            if automatic_row
            else ""
        )
        + "Exemplos de atos: perguntar, contar, admitir, propor, convidar, prometer, provocar, esclarecer, pedir. "
        "Não converta um ato conversacional em resultado futuro. Exemplo: 'me levar para a balada' dentro de um convite significa Mary FORMULAR O CONVITE; "
        "não significa que a ida à balada já tenha acontecido. 'Eu prometo que vou ser divertida' significa Mary FAZER A PROMESSA; "
        "não significa que ela já tenha sido divertida na balada. "
        "Não use a fala atual do usuário, a compreensão atual ou a resposta de Mary para inventar novos objetivos da linha. "
        "Depois determine se esses atos da FALA-GUIA já foram realizados na conversa. "
        "Uma informação fornecida espontaneamente pelo USUÁRIO pode cumprir um objetivo sem Mary precisar repetir a pergunta. "
        "Os FATOS/DECISÕES RECENTES DO USUÁRIO são trechos literais previamente aterrados no texto real do usuário e também podem cumprir a finalidade quando responderem diretamente ao objetivo. "
        "Pronomes e possessivos da FALA-GUIA são lidos da perspectiva de Mary: 'me' refere-se a Mary; 'me levar' significa o interlocutor levar Mary, salvo contexto explícito contrário. "
        "Exija evidência literal na CONVERSA DA LINHA ou nos FATOS/DECISÕES RECENTES DO USUÁRIO aterrados. "
        "No campo evidencia, prefira UMA citação literal contínua. Se precisar abreviar uma citação longa, use reticências apenas para ligar fragmentos que existam literalmente na MESMA fala; nunca parafraseie a evidência. "
        "B) COERÊNCIA CONVERSACIONAL: compare a COMPREENSÃO DA ENTRADA ATUAL com a RESPOSTA ATUAL DE MARY. A entrada pode conter direção/encenação e fala; preserve ambas sem transformar uma na outra. "
        "Verifique se Mary respeitou quem iniciou cada ação, quem é alvo de vocativos, perguntas, provocações, aceitações, recusas e correções, e se respondeu ao movimento atual sem inverter sujeito, destinatário, posse ou iniciativa. "
        "Não exija que Mary repita as palavras do usuário; valide o sentido e a relação causal com o movimento anterior. "
        "C) CONSISTÊNCIA FACTUAL: verifique se a RESPOSTA ATUAL DE MARY contradiz algum fato explícito das FONTES AUTORITATIVAS. "
        "As fontes autoritativas vencem falas anteriores de Mary. "
        "Contradição dura inclui troca de identidade, papel, profissão, função, proprietário, motorista/passageiro, residência, relacionamento, posição física ou outro fato objetivo explícito. "
        "Não marque contradição por estilo, opinião, criatividade compatível ou missão incompleta. "
        "D) LIMITE DE REVELAÇÃO: compare a RESPOSTA ATUAL DE MARY com a REGRA DE REVELAÇÃO DA LINHA ATUAL. "
        "Fatos marcados como NÃO PODE podem existir na DESCRIÇÃO INICIAL e serem conhecidos por Mary, mas não podem ser verbalizados ainda. "
        "Se o usuário perguntou diretamente por conteúdo reservado, isso NÃO autoriza quebrar a fronteira; Mary deve reagir sem mentir, sem inventar e sem revelar o dado reservado. "
        "Marque violação somente quando Mary efetivamente verbalizar conteúdo que a regra atual proíbe. "
        "A obrigação conversacional atual, quando existir, deve ser atendida pela RESPOSTA ATUAL DE MARY dentro dessa fronteira de revelação. "
        "Não reprove uma linha verbal por Mary não executar uma ação física que não esteja na FALA-GUIA; ações físicas pertencem ao runtime/cena. "
        "Retorne somente JSON com: "
        "{\"obrigacao_usuario\":{\"existe\":true,\"requisito\":\"\",\"atendida\":true,\"evidencia\":\"\"},"
        "\"coerencia_conversacional\":{\"ok\":true,\"problema\":\"\",\"trecho_mary\":\"\",\"correcao\":\"\"},"
        "\"objetivos_guia\":[{\"objetivo\":\"\",\"alcancado\":true,\"fonte\":\"USUÁRIO\",\"evidencia\":\"\"}],"
        "\"contradicao_dura\":{\"existe\":false,\"fato_autoritativo\":\"\",\"trecho_mary\":\"\",\"correcao\":\"\"},"
        "\"violacao_revelacao\":{\"existe\":false,\"conteudo_reservado\":\"\",\"trecho_mary\":\"\",\"correcao\":\"\"},"
        "\"cumpriu\":true,\"faltou\":\"\",\"motivo\":\"\"}."
    )

    started = time.perf_counter()
    raw = chat(
        api_key=api_key,
        model=model,
        fallback_model=fallback_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um Diretor de continuidade semântica. "
                    "Valide finalidade da linha, coerência com o movimento atual do usuário, verdade factual e limite de revelação. "
                    "Os objetivos da linha vêm somente da FALA-GUIA ORIGINAL e devem ser entendidos como atos conversacionais de Mary, não como resultados futuros. "
                    "Não exija repetição literal da fala-guia. "
                    "Nunca invente evidência."
                ),
            },
            {"role": "user", "content": payload},
        ],
        temperature=0.0,
        max_tokens=1400,
    )
    duration_ms = round((time.perf_counter() - started) * 1000.0, 1)

    parsed = {}
    parse_error = ""
    try:
        text = str(raw or "").strip()
        text = re.sub(r"^\s*\x60\x60\x60(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*\x60\x60\x60\s*$", "", text)
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= start:
            text = text[start : end + 1]
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("director response is not a JSON object")
    except Exception as exc:
        parse_error = str(exc)
        parsed = {}

    conversation_norm = conversation.casefold()
    response_norm = _clean(mary_text).casefold()

    objectives = parsed.get("objetivos_guia", [])
    if not isinstance(objectives, list):
        objectives = []
    normalized_objectives = []
    for item in objectives:
        if not isinstance(item, dict):
            continue
        evidence = _clean(item.get("evidencia"))
        claimed_source = _clean(item.get("fonte")).upper()
        source = _evidence_source(evidence, conversation_entries)
        valid = bool(evidence) and bool(source)
        normalized_objectives.append(
            {
                "requirement": _clean(item.get("objetivo")),
                "found": bool(item.get("alcancado", False)) and valid,
                "source": source,
                "claimed_source": claimed_source,
                "evidence": evidence if valid else "",
                "invalid_guide_evidence": False,
            }
        )

    obligation_raw = parsed.get("obrigacao_usuario", {})
    if not isinstance(obligation_raw, dict):
        obligation_raw = {}
    obligation_evidence = _clean(obligation_raw.get("evidencia"))
    obligation_claimed_satisfied = bool(obligation_raw.get("atendida", False))
    # A obrigação é uma validação semântica. A evidência pode ser citação literal
    # OU uma descrição curta do que Mary fez; não exija substring literal inteira.
    obligation_evidence_valid = (
        True
        if not obligation_exists
        else obligation_claimed_satisfied and bool(obligation_evidence)
    )
    normalized_obligation = {
        "exists": obligation_exists,
        "requirement": obligation_text,
        "satisfied": (
            True
            if not obligation_exists
            else obligation_claimed_satisfied and obligation_evidence_valid
        ),
        "evidence": obligation_evidence if obligation_evidence_valid else "",
    }

    coherence_raw = parsed.get("coerencia_conversacional", {})
    if not isinstance(coherence_raw, dict):
        coherence_raw = {}
    conversation_consistency = {
        "ok": bool(coherence_raw.get("ok", True)),
        "issue": _clean(coherence_raw.get("problema")),
        "mary_excerpt": _clean(coherence_raw.get("trecho_mary")),
        "correction": _clean(coherence_raw.get("correcao")),
    }

    contradiction_raw = parsed.get("contradicao_dura", {})
    if not isinstance(contradiction_raw, dict):
        contradiction_raw = {}
    hard_contradiction = {
        "exists": bool(contradiction_raw.get("existe", False)),
        "authoritative_fact": _clean(contradiction_raw.get("fato_autoritativo")),
        "mary_excerpt": _clean(contradiction_raw.get("trecho_mary")),
        "correction": _clean(contradiction_raw.get("correcao")),
    }

    revelation_raw = parsed.get("violacao_revelacao", {})
    if not isinstance(revelation_raw, dict):
        revelation_raw = {}
    revelation_violation = {
        "exists": bool(revelation_raw.get("existe", False)),
        "reserved_content": _clean(revelation_raw.get("conteudo_reservado")),
        "mary_excerpt": _clean(revelation_raw.get("trecho_mary")),
        "correction": _clean(revelation_raw.get("correcao")),
    }

    all_objectives = (
        True
        if not speech_guide
        else bool(normalized_objectives)
        and all(bool(item.get("found")) for item in normalized_objectives)
    )

    fulfilled = (
        not parse_error
        and not hard_contradiction["exists"]
        and not revelation_violation["exists"]
        and conversation_consistency["ok"]
        and normalized_obligation["satisfied"]
        and all_objectives
        and bool(parsed.get("cumpriu", False))
    )

    missing_parts = []
    if obligation_exists and not normalized_obligation["satisfied"]:
        missing_parts.append(obligation_text or "responder à fala atual do usuário")
    for item in normalized_objectives:
        if not item["found"] and item["requirement"]:
            missing_parts.append(item["requirement"])

    return {
        "fulfilled": fulfilled,
        "missing": "; ".join(missing_parts) or _clean(parsed.get("faltou")),
        "reason": _clean(parsed.get("motivo")),
        "elements": normalized_objectives,
        "user_obligation": normalized_obligation,
        "hard_contradiction": hard_contradiction,
        "revelation_violation": revelation_violation,
        "conversation_consistency": conversation_consistency,
        "model": model,
        "duration_ms": duration_ms,
        "input_payload": payload,
        "raw_response": raw,
        "parsed_response": parsed,
        "parse_error": parse_error,
        "invalid_guide_evidence": any(
            bool(item.get("invalid_guide_evidence", False))
            for item in normalized_objectives
        ),
    }
