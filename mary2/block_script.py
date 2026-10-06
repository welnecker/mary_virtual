from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import gspread

from openrouter_client import chat


BLOCK_HEADERS = {
    "ordem": "order",
    "objetivo atual": "objective",
    "território livre": "free_territory",
    "territorio livre": "free_territory",
    "convergência": "convergence",
    "convergencia": "convergence",
    "tom / atitude": "tone",
    "atmosfera": "atmosphere",
    "memória permanente de mary": "permanent_memory",
    "memoria permanente de mary": "permanent_memory",
    "memória recente autoral": "authorial_recent_memory",
    "memoria recente autoral": "authorial_recent_memory",
    "memória dinâmica necessária": "dynamic_requirement",
    "memoria dinamica necessaria": "dynamic_requirement",
    "ação física permitida": "physical_action",
    "acao fisica permitida": "physical_action",
    "limites específicos": "specific_limits",
    "limites especificos": "specific_limits",
    "interações alvo": "target_interactions",
    "interacoes alvo": "target_interactions",
    "máximo de interações": "max_interactions",
    "maximo de interacoes": "max_interactions",
    "depende da resposta do usuário?": "depends_on_user",
    "depende da resposta do usuario?": "depends_on_user",
    "prompt do bloco": "prompt_preview",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any, default: int) -> int:
    try:
        return int(float(_clean(value)))
    except Exception:
        return int(default)


def _yes(value: Any) -> bool:
    return _clean(value).casefold() in {"sim", "s", "yes", "true", "1"}


def _target_range(value: Any) -> tuple[int, int]:
    text = _clean(value).replace("–", "-").replace("—", "-")
    numbers: list[int] = []
    current = ""
    for char in text:
        if char.isdigit():
            current += char
        elif current:
            numbers.append(int(current))
            current = ""
    if current:
        numbers.append(int(current))

    if not numbers:
        return 2, 3
    if len(numbers) == 1:
        number = max(1, numbers[0])
        return number, number
    low = max(1, min(numbers[0], numbers[1]))
    high = max(low, max(numbers[0], numbers[1]))
    return low, high


def load_block_rows(
    *,
    service_account_info: dict,
    spreadsheet_id: str,
    worksheet_name: str,
) -> list[dict]:
    """Carrega blocos dramáticos da planilha autoral nova."""
    if not service_account_info:
        raise ValueError("service_account_info ausente para roteiro em blocos")
    if not _clean(spreadsheet_id):
        raise ValueError("spreadsheet_id ausente para roteiro em blocos")

    client = gspread.service_account_from_dict(service_account_info)
    worksheet = client.open_by_key(_clean(spreadsheet_id)).worksheet(
        _clean(worksheet_name) or "ROTEIRO_BLOCOS_TESTE"
    )
    values = worksheet.get_all_values()
    if not values:
        return []

    header_index = -1
    headers: list[str] = []
    for idx, source in enumerate(values):
        normalized = [_clean(cell).lower() for cell in source]
        if "ordem" in normalized and "objetivo atual" in normalized:
            header_index = idx
            headers = normalized
            break
    if header_index < 0:
        raise ValueError("cabeçalho do roteiro em blocos não encontrado")

    rows: list[dict] = []
    for source_row in values[header_index + 1 :]:
        if not any(_clean(cell) for cell in source_row):
            continue

        record: dict[str, Any] = {}
        for index, header in enumerate(headers):
            key = BLOCK_HEADERS.get(header)
            if key:
                record[key] = _clean(
                    source_row[index] if index < len(source_row) else ""
                )

        objective = _clean(record.get("objective"))
        if not objective:
            continue

        order = _int(record.get("order"), len(rows) + 1)
        target_min, target_max = _target_range(
            record.get("target_interactions")
        )
        hard_max = max(
            target_max,
            _int(record.get("max_interactions"), 5),
        )

        record["order"] = order
        record["block_id"] = f"bloco_{order:02d}"
        record["scene_id"] = record["block_id"]  # compatibilidade de auditoria
        record["target_min"] = target_min
        record["target_max"] = target_max
        record["min_turns"] = target_min
        record["ideal_turns"] = target_max
        record["max_turns"] = hard_max
        record["depends_on_user"] = _yes(record.get("depends_on_user"))
        rows.append(record)

    rows.sort(key=lambda item: int(item.get("order", 0) or 0))
    for index, row in enumerate(rows):
        row["next_block_id"] = (
            _clean(rows[index + 1].get("block_id"))
            if index + 1 < len(rows)
            else ""
        )
    return rows


def ensure_block_state(narrative: dict, rows: list[dict]) -> dict:
    state = narrative.get("block_script")
    if not isinstance(state, dict) or state.get("engine") != "block_script_v1":
        state = {
            "engine": "block_script_v1",
            "block_index": 0,
            "block_id": _clean(rows[0].get("block_id")) if rows else "",
            "block_turn": 0,
            "completed_block_ids": [],
            "dynamic_memory": [],
            "last_dependency": {},
            "waiting_for_dependency": False,
            "holding_for_next_block": False,
            "completed": False,
        }
        narrative["block_script"] = state

    if not isinstance(state.get("completed_block_ids"), list):
        state["completed_block_ids"] = []
    if not isinstance(state.get("dynamic_memory"), list):
        state["dynamic_memory"] = []
    if not isinstance(state.get("last_dependency"), dict):
        state["last_dependency"] = {}

    index = max(0, _int(state.get("block_index"), 0))
    if rows:
        index = min(index, len(rows) - 1)
        valid_ids = [_clean(row.get("block_id")) for row in rows]
        current_id = _clean(state.get("block_id"))
        if current_id in valid_ids:
            index = valid_ids.index(current_id)
        else:
            state["block_id"] = _clean(rows[index].get("block_id"))

    state["block_index"] = index
    state["block_turn"] = max(0, _int(state.get("block_turn"), 0))
    state["waiting_for_dependency"] = bool(
        state.get("waiting_for_dependency", False)
    )
    state["holding_for_next_block"] = bool(
        state.get("holding_for_next_block", False)
    )
    state["completed"] = bool(state.get("completed", False))
    return state


def current_block_row(rows: list[dict], state: dict) -> dict:
    if not rows:
        return {}
    index = max(
        0,
        min(_int(state.get("block_index"), 0), len(rows) - 1),
    )
    return dict(rows[index])


def block_stage(row: dict, state: dict) -> str:
    turn = max(0, _int(state.get("block_turn"), 0))
    target_min = max(1, _int(row.get("target_min"), 2))
    target_max = max(target_min, _int(row.get("target_max"), 3))
    hard_max = max(target_max, _int(row.get("max_turns"), 5))

    if bool(state.get("holding_for_next_block", False)):
        return "aguardando_proximo_bloco"
    if bool(state.get("waiting_for_dependency", False)) or turn >= hard_max - 1:
        return "convergencia_direta"
    if turn < target_min - 1:
        return "desenvolvimento_livre"
    if turn < target_max - 1:
        return "aproximando_convergencia"
    return "convergencia"


def _dynamic_memory_text(state: dict) -> str:
    items = state.get("dynamic_memory", []) if isinstance(state, dict) else []
    if not isinstance(items, list) or not items:
        return "- (nenhuma memória dinâmica confirmada ainda)"
    lines: list[str] = []
    for item in items[-12:]:
        if isinstance(item, dict):
            text = _clean(item.get("summary")) or _clean(item.get("value"))
        else:
            text = _clean(item)
        if text:
            lines.append(f"- {text}")
    return "\n".join(lines) if lines else "- (nenhuma memória dinâmica confirmada ainda)"


def build_block_prompt(
    *,
    facts_prompt: str,
    row: dict,
    state: dict,
    scene: dict | None = None,
) -> str:
    stage = block_stage(row, state)
    next_turn = int(state.get("block_turn", 0) or 0) + 1
    depends = bool(row.get("depends_on_user", False))
    target_min = max(1, _int(row.get("target_min"), 2))
    target_max = max(target_min, _int(row.get("target_max"), 3))
    hard_max = max(target_max, _int(row.get("max_turns"), 5))

    if stage == "desenvolvimento_livre":
        rhythm = (
            "Viva o bloco atual sem pressa. Reaja primeiro ao usuário e use o território "
            "livre como paleta de improviso; não tente usar todos os itens."
        )
    elif stage == "aproximando_convergencia":
        rhythm = (
            "Continue natural, mas comece a orientar o clima da conversa para a convergência. "
            "Prepare a passagem; não execute ainda o próximo bloco."
        )
    elif stage in {"convergencia", "convergencia_direta"}:
        rhythm = (
            "Feche organicamente este bloco. A resposta deve deixar a cena pronta para a "
            "convergência indicada, sem executar o conteúdo do próximo bloco."
        )
    else:
        rhythm = (
            "A planilha ainda não possui um próximo bloco. Continue apenas reagindo ao momento "
            "presente sem abrir novo assunto de roteiro."
        )

    dependency_rule = ""
    if depends:
        dependency_rule = (
            "\n\nDEPENDÊNCIA DA RESPOSTA DO USUÁRIO\n"
            + (
                _clean(row.get("dynamic_requirement"))
                or "Este bloco precisa de uma resposta concreta do usuário antes de avançar."
            )
            + "\nO runtime decide quando essa informação foi realmente fornecida. "
              "Não invente a resposta nem a coloque na boca do usuário."
        )

    return (
        "════════════════════════════════════════════════════════════\n"
        "BLOCO DRAMÁTICO ATUAL\n"
        "════════════════════════════════════════════════════════════\n"
        f"BLOCO={_clean(row.get('block_id'))}\n"
        f"ORDEM={int(row.get('order', 0) or 0)}\n"
        f"INTERAÇÃO_NESTE_BLOCO={next_turn}\n"
        f"ESTÁGIO={stage}\n\n"
        "OBJETIVO ATUAL\n"
        f"{_clean(row.get('objective')) or '(não informado)'}\n\n"
        "TERRITÓRIO LIVRE\n"
        f"{_clean(row.get('free_territory')) or '(reaja naturalmente ao momento atual)'}\n"
        "Os itens acima são possibilidades de improviso, não uma checklist.\n\n"
        "MEMÓRIA PERMANENTE DE MARY\n"
        f"{_clean(row.get('permanent_memory')) or 'Use o perfil permanente já fornecido no prompt principal.'}\n\n"
        "MEMÓRIA RECENTE AUTORAL\n"
        f"{_clean(row.get('authorial_recent_memory')) or '(nenhuma adicional)'}\n\n"
        "MEMÓRIA DINÂMICA CONFIRMADA NESTA RUN\n"
        f"{_dynamic_memory_text(state)}\n\n"
        "TOM / ATITUDE\n"
        f"{_clean(row.get('tone')) or '(voz natural de Mary)'}\n\n"
        "ATMOSFERA\n"
        f"{_clean(row.get('atmosphere')) or '(seguir o momento atual)'}\n\n"
        "AÇÃO FÍSICA PERMITIDA\n"
        f"{_clean(row.get('physical_action')) or '(nenhuma instrução adicional)'}\n\n"
        "LIMITES ESPECÍFICOS\n"
        f"{_clean(row.get('specific_limits')) or '(nenhum adicional)'}\n\n"
        "CONVERGÊNCIA\n"
        f"{_clean(row.get('convergence')) or '(nenhuma próxima passagem informada)'}\n"
        "Convergência é direção futura: prepare a cena, mas não execute o próximo bloco antes "
        "da troca feita pelo runtime.\n\n"
        "RITMO DESTE TURNO\n"
        f"{rhythm}\n"
        f"Faixa autoral: {target_min}–{target_max} interações; limite de convergência: {hard_max}."
        f"{dependency_rule}\n\n"
        "REGRAS UNIVERSAIS DESTE BLOCO\n"
        "- Responda primeiro ao que o usuário realmente disse.\n"
        "- Não invente fatos, lembranças, decisões ou ações do usuário.\n"
        "- [PENSAMENTO] é subtexto emocional do momento, não fato novo e não resumo burocrático.\n"
        "- Use memória recente para ganhar profundidade e continuidade, não para repetir fatos mecanicamente.\n"
        "- Não transforme o objetivo atual em pergunta ou frase repetida a cada interação.\n\n"
        "CONTEXTO FIXO DO CAPÍTULO\n"
        f"{_clean(facts_prompt) or '(nenhum adicional)'}"
    )


_DEPENDENCY_PROMPT = """Você é um verificador mínimo de passagem de bloco em um roleplay.
Sua única tarefa é decidir se a FALA ATUAL DO USUÁRIO forneceu a informação necessária
descrita em REQUIREMENT.

Não avalie estilo de Mary. Não dirija a cena. Não invente informação ausente.
Aceite equivalência semântica, respostas coloquiais e recusas explícitas.
Uma recusa explícita em responder também encerra a dependência, registrando-a como recusa.

Retorne SOMENTE JSON:
{
  "satisfied": true,
  "refused": false,
  "summary": "fato confirmado de forma curta",
  "source_quote": "trecho literal da fala do usuário"
}
"""


def evaluate_block_dependency(
    *,
    api_key: str,
    model: str,
    fallback_model: str | None,
    row: dict,
    user_text: str,
) -> dict:
    if not bool(row.get("depends_on_user", False)):
        return {
            "satisfied": True,
            "refused": False,
            "summary": "bloco não depende de resposta obrigatória do usuário",
            "source_quote": "",
            "raw": "",
        }

    requirement = _clean(row.get("dynamic_requirement"))
    if not requirement or requirement.casefold().startswith("nenhuma"):
        return {
            "satisfied": True,
            "refused": False,
            "summary": "nenhuma memória dinâmica obrigatória definida",
            "source_quote": "",
            "raw": "",
        }

    payload = {
        "requirement": requirement,
        "user_text": _clean(user_text),
    }
    raw = chat(
        api_key=api_key,
        model=model,
        fallback_model=fallback_model,
        messages=[
            {"role": "system", "content": _DEPENDENCY_PROMPT},
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False),
            },
        ],
        temperature=0.0,
    )

    text = _clean(raw)
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    try:
        data = json.loads(text)
    except Exception:
        data = {}

    quote = _clean(data.get("source_quote"))
    user_fold = _clean(user_text).casefold()
    if quote and quote.casefold() not in user_fold:
        quote = ""

    satisfied = bool(data.get("satisfied", False))
    refused = bool(data.get("refused", False))
    if refused:
        satisfied = True

    return {
        "satisfied": satisfied,
        "refused": refused,
        "summary": _clean(data.get("summary")),
        "source_quote": quote,
        "raw": raw,
    }


def apply_block_turn(
    *,
    rows: list[dict],
    state: dict,
    row: dict,
    dependency: dict,
    scene: dict,
) -> dict:
    before = deepcopy(state)
    turn_after = max(0, _int(state.get("block_turn"), 0)) + 1
    state["block_turn"] = turn_after

    depends = bool(row.get("depends_on_user", False))
    dependency_satisfied = bool(
        dependency.get("satisfied", False)
    ) if isinstance(dependency, dict) else not depends

    if isinstance(dependency, dict):
        state["last_dependency"] = deepcopy(dependency)

    summary = _clean(dependency.get("summary")) if isinstance(dependency, dict) else ""
    if depends and dependency_satisfied and summary:
        memory = state.get("dynamic_memory", [])
        if not isinstance(memory, list):
            memory = []
        key = summary.casefold()
        if key not in {
            _clean(item.get("summary") if isinstance(item, dict) else item).casefold()
            for item in memory
        }:
            memory.append(
                {
                    "block_id": _clean(row.get("block_id")),
                    "summary": summary,
                    "source_quote": _clean(dependency.get("source_quote")),
                    "refused": bool(dependency.get("refused", False)),
                }
            )
        state["dynamic_memory"] = memory[-24:]

    target_min = max(1, _int(row.get("target_min"), 2))
    target_max = max(target_min, _int(row.get("target_max"), 3))
    hard_max = max(target_max, _int(row.get("max_turns"), 5))

    index = max(0, _int(state.get("block_index"), 0))
    has_next = index + 1 < len(rows)

    # Bloco sem dependência: troca deterministicamente no fim da faixa alvo.
    # Bloco dependente: só troca depois de resposta suficiente/recusa explícita.
    ready = (
        (not depends and turn_after >= target_max)
        or (depends and dependency_satisfied and turn_after >= target_min)
    )

    advanced = False
    advanced_to = ""
    holding = False

    if ready and has_next:
        current_id = _clean(row.get("block_id"))
        completed = state.get("completed_block_ids", [])
        if not isinstance(completed, list):
            completed = []
        if current_id and current_id not in completed:
            completed.append(current_id)
        state["completed_block_ids"] = completed[-64:]
        state["block_index"] = index + 1
        state["block_id"] = _clean(rows[index + 1].get("block_id"))
        state["block_turn"] = 0
        state["waiting_for_dependency"] = False
        state["holding_for_next_block"] = False
        advanced = True
        advanced_to = state["block_id"]
    elif ready and not has_next:
        # Aba piloto incompleta: não inventa próximo bloco e não cai no roteiro legado.
        state["holding_for_next_block"] = True
        state["waiting_for_dependency"] = False
        holding = True
    else:
        state["waiting_for_dependency"] = bool(
            depends and not dependency_satisfied and turn_after >= target_max
        )
        state["holding_for_next_block"] = False

    after = deepcopy(state)
    return {
        "state_before": before,
        "state_after": after,
        "stage": block_stage(row, before),
        "advanced": advanced,
        "advanced_to": advanced_to,
        "dependency_satisfied": dependency_satisfied,
        "waiting_for_dependency": bool(state.get("waiting_for_dependency", False)),
        "holding_for_next_block": holding or bool(
            state.get("holding_for_next_block", False)
        ),
        "target_min": target_min,
        "target_max": target_max,
        "max_interactions": hard_max,
        "physical_state": deepcopy(
            scene.get("physical_state", {})
            if isinstance(scene, dict)
            else {}
        ),
    }


def block_ready_for_choice(state: dict) -> bool:
    return bool(state.get("completed", False))
