from __future__ import annotations

import json
import re
import time

from openrouter_client import chat


def _clean(value) -> str:
    return str(value or "").strip()


def validate_direct_semantic_turn(
    *,
    api_key: str,
    model: str,
    fallback_model: str | None,
    row: dict,
    interpretation: dict,
    mary_text: str,
    user_text: str = "",
    line_dialogue: list[dict] | None = None,
) -> dict:
    """Valida em uma só chamada: finalidade da linha + consistência factual dura."""
    obligation = interpretation.get("user_obligation", {}) if isinstance(interpretation, dict) else {}
    if not isinstance(obligation, dict):
        obligation = {}
    obligation_exists = bool(obligation.get("exists", False))
    obligation_text = _clean(obligation.get("requirement"))
    speech_guide = _clean(row.get("speech_guide"))

    history: list[str] = []
    for message in (line_dialogue or [])[-10:]:
        if not isinstance(message, dict):
            continue
        role = _clean(message.get("role")).lower()
        content = _clean(message.get("content"))
        if not content:
            continue
        history.append(("MARY" if role == "assistant" else "USUÁRIO") + ": " + content)
    if _clean(user_text):
        history.append("USUÁRIO: " + _clean(user_text))
    if _clean(mary_text):
        history.append("MARY: " + _clean(mary_text))
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
        "Significado: "
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
        + "\n\nCOMPREENSÃO DA FALA ATUAL\n"
        + understanding
        + "\n\nOBRIGAÇÃO CONVERSACIONAL ATUAL\n"
        + (obligation_text if obligation_exists else "(nenhuma)")
        + "\n\nCONVERSA DA LINHA ATIVA\n"
        + conversation
        + "\n\nRESPOSTA ATUAL DE MARY\n"
        + _clean(mary_text)
        + "\n\nTAREFA\n"
        "Faça duas validações independentes. "
        "A) FINALIDADE DA LINHA: primeiro decomponha EXCLUSIVAMENTE a FALA-GUIA ORIGINAL em seus objetivos semânticos. "
        "Não use a fala atual do usuário, a compreensão atual ou a resposta de Mary para inventar novos objetivos da linha. "
        "Depois determine se esses objetivos da FALA-GUIA já aconteceram na conversa. "
        "Uma informação fornecida espontaneamente pelo USUÁRIO pode cumprir um objetivo sem Mary precisar repetir a pergunta. "
        "Exija evidência literal na CONVERSA DA LINHA. "
        "B) CONSISTÊNCIA FACTUAL: verifique se a RESPOSTA ATUAL DE MARY contradiz algum fato explícito das FONTES AUTORITATIVAS. "
        "As fontes autoritativas vencem falas anteriores de Mary. "
        "Contradição dura inclui troca de proprietário, motorista/passageiro, residência, relacionamento, posição física ou outro fato objetivo explícito. "
        "Não marque contradição por estilo, opinião, criatividade compatível ou missão incompleta. "
        "A obrigação conversacional atual, quando existir, deve ser atendida pela RESPOSTA ATUAL DE MARY. "
        "Retorne somente JSON com: "
        "{\"obrigacao_usuario\":{\"existe\":true,\"requisito\":\"\",\"atendida\":true,\"evidencia\":\"\"},"
        "\"objetivos_guia\":[{\"objetivo\":\"\",\"alcancado\":true,\"fonte\":\"USUÁRIO\",\"evidencia\":\"\"}],"
        "\"contradicao_dura\":{\"existe\":false,\"fato_autoritativo\":\"\",\"trecho_mary\":\"\",\"correcao\":\"\"},"
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
                    "Valide finalidade da linha e verdade factual. "
                    "Os objetivos da linha vêm somente da FALA-GUIA ORIGINAL. "
                    "Não exija repetição literal da fala-guia. "
                    "Nunca invente evidência."
                ),
            },
            {"role": "user", "content": payload},
        ],
        temperature=0.0,
        max_tokens=460,
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
        valid = bool(evidence) and evidence.casefold() in conversation_norm
        normalized_objectives.append(
            {
                "requirement": _clean(item.get("objetivo")),
                "found": bool(item.get("alcancado", False)) and valid,
                "source": _clean(item.get("fonte")).upper(),
                "evidence": evidence if valid else "",
            }
        )

    obligation_raw = parsed.get("obrigacao_usuario", {})
    if not isinstance(obligation_raw, dict):
        obligation_raw = {}
    obligation_evidence = _clean(obligation_raw.get("evidencia"))
    obligation_evidence_valid = bool(obligation_evidence) and obligation_evidence.casefold() in response_norm
    normalized_obligation = {
        "exists": obligation_exists,
        "requirement": obligation_text,
        "satisfied": (
            True
            if not obligation_exists
            else bool(obligation_raw.get("atendida", False)) and obligation_evidence_valid
        ),
        "evidence": obligation_evidence if obligation_evidence_valid else "",
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

    all_objectives = (
        True
        if not speech_guide
        else bool(normalized_objectives)
        and all(bool(item.get("found")) for item in normalized_objectives)
    )

    fulfilled = (
        not parse_error
        and not hard_contradiction["exists"]
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
        "model": model,
        "duration_ms": duration_ms,
        "input_payload": payload,
        "raw_response": raw,
        "parsed_response": parsed,
        "parse_error": parse_error,
    }
