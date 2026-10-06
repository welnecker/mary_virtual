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
}


MARKER_DESCRIPTIONS = {
    "carro_em_movimento": "O carro do personal está efetivamente em movimento rumo a Camburi.",
    "usuario_residencia_ou_vida_domestica": "O usuário afirmou ao menos um fato confiável sobre onde mora ou com quem vive.",
    "usuario_preferencia_noturna": "O usuário afirmou ao menos uma preferência real de lazer para sábado/noite.",
    "mary_nautico": "Mary mencionou explicitamente o Clube Náutico dentro da conversa.",
    "mary_passado_nautico": "Mary disse que frequentava o Clube Náutico quando solteira.",
    "mary_retomar_vida_social": "Mary revelou que sua vida social esfriou e que deseja retomar essa parte da vida.",
    "possibilidade_encontro_posterior": "Mary abriu a possibilidade de encontrá-lo mais tarde, sem presumir aceite ou logística.",
    "chegada_golden_tulip": "O veículo efetivamente chegou e parou/encostou próximo ao Golden Tulip.",
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


def _normalized_scene_text(scene: dict) -> str:
    if not isinstance(scene, dict):
        return ""
    values = [
        scene.get("location", ""),
        scene.get("event", ""),
        scene.get("proximity", ""),
        scene.get("scene_caption", ""),
        scene.get("resolution_summary", ""),
    ]
    return " ".join(
        _clean(value).casefold()
        for value in values
        if _clean(value)
    )


def derive_physical_markers(scene: dict) -> list[str]:
    text = _normalized_scene_text(scene)
    markers: list[str] = []

    moving_terms = (
        "em movimento",
        "segue pela estrada",
        "segue pela",
        "carro segue",
        "suv segue",
        "trafegando",
        "rodando",
    )
    if any(term in text for term in moving_terms):
        markers.append("carro_em_movimento")

    arrived_golden = "golden tulip" in text
    stopped_terms = (
        "parou",
        "parado",
        "encostou",
        "encostado",
        "estacion",
    )
    if arrived_golden and any(term in text for term in stopped_terms):
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
    if not isinstance(state, dict) or state.get("engine") != "carona_funnel_v2":
        state = {
            "engine": "carona_funnel_v2",
            "scene_index": 0,
            "scene_id": scene_ids[0] if scene_ids else "",
            "scene_turn": 0,
            "completed_scene_ids": [],
            "markers": [],
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
    ideal_turns = int(
        row.get("ideal_turns", min_turns) or min_turns
    )
    max_turns = int(
        row.get("max_turns", ideal_turns) or ideal_turns
    )

    stage_rule = {
        "abertura": (
            "Há liberdade para reagir e explorar a ABERTURA PERMITIDA. "
            "Não force a conclusão antes que a conversa tenha respirado."
        ),
        "desenvolvimento": (
            "Reaja livremente, mas comece a favorecer a CONVERGÊNCIA. "
            "Evite abrir temas que não ajudam esta cena."
        ),
        "convergencia": (
            "A conversa já deve estreitar. Priorize CONVERGÊNCIA e pendências; "
            "não reabra assuntos consumidos nem crie novos ramos."
        ),
        "fechamento": (
            "O limite narrativo foi alcançado. Responda ao usuário e trabalhe "
            "somente para satisfazer a CONDIÇÃO DE SAÍDA, sem controlar decisões "
            "ou ações dele. Não abra nenhum assunto novo."
        ),
    }[stage]

    return "\n".join(
        [
            _clean(facts_prompt),
            "",
            "CONTRATO DA CENA EM FUNIL — PRIORIDADE NARRATIVA",
            "O roteiro controla o território; Mary escolhe como caminhar dentro dele.",
            "Não existe fala-guia obrigatória, microprompt por linha ou respiro.",
            "Mary deve reagir de verdade à fala atual do usuário, com personalidade e iniciativa local.",
            "Liberdade de expressão NÃO autoriza criar fatos, planos, decisões ou direções fora deste contrato.",
            "",
            f"CENA_ID={_clean(row.get('scene_id'))}",
            f"ORDEM_DA_CENA={int(row.get('order', 0) or 0)}",
            f"TURNO_DA_CENA={next_turn}",
            f"FAIXA=min:{min_turns} ideal:{ideal_turns} max:{max_turns}",
            f"POSIÇÃO_NO_FUNIL={stage}",
            "",
            "OBJETIVO DA CENA",
            _clean(row.get("objective")) or "(não informado)",
            "",
            "ABERTURA PERMITIDA",
            _clean(row.get("opening_allowed")) or "(nenhuma)",
            "",
            "CONVERGÊNCIA",
            _clean(row.get("convergence")) or "(nenhuma)",
            "",
            "PAREDES — NÃO PODE",
            _clean(row.get("forbidden")) or "(nenhuma)",
            "",
            "CONDIÇÃO DE SAÍDA",
            _clean(row.get("exit_condition")) or "(não informada)",
            "",
            "SAÍDA PREVISTA",
            _clean(row.get("next_scene")) or "(não informada)",
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
            "MARCADORES OBRIGATÓRIOS PARA SAÍDA",
            marker_summary(required_markers(row)),
            "",
            "MARCADORES JÁ COMPROVADOS",
            marker_summary(achieved_markers(state, scene or {})),
            "",
            "PENDÊNCIAS REAIS DA CENA",
            marker_summary(pending_markers(row, state, scene or {})),
            "",
            _memory_text(state),
            "",
            "DINÂMICA DESTE TURNO",
            stage_rule,
            "Use fatos lembrados para evitar repetição e contradição, nunca como inspiração automática de assunto.",
            "Preserve modalidade: talvez não é sim; hipótese não é fato; brincadeira não é confirmação.",
            "Não repita perguntas já respondidas apenas para preencher turno.",
            "A resposta pode ser curta. Profundidade vem da pertinência, não do comprimento.",
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
  "user_facts": [],
  "consumed_topics": [],
  "user_stance": {},
  "summary": ""
}

REGRAS DE FRONTEIRA:
- boundary_ok=false se Mary abrir assunto fora de ABERTURA PERMITIDA/CONVERGÊNCIA, violar NÃO PODE, inventar fato/decisão/ação do usuário ou antecipar território de cena futura.
- Em convergência/fechamento, abrir um assunto novo que não ajuda uma pendência é violação.
- Não aprove uma resposta só porque ela soa natural; confira o território autorizado.

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
    physical = set(derive_physical_markers(scene))
    semantic_allowed = [
        marker
        for marker in required
        if marker not in {"carro_em_movimento", "chegada_golden_tulip"}
    ]

    payload = {
        "scene_id": _clean(row.get("scene_id")),
        "scene_turn": int(state.get("scene_turn", 0) or 0) + 1,
        "stage": funnel_stage(row, state),
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
        "pending_markers": pending_markers(row, state, scene),
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

    return {
        "boundary_ok": bool(data.get("boundary_ok", True)),
        "violations": _unique_text(data.get("violations", []), limit=12),
        "semantic_markers": semantic_markers,
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
) -> str:
    violations = "; ".join(
        _unique_text(
            evaluation.get("violations", []),
            limit=12,
        )
    ) or "saída fora das paredes da cena"

    return (
        "CORREÇÃO DE FRONTEIRA DO FUNIL. "
        "Reescreva somente a resposta de Mary. "
        "Mantenha a reação humana à fala atual, mas elimine estas violações: "
        + violations
        + ". Permaneça dentro de ABERTURA/CONVERGÊNCIA e PAREDES da cena "
        + _clean(row.get("scene_id"))
        + ". Não invente ação, decisão, aceite, logística ou fato do usuário. "
        "Use exatamente [FALA] e depois [PENSAMENTO]."
    )


def apply_funnel_evaluation(
    *,
    rows: list[dict],
    state: dict,
    row: dict,
    evaluation: dict,
) -> dict:
    before = deepcopy(state)
    memory = state.setdefault("memory", {})

    memory["user_facts"] = _unique_text(
        list(memory.get("user_facts", []))
        + list(evaluation.get("user_facts", [])),
        limit=24,
    )
    memory["mary_facts"] = _unique_text(
        list(memory.get("mary_facts", []))
        + list(evaluation.get("mary_facts", [])),
        limit=24,
    )
    memory["consumed_topics"] = _unique_text(
        list(memory.get("consumed_topics", []))
        + list(evaluation.get("consumed_topics", [])),
        limit=24,
    )

    state["scene_turn"] = (
        int(state.get("scene_turn", 0) or 0) + 1
    )
    state["last_evaluation"] = deepcopy(evaluation)
    state["last_advance_reason"] = ""

    min_turns = int(
        row.get("min_turns", 1) or 1
    )
    can_advance = (
        bool(evaluation.get("boundary_ok", True))
        and bool(
            evaluation.get(
                "exit_condition_met",
                False,
            )
        )
        and int(state["scene_turn"]) >= min_turns
    )

    advanced_to = ""

    if can_advance:
        current_id = _clean(
            row.get("scene_id")
        )
        state["completed_scene_ids"] = _unique_text(
            list(
                state.get(
                    "completed_scene_ids",
                    [],
                )
            )
            + [current_id],
            limit=64,
        )

        candidates = list(
            evaluation.get(
                "consolidated_memory_candidates",
                [],
            )
        )
        if evaluation.get("user_stance"):
            candidates.append(
                f"Na cena {current_id}, posição do usuário: "
                f"{_clean(evaluation.get('user_stance'))}."
            )

        memory["consolidated"] = _unique_text(
            list(memory.get("consolidated", []))
            + candidates,
            limit=40,
        )

        next_index = (
            int(state.get("scene_index", 0) or 0)
            + 1
        )

        if next_index >= len(rows):
            state["completed"] = True
            state["scene_id"] = ""
            state["last_advance_reason"] = (
                "condição de saída satisfeita; "
                "funil concluído"
            )
            advanced_to = "FIM"
        else:
            state["scene_index"] = next_index
            state["scene_id"] = _clean(
                rows[next_index].get("scene_id")
            )
            state["scene_turn"] = 0
            state["last_advance_reason"] = (
                "condição de saída satisfeita"
            )
            advanced_to = state["scene_id"]

            # A memória curta pertence à cena.
            # Só o consolidado atravessa o funil.
            memory["user_facts"] = []
            memory["mary_facts"] = []
            memory["consumed_topics"] = []

    return {
        "state_before": before,
        "state_after": deepcopy(state),
        "advanced": can_advance,
        "advanced_to": advanced_to,
        "stage": funnel_stage(
            row,
            before,
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
