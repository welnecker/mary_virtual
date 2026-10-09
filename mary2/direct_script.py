from __future__ import annotations

import json
import re
import time
from copy import deepcopy
from typing import Any

import gspread

from openrouter_client import chat


DIRECT_HEADERS = {
    "ordem": "order",
    "roteiro": "script_name",
    "tipo": "type",
    "fala-guia": "speech_guide",
    "modo": "interaction_mode",
    "modo de interação": "interaction_mode",
    "modo de interacao": "interaction_mode",
    "interação": "interaction_mode",
    "interacao": "interaction_mode",
    "prosseguir": "interaction_mode",
    "revelacao": "revelation_policy",
    "revelação": "revelation_policy",
    "estilo / atitude": "style",
    "pré-condição": "precondition",
    "pre-condição": "precondition",
    "vestimenta atual": "wardrobe",
    "ação física / encenação": "physical_action",
    "acao fisica / encenacao": "physical_action",
    "tipo de conclusão": "completion_type",
    "tipo de conclusao": "completion_type",
    "memória recente para roteiro": "recent_memory",
    "memoria recente para roteiro": "recent_memory",
    "memória instantânea": "instant_memory",
    "memoria instantanea": "instant_memory",
    "memória instantânea-local": "instant_memory",
    "memoria instantanea-local": "instant_memory",
    "memória permanente": "permanent_memory",
    "memoria permanente": "permanent_memory",
    "memória permanente-global": "permanent_memory",
    "memoria permanente-global": "permanent_memory",
    "memória física": "physical_memory",
    "memoria fisica": "physical_memory",
    "memória física-global": "physical_memory",
    "memoria fisica-global": "physical_memory",
    "descrição inicial": "initial_description",
    "descricao inicial": "initial_description",
    "descrição inicial-cena": "initial_description",
    "descricao inicial-cena": "initial_description",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def is_automatic_direct_row(row: dict | None) -> bool:
    """Linha automática: Mary conduz sozinha e a linha termina sem resposta do usuário."""
    if not isinstance(row, dict):
        return False
    mode = _clean(row.get("interaction_mode")).casefold()
    return mode in {"automatico", "automático", "automatic", "auto"}


def is_blocked_direct_row(row: dict | None) -> bool:
    """Linha bloqueada: Mary fala primeiro e só depois libera a resposta do usuário."""
    if not isinstance(row, dict):
        return False
    mode = _clean(row.get("interaction_mode")).casefold()
    return mode in {"bloqueado", "bloqueada", "blocked", "mary_first", "mary-first"}


def extract_direct_character_name(row: dict | None, user_text: Any) -> str:
    """Captura nome declarado pelo interlocutor sem depender do modelo."""
    text = _clean(user_text)
    if not text:
        return ""

    patterns = (
        r"\bmeu nome (?:é|e)\s+([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ' -]{1,40})",
        r"\beu sou\s+([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ' -]{1,40})",
        r"\bpode me chamar de\s+([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ' -]{1,40})",
        r"\bme chamo\s+([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ' -]{1,40})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            value = _clean(match.group(1))
            value = re.split(r"[,.!?;:\n]", value, maxsplit=1)[0].strip()
            return value[:48]

    guide = _clean((row or {}).get("speech_guide")).casefold()
    words = text.split()
    if "nome" in guide and 1 <= len(words) <= 3:
        candidate = " ".join(words).strip(" .,!?:;")
        if re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ' -]{1,47}", candidate):
            return candidate

    return ""


DIRECT_CHAPTER_PREFIX = "sheet:"


def parse_direct_script_id(value: Any) -> dict:
    """Interpreta IDs autorais no formato Nome+índice, por exemplo Carona4."""
    script_id = _clean(value)
    match = re.match(r"^(.*?)(\d+)$", script_id)
    if not match or not _clean(match.group(1)):
        return {
            "script_id": script_id,
            "script_name": script_id,
            "script_index": 0,
            "valid": False,
        }
    return {
        "script_id": script_id,
        "script_name": _clean(match.group(1)),
        "script_index": int(match.group(2)),
        "valid": True,
    }


def direct_chapter_id(script_id: Any) -> str:
    value = _clean(script_id)
    return f"{DIRECT_CHAPTER_PREFIX}{value}" if value else ""


def direct_script_id_from_chapter_id(chapter_id: Any) -> str:
    value = _clean(chapter_id)
    if not value.startswith(DIRECT_CHAPTER_PREFIX):
        return ""
    return _clean(value[len(DIRECT_CHAPTER_PREFIX):])


def build_direct_chapter(script_id: Any) -> dict:
    """Cria em memória a configuração de um capítulo descoberto na planilha."""
    parsed = parse_direct_script_id(script_id)
    if not parsed["valid"]:
        raise ValueError(
            f"ID de roteiro direto inválido: {parsed['script_id']!r}. "
            "Use Nome+índice, por exemplo Carona4."
        )

    # O primeiro roteiro da história é a Confissão com Janio.
    # Os seguintes usam PERSONAGEM_DA_CENA por padrão. Linhas automáticas
    # ignoram o interlocutor e bloqueiam a entrada livre do usuário.
    user_role = "JANIO" if int(parsed["script_index"]) == 1 else "PERSONAGEM_DA_CENA"
    temporary_active = user_role == "PERSONAGEM_DA_CENA"
    present = ["MARY", "JANIO"] if user_role == "JANIO" else ["MARY", "PERSONAGEM_DA_CENA"]

    return {
        "title": parsed["script_name"],
        "allowed_roles": [user_role],
        "phase_context": "chapter",
        "script_mode": "direct_sheet",
        "script_worksheet": "MINHA_SUGESTAO",
        "script_name": parsed["script_id"],
        "sheet_script_index": parsed["script_index"],
        "inherit_character": temporary_active,
        "inherit_scene": False,
        "decision_after_turns": 0,
        "choices": [],
        "opening_caption": "",
        "opening_mary": "",
        "model_opening": False,
        "initial_scene": {
            "location": "",
            "time": "",
            "present_characters": present,
            "interaction_mode": "in_person",
            "user_role": user_role,
            "proximity": "",
            "sexual_intensity": "none",
            "mary_immediate_goal": "",
            "mary_action": "",
            "event": "",
            "open_hook": False,
            "hook_resolution": "",
            "temporary_character": {
                "active": temporary_active,
                "name": "" if user_role == "JANIO" else "Personagem da cena",
                "description": "",
                "relation_to_mary": "",
                "user_can_play": temporary_active,
            },
            "return_anchor": "",
            "scene_changed": True,
            "show_caption": False,
            "scene_caption": "",
            "arc_phase": "opening",
            "resolution_type": "none",
            "resolution_summary": "",
            "start_new_scene": True,
            "turns_in_scene": 0,
            "scene_number": int(parsed["script_index"]),
            "mary_should_initiate": False,
            "user_scene_direction": "",
        },
    }


def load_direct_script_catalog(
    *,
    service_account_info: dict,
    spreadsheet_id: str,
    worksheet_name: str = "MINHA_SUGESTAO",
) -> list[dict]:
    """Descobre os roteiros Nome+índice diretamente da coluna Roteiro."""
    if not service_account_info:
        raise ValueError("service_account_info ausente para catálogo de roteiros")
    if not _clean(spreadsheet_id):
        raise ValueError("spreadsheet_id ausente para catálogo de roteiros")

    client = gspread.service_account_from_dict(service_account_info)
    worksheet = client.open_by_key(_clean(spreadsheet_id)).worksheet(
        _clean(worksheet_name) or "MINHA_SUGESTAO"
    )
    values = worksheet.get_all_values()
    if not values:
        return []

    header_index = -1
    roteiro_index = -1
    fala_guia_index = -1
    for idx, source in enumerate(values):
        normalized = [_clean(cell).lower() for cell in source]
        if "ordem" in normalized and "roteiro" in normalized:
            header_index = idx
            roteiro_index = normalized.index("roteiro")
            fala_guia_index = (
                normalized.index("fala-guia")
                if "fala-guia" in normalized
                else -1
            )
            break
    if header_index < 0 or roteiro_index < 0:
        raise ValueError("cabeçalho do catálogo de roteiros não encontrado")

    catalog_by_id: dict[str, dict] = {}
    first_seen = 0
    for source_row in values[header_index + 1:]:
        script_id = _clean(
            source_row[roteiro_index] if roteiro_index < len(source_row) else ""
        )
        if not script_id:
            continue
        parsed = parse_direct_script_id(script_id)
        if not parsed["valid"]:
            continue
        key = parsed["script_id"].casefold()
        if key not in catalog_by_id:
            first_seen += 1
            catalog_by_id[key] = {
                **parsed,
                "first_seen": first_seen,
                "chapter_id": direct_chapter_id(parsed["script_id"]),
                "row_count": 0,
                "executable_row_count": 0,
            }
        catalog_by_id[key]["row_count"] += 1
        if (
            fala_guia_index >= 0
            and fala_guia_index < len(source_row)
            and _clean(source_row[fala_guia_index])
        ):
            catalog_by_id[key]["executable_row_count"] += 1

    catalog = list(catalog_by_id.values())
    catalog.sort(
        key=lambda item: (
            int(item.get("script_index", 0) or 0),
            int(item.get("first_seen", 0) or 0),
        )
    )

    seen_indexes: dict[int, str] = {}
    for item in catalog:
        index = int(item.get("script_index", 0) or 0)
        previous = seen_indexes.get(index)
        if previous and previous.casefold() != str(item["script_id"]).casefold():
            raise ValueError(
                f"Índice de roteiro duplicado {index}: {previous!r} e {item['script_id']!r}."
            )
        seen_indexes[index] = str(item["script_id"])

    return catalog


def next_direct_script(
    catalog: list[dict],
    current_script_id: Any,
) -> dict:
    current = _clean(current_script_id).casefold()
    for index, item in enumerate(catalog):
        if _clean(item.get("script_id")).casefold() != current:
            continue
        if index + 1 < len(catalog):
            return dict(catalog[index + 1])
        return {}
    return {}


def _resolve_placeholders(text: str, *, character_name: str) -> str:
    value = _clean(text)
    name = _clean(character_name)
    if name.lower() in {"", "personal", "personagem", "personagem_da_cena"}:
        name = ""
    value = value.replace("{usuario}", name)
    value = re.sub(r"\s+,", ",", value)
    value = re.sub(r",\s*,", ",", value)
    value = re.sub(r"\s{2,}", " ", value)
    return value.strip(" ,")


def load_direct_script_rows(
    *,
    service_account_info: dict,
    spreadsheet_id: str,
    worksheet_name: str,
    script_name: str,
) -> list[dict]:
    """Lê o roteiro autoral sem reinterpretar ou enriquecer seus campos."""
    if not service_account_info:
        raise ValueError("service_account_info ausente para roteiro direto")
    if not _clean(spreadsheet_id):
        raise ValueError("spreadsheet_id ausente para roteiro direto")

    client = gspread.service_account_from_dict(service_account_info)
    worksheet = client.open_by_key(_clean(spreadsheet_id)).worksheet(
        _clean(worksheet_name) or "MINHA_SUGESTAO"
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
        raise ValueError("cabeçalho do roteiro direto não encontrado")

    rows: list[dict] = []
    for source_row in values[header_index + 1 :]:
        if not any(_clean(cell) for cell in source_row):
            continue

        record: dict[str, Any] = {}
        for index, header in enumerate(headers):
            key = DIRECT_HEADERS.get(header)
            if key:
                record[key] = _clean(
                    source_row[index] if index < len(source_row) else ""
                )

        if _clean(record.get("script_name")).casefold() != _clean(script_name).casefold():
            continue
        try:
            record["order"] = int(float(_clean(record.get("order"))))
        except Exception:
            continue
        if not _clean(record.get("speech_guide")):
            continue

        record["line_id"] = f"linha_{record['order']:02d}"
        rows.append(record)

    rows.sort(key=lambda item: int(item.get("order", 0) or 0))

    # Memórias marcadas como GLOBAL são autoradas uma única vez na planilha,
    # mas precisam acompanhar todas as linhas entregues ao Redator.
    permanent_memory_global = next(
        (_clean(item.get("permanent_memory")) for item in rows if _clean(item.get("permanent_memory"))),
        "",
    )
    physical_memory_global = next(
        (_clean(item.get("physical_memory")) for item in rows if _clean(item.get("physical_memory"))),
        "",
    )
    for item in rows:
        item["permanent_memory"] = permanent_memory_global
        item["physical_memory"] = physical_memory_global

    return rows


def ensure_direct_state(narrative: dict, rows: list[dict]) -> dict:
    state = narrative.get("direct_script")
    if not isinstance(state, dict) or state.get("engine") != "direct_sheet_v1":
        state = {
            "engine": "direct_sheet_v1",
            "index": 0,
            "current_order": int(rows[0].get("order", 0) or 0) if rows else 0,
            "awaiting_reply_order": 0,
            "completed_orders": [],
            "line_dialogue": [],
            "completed": not bool(rows),
        }
        narrative["direct_script"] = state

    if not isinstance(state.get("completed_orders"), list):
        state["completed_orders"] = []
    if not isinstance(state.get("line_dialogue"), list):
        state["line_dialogue"] = []

    completed = sorted({
        int(value)
        for value in state.get("completed_orders", [])
        if str(value).strip()
    })
    state["completed_orders"] = completed

    index = max(0, int(state.get("index", 0) or 0))
    while (
        index < len(rows)
        and int(rows[index].get("order", 0) or 0) in completed
    ):
        index += 1

    state["index"] = min(index, len(rows))
    state["awaiting_reply_order"] = max(
        0, int(state.get("awaiting_reply_order", 0) or 0)
    )

    if state["index"] >= len(rows):
        state["current_order"] = 0
        state["completed"] = True
    else:
        current_order = int(rows[state["index"]].get("order", 0) or 0)
        if current_order in completed:
            raise RuntimeError(
                "direct_script inválido: tentativa de regressão para linha já concluída"
            )
        state["current_order"] = current_order
        state["completed"] = bool(state.get("completed", False)) and not rows

    return state


def register_direct_user_reply(
    state: dict,
    rows: list[dict],
    user_text: str,
) -> dict:
    """A fala seguinte do usuário encerra a linha que Mary acabou de emitir."""
    before = deepcopy(state)
    awaiting = int(state.get("awaiting_reply_order", 0) or 0)
    if awaiting and _clean(user_text):
        completed = {
            int(value)
            for value in (state.get("completed_orders", []) or [])
            if str(value).strip()
        }
        completed.add(awaiting)
        state["completed_orders"] = sorted(completed)
        state["awaiting_reply_order"] = 0
        state["line_dialogue"] = []
        state["index"] = min(int(state.get("index", 0) or 0) + 1, len(rows))
        if state["index"] >= len(rows):
            state["current_order"] = 0
            state["completed"] = True
        else:
            state["current_order"] = int(rows[state["index"]].get("order", 0) or 0)

    return {"state_before": before, "state_after": deepcopy(state)}


def current_direct_row(rows: list[dict], state: dict) -> dict:
    if not rows or bool(state.get("completed", False)):
        return {}
    index = max(0, min(int(state.get("index", 0) or 0), len(rows) - 1))
    return dict(rows[index])


def mark_direct_line_emitted(
    state: dict,
    row: dict,
    rows: list[dict] | None = None,
) -> None:
    order = int(row.get("order", 0) or 0)
    if not order:
        return

    last_order = 0
    if rows:
        last_order = max(int(item.get("order", 0) or 0) for item in rows)

    if is_automatic_direct_row(row):
        completed = {
            int(value)
            for value in (state.get("completed_orders", []) or [])
            if str(value).strip()
        }
        completed.add(order)
        state["completed_orders"] = sorted(completed)
        state["awaiting_reply_order"] = 0
        state["line_dialogue"] = []
        if rows:
            current_index = next(
                (
                    idx
                    for idx, item in enumerate(rows)
                    if int(item.get("order", 0) or 0) == order
                ),
                int(state.get("index", 0) or 0),
            )
            state["index"] = min(current_index + 1, len(rows))
            if state["index"] >= len(rows):
                state["current_order"] = 0
                state["completed"] = True
            else:
                state["current_order"] = int(rows[state["index"]].get("order", 0) or 0)
                state["completed"] = False
        return

    if last_order and order == last_order:
        completed = {
            int(value)
            for value in (state.get("completed_orders", []) or [])
            if str(value).strip()
        }
        completed.add(order)
        state["completed_orders"] = sorted(completed)
        state["awaiting_reply_order"] = 0
        state["current_order"] = 0
        state["index"] = len(rows)
        state["completed"] = True
        state["line_dialogue"] = []
        return

    state["awaiting_reply_order"] = order
    state["current_order"] = order


def record_direct_line_turn(
    state: dict,
    *,
    user_text: str,
    mary_text: str,
) -> None:
    """Guarda somente a conversa ocorrida enquanto a linha atual permanece ativa."""
    dialogue = state.get("line_dialogue")
    if not isinstance(dialogue, list):
        dialogue = []
        state["line_dialogue"] = dialogue
    if _clean(user_text):
        dialogue.append({"role": "user", "content": _clean(user_text)})
    if _clean(mary_text):
        dialogue.append({"role": "assistant", "content": _clean(mary_text)})
    # Evita crescimento ilimitado em linhas excepcionalmente longas.
    if len(dialogue) > 12:
        state["line_dialogue"] = dialogue[-12:]


def direct_script_ready_for_choice(state: dict) -> bool:
    return bool(state.get("completed", False))




def direct_line_correction_prompt(row: dict, evaluation: dict) -> str:
    """Corrige só a lacuna apontada, preservando personalidade, continuidade e espontaneidade."""
    guide = _clean(row.get("speech_guide"))
    missing = _clean(evaluation.get("missing"))
    elements = evaluation.get("elements", [])
    user_obligation = evaluation.get("user_obligation", {})
    unmet = [
        _clean(item.get("requirement"))
        for item in elements
        if isinstance(item, dict)
        and not bool(item.get("found", False))
        and _clean(item.get("requirement"))
    ]
    if isinstance(user_obligation, dict) and bool(user_obligation.get("exists", False)) and not bool(user_obligation.get("satisfied", False)):
        user_requirement = _clean(user_obligation.get("requirement")) or "responder diretamente à fala atual do usuário"
        unmet.insert(0, user_requirement)
    detail = "; ".join(unmet) or missing or "as obrigações do turno"
    return (
        "CORREÇÃO CIRÚRGICA DA MESMA LINHA. Preserve personalidade, continuidade e espontaneidade. "
        "A primeira resposta pode conter partes naturais e válidas: não reinicie tudo do zero e não reescreva "
        "o que já funciona sem necessidade. Faça a menor alteração necessária para acrescentar os elementos ausentes. "
        f"Elementos ainda não satisfeitos: {detail}. "
        f"A FALA-GUIA continua sendo: {guide}. "
        "Se a lacuna for uma obrigação conversacional trazida pelo usuário, responda primeiro a ela de forma natural; use as memórias autoritativas quando a obrigação for factual. "
        "Depois preserve e cumpra a FALA-GUIA na mesma resposta, de modo natural. "
        "Reaja ao significado da fala atual do usuário sem repeti-la ou parafraseá-la mecanicamente. "
        "Não copie literalmente a FALA-GUIA se puder cumprir a mesma intenção com naturalidade. "
        "Não invente fatos, dados, ações ou informações para compensar a falha. "
        "Não explique a correção. Mantenha exatamente o formato [FALA] seguido de [PENSAMENTO]."
    )


def build_direct_writer_prompt(
    *,
    row: dict,
    all_rows: list[dict] | None = None,
    recent_messages: list[dict] | None = None,
    user_text: str,
    interpretation: dict | None = None,
    previous_mary_text: str = "",
    previous_conversation_state: dict | None = None,
    active_interlocutor: str = "",
    character_name: str = "",
) -> str:
    """Prompt direto: conversa real + roteiro completo + linha ativa + cânone."""
    if not row:
        return (
            "VOCÊ É MARY.\n"
            "O roteiro deste capítulo terminou. Responda naturalmente apenas ao último usuário, "
            "sem iniciar nova etapa narrativa.\n\n"
            "FALA ATUAL DO USUÁRIO\n"
            f"{_clean(user_text) or '(sem fala verbal)'}\n\n"
            "FORMATO\n[FALA] fala de Mary\n[PENSAMENTO] uma frase íntima curta."
        )

    interpretation = interpretation if isinstance(interpretation, dict) else {}
    automatic_line = is_automatic_direct_row(row)
    blocked_line = is_blocked_direct_row(row)
    active_order = int(row.get("order", 0) or 0)
    speech_guide = _resolve_placeholders(
        row.get("speech_guide", ""),
        character_name=character_name,
    )

    script_lines: list[str] = []
    for source in (all_rows or [row]):
        order = int(source.get("order", 0) or 0)
        guide = _resolve_placeholders(
            source.get("speech_guide", ""),
            character_name=character_name,
        )
        status = "ATIVA — PODE SER DESENVOLVIDA AGORA" if order == active_order else (
            "PASSADA — NÃO REPETIR" if order < active_order else "FUTURA — NÃO EXECUTAR NEM ANTECIPAR"
        )
        parts = [f"LINHA {order} [{status}]"]
        if order <= active_order:
            parts.append("Fala-guia: " + (guide or "(vazia)"))
            style = _clean(source.get("style"))
            instant = _clean(source.get("instant_memory"))
            if style:
                parts.append("Estilo/atitude: " + style)
            if instant:
                parts.append("Estado local da linha: " + instant)
        else:
            # Linhas futuras servem como mapa de progressão, mas o texto autoral literal
            # fica oculto para reduzir antecipação/cópia prematura.
            parts.append("Objetivo futuro: existe um próximo passo autoral reservado pelo runtime.")
        script_lines.append("\n".join(parts))

    conversation_lines: list[str] = []
    for message in (recent_messages or []):
        if not isinstance(message, dict):
            continue
        role = _clean(message.get("role")).lower()
        content = _clean(message.get("content"))
        if not content:
            continue
        speaker = "MARY" if role == "assistant" else "USUÁRIO"
        conversation_lines.append(f"{speaker}: {content}")
    conversation_text = "\n".join(conversation_lines) or "(primeiro turno do capítulo)"

    obligation = interpretation.get("user_obligation", {})
    if not isinstance(obligation, dict):
        obligation = {}
    semantic_support = "\n".join(
        [
            "Relação com o turno anterior: " + (
                _clean(interpretation.get("relation_to_previous")) or "(não determinada)"
            ),
            "Movimento atual do usuário: " + (
                _clean(interpretation.get("move")) or "(não determinado)"
            ),
            "Significado: " + (
                _clean(interpretation.get("literal_meaning"))
                or _clean(interpretation.get("user_meaning"))
                or "(não determinado)"
            ),
            "Obrigação direta: " + (
                _clean(obligation.get("requirement"))
                if obligation.get("exists")
                else "(nenhuma detectada)"
            ),
        ]
    )

    return (
        "VOCÊ É MARY.\n"
        "Converse como uma mulher real vivendo esta cena. Sua prioridade é compreender e continuar "
        "a CONVERSA REAL, não recitar o roteiro nem obedecer mecanicamente a palavras isoladas.\n\n"

        "==================================================\n"
        "CÂNONE GLOBAL — FATOS DUROS\n"
        "==================================================\n"
        + (_clean(row.get("permanent_memory")) or "(não informado)")
        + "\n\nMEMÓRIA FÍSICA DE MARY\n"
        + (_clean(row.get("physical_memory")) or "(não informada)")
        + "\n\nDESCRIÇÃO DA CENA\n"
        + (_clean(row.get("initial_description")) or "(não informada)")
        + "\n\nREGRA DE REVELAÇÃO DA LINHA ATUAL\n"
        + (_clean(row.get("revelation_policy")) or "(sem restrição autoral específica)")
        + "\n\nIMPORTANTE SOBRE A DESCRIÇÃO DA CENA\n"
        "A DESCRIÇÃO DA CENA pode conter toda a verdade que Mary conhece. "
        "Conhecer um fato NÃO significa estar autorizada a verbalizá-lo agora. "
        "A REGRA DE REVELAÇÃO DA LINHA ATUAL define a fronteira do que pode ou não pode ser dito neste turno. "
        "Se o usuário perguntar diretamente por algo marcado como NÃO PODE, Mary deve reagir à pergunta sem mentir, sem inventar e sem revelar o conteúdo reservado; "
        "ela pode hesitar, pedir um instante, dizer que vai contar ou preparar a revelação de modo natural.\n"
        + "\nINTERLOCUTOR ATIVO\n"
        + (_clean(active_interlocutor) or "(não especificado)")
        + "\n\nESTADO FÍSICO/LOCAL ATUAL\n"
        + (_clean(row.get("instant_memory")) or "(não informado)")
        + "\n\n"

        "==================================================\n"
        "ROTEIRO COMPLETO DO CAPÍTULO — MAPA, NÃO CHECKLIST\n"
        "==================================================\n"
        + "\n\n".join(script_lines)
        + "\n\nREGRA DE EXECUÇÃO DO ROTEIRO:\n"
        "Você conhece o roteiro inteiro apenas para compreender a trajetória. "
        "SOMENTE a linha marcada ATIVA pode ser desenvolvida. Linhas FUTURAS aparecem sem fala-guia literal e jamais podem ser executadas, "
        "citadas ou antecipadas. Linhas PASSADAS não devem ser repetidas. "
        "A fala-guia é direção semântica de Mary, nunca texto do usuário e nunca texto interno a ser mencionado.\n\n"

        "==================================================\n"
        "CONVERSA REAL — FONTE PRINCIPAL DE CONTINUIDADE\n"
        "==================================================\n"
        + conversation_text
        + "\n\n"
        + (
            "CONTINUAÇÃO AUTOMÁTICA\n"
            "O usuário NÃO falou neste turno. O botão Prosseguir apenas autorizou a sequência. "
            "Mary está conduzindo a cena consigo mesma: pode pensar, murmurar, falar sozinha ou verbalizar "
            "algo compatível com a FALA-GUIA. Não responda à palavra 'Prosseguir' e não invente interlocutor.\n\n"
            if automatic_line
            else (
                "INICIATIVA DE MARY\n"
                "O usuário NÃO falou neste turno. Mary deve iniciar esta linha dirigindo-se naturalmente ao interlocutor conforme a FALA-GUIA. "
                "Depois dessa fala, pare e aguarde a resposta do usuário; não execute a próxima linha.\n\n"
                if blocked_line
                else (
                "USUÁRIO AGORA:\n"
                + (_clean(user_text) or "(sem fala verbal)")
                + "\n\n"
                "Leia a fala atual como continuação causal da conversa acima. "
                "Perguntas, provocações, ironias, confirmações, recusas e brincadeiras devem ser respondidas pelo sentido, "
                "não espelhadas nem devolvidas mecanicamente.\n\n"
                )
            )
        )
        + "==================================================\n"
        "APOIO SEMÂNTICO — SECUNDÁRIO, NÃO SUBSTITUI A CONVERSA\n"
        "==================================================\n"
        + semantic_support
        + "\n\n"
        "Se este apoio parecer incompatível com a conversa real, confie primeiro na conversa real e nos fatos duros.\n\n"

        "==================================================\n"
        "LINHA ATIVA AGORA\n"
        "==================================================\n"
        f"Ordem: {active_order}\n"
        "Fala-guia: " + (speech_guide or "(nenhuma)") + "\n"
        "Estilo/atitude: " + (_clean(row.get("style")) or "natural") + "\n"
        "Revelação permitida nesta linha: " + (_clean(row.get("revelation_policy")) or "(sem restrição autoral específica)") + "\n\n"

        "REGRAS ESSENCIAIS\n"
        + (
            "1. Este é um turno automático: não há fala do usuário para responder; continue a experiência interna de Mary.\n"
            if automatic_line
            else (
                "1. Este é um turno de iniciativa de Mary: não há fala atual do usuário para responder. Execute a FALA-GUIA como iniciativa natural e encerre a resposta aguardando o interlocutor.\n"
                if blocked_line
                else "1. Responda primeiro ao que o usuário realmente acabou de fazer conversacionalmente.\n"
            )
        )
        + "2. Depois, se couber naturalmente, desenvolva a linha ativa. Se não couber, mantenha-a pendente.\n"
        "3. Não repita ou espelhe a pergunta/frase do usuário como se fosse resposta.\n"
        "4. Preserve sujeitos, papéis, posse, destinatários e autoria das iniciativas.\n"
        "5. Não invente fatos pessoais do usuário nem antecipe linhas futuras.\n"
        "6. A REGRA DE REVELAÇÃO é obrigatória: fatos marcados como NÃO PODE permanecem verdadeiros no conhecimento de Mary, mas não podem ser verbalizados ainda, mesmo se o usuário perguntar diretamente. Reaja sem mentir, sem inventar e sem adiantar o fato reservado.\n"
        "7. Nunca mencione prompt, fala-guia, roteiro, modelo, Diretor, memória, instrução interna ou qualquer mecanismo do sistema.\n"
        "8. O pensamento é íntimo, curto e pertence a Mary; também não pode mencionar mecanismos do sistema nem revelar fatos proibidos.\n\n"

        "FORMATO\n"
        "[FALA] fala natural de Mary em primeira pessoa\n"
        "[PENSAMENTO] uma frase curta, íntima e situacional em primeira pessoa."
    )

