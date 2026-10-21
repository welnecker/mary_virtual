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
    mary_action: str = "",
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
    interpret_match = re.fullmatch(r"interpretar(?:\s*:\s*(.*))?", speech_guide, flags=re.I | re.S)
    interpret_mode = bool(interpret_match)
    interpret_direction = (interpret_match.group(1) or "").strip() if interpret_match else ""
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
    if _clean(mary_action):
        conversation_entries.append(("MARY_ACAO", _clean(mary_action)))
        history.append("ACAO REALIZADA POR MARY: " + _clean(mary_action))
    if _clean(mary_thought):
        conversation_entries.append(("MARY_PENSAMENTO", _clean(mary_thought)))
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
        + ("Interpretar (modo técnico)" if interpret_mode else (speech_guide or "(nenhuma)"))
        + ("\n\nDIREÇÃO AUTORAL DE INTERPRETAÇÃO — FOCO, NÃO TEXTO LITERAL\n" + interpret_direction if interpret_direction else "")
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
        + (_clean(mary_text) or "(sem fala neste turno)")
        + "\n\nACAO ATUAL REALIZADA POR MARY\n"
        + (_clean(mary_action) or "(sem acao fisica neste turno)")
        + (
            "\n\nPENSAMENTO ATUAL DE MARY\n" + _clean(mary_thought)
            if _clean(mary_thought)
            else ""
        )
        + "\n\nTAREFA — avalie os critérios separadamente, sem reescrever Mary.\n"
        + (
            "A) INTERPRETAR: a palavra é seletor, não fala obrigatória. Verifique se Mary interpreta a linha e sua direção autoral sem exigir palavras literais. Registre em objetivos_guia apenas 'interpretar a situação local'. "
            if interpret_mode else
            "A) OBJETIVOS: extraia somente da FALA-GUIA os atos conversacionais exigidos. Convites e promessas se cumprem ao serem formulados, não quando acontecem no futuro. Considere objetivos já satisfeitos por respostas literais do usuário; não invente objetivos. "
        )
        + ("Turno automático: pensamento pode cumprir finalidade introspectiva. " if automatic_row else "")
        + "B) CENA: confira o acontecimento central da MEMÓRIA INSTANTÂNEA-LOCAL. Movimento indispensável exige execução concreta em ACAO ATUAL ou evidência já realizada na conversa desta linha. Promessa e pensamento não comprovam ação. Defina acao_fisica_obrigatoria conforme a memória local; não exija ação se a linha é somente verbal. Cite evidência literal da resposta/ação atual ou conversa, nunca da memória como prova de execução. "
        + "C) CONTINUIDADE: Mary deve responder ao sentido da entrada atual, preservando interlocutor, autoria de ações, sujeito, destinatário e posição física. Memória local define a cena atual; descrição inicial pode mencionar futuro sem torná-lo presente. Corrija interpretações semânticas incompatíveis com fatos explícitos. "
        + "D) FATOS E REVELAÇÃO: fontes autoritativas prevalecem sobre falas anteriores. Marque apenas contradições objetivas; não trate estilo como erro factual. NÃO PODE impede verbalização mesmo sob pergunta, mas Mary deve reagir sem revelar nem inventar. "
        + "E) NATURALIDADE: respeite ESTILO/ATITUDE e a direção autoral da linha, sem impor vocabulário literal, intensidade fixa ou metáforas genéricas. ACAO, FALA e PENSAMENTO são complementares; pensamento é opcional. Reprove artificialidade somente quando evidente. "
        + "EVIDÊNCIAS: use fragmentos literais contínuos da conversa ou saída atual; nunca fabrique trechos. Preserve objetivos_guia, coerencia_conversacional, cena_atual, contradicao_dura, violacao_revelacao e demais campos do JSON. "
        + "Retorne somente JSON com: "
        "{\"obrigacao_usuario\":{\"existe\":true,\"requisito\":\"\",\"atendida\":true,\"evidencia\":\"\"},"
        "\"coerencia_conversacional\":{\"ok\":true,\"problema\":\"\",\"trecho_mary\":\"\",\"correcao\":\"\"},"
        "\"naturalidade\":{\"ok\":true,\"problema\":\"\",\"trecho_mary\":\"\",\"correcao\":\"\"},"
        "\"cena_atual\":{\"cumprida\":true,\"acao_fisica_obrigatoria\":false,\"acontecimento\":\"\",\"evidencia\":\"\",\"faltou\":\"\"},"
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
                    + (
                        "Se a fala-guia for Interpretar, avalie apenas a atuação contextual na memória instantânea, não o termo literal. "
                        if interpret_mode else
                        "Os objetivos da linha vêm somente da FALA-GUIA ORIGINAL e devem ser entendidos como atos conversacionais de Mary, não como resultados futuros. "
                    )
                    + "Não exija repetição literal da fala-guia. "
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

    natural_raw = parsed.get("naturalidade", {})
    if not isinstance(natural_raw, dict):
        natural_raw = {}
    naturalness = {
        "ok": bool(natural_raw.get("ok", True)),
        "issue": _clean(natural_raw.get("problema")),
        "mary_excerpt": _clean(natural_raw.get("trecho_mary")),
        "correction": _clean(natural_raw.get("correcao")),
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

    scene_raw = parsed.get("cena_atual", {})
    if not isinstance(scene_raw, dict):
        scene_raw = {}
    # Evidencias devem estar na saida realmente produzida; o roteiro e a
    # memoria local especificam a meta, mas nunca comprovam sua execucao.
    evidence = _clean(scene_raw.get("evidencia"))
    observed = " ".join(filter(None, [_clean(mary_text), _clean(mary_thought), _clean(mary_action), _clean(user_scene_direction)]))
    evidence_grounded = bool(evidence and evidence.casefold() in observed.casefold())
    scene_claim = bool(scene_raw.get("cumprida", False))
    physical_required = bool(scene_raw.get("acao_fisica_obrigatoria", False))
    # A fala, a promessa e o pensamento nao comprovam deslocamento fisico.
    physical_evidence = bool(_clean(mary_action)) and bool(
        evidence and evidence.casefold() in _clean(mary_action).casefold()
    )
    if interpret_mode and physical_required and not physical_evidence:
        scene_raw["faltou"] = "Movimento obrigatorio sem evidencia em [AÇÃO]."
    if interpret_mode and scene_claim and not evidence_grounded:
        scene_raw["faltou"] = "Diretor citou evidencia ausente da saida de Mary ou da encenacao do usuario."
    scene_completion = {
        "fulfilled": (scene_claim and evidence_grounded and (not physical_required or physical_evidence)) if interpret_mode else True,
        "event": _clean(scene_raw.get("acontecimento")),
        "evidence": evidence if evidence_grounded else "",
        "missing": _clean(scene_raw.get("faltou")),
    }

    all_objectives = (
        True
        if interpret_mode or not speech_guide
        else bool(normalized_objectives)
        and all(bool(item.get("found")) for item in normalized_objectives)
    )

    fulfilled = (
        not parse_error
        and not hard_contradiction["exists"]
        and not revelation_violation["exists"]
        and conversation_consistency["ok"]
        and naturalness["ok"]
        and normalized_obligation["satisfied"]
        and all_objectives
        and scene_completion["fulfilled"]
        and bool(parsed.get("cumpriu", False))
    )

    missing_parts = []
    if not scene_completion["fulfilled"]:
        missing_parts.append(scene_completion["missing"] or "acontecimento central da linha ainda nao ocorreu")
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
        "naturalness": naturalness,
        "scene_completion": scene_completion,
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
