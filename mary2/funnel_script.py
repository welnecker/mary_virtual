from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import gspread

from openrouter_client import chat


FUNNEL_HEADERS = {
    "ordem": "order",
    "cena id": "scene_id",
    "objetivo da cena": "objective",
    "abertura permitida": "opening_allowed",
    "convergência": "convergence",
    "convergencia": "convergence",
    "não pode": "forbidden",
    "nao pode": "forbidden",
    "min turns": "min_turns",
    "ideal turns": "ideal_turns",
    "max turns": "max_turns",
    "condição de saída": "exit_condition",
    "condicao de saida": "exit_condition",
    "saída prevista": "next_scene",
    "saida prevista": "next_scene",
    "atmosfera / atitude": "atmosphere",
    "vestimenta": "wardrobe",
    "fatos fixos da cena": "fixed_facts",
    "memória a consolidar": "memory_policy",
    "memoria a consolidar": "memory_policy",
    "marcos de saída": "exit_markers",
    "marcos de saida": "exit_markers",
    "missão obrigatória": "mission",
    "missao obrigatoria": "mission",
    "entregas obrigatórias": "deliverables",
    "entregas obrigatorias": "deliverables",
    "critério de conclusão": "completion_criterion",
    "criterio de conclusao": "completion_criterion",
}


PHYSICAL_ONLY_MARKERS = {
    "carro_em_movimento",
    "mary_passageira_instalada",
    "aproximando_golden_tulip",
    "chegada_golden_tulip",
}

USER_INFORMATION_MARKERS = {
    "usuario_residencia",
    "usuario_desvio_camburi",
    "usuario_vida_domestica",
    "usuario_preferencia_noturna",
}

MARY_DELIVERY_MARKERS = {
    "mary_reage_suv",
    "mary_comenta_transito",
    "mary_nautico",
    "mary_passado_nautico",
    "mary_retomar_vida_social",
    "mary_plano_hoje",
    "possibilidade_encontro_hoje",
    "possibilidade_encontro_posterior",
    "mary_indica_golden_tulip",
    "mary_reconhecimento_companhia",
    "contato_tratado",
    "despedida_realizada",
}

SHARED_EVIDENCE_MARKERS = set()


MARKER_DESCRIPTIONS = {
    "carro_em_movimento": "O carro do personal está efetivamente em movimento rumo a Camburi.",
    "mary_passageira_instalada": "Mary está efetivamente instalada no banco do passageiro.",
    "usuario_residencia": "O usuário afirmou onde mora ou sua região de residência.",
    "usuario_desvio_camburi": "O usuário esclareceu se levar Mary a Camburi representa desvio relevante em relação ao seu caminho.",
    "usuario_vida_domestica": "O usuário afirmou se mora sozinho ou com alguém / como é sua coabitação.",
    "usuario_preferencia_noturna": "O usuário afirmou ao menos uma preferência real de lazer para sábado/noite.",
    "mary_reage_suv": "Mary reagiu ao SUV do personal de modo compatível com o primeiro contato com o veículo.",
    "mary_comenta_transito": "Mary comentou o trânsito ou fluxo da via já dentro do trajeto, sem controlar a condução.",
    "mary_nautico": "Mary mencionou explicitamente o Clube Náutico dentro da conversa.",
    "mary_passado_nautico": "Mary disse que frequentava o Clube Náutico quando solteira.",
    "mary_retomar_vida_social": "Mary revelou que sua vida social esfriou e que deseja retomar essa parte da vida.",
    "mary_plano_hoje": "Mary deixou explícito que pretende sair naquela noite, por volta das oito, depois de ir para casa e se arrumar.",
    "possibilidade_encontro_hoje": "Mary abriu ao personal a possibilidade de encontrá-la no Clube Náutico naquela mesma noite, sem presumir aceite ou logística.",
    "possibilidade_encontro_posterior": "Mary abriu a possibilidade de encontrá-lo mais tarde, sem presumir aceite ou logística.",
    "aproximando_golden_tulip": "O estado físico indica que o SUV está se aproximando do destino/Golden Tulip.",
    "mary_indica_golden_tulip": "Mary indicou explicitamente o Golden Tulip como referência de chegada e pediu para parar por perto, sem controlar a ação do motorista.",
    "chegada_golden_tulip": "A chegada ao Golden Tulip está efetivamente estabelecida pelo estado físico estruturado.",
    "mary_reconhecimento_companhia": "Mary reconheceu explicitamente que gostou da companhia/conversa.",
    "contato_tratado": "A troca de contato foi realmente tratada sem inventar número ou confirmação do usuário.",
    "despedida_realizada": "Mary realizou a despedida e não abriu novo assunto depois dela.",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any, default: int) -> int:
    try:
        return int(float(_clean(value)))
    except Exception:
        return int(default)


def _unique_text(items: Any, *, limit: int = 24) -> list[str]:
    if items is None:
        source: list[Any] = []
    elif isinstance(items, list):
        source = items
    elif isinstance(items, (tuple, set)):
        source = list(items)
    else:
        source = [items]

    result: list[str] = []
    seen: set[str] = set()
    for item in source:
        value = _clean(item)
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def _marker_list(value: Any) -> list[str]:
    return _unique_text(
        [
            part.strip()
            for part in _clean(value).replace(",", ";").split(";")
            if part.strip()
        ],
        limit=32,
    )


def required_markers(row: dict) -> list[str]:
    return _marker_list(row.get("exit_markers", ""))


def derive_physical_markers(scene: dict) -> list[str]:
    """Converte apenas physical_state estruturado em marcadores do funil."""
    if not isinstance(scene, dict):
        return []

    physical = scene.get("physical_state", {})
    if not isinstance(physical, dict):
        return []

    location_type = _clean(physical.get("location_type")).lower()
    vehicle_motion = _clean(physical.get("vehicle_motion")).lower()
    mary_position = _clean(physical.get("mary_position")).lower()
    arrival_state = _clean(physical.get("arrival_state")).lower()

    markers: list[str] = []

    if vehicle_motion == "moving":
        markers.append("carro_em_movimento")

    if mary_position == "passenger_seat":
        markers.append("mary_passageira_instalada")

    if arrival_state in {"approaching", "arrived"}:
        markers.append("aproximando_golden_tulip")

    if arrival_state == "arrived":
        markers.append("chegada_golden_tulip")

    return markers


def achieved_markers(
    state: dict,
    scene: dict | None = None,
) -> list[str]:
    saved = _unique_text(
        state.get("markers", []),
        limit=32,
    )
    physical = derive_physical_markers(
        scene or {}
    )
    return _unique_text(
        saved + physical,
        limit=32,
    )


def pending_markers(
    row: dict,
    state: dict,
    scene: dict | None = None,
) -> list[str]:
    achieved = set(
        achieved_markers(
            state,
            scene,
        )
    )
    return [
        marker
        for marker in required_markers(row)
        if marker not in achieved
    ]


def marker_summary(markers: list[str]) -> str:
    if not markers:
        return "- (nenhum)"
    return "\n".join(
        f"- {marker}: "
        f"{MARKER_DESCRIPTIONS.get(marker, marker)}"
        for marker in markers
    )


def load_funnel_rows(
    *,
    service_account_info: dict,
    spreadsheet_id: str,
    worksheet_name: str,
) -> list[dict]:
    if not service_account_info:
        raise ValueError("service_account_info ausente para roteiro em funil")
    if not _clean(spreadsheet_id):
        raise ValueError("spreadsheet_id ausente para roteiro em funil")

    client = gspread.service_account_from_dict(service_account_info)
    worksheet = client.open_by_key(_clean(spreadsheet_id)).worksheet(
        _clean(worksheet_name) or "ROTEIRO_FUNIL_CARONA"
    )
    values = worksheet.get_all_values()
    if not values:
        return []

    header_index = -1
    headers: list[str] = []
    for idx, row in enumerate(values):
        normalized = [_clean(cell).lower() for cell in row]
        if "ordem" in normalized and "cena id" in normalized and "objetivo da cena" in normalized:
            header_index = idx
            headers = normalized
            break
    if header_index < 0:
        raise ValueError("cabeçalho do roteiro em funil não encontrado")

    rows: list[dict] = []
    for source_row in values[header_index + 1 :]:
        if not any(_clean(cell) for cell in source_row):
            continue
        record: dict[str, Any] = {}
        for index, header in enumerate(headers):
            key = FUNNEL_HEADERS.get(header)
            if key:
                record[key] = _clean(source_row[index] if index < len(source_row) else "")
        if not _clean(record.get("scene_id")):
            continue
        record["order"] = _int(record.get("order"), len(rows) + 1)
        record["min_turns"] = max(1, _int(record.get("min_turns"), 1))
        record["ideal_turns"] = max(
            record["min_turns"],
            _int(record.get("ideal_turns"), record["min_turns"]),
        )
        record["max_turns"] = max(
            record["ideal_turns"],
            _int(record.get("max_turns"), record["ideal_turns"]),
        )
        rows.append(record)

    rows.sort(key=lambda item: int(item.get("order", 0) or 0))
    return rows


def ensure_funnel_state(narrative: dict, rows: list[dict]) -> dict:
    scene_ids = [
        _clean(row.get("scene_id"))
        for row in rows
        if _clean(row.get("scene_id"))
    ]
    state = narrative.get("funnel_script")
    if not isinstance(state, dict) or state.get("engine") != "carona_funnel_v4":
        state = {
            "engine": "carona_funnel_v4",
            "scene_index": 0,
            "scene_id": scene_ids[0] if scene_ids else "",
            "scene_turn": 0,
            "completed_scene_ids": [],
            "markers": [],
            "user_stance": {},
            "memory": {
                "user_facts": [],
                "mary_facts": [],
                "consumed_topics": [],
                "consolidated": [],
            },
            "last_evaluation": {},
            "last_advance_reason": "",
            "completed": False,
        }
        narrative["funnel_script"] = state

    # O motor novo substitui o estado híbrido somente na Carona.
    narrative.pop("hybrid_script", None)

    memory = state.get("memory")
    if not isinstance(memory, dict):
        memory = {}
        state["memory"] = memory
    for key in ("user_facts", "mary_facts", "consumed_topics", "consolidated"):
        if not isinstance(memory.get(key), list):
            memory[key] = []

    index = max(0, _int(state.get("scene_index"), 0))
    if rows:
        index = min(index, len(rows) - 1)
        expected_id = _clean(rows[index].get("scene_id"))
        if _clean(state.get("scene_id")) not in scene_ids:
            state["scene_id"] = expected_id
        elif _clean(state.get("scene_id")) != expected_id:
            found = next(
                (
                    i
                    for i, row in enumerate(rows)
                    if _clean(row.get("scene_id"))
                    == _clean(state.get("scene_id"))
                ),
                index,
            )
            index = found

    state["scene_index"] = index
    state["scene_turn"] = max(0, _int(state.get("scene_turn"), 0))
    state["completed_scene_ids"] = _unique_text(
        state.get("completed_scene_ids", []),
        limit=64,
    )
    state["markers"] = _unique_text(
        state.get("markers", []),
        limit=32,
    )
    if not isinstance(state.get("user_stance"), dict):
        state["user_stance"] = {}
    state["completed"] = bool(state.get("completed", False))
    return state


def current_funnel_row(rows: list[dict], state: dict) -> dict:
    if not rows or bool(state.get("completed", False)):
        return {}
    index = max(
        0,
        min(_int(state.get("scene_index"), 0), len(rows) - 1),
    )
    return dict(rows[index])


def funnel_stage(row: dict, state: dict) -> str:
    next_turn = int(state.get("scene_turn", 0) or 0) + 1
    min_turns = int(row.get("min_turns", 1) or 1)
    ideal_turns = int(
        row.get("ideal_turns", min_turns) or min_turns
    )
    max_turns = int(
        row.get("max_turns", ideal_turns) or ideal_turns
    )

    if next_turn <= min_turns:
        return "abertura"
    if next_turn < ideal_turns:
        return "desenvolvimento"
    if next_turn < max_turns:
        return "convergencia"
    return "fechamento"


def _fact_text(item: Any) -> str:
    if isinstance(item, dict):
        fact = _clean(item.get("fact"))
        modality = _clean(item.get("modality"))
        category = _clean(item.get("category"))
        parts = [part for part in (category, modality) if part]
        suffix = f" [{'/'.join(parts)}]" if parts else ""
        return fact + suffix if fact else ""
    return _clean(item)


def _memory_text(state: dict) -> str:
    memory = (
        state.get("memory", {})
        if isinstance(state, dict)
        else {}
    )

    user_facts = [
        _fact_text(item)
        for item in memory.get("user_facts", [])
        if _fact_text(item)
    ]
    consumed = _unique_text(
        memory.get("consumed_topics", []),
        limit=24,
    )
    consolidated = [
        _fact_text(item)
        for item in memory.get("consolidated", [])
        if _fact_text(item)
    ]

    sections = ["FATOS CONFIRMADOS DO USUÁRIO NESTA CENA"]
    sections.extend(f"- {item}" for item in user_facts)
    if not user_facts:
        sections.append("- (nenhum)")

    sections.append("ASSUNTOS JÁ CONSUMIDOS")
    sections.extend(f"- {item}" for item in consumed)
    if not consumed:
        sections.append("- (nenhum)")

    sections.append("MEMÓRIA CONSOLIDADA DE CENAS ANTERIORES")
    sections.extend(f"- {item}" for item in consolidated)
    if not consolidated:
        sections.append("- (nenhum)")

    return "\n".join(sections)


def build_funnel_prompt(
    *,
    facts_prompt: str,
    row: dict,
    state: dict,
    scene: dict | None = None,
) -> str:
    stage = funnel_stage(row, state)
    next_turn = int(state.get("scene_turn", 0) or 0) + 1
    min_turns = int(row.get("min_turns", 1) or 1)
    ideal_turns = int(row.get("ideal_turns", min_turns) or min_turns)
    max_turns = int(row.get("max_turns", ideal_turns) or ideal_turns)

    pending = pending_markers(row, state, scene or {})
    achieved = achieved_markers(state, scene or {})
    conversational_pending = [
        marker
        for marker in pending
        if marker not in PHYSICAL_ONLY_MARKERS
    ]
    next_priority = (
        conversational_pending[0]
        if conversational_pending
        else ""
    )

    if stage == "abertura":
        stage_rule = (
            "Responda ao usuário naturalmente, mas não desperdice o turno. "
            "Quando houver espaço conversacional, avance a PRIMEIRA ENTREGA PENDENTE."
        )
    elif stage == "desenvolvimento":
        stage_rule = (
            "A missão já deve estar avançando. Responda ao usuário e conduza "
            "ativamente a conversa para uma ENTREGA PENDENTE."
        )
    else:
        stage_rule = (
            "Prioridade máxima às ENTREGAS PENDENTES. Responda ao usuário sem abrir "
            "ramificações e faça a fala avançar diretamente uma pendência real."
        )

    mission = (
        _clean(row.get("mission"))
        or _clean(row.get("objective"))
        or "(missão não informada)"
    )
    deliverables = (
        _clean(row.get("deliverables"))
        or marker_summary(required_markers(row))
    )
    completion = (
        _clean(row.get("completion_criterion"))
        or _clean(row.get("exit_condition"))
        or "(critério não informado)"
    )

    return "\n".join(
        [
            "════════════════════════════════════════════════════════════",
            "MISSÃO OBRIGATÓRIA DO FUNIL — AUTORIDADE MÁXIMA",
            "════════════════════════════════════════════════════════════",
            mission,
            "",
            "ENTREGAS OBRIGATÓRIAS",
            deliverables,
            "",
            "REGRA ABSOLUTA",
            "A fala do usuário define COMO Mary responde; a MISSÃO define PARA ONDE a conversa deve andar.",
            "Assuntos incidentais podem alterar tom, humor e forma, mas NÃO podem substituir a missão.",
            "Mary pode reagir a um assunto lateral, porém deve aproveitar a primeira oportunidade natural para avançar UMA entrega pendente.",
            "Mary NÃO pode encerrar, trocar de assunto por iniciativa própria ou permanecer em conversa lateral enquanto houver entrega conversacional pendente.",
            "Pendências físicas pertencem ao Diretor/runtime e NÃO devem ser forçadas pela fala de Mary.",
            "",
            "CRITÉRIO DE CONCLUSÃO E TROCA DE FUNIL",
            completion,
            "Quando todas as entregas forem comprovadas nesta resposta, a missão está concluída.",
            "Nesse caso, NÃO abra outro assunto desta cena: conclua apenas a resposta atual.",
            f"O próximo turno será controlado por: {_clean(row.get('next_scene')) or '(fim)'}.",
            "Min/ideal/max são apenas referências de ritmo; missão cumprida encerra o funil imediatamente.",
            "",
            "ESTADO OPERACIONAL DA MISSÃO",
            f"CENA_ID={_clean(row.get('scene_id'))}",
            f"TURNO_DA_CENA={next_turn}",
            f"RITMO_REFERÊNCIA=min:{min_turns} ideal:{ideal_turns} max:{max_turns}",
            f"ESTÁGIO={stage}",
            "",
            "ENTREGAS JÁ COMPROVADAS",
            marker_summary(achieved),
            "",
            "ENTREGAS AINDA PENDENTES",
            marker_summary(pending),
            "",
            "PRÓXIMA PRIORIDADE",
            (
                f"{next_priority}: {MARKER_DESCRIPTIONS.get(next_priority, next_priority)}"
                if next_priority
                else (
                    "AGUARDAR ESTADO FÍSICO DO DIRETOR/RUNTIME — "
                    "não tente verbalizar uma pendência física."
                    if pending
                    else "MISSÃO CUMPRIDA — não abrir novo assunto."
                )
            ),
            "",
            "════════════════════════════════════════════════════════════",
            "CONTRATO SECUNDÁRIO — COMO CUMPRIR A MISSÃO",
            "════════════════════════════════════════════════════════════",
            "ABERTURA PERMITIDA",
            _clean(row.get("opening_allowed")) or "(nenhuma)",
            "",
            "CONVERGÊNCIA",
            _clean(row.get("convergence")) or "(nenhuma)",
            "",
            "PAREDES — NÃO PODE",
            _clean(row.get("forbidden")) or "(nenhuma)",
            "",
            "ATMOSFERA / ATITUDE",
            _clean(row.get("atmosphere")) or "(livre)",
            "",
            "VESTIMENTA",
            _clean(row.get("wardrobe")) or "(usar continuidade atual)",
            "",
            "FATOS FIXOS DA CENA",
            _clean(row.get("fixed_facts")) or "(nenhum adicional)",
            "",
            "POLÍTICA DE MEMÓRIA",
            _clean(row.get("memory_policy"))
            or "(consolidar apenas fatos consequentes)",
            "",
            _memory_text(state),
            "",
            "DINÂMICA DESTE TURNO",
            stage_rule,
            "Não repita pergunta ou entrega já cumprida.",
            "Não transforme assunto incidental em novo objetivo.",
            "Preserve modalidade: talvez não é sim; hipótese não é fato; brincadeira não é confirmação.",
            "A resposta pode ser curta. Profundidade vem da pertinência, não do comprimento.",
            "",
            "CONTEXTO FIXO DO CAPÍTULO — SUBORDINADO À MISSÃO ACIMA",
            _clean(facts_prompt),
        ]
    ).strip()


_EVALUATOR_PROMPT = """
Você é o FISCAL DE FRONTEIRAS E EXTRATOR DE EVIDÊNCIAS de uma cena narrativa em funil.
Você NÃO decide se a cena terminou. O runtime decide isso por marcadores obrigatórios.
Avalie somente o turno atual e retorne SOMENTE JSON válido.

Formato:
{
  "boundary_ok": true,
  "violations": [],
  "semantic_markers": [],
  "mission_progress_ok": true,
  "mission_progress_target": "",
  "user_facts": [],
  "consumed_topics": [],
  "user_stance": {},
  "summary": ""
}

REGRAS DE FRONTEIRA:
- boundary_ok=false se Mary abrir assunto fora de ABERTURA PERMITIDA/CONVERGÊNCIA, violar NÃO PODE, inventar fato/decisão/ação do usuário ou antecipar território de cena futura.
- Em convergência/fechamento, abrir um assunto novo que não ajuda uma pendência é violação.
- Não aprove uma resposta só porque ela soa natural; confira o território autorizado.
- Se houver pending_markers, a resposta de Mary deve avançar a missão: ou cumprir uma entrega de Mary, ou perguntar/conduzir claramente para obter a próxima entrega do usuário.
- Responder apenas ao assunto incidental sem avançar ou buscar next_priority significa mission_progress_ok=false.
- Quando mission_progress_ok=false, boundary_ok também deve ser false e violations deve incluir "missão obrigatória ignorada".

MARCADORES:
- semantic_markers pode conter SOMENTE IDs listados em allowed_semantic_markers.
- Marque um ID somente quando houver evidência explícita no texto atual de Mary ou do usuário.
- Não marque evento físico que pertence a physical_markers; esses vêm do runtime.

FATOS DO USUÁRIO:
- user_facts contém SOMENTE afirmações factuais do usuário, nunca perguntas, convites, comandos, brincadeiras ou falas sociais.
- Cada item deve ser objeto com: category, fact, modality, source_quote.
- source_quote deve ser trecho literal da fala atual do usuário que sustenta o fato.
- modality deve preservar confirmado, talvez/incerto, negado, hipotético ou brincadeira.
- Se não houver fato real, retorne [].

POSIÇÃO DO USUÁRIO:
- user_stance só deve existir quando a fala atual expressar posição relevante sobre uma proposta/possibilidade da cena.
- Formato: {"value":"aceitou|recusou|talvez/incerto|não respondeu", "source_quote":"trecho literal"}.
- Caso contrário, retorne {}.

MEMÓRIA:
- consumed_topics serve apenas para impedir repetição.
- Não transforme algo inventado por Mary em fato estrutural.
- summary descreve em uma frase o avanço real do turno.
""".strip()


def _extract_json(raw: str) -> dict:
    text = _clean(raw)
    fence = chr(96) * 3
    text = text.replace(fence + "json", "").replace(fence, "").strip()

    try:
        data = json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < start:
            raise
        data = json.loads(text[start : end + 1])

    if not isinstance(data, dict):
        raise ValueError(
            "validador do funil não retornou objeto JSON"
        )
    return data


def _looks_like_question_quote(value: str) -> bool:
    text = _clean(value).casefold().lstrip(" -…")
    if "?" in text:
        return True
    starters = (
        "qual ",
        "qual é",
        "quais ",
        "quem ",
        "onde ",
        "aonde ",
        "como ",
        "quando ",
        "por que ",
        "porque ",
        "o que ",
        "que horas ",
    )
    return any(text.startswith(prefix) for prefix in starters)


def _normalize_user_facts(items: Any, user_text: str) -> list[dict]:
    source_text = _clean(user_text)
    source_fold = source_text.casefold()
    result: list[dict] = []

    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        fact = _clean(item.get("fact"))
        category = _clean(item.get("category"))
        modality = _clean(item.get("modality"))
        quote = _clean(item.get("source_quote"))

        if not fact or not quote:
            continue
        if quote.casefold() not in source_fold:
            continue
        if _looks_like_question_quote(quote):
            continue

        result.append(
            {
                "category": category or "outro",
                "fact": fact,
                "modality": modality or "confirmado",
                "source_quote": quote,
            }
        )

    return result[:12]


def _normalize_user_stance(value: Any, user_text: str) -> dict:
    if not isinstance(value, dict):
        return {}
    stance = _clean(value.get("value"))
    quote = _clean(value.get("source_quote"))
    if not stance or not quote:
        return {}
    if quote.casefold() not in _clean(user_text).casefold():
        return {}
    return {
        "value": stance,
        "source_quote": quote,
    }


def evaluate_funnel_turn(
    *,
    api_key: str,
    model: str,
    fallback_model: str | None,
    row: dict,
    state: dict,
    scene: dict,
    user_text: str,
    mary_text: str,
) -> dict:
    required = required_markers(row)
    pending_now = pending_markers(row, state, scene)
    physical = set(derive_physical_markers(scene))
    semantic_allowed = [
        marker
        for marker in required
        if marker not in PHYSICAL_ONLY_MARKERS
    ]

    payload = {
        "scene_id": _clean(row.get("scene_id")),
        "scene_turn": int(state.get("scene_turn", 0) or 0) + 1,
        "stage": funnel_stage(row, state),
        "mission": _clean(row.get("mission")) or _clean(row.get("objective")),
        "deliverables": _clean(row.get("deliverables")),
        "completion_criterion": _clean(row.get("completion_criterion")),
        "objective": _clean(row.get("objective")),
        "opening_allowed": _clean(row.get("opening_allowed")),
        "convergence": _clean(row.get("convergence")),
        "forbidden": _clean(row.get("forbidden")),
        "fixed_facts": _clean(row.get("fixed_facts")),
        "memory_policy": _clean(row.get("memory_policy")),
        "allowed_semantic_markers": {
            marker: MARKER_DESCRIPTIONS.get(marker, marker)
            for marker in semantic_allowed
        },
        "physical_markers": sorted(physical),
        "already_achieved_markers": achieved_markers(state, scene),
        "pending_markers": pending_now,
        "next_priority": (
            pending_now[0]
            if pending_now
            else ""
        ),
        "next_priority_description": (
            MARKER_DESCRIPTIONS.get(
                pending_now[0],
                pending_now[0],
            )
            if pending_now
            else ""
        ),
        "user_text": _clean(user_text),
        "mary_text": _clean(mary_text),
    }

    raw = chat(
        api_key=api_key,
        model=model,
        fallback_model=fallback_model,
        messages=[
            {"role": "system", "content": _EVALUATOR_PROMPT},
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False),
            },
        ],
        temperature=0.0,
        max_tokens=700,
    )
    data = _extract_json(raw)

    semantic_markers = [
        marker
        for marker in _unique_text(data.get("semantic_markers", []), limit=16)
        if marker in semantic_allowed
    ]

    mission_progress_ok = bool(
        data.get(
            "mission_progress_ok",
            True,
        )
    )
    boundary_ok = bool(data.get("boundary_ok", True))
    violations = _unique_text(
        data.get("violations", []),
        limit=12,
    )
    mission_progress_target = _clean(
        data.get("mission_progress_target")
    )
    if (
        not mission_progress_ok
        and mission_progress_target not in PHYSICAL_ONLY_MARKERS
    ):
        boundary_ok = False
        violations = _unique_text(
            violations + ["missão obrigatória ignorada"],
            limit=12,
        )

    return {
        "boundary_ok": boundary_ok,
        "violations": violations,
        "semantic_markers": semantic_markers,
        "mission_progress_ok": mission_progress_ok,
        "mission_progress_target": mission_progress_target,
        "physical_markers": sorted(physical),
        "user_facts": _normalize_user_facts(
            data.get("user_facts", []),
            user_text,
        ),
        "consumed_topics": _unique_text(
            data.get("consumed_topics", []),
            limit=12,
        ),
        "user_stance": _normalize_user_stance(
            data.get("user_stance", {}),
            user_text,
        ),
        "summary": _clean(data.get("summary")),
        "raw": raw,
    }


def correction_prompt(
    row: dict,
    evaluation: dict,
    *,
    state: dict | None = None,
    scene: dict | None = None,
) -> str:
    violations = "; ".join(
        _unique_text(
            evaluation.get("violations", []),
            limit=12,
        )
    ) or "saída fora das paredes da cena"

    pending = [
        marker
        for marker in pending_markers(
            row,
            state or {},
            scene or {},
        )
        if marker not in PHYSICAL_ONLY_MARKERS
    ]
    mission = _clean(row.get("mission")) or _clean(row.get("objective"))
    return (
        "CORREÇÃO DE MISSÃO DO FUNIL. "
        "Reescreva somente a resposta de Mary. "
        "Elimine estas violações: "
        + violations
        + ". MISSÃO OBRIGATÓRIA: "
        + mission
        + ". ENTREGAS DO FUNIL: "
        + marker_summary(pending).replace("\n", " | ")
        + ". Reaja à fala atual do usuário, mas faça esta resposta avançar "
        "a próxima entrega ainda pendente em vez de permanecer no assunto incidental. "
        "Não invente ação, decisão, aceite, logística ou fato do usuário. "
        "Use exatamente [FALA] e depois [PENSAMENTO]."
    )


def _merge_fact_dicts(existing: Any, new_items: Any, *, limit: int = 24) -> list[dict]:
    result: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    for item in list(existing or []) + list(new_items or []):
        if not isinstance(item, dict):
            continue
        fact = _clean(item.get("fact"))
        if not fact:
            continue
        normalized = {
            "category": _clean(item.get("category")) or "outro",
            "fact": fact,
            "modality": _clean(item.get("modality")) or "confirmado",
            "source_quote": _clean(item.get("source_quote")),
        }
        key = (
            normalized["category"].casefold(),
            normalized["fact"].casefold(),
            normalized["modality"].casefold(),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
        if len(result) >= limit:
            break

    return result


def apply_funnel_evaluation(
    *,
    rows: list[dict],
    state: dict,
    row: dict,
    evaluation: dict,
    scene: dict,
) -> dict:
    before = deepcopy(state)
    memory = state.setdefault("memory", {})

    memory["user_facts"] = _merge_fact_dicts(
        memory.get("user_facts", []),
        evaluation.get("user_facts", []),
        limit=24,
    )
    memory["consumed_topics"] = _unique_text(
        list(memory.get("consumed_topics", []))
        + list(evaluation.get("consumed_topics", [])),
        limit=24,
    )

    semantic = _unique_text(
        evaluation.get("semantic_markers", []),
        limit=16,
    )
    physical = derive_physical_markers(scene)
    saved_semantic = [
        marker
        for marker in _unique_text(state.get("markers", []), limit=32)
        if marker not in PHYSICAL_ONLY_MARKERS
    ]
    state["markers"] = _unique_text(
        saved_semantic + semantic,
        limit=32,
    )

    current_stance = evaluation.get("user_stance", {})
    if (
        isinstance(current_stance, dict)
        and _clean(current_stance.get("value"))
    ):
        state["user_stance"] = deepcopy(current_stance)

    state["scene_turn"] = int(state.get("scene_turn", 0) or 0) + 1
    state["last_evaluation"] = deepcopy(evaluation)
    state["last_advance_reason"] = ""

    required = required_markers(row)
    achieved = achieved_markers(state, scene)
    missing = [
        marker
        for marker in required
        if marker not in set(achieved)
    ]

    can_advance = (
        bool(evaluation.get("boundary_ok", True))
        and not missing
    )

    advanced_to = ""
    completed_markers = list(achieved)

    if can_advance:
        current_id = _clean(row.get("scene_id"))
        state["completed_scene_ids"] = _unique_text(
            list(state.get("completed_scene_ids", []))
            + [current_id],
            limit=64,
        )

        consolidated = _merge_fact_dicts(
            memory.get("consolidated", []),
            memory.get("user_facts", []),
            limit=40,
        )

        stance = state.get("user_stance", {})
        if isinstance(stance, dict) and _clean(stance.get("value")):
            consolidated = _merge_fact_dicts(
                consolidated,
                [
                    {
                        "category": "posição_na_cena",
                        "fact": (
                            f"Na cena {current_id}, posição do usuário: "
                            f"{_clean(stance.get('value'))}."
                        ),
                        "modality": _clean(stance.get("value")),
                        "source_quote": _clean(stance.get("source_quote")),
                    }
                ],
                limit=40,
            )

        memory["consolidated"] = consolidated

        next_index = int(state.get("scene_index", 0) or 0) + 1
        if next_index >= len(rows):
            state["completed"] = True
            state["scene_id"] = ""
            state["last_advance_reason"] = (
                "missão cumprida; todas as entregas obrigatórias foram comprovadas; funil concluído"
            )
            advanced_to = "FIM"
        else:
            state["scene_index"] = next_index
            state["scene_id"] = _clean(rows[next_index].get("scene_id"))
            state["scene_turn"] = 0
            state["markers"] = []
            state["user_stance"] = {}
            state["last_advance_reason"] = (
                "missão cumprida; todas as entregas obrigatórias foram comprovadas"
            )
            advanced_to = state["scene_id"]

            memory["user_facts"] = []
            memory["mary_facts"] = []
            memory["consumed_topics"] = []

    return {
        "state_before": before,
        "state_after": deepcopy(state),
        "advanced": can_advance,
        "advanced_to": advanced_to,
        "stage": funnel_stage(row, before),
        "required_markers": required,
        "achieved_markers": completed_markers,
        "pending_markers": missing,
        "exit_ready": not missing,
        "physical_state": deepcopy(
            scene.get("physical_state", {})
            if isinstance(scene, dict)
            else {}
        ),
    }


def funnel_ready_for_choice(
    state: dict,
) -> bool:
    return bool(
        state.get("completed", False)
    )


def compact_context_messages(
    messages: list[dict[str, str]],
    *,
    limit: int = 8,
) -> list[dict[str, str]]:
    cleaned = [
        {
            "role": str(
                item.get("role", "")
            ),
            "content": _clean(
                item.get("content")
            ),
        }
        for item in messages
        if _clean(
            item.get("content")
        )
    ]
    return cleaned[
        -max(2, int(limit or 8)) :
    ]
