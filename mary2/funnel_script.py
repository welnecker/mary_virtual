from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import gspread

from openrouter_client import chat


REDATOR_HEADERS = {
    "ordem": "order",
    "roteiro": "script_name",
    "tipo": "line_type",
    "fala-guia": "guide",
    "fala guia": "guide",
    "estilo / atitude": "style",
    "atmosfera": "atmosphere",
    "fato liberado nesta linha": "released_fact",
    "pré-condição": "precondition",
    "pre-condição": "precondition",
    "pre-condicao": "precondition",
    "vestimenta atual": "wardrobe",
    "ação física / encenação": "physical_action",
    "acao fisica / encenacao": "physical_action",
    "limites do redator": "forbidden",
    "missão da linha": "mission",
    "missao da linha": "mission",
    "condição de conclusão": "completion_criterion",
    "condicao de conclusao": "completion_criterion",
    "tipo de conclusão": "completion_type",
    "tipo de conclusao": "completion_type",
}

GENERIC_COMPLETION_TYPES = {"USER", "MARY", "PHYSICAL", "MIXED"}


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


def required_markers(row: dict) -> list[str]:
    """Adaptador legado: um passo genérico exige apenas sua conclusão."""
    return ["step_complete"] if _clean(row.get("completion_criterion")) else []


def achieved_markers(
    state: dict,
    scene: dict | None = None,
) -> list[str]:
    return ["step_complete"] if bool(state.get("step_complete", False)) else []


def pending_markers(
    row: dict,
    state: dict,
    scene: dict | None = None,
) -> list[str]:
    if not required_markers(row):
        return []
    return [] if bool(state.get("step_complete", False)) else ["step_complete"]


def marker_summary(markers: list[str]) -> str:
    if not markers:
        return "- (nenhum)"
    labels = {
        "step_complete": "condição de conclusão do passo ainda não comprovada",
    }
    return "\n".join(f"- {labels.get(marker, marker)}" for marker in markers)


def derive_physical_markers(scene: dict) -> list[str]:
    """Mantido apenas para auditoria compatível; não decide progressão."""
    physical = scene.get("physical_state", {}) if isinstance(scene, dict) else {}
    if not isinstance(physical, dict):
        return []
    result: list[str] = []
    for key in ("location_type", "vehicle_motion", "mary_position", "arrival_state"):
        value = _clean(physical.get(key))
        if value and value.lower() != "unknown":
            result.append(f"physical:{key}={value}")
    return result


def load_funnel_rows(
    *,
    service_account_info: dict,
    spreadsheet_id: str,
    worksheet_name: str,
) -> list[dict]:
    """Carrega passos autorais diretamente de ROTEIRO_REDATOR."""
    if not service_account_info:
        raise ValueError("service_account_info ausente para roteiro")
    if not _clean(spreadsheet_id):
        raise ValueError("spreadsheet_id ausente para roteiro")

    client = gspread.service_account_from_dict(service_account_info)
    worksheet = client.open_by_key(_clean(spreadsheet_id)).worksheet(
        _clean(worksheet_name) or "ROTEIRO_REDATOR"
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
        raise ValueError("cabeçalho do ROTEIRO_REDATOR não encontrado")

    rows: list[dict] = []
    for source_row in values[header_index + 1 :]:
        if not any(_clean(cell) for cell in source_row):
            continue
        record: dict[str, Any] = {}
        for index, header in enumerate(headers):
            key = REDATOR_HEADERS.get(header)
            if key:
                record[key] = _clean(source_row[index] if index < len(source_row) else "")

        order = _int(record.get("order"), len(rows) + 1)
        if not _clean(record.get("guide")) and not _clean(record.get("mission")):
            continue

        completion_type = _clean(record.get("completion_type")).upper() or "MIXED"
        if completion_type not in GENERIC_COMPLETION_TYPES:
            completion_type = "MIXED"

        record["order"] = order
        record["scene_id"] = f"roteiro_step_{order:02d}"
        record["completion_type"] = completion_type
        record["objective"] = _clean(record.get("mission")) or _clean(record.get("guide"))
        record["opening_allowed"] = _clean(record.get("released_fact"))
        record["convergence"] = _clean(record.get("mission"))
        record["fixed_facts"] = _clean(record.get("precondition"))
        record["memory_policy"] = (
            "Preserve somente fatos explicitamente confirmados e evidências úteis "
            "para continuidade; não transforme hipótese, pergunta ou fala de Mary em fato do usuário."
        )
        record["deliverables"] = _clean(record.get("completion_criterion"))
        record["exit_condition"] = _clean(record.get("completion_criterion"))
        record["min_turns"] = 1
        record["ideal_turns"] = 2
        record["max_turns"] = 3
        rows.append(record)

    rows.sort(key=lambda item: int(item.get("order", 0) or 0))
    for index, row in enumerate(rows):
        row["next_scene"] = (
            _clean(rows[index + 1].get("scene_id"))
            if index + 1 < len(rows)
            else ""
        )
    return rows


def ensure_funnel_state(narrative: dict, rows: list[dict]) -> dict:
    scene_ids = [
        _clean(row.get("scene_id"))
        for row in rows
        if _clean(row.get("scene_id"))
    ]
    state = narrative.get("funnel_script")
    if not isinstance(state, dict) or state.get("engine") != "generic_script_v6":
        state = {
            "engine": "generic_script_v6",
            "scene_index": 0,
            "scene_id": scene_ids[0] if scene_ids else "",
            "scene_turn": 0,
            "completed_scene_ids": [],
            "markers": [],
            "step_complete": False,
            "step_evidence": [],
            "step_missing": [],
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
    state["markers"] = []
    state["step_complete"] = bool(state.get("step_complete", False))
    if not isinstance(state.get("step_evidence"), list):
        state["step_evidence"] = []
    if not isinstance(state.get("step_missing"), list):
        state["step_missing"] = []
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


def _step_evidence_text(state: dict) -> str:
    evidence = state.get("step_evidence", []) if isinstance(state, dict) else []
    if not isinstance(evidence, list) or not evidence:
        return "- (nenhuma evidência acumulada ainda)"
    lines: list[str] = []
    for item in evidence[:12]:
        if isinstance(item, dict):
            source = _clean(item.get("source")) or "context"
            detail = _clean(item.get("detail")) or _clean(item.get("quote"))
            if detail:
                lines.append(f"- [{source}] {detail}")
        else:
            value = _clean(item)
            if value:
                lines.append(f"- {value}")
    return "\n".join(lines) if lines else "- (nenhuma evidência acumulada ainda)"


def build_funnel_prompt(
    *,
    facts_prompt: str,
    row: dict,
    state: dict,
    scene: dict | None = None,
) -> str:
    stage = funnel_stage(row, state)
    next_turn = int(state.get("scene_turn", 0) or 0) + 1
    mission = _clean(row.get("mission")) or _clean(row.get("objective"))
    completion = _clean(row.get("completion_criterion"))
    guide = _clean(row.get("guide"))
    completion_type = _clean(row.get("completion_type")).upper() or "MIXED"

    if stage == "abertura":
        stage_rule = (
            "Responda naturalmente à fala atual e comece a trabalhar a MISSÃO desta linha. "
            "Não tente executar linhas futuras."
        )
    elif stage == "desenvolvimento":
        stage_rule = (
            "Continue organicamente esta mesma missão. Use o que já foi obtido e busque apenas "
            "o que ainda falta para a condição de conclusão."
        )
    else:
        stage_rule = (
            "Convirja diretamente para a condição de conclusão desta linha, sem abrir ramificações novas."
        )

    return "\n".join(
        [
            "════════════════════════════════════════════════════════════",
            "PASSO AUTORAL ATUAL — AUTORIDADE MÁXIMA",
            "════════════════════════════════════════════════════════════",
            f"PASSO={_clean(row.get('scene_id'))}",
            f"ORDEM={int(row.get('order', 0) or 0)}",
            f"TIPO_DE_CONCLUSÃO={completion_type}",
            f"TURNO_NESTE_PASSO={next_turn}",
            f"ESTÁGIO={stage}",
            "",
            "MISSÃO DA LINHA",
            mission or "(não informada)",
            "",
            "FALA-GUIA AUTORAL",
            guide or "(sem fala-guia)",
            "A fala-guia define intenção, direção e conteúdo permitido; NÃO exige repetição literal.",
            "",
            "CONDIÇÃO DE CONCLUSÃO",
            completion or "(não informada)",
            "",
            "REGRA DE EXECUÇÃO",
            "A fala atual do usuário define COMO Mary reage; a MISSÃO DA LINHA define PARA ONDE a resposta deve andar.",
            "Mary pode levar uma, duas ou três interações para concluir o passo.",
            "Não avance para a próxima linha por conta própria.",
            "Não repita pergunta que já foi respondida de forma suficiente.",
            "Não invente resposta, ação, aceite, recusa ou fato do usuário.",
            "Se a conclusão depender do estado físico, não verbalize o fato para forçá-lo; o Diretor fornece physical_state.",
            "",
            "EVIDÊNCIAS JÁ ACUMULADAS NESTE PASSO",
            _step_evidence_text(state),
            "",
            "PENDÊNCIAS INFORMADAS PELO ÚLTIMO AVALIADOR",
            (
                "\n".join(f"- {_clean(item)}" for item in state.get("step_missing", []) if _clean(item))
                if isinstance(state.get("step_missing"), list) and state.get("step_missing")
                else "- (nenhuma registrada)"
            ),
            "",
            "TERRITÓRIO LIBERADO NESTA LINHA",
            _clean(row.get("released_fact")) or _clean(row.get("opening_allowed")) or "(nenhum adicional)",
            "",
            "PRÉ-CONDIÇÃO",
            _clean(row.get("precondition")) or _clean(row.get("fixed_facts")) or "(nenhuma adicional)",
            "",
            "LIMITES — NÃO PODE",
            _clean(row.get("forbidden")) or "(nenhum adicional)",
            "",
            "ESTILO / ATITUDE",
            _clean(row.get("style")) or "(usar voz natural de Mary)",
            "",
            "ATMOSFERA",
            _clean(row.get("atmosphere")) or "(usar continuidade atual)",
            "",
            "VESTIMENTA",
            _clean(row.get("wardrobe")) or "(usar continuidade atual)",
            "",
            "AÇÃO FÍSICA / ENCENAÇÃO PERMITIDA",
            _clean(row.get("physical_action")) or "(nenhuma obrigatória)",
            "",
            "DINÂMICA DESTE TURNO",
            stage_rule,
            "Preserve modalidade: talvez não é sim; hipótese não é fato; brincadeira não é confirmação.",
            "",
            _memory_text(state),
            "",
            "CONTEXTO FIXO DO CAPÍTULO — SUBORDINADO À LINHA ATUAL",
            _clean(facts_prompt),
        ]
    ).strip()


_EVALUATOR_PROMPT = """
Você é um AVALIADOR GENÉRICO DE PASSO AUTORAL.
Você não conhece esta história de antemão e não usa IDs específicos de roteiro.
Avalie somente o contrato recebido no payload, as evidências acumuladas, a fala atual,
a resposta de Mary e o physical_state estruturado.

Retorne SOMENTE JSON válido neste formato:
{
  "boundary_ok": true,
  "violations": [],
  "step_complete": false,
  "completion_evidence": [],
  "missing": [],
  "mission_progress_ok": true,
  "user_facts": [],
  "consumed_topics": [],
  "user_stance": {},
  "summary": ""
}

REGRAS DE FRONTEIRA:
- boundary_ok=false somente quando Mary viola explicitamente os LIMITES da linha, inventa fato/ação/decisão do usuário, antecipa conteúdo de linha futura, cria rota/programa/objetivo não autorizado ou contradiz fato fixo.
- Falta de progresso NÃO é violação de fronteira.
- Não use naturalidade como desculpa para abrir assunto novo não autorizado.

CONCLUSÃO DO PASSO:
- Decida step_complete SOMENTE pela CONDIÇÃO DE CONCLUSÃO recebida.
- Considere cumulativamente prior_step_evidence + user_text atual + mary_text atual + physical_state atual.
- Não exija palavras idênticas às da condição; avalie equivalência semântica.
- Se a condição estiver parcialmente cumprida, step_complete=false e liste objetivamente o que falta em missing.
- Se estiver totalmente cumprida, step_complete=true e missing=[].
- completion_evidence deve conter apenas evidências que sustentam a conclusão ou avanço real.
- Cada evidência deve ser {"source":"user|mary|physical|prior","detail":"...","quote":"..."}.
- Para source=user, quote deve ser trecho literal da fala atual do usuário quando a evidência for nova neste turno.
- Para source=mary, quote deve ser trecho literal da resposta atual de Mary quando a evidência for nova neste turno.
- Para source=physical, detail deve citar somente campos/valores do physical_state fornecido.
- Para source=prior, use somente evidência já presente em prior_step_evidence.

TIPO DE CONCLUSÃO:
- USER: a conclusão depende de informação/posição fornecida pelo usuário; Mary perguntar não significa que o usuário respondeu.
- MARY: a conclusão depende do que Mary efetivamente disse/entregou.
- PHYSICAL: a conclusão depende somente do physical_state estruturado; não inferir estado físico pela prosa.
- MIXED: combine apenas as fontes realmente exigidas pela condição.

PROGRESSO:
- mission_progress_ok=true quando Mary reagiu de forma pertinente e conduziu o passo em direção à condição, mesmo que o usuário ainda precise responder.
- mission_progress_ok=false quando Mary ficou apenas em assunto incidental ou se afastou da missão sem violar necessariamente uma parede.

FATOS DO USUÁRIO:
- user_facts contém apenas afirmações factuais realmente ditas pelo usuário.
- Cada item: {"category":"...", "fact":"...", "modality":"confirmado|talvez/incerto|negado|hipotético|brincadeira", "source_quote":"trecho literal"}.
- Nunca transforme pergunta de Mary, inferência ou fala social em fato do usuário.

POSIÇÃO DO USUÁRIO:
- user_stance só existe quando a fala atual expressar posição relevante sobre uma proposta da linha.
- Formato: {"value":"aceitou|recusou|talvez/incerto|não respondeu","source_quote":"trecho literal"}.
- Caso contrário, {}.

summary descreve em uma frase o avanço real do turno.
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


def _normalize_completion_evidence(
    items: Any,
    *,
    user_text: str,
    mary_text: str,
    prior_evidence: list,
) -> list[dict]:
    user_fold = _clean(user_text).casefold()
    mary_fold = _clean(mary_text).casefold()
    normalized: list[dict] = []

    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        source = _clean(item.get("source")).lower()
        detail = _clean(item.get("detail"))
        quote = _clean(item.get("quote"))
        if source not in {"user", "mary", "physical", "prior"}:
            continue
        if source == "user" and quote and quote.casefold() not in user_fold:
            continue
        if source == "mary" and quote and quote.casefold() not in mary_fold:
            continue
        if source == "prior":
            prior_text = " ".join(
                _clean(x.get("detail")) + " " + _clean(x.get("quote"))
                for x in prior_evidence
                if isinstance(x, dict)
            ).casefold()
            needle = (detail or quote).casefold()
            if needle and needle not in prior_text:
                continue
        if not detail and not quote:
            continue
        normalized.append(
            {
                "source": source,
                "detail": detail or quote,
                "quote": quote,
            }
        )

    seen: set[tuple[str, str, str]] = set()
    result: list[dict] = []
    for item in normalized:
        key = (
            _clean(item.get("source")).casefold(),
            _clean(item.get("detail")).casefold(),
            _clean(item.get("quote")).casefold(),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
        if len(result) >= 16:
            break
    return result


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
    prior_evidence = (
        state.get("step_evidence", [])
        if isinstance(state.get("step_evidence"), list)
        else []
    )
    physical_state = (
        scene.get("physical_state", {})
        if isinstance(scene, dict) and isinstance(scene.get("physical_state"), dict)
        else {}
    )

    payload = {
        "step_id": _clean(row.get("scene_id")),
        "order": int(row.get("order", 0) or 0),
        "step_turn": int(state.get("scene_turn", 0) or 0) + 1,
        "stage": funnel_stage(row, state),
        "completion_type": _clean(row.get("completion_type")).upper() or "MIXED",
        "mission": _clean(row.get("mission")) or _clean(row.get("objective")),
        "guide": _clean(row.get("guide")),
        "completion_criterion": _clean(row.get("completion_criterion")),
        "released_fact": _clean(row.get("released_fact")),
        "precondition": _clean(row.get("precondition")),
        "forbidden": _clean(row.get("forbidden")),
        "prior_step_evidence": prior_evidence,
        "prior_missing": (
            state.get("step_missing", [])
            if isinstance(state.get("step_missing"), list)
            else []
        ),
        "physical_state": physical_state,
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
        max_tokens=900,
    )
    data = _extract_json(raw)

    boundary_ok = bool(data.get("boundary_ok", True))
    step_complete = bool(data.get("step_complete", False))
    violations = _unique_text(data.get("violations", []), limit=12)
    missing = _unique_text(data.get("missing", []), limit=12)
    mission_progress_ok = bool(data.get("mission_progress_ok", True))

    evidence = _normalize_completion_evidence(
        data.get("completion_evidence", []),
        user_text=user_text,
        mary_text=mary_text,
        prior_evidence=prior_evidence,
    )

    if step_complete and missing:
        step_complete = False

    return {
        "boundary_ok": boundary_ok,
        "violations": violations,
        "step_complete": step_complete,
        "completion_evidence": evidence,
        "missing": missing,
        "mission_progress_ok": mission_progress_ok,
        "mission_progress_target": _clean(row.get("completion_criterion")),
        "semantic_markers": [],
        "physical_markers": derive_physical_markers(scene),
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
        _unique_text(evaluation.get("violations", []), limit=12)
    ) or "a resposta saiu dos limites autorais desta linha"

    mission = _clean(row.get("mission")) or _clean(row.get("objective"))
    completion = _clean(row.get("completion_criterion"))
    missing = _unique_text(evaluation.get("missing", []), limit=12)

    return (
        "CORREÇÃO DE FRONTEIRA DO PASSO AUTORAL. "
        "Reescreva somente a resposta de Mary, sem avançar para a próxima linha. "
        f"VIOLAÇÕES: {violations}. "
        f"MISSÃO DA LINHA: {mission}. "
        f"CONDIÇÃO DE CONCLUSÃO: {completion}. "
        + (
            "AINDA FALTA: " + " | ".join(missing) + ". "
            if missing
            else ""
        )
        + "Reaja naturalmente à fala atual do usuário dentro deste território. "
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

    prior_evidence = (
        state.get("step_evidence", [])
        if isinstance(state.get("step_evidence"), list)
        else []
    )
    current_evidence = (
        evaluation.get("completion_evidence", [])
        if isinstance(evaluation.get("completion_evidence"), list)
        else []
    )
    merged_evidence: list[dict] = []
    seen_evidence: set[tuple[str, str, str]] = set()
    for item in [*prior_evidence, *current_evidence]:
        if not isinstance(item, dict):
            continue
        normalized = {
            "source": _clean(item.get("source")) or "context",
            "detail": _clean(item.get("detail")) or _clean(item.get("quote")),
            "quote": _clean(item.get("quote")),
        }
        if not normalized["detail"]:
            continue
        key = (
            normalized["source"].casefold(),
            normalized["detail"].casefold(),
            normalized["quote"].casefold(),
        )
        if key in seen_evidence:
            continue
        seen_evidence.add(key)
        merged_evidence.append(normalized)
        if len(merged_evidence) >= 20:
            break

    state["step_evidence"] = merged_evidence
    state["step_missing"] = _unique_text(
        evaluation.get("missing", []),
        limit=12,
    )
    state["step_complete"] = bool(evaluation.get("step_complete", False))
    state["markers"] = []

    current_stance = evaluation.get("user_stance", {})
    if isinstance(current_stance, dict) and _clean(current_stance.get("value")):
        state["user_stance"] = deepcopy(current_stance)

    state["scene_turn"] = int(state.get("scene_turn", 0) or 0) + 1
    state["last_evaluation"] = deepcopy(evaluation)
    state["last_advance_reason"] = ""

    can_advance = (
        bool(evaluation.get("boundary_ok", True))
        and bool(evaluation.get("step_complete", False))
    )

    advanced_to = ""
    completed_evidence = deepcopy(merged_evidence)

    if can_advance:
        current_id = _clean(row.get("scene_id"))
        state["completed_scene_ids"] = _unique_text(
            list(state.get("completed_scene_ids", [])) + [current_id],
            limit=64,
        )

        consolidated = _merge_fact_dicts(
            memory.get("consolidated", []),
            memory.get("user_facts", []),
            limit=40,
        )
        memory["consolidated"] = consolidated

        next_index = int(state.get("scene_index", 0) or 0) + 1
        if next_index >= len(rows):
            state["completed"] = True
            state["scene_id"] = ""
            state["last_advance_reason"] = (
                "condição de conclusão do passo comprovada; roteiro concluído"
            )
            advanced_to = "FIM"
        else:
            state["scene_index"] = next_index
            state["scene_id"] = _clean(rows[next_index].get("scene_id"))
            state["scene_turn"] = 0
            state["step_complete"] = False
            state["step_evidence"] = []
            state["step_missing"] = []
            state["user_stance"] = {}
            state["last_advance_reason"] = (
                "condição de conclusão do passo comprovada"
            )
            advanced_to = state["scene_id"]

            memory["user_facts"] = []
            memory["mary_facts"] = []
            memory["consumed_topics"] = []

    required = required_markers(row)
    pending = [] if bool(evaluation.get("step_complete", False)) else required
    achieved = ["step_complete"] if bool(evaluation.get("step_complete", False)) else []

    return {
        "state_before": before,
        "state_after": deepcopy(state),
        "advanced": can_advance,
        "advanced_to": advanced_to,
        "stage": funnel_stage(row, before),
        "required_markers": required,
        "achieved_markers": achieved,
        "pending_markers": pending,
        "exit_ready": bool(evaluation.get("step_complete", False)),
        "completion_evidence": completed_evidence,
        "missing": _unique_text(evaluation.get("missing", []), limit=12),
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
