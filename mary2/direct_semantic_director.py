from __future__ import annotations

import json
import re
import time

from openrouter_client import chat


def _clean(value) -> str:
    return str(value or "").strip()


def _normalize_evidence_text(value: str) -> str:
    """Ignore Markdown around speaker labels without weakening factual evidence.

    'Silvia:' and '**Silvia:**' are the same spoken label, while the
    words, punctuation, and evidence source remain otherwise unchanged.
    """
    normalized = _clean(value)
    # Supports **Silvia:** and **Silvia**: without removing emphasis from prose.
    normalized = re.sub(r"\*\*([^*\n]{1,80}:)\*\*", r"\1", normalized)
    normalized = re.sub(r"\*\*([^*\n]{1,80})\*\*:", r"\1:", normalized)
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def _evidence_source(evidence: str, entries: list[tuple[str, str]]) -> str:
    """Determina a autoria pela conversa real, nunca pelo rótulo produzido pelo LLM.

    Aceita uma citação literal contínua ou uma citação abreviada por reticências,
    desde que TODOS os fragmentos substantivos existam literalmente na MESMA fala.
    Isso evita falso negativo quando o Diretor encurta uma evidência real sem
    permitir que uma paráfrase inventada conte como prova.
    """
    needle = _normalize_evidence_text(evidence)
    if not needle:
        return ""

    for source, content in entries:
        haystack = _normalize_evidence_text(content)
        if needle in haystack:
            return source

    # O Diretor às vezes cita dois trechos reais da mesma fala unidos por "..."
    # ou "(...)". Valide somente se todos os fragmentos relevantes forem literais
    # e pertencerem ao mesmo enunciado.
    fragments = [
        _normalize_evidence_text(part).strip(" .,!?:;()[]{}-—")
        for part in re.split(r"(?:\.\.\.|…|\(\.\.\.\)|\[…\])", evidence)
    ]
    fragments = [part for part in fragments if len(part) >= 8]
    if len(fragments) < 2:
        return ""

    for source, content in entries:
        haystack = _normalize_evidence_text(content)
        if all(fragment in haystack for fragment in fragments):
            return source
    return ""


def _explicit_physical_requirement(*, speech_guide: str, action_guide: str) -> bool:
    """Only an explicit authorial physical command may block an Interpretar line.

    The Director cannot upgrade a description, a conditional opportunity or an
    already enacted user movement into a mandatory new Mary action.
    """
    guidance = "\n".join(filter(None, [_clean(speech_guide), _clean(action_guide)]))
    clauses = re.split(r"[.!?;\n]+", guidance)
    for clause in clauses:
        clause = clause.strip()
        if re.match(r"^(?:se|caso|quando|pode|poderá|poderia|talvez)\b", clause, flags=re.I):
            continue
        if re.search(
            r"\bmary\s+(?:deve|precisa|obrigatoriamente)\s+"
            r"(?:se\s+)?(?:aproximar|levantar|sentar|abrir|fechar|entrar|sair|"
            r"beijar|abraçar|pegar|segurar|mover|andar|ir|subir|deitar|"
            r"juntar|tirar|colocar|entregar|caminhar|tocar)\b",
            clause, flags=re.I,
        ):
            return True
    return False


def _guide_objective_is_optional(objective: str, speech_guide: str) -> bool:
    """Separate opportunities/style from required acts without weakening safety gates.

    This is deliberately conservative: unqualified, concrete obligations
    remain mandatory. A secondary character's optional contribution never
    blocks Mary's turn or forces the character to repeat a line.
    """
    obj = _clean(objective).casefold()
    guide = _clean(speech_guide).casefold()
    if not obj:
        return True

    # Personagens secundários indicados por rótulos autorais de fala
    # (SILVIA:, RICARDO:, etc.) são oportunidades, salvo obrigação explícita.
    secondary_labels = [
        label.casefold() for label in re.findall(
            r"(?m)^([A-ZÀ-Ý][A-ZÀ-Ý]{1,39}):", speech_guide or ""
        ) if label.casefold() != "mary"
    ]
    explicit = any(re.search(
        rf"\b{re.escape(label)}\s*:\s*(?:deve|precisa|obrigatoriamente|é obrigatório)",
        guide,
    ) for label in secondary_labels)
    mary_must_act = bool(re.search(
        r"\bmary\s*:\s*(?:deve|precisa|obrigatoriamente|é obrigatório)",
        guide,
    ))
    if secondary_labels and not explicit and not mary_must_act and not re.search(
        r"\b(?:deve|precisa|obrigatóri[oa]|obrigatoriamente)\b", obj
    ):
        # O vínculo Mary<->personagem secundário não deve prender a linha.
        # A obrigação conversacional atual e as verificações factuais permanecem.
        return True

    optional_prefix = (
        "se ", "caso ", "quando ", "pode ", "poderá ", "poderia ",
        "se fizer sentido", "se a conversa", "se houver",
        "evitar ", "não ", "sem ", "preferir ", "manter ",
        "permitir ", "podendo ", "com naturalidade",
    )
    if obj.startswith(optional_prefix):
        return True

    optional_patterns = (
        r"\b(?:pode|poderá|poderia|podendo|talvez|opcional|se couber)\b",
        r"\bse (?:a conversa|houver|surgir|fizer sentido|for pertinente)\b",
        r"\b(?:sem exigir|sem forçar|evitar|não repetir|não transformar)\b",
    )
    if any(re.search(p, obj) for p in optional_patterns):
        return True

    # Guias mistos: a primeira frase pode ser obrigatória, enquanto a
    # sugestão após "Se fizer sentido..." é opcional mesmo que o Diretor
    # a reformule como um imperativo isolado.
    if not re.search(r"\b(?:deve|precisa|obrigatóri[oa]|obrigatoriamente)\b", obj):
        objective_terms = set(re.findall(r"[a-zà-ÿ]{5,}", obj))
        for clause in re.split(r"[.!?;\n]+", guide):
            if re.match(r"\s*(?:se |caso |quando |pode |poderá |poderia )", clause):
                conditional_terms = set(re.findall(r"[a-zà-ÿ]{5,}", clause))
                shared = objective_terms & conditional_terms
                if len(shared) >= 2 or (len(objective_terms) == 1 and shared):
                    return True

    # A qualified guide can be paraphrased as a bare imperative by the LLM.
    # Keep its conditional meaning rather than promoting it into an order.
    # A guide beginning with a conditional is optional as a whole, even
    # if the Director paraphrases that opportunity as a bare command.
    if guide.startswith(("se ", "caso ", "quando ", "pode ", "poderá ", "poderia ")):
        if not re.search(r"\b(?:deve|precisa|obrigatóri[oa]|obrigatoriamente)\b", obj):
            return True
    return False


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
    explicit_physical_required = _explicit_physical_requirement(
        speech_guide=interpret_direction if interpret_mode else speech_guide,
        action_guide=_clean(row.get("action_guide")),
    )
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
        + "\n\nDESCRIÇÃO-GUIA DA LINHA ATUAL — MISSÃO FÍSICA\n"
        + (_clean(row.get("action_guide")) or "(sem ação especificada)")
        + "\n\nREGRA DE REVELAÇÃO DA LINHA ATUAL\n"
        + (revelation_policy or "(sem restrição autoral específica)")
        + "\n\nENTRADA ORIGINAL DO USUÁRIO — CONFERÊNCIA INDEPENDENTE\n"
        + "Fala literal: " + (_clean(user_text) or "(sem fala)") + "\n"
        + "Encenação literal: " + (_clean(user_scene_direction) or "(nenhuma)") + "\n"
        + "Para validar sujeito, alvo e ações, confronte a hipótese da Compreensão com estes trechos literais e com a conversa, nunca trate a interpretação como evidência autônoma.\n"
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
            "A) OBJETIVOS: separe obrigações expressas (DEVE, PRECISA, OBRIGATÓRIO) de oportunidades (PODE, SE HOUVER GANCHO, SE FIZER SENTIDO), sugestões e limites de estilo (EVITAR, SEM, NÃO REPETIR). Só obrigações imediatas bloqueiam a conclusão. Um assunto opcional pode ocorrer mais tarde no capítulo, sem cobrança neste turno. SILVIA e outras personagens secundárias participam quando o fluxo pedir; não exija uma fala nova delas a cada turno nem faça Mary interromper o usuário para provocar participação. Convites de Mary são iniciativas opcionais: não exija aceite nem realização da atividade para concluir a linha. Se o usuário recusar, ignorar ou mudar de assunto, não cobre repetição da proposta. Uma atividade aceita pode continuar por vários turnos sem precisar inventar nova proposta. Promessas se cumprem apenas conforme a obrigação expressa da linha, não por antecipação. Considere objetivos já satisfeitos por respostas literais do usuário; não invente objetivos. "
        )
        + ("Turno automático: pensamento pode cumprir finalidade introspectiva. " if automatic_row else "")
        + "B) CENA: a DESCRIÇÃO-GUIA determina ações e acontecimentos da linha ativa; a MEMÓRIA INSTANTÂNEA-LOCAL contextualiza e não cria tarefas. Diferencie ações obrigatórias de possibilidades. Comandos físicos explícitos de Mary precisam aparecer em [AÇÃO], sem exigir repetição de atos já realizados. Não obrigue personagens secundários a falar por rotina. Evidências vêm da saída atual ou da conversa, nunca da memória como prova de execução. "
        + "C) CONTINUIDADE: Mary deve responder ao sentido da entrada atual, preservando interlocutor, autoria de ações, sujeito, destinatário e posição física. Memória local define a cena atual; descrição inicial pode mencionar futuro sem torná-lo presente. Corrija interpretações semânticas incompatíveis com fatos explícitos. "
        + "C1) PARTICIPANTES E EVIDÊNCIA: identifique separadamente quem fala, para quem, quem é citado e quem pratica/recebe cada ação. O usuário pode trocar de personagem entre turnos. Se a resposta de Mary declarar uma ação física de terceiros, exija suporte na fala literal, na encenação ou nos fatos confirmados; uma hipótese do módulo de compreensão ou uma fala equivocada anterior de Mary NÃO comprovam a ação. Se Mary for questionada sobre uma interpretação anterior sem base, aceite esclarecimento ou correção, nunca novos detalhes inventados para defendê-la. Marque coerencia_conversacional.ok=false quando houver transferência de agente/alvo ou acontecimento concreto não sustentado. Não reprove brincadeiras claramente figuradas nem exija certeza impossível em falas genuinamente ambíguas. "
        + "D) FATOS E REVELAÇÃO: fontes autoritativas prevalecem sobre falas anteriores. Marque apenas contradições objetivas; não trate estilo como erro factual. NÃO PODE impede verbalização mesmo sob pergunta, mas Mary deve reagir sem revelar nem inventar. "
        + "E) NATURALIDADE: respeite ESTILO/ATITUDE e a direção autoral da linha, sem impor vocabulário literal, intensidade fixa ou metáforas genéricas. ACAO e FALA bastam; PENSAMENTO é opcional e nunca é requisito para aprovação. Observe gestos repetidos sem função (sorriso de canto, sustentar o olhar, ajeitar cabelos ou pernas), explicações de intenções alheias sem evidência e perguntas que transformam toda interação amistosa em teste ou avaliação. Reprove quando o artificialismo for evidente, mas NÃO exija sempre silêncio, respostas curtas ou eliminação de sensualidade, humor e iniciativa. Compare com a conversa disponível, não apenas com uma frase isolada. "
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
                        "A FALA-GUIA define direção, não uma lista de perguntas obrigatórias. Distinga exigências explícitas de opções, oportunidades contextuais e limites de estilo. Silvia só deve intervir quando acrescentar algo real; não reitere uma participação que já ocorreu durante a mesma linha. "
                    )
                    + "Não exija repetição literal da fala-guia. "
                    "Nunca invente evidência."
                ),
            },
            {"role": "user", "content": payload},
        ],
        temperature=0.0,
        max_tokens=2600,
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
        requirement = _clean(item.get("objetivo"))
        optional = _guide_objective_is_optional(requirement, speech_guide)
        normalized_objectives.append(
            {
                "requirement": requirement,
                "optional": optional,
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

    # Requisito de legibilidade: em turnos com multiplas falas, o nome do
    # personagem acompanha cada intervencao. Isso nao altera a autoria.
    dialogue_turns = [line.strip() for line in _clean(mary_text).splitlines()
                      if re.match(r"^\\s*[—–-]\\s+", line)]
    unlabeled_turns = [line for line in dialogue_turns
                       if not re.match(r"^[—–-]\\s*[A-ZÀ-Ý][a-zà-ÿ]+(?:\\s+[A-ZÀ-Ý][a-zà-ÿ]+){0,2}:", line)]
    speaker_format_invalid = len(dialogue_turns) >= 2 and bool(unlabeled_turns)
    if speaker_format_invalid:
        conversation_consistency["ok"] = False
        conversation_consistency["issue"] = "Diálogo de múltiplas personagens sem atribuição nominal em cada fala."
        conversation_consistency["correction"] = (
            "Identifique cada turno com Mary:, Silvia: ou o nome da personagem, "
            "conservando integralmente as falas e a ordem. Não crie nem exclua acontecimentos."
        )

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
    # O Diretor fornece uma hipótese semântica, não cria obrigações autorais.
    # Evidência literal é auditável, mas a citação inexata do Diretor não
    # pode prender indefinidamente uma linha interpretativa já realizada.
    evidence = _clean(scene_raw.get("evidencia"))
    source = _evidence_source(evidence, conversation_entries)
    evidence_grounded = bool(source)
    scene_claim = bool(scene_raw.get("cumprida", False))
    director_physical_claim = bool(scene_raw.get("acao_fisica_obrigatoria", False))
    physical_required = bool(explicit_physical_required)
    # Somente um comando FÍSICO explícito do autor exige ação concreta de Mary.
    # Fala, pensamento e encenação do interlocutor não substituem essa ação.
    physical_evidence = bool(_clean(mary_action)) and (
        _evidence_source(evidence, [("MARY_ACAO", _clean(mary_action))]) == "MARY_ACAO"
    )
    if physical_required and not physical_evidence:
        # A citação do Diretor pode ser imprecisa, porém a ação obrigatória
        # precisa estar comprovada; sem evidência adequada, a linha continua.
        scene_missing = "Movimento físico explicitamente obrigatório sem evidência em [AÇÃO]."
    elif not scene_claim:
        scene_missing = _clean(scene_raw.get("faltou")) or "A finalidade central da linha ainda não foi cumprida."
    else:
        scene_missing = ""
    scene_completion = {
        "fulfilled": (
            scene_claim and bool(_clean(mary_text) or _clean(mary_action))
            and (not physical_required or physical_evidence)
        ),
        "event": _clean(scene_raw.get("acontecimento")),
        "evidence": evidence if evidence_grounded else "",
        "evidence_grounded": evidence_grounded,
        "director_physical_claim": director_physical_claim,
        "physical_required_by_author": physical_required,
        "missing": scene_missing,
    }

    required_objectives = [item for item in normalized_objectives if not item["optional"]]
    all_objectives = (
        True
        if interpret_mode or not speech_guide
        else (
            all(bool(item.get("found")) for item in required_objectives)
            and (
                bool(required_objectives)
                or _guide_objective_is_optional(speech_guide, speech_guide)
            )
        )
    )
    # A resposta global "cumpriu" do Diretor é apenas diagnóstica:
    # oportunidades não utilizadas não podem reverter os critérios verificáveis.
    # Mantemos todas as checagens independentes de coerência e fatos.

    fulfilled = (
        not parse_error
        and not hard_contradiction["exists"]
        and not revelation_violation["exists"]
        and conversation_consistency["ok"]
        and naturalness["ok"]
        and normalized_obligation["satisfied"]
        and all_objectives
        and scene_completion["fulfilled"]
    )

    missing_parts = []
    if not scene_completion["fulfilled"]:
        missing_parts.append(scene_completion["missing"] or "acontecimento central da linha ainda nao ocorreu")
    if obligation_exists and not normalized_obligation["satisfied"]:
        missing_parts.append(obligation_text or "responder à fala atual do usuário")
    if speech_guide and not interpret_mode and not required_objectives and not _guide_objective_is_optional(speech_guide, speech_guide):
        missing_parts.append("Ato obrigatório da FALA-GUIA sem evidência validada")
    for item in normalized_objectives:
        if not item["optional"] and not item["found"] and item["requirement"]:
            missing_parts.append(item["requirement"])

    return {
        "fulfilled": fulfilled,
        "missing": "" if fulfilled else ("; ".join(missing_parts) or _clean(parsed.get("faltou"))),
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
