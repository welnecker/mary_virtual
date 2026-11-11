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
    "descrição-guia": "action_guide",
    "descricao-guia": "action_guide",
    "pensamento-guia": "thought_guide",
    "onomatopeia": "onomatopoeia",
    "onomatopéia": "onomatopoeia",
    "modo": "interaction_mode",
    "modo de interação": "interaction_mode",
    "modo de interacao": "interaction_mode",
    "interação": "interaction_mode",
    "interacao": "interaction_mode",
    "prosseguir": "interaction_mode",
    "revelacao": "revelation_policy",
    "revelação": "revelation_policy",
    "estilo / atitude": "style",
    "orgulho ferido": "hurt_style",
    "prompt negativo": "negative_prompt",
    "direção dos interlocutores": "interlocutor_direction",
    "direcao dos interlocutores": "interlocutor_direction",
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


def hurt_loop_max_interactions(loop_row: dict | None) -> int:
    """Lê o limite autoral da linha LOOP; três é fallback legado.

    Aceita LIMITE_INTERACOES=4 ou descrições como 'após três tentativas'.
    O número limita turnos sem reconciliação, não exige pedido de desculpas.
    """
    text = _clean((loop_row or {}).get("speech_guide"))
    explicit = re.search(r"\bLIMITE[_ ]INTERACOES\s*[:=]\s*(\d+)\b", text, flags=re.I)
    if explicit:
        return max(1, min(20, int(explicit.group(1))))
    natural = re.search(
        r"\b(?:ap[oó]s|depois\s+de|at[eé])\s+"
        r"(um|uma|dois|duas|tr[eê]s|quatro|cinco|seis|sete|oito|nove|dez|\d+)\s+"
        r"(?:intera[çc][õo]es|tentativas|turnos)\b",
        text, flags=re.I,
    )
    if natural:
        names = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3,
                 "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7,
                 "oito": 8, "nove": 9, "dez": 10}
        word = natural.group(1).casefold()
        return max(1, min(20, names.get(word, int(word) if word.isdigit() else 3)))
    return 3


def is_direct_thought_disabled(row: dict | None) -> bool:
    """A célula 'Sem pensamento' desativa o canal de pensamento nesta linha."""
    return (
        isinstance(row, dict)
        and _clean(row.get("thought_guide")).casefold() == "sem pensamento"
    )


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

    # Nenhum personagem é imposto pelo número do capítulo.
    # A identidade concreta do interlocutor vem da cena autoral.
    user_role = "PERSONAGEM_DA_CENA"
    temporary_active = True
    present = ["MARY", "PERSONAGEM_DA_CENA"]

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
                "name": "Personagem da cena",
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



def load_direct_info_board(
    *,
    service_account_info: dict,
    spreadsheet_id: str,
    script_name: str,
) -> str:
    """Quadro exclusivamente visual para o jogador; nunca integra prompts."""
    if not service_account_info or not _clean(spreadsheet_id) or not _clean(script_name):
        return ""
    client = gspread.service_account_from_dict(service_account_info)
    worksheet = client.open_by_key(_clean(spreadsheet_id)).worksheet("QUADROS_INFORMATIVOS")
    values = worksheet.get_all_values()
    if not values:
        return ""
    headers = [_clean(x).casefold() for x in values[0]]
    if "roteiro" not in headers or "quadro inicial" not in headers:
        raise ValueError("QUADROS_INFORMATIVOS precisa das colunas ROTEIRO e QUADRO INICIAL")
    script_col, board_col = headers.index("roteiro"), headers.index("quadro inicial")
    for cells in values[1:]:
        if script_col < len(cells) and _clean(cells[script_col]).casefold() == _clean(script_name).casefold():
            return _clean(cells[board_col]) if board_col < len(cells) else ""
    return ""


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
    emotional_loop_row: dict = {}
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
        if _clean(record.get("order")).casefold() == "loop":
            if _clean(record.get("speech_guide")):
                record["order"] = 0
                record["line_id"] = "loop_orgulho_ferido"
                emotional_loop_row = record
            continue  # A linha especial nunca pertence à progressão sequencial.
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
    # Apenas a PRIMEIRA linha pode oferecer um padrão geral do capítulo.
    # A primeira orientação encontrada em uma linha posterior é local e não
    # pode contaminar linhas anteriores nem outros momentos do roteiro.
    hurt_style_global = _clean(rows[0].get("hurt_style")) if rows else ""
    negative_prompt_global = _clean(rows[0].get("negative_prompt")) if rows else ""
    for item in rows:
        item["permanent_memory"] = permanent_memory_global
        item["physical_memory"] = physical_memory_global
        # A orientação específica da linha prevalece; a primeira instrução
        # disponível no capítulo é apenas fallback para linhas não preenchidas.
        # Isso permite que a mesma personagem seja contrariada por causas
        # diferentes conforme a missão atual.
        item["hurt_style"] = _clean(item.get("hurt_style")) or hurt_style_global
        item["negative_prompt"] = _clean(item.get("negative_prompt")) or negative_prompt_global
        if emotional_loop_row:
            item["_emotional_loop_row"] = dict(emotional_loop_row)

    return rows


def ensure_direct_state(narrative: dict, rows: list[dict]) -> dict:
    state = narrative.get("direct_script")
    if not isinstance(state, dict) or state.get("engine") != "direct_sheet_v1":
        state = {
            "engine": "direct_sheet_v1",
            "index": 0,
            "current_order": int(rows[0].get("order", 0) or 0) if rows else 0,
            "awaiting_reply_order": 0,
            "automatic_emitted_order": 0,
            "completed_orders": [],
            "line_dialogue": [],
            "completed": not bool(rows),
        }
        narrative["direct_script"] = state

    if not isinstance(state.get("completed_orders"), list):
        state["completed_orders"] = []
    if not isinstance(state.get("line_dialogue"), list):
        state["line_dialogue"] = []
    state["automatic_emitted_order"] = max(
        0, int(state.get("automatic_emitted_order", 0) or 0)
    )

    completed = sorted({
        int(value)
        for value in state.get("completed_orders", [])
        if str(value).strip()
    })
    state["completed_orders"] = completed

    index = max(0, int(state.get("index", 0) or 0))
    awaiting_order = int(state.get("awaiting_reply_order", 0) or 0)
    current_order = int(state.get("current_order", 0) or 0)
    # A inserção de uma linha desloca índices antigos. Reancore pelo número
    # de ORDEM da linha ativa antes de consultar a posição armazenada.
    anchor_order = awaiting_order or current_order
    if anchor_order and anchor_order not in completed:
        index = next(
            (
                idx for idx, item in enumerate(rows)
                if int(item.get("order", 0) or 0) == anchor_order
            ),
            index,
        )
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
    scene_direction: str = "",
) -> dict:
    """Uma fala ou encenação nova do usuário encerra a linha emitida por Mary."""
    before = deepcopy(state)
    awaiting = int(state.get("awaiting_reply_order", 0) or 0)
    if awaiting and (_clean(user_text) or _clean(scene_direction)):
        completed = {
            int(value)
            for value in (state.get("completed_orders", []) or [])
            if str(value).strip()
        }
        completed.add(awaiting)
        state["completed_orders"] = sorted(completed)
        state["awaiting_reply_order"] = 0
        state["line_dialogue"] = []
        # O índice persistido pode estar defasado após inserções de linhas
        # na planilha. Avance pela ORDEM concluída, nunca por index + 1.
        state["index"] = next(
            (
                idx for idx, item in enumerate(rows)
                if int(item.get("order", 0) or 0) > awaiting
                and int(item.get("order", 0) or 0) not in completed
            ),
            len(rows),
        )
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
        # A resposta pertence à própria linha automática. Ela só será
        # consumida quando o jogador clicar Prosseguir depois de vê-la.
        # Não emita outra resposta nem crie turno intermediário nesse clique.
        state["automatic_emitted_order"] = order
        state["awaiting_reply_order"] = 0
        state["current_order"] = order
        state["completed"] = False
        state["line_dialogue"] = []
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


def advance_emitted_automatic_line(
    state: dict, rows: list[dict]
) -> bool:
    """Prosseguir depois da resposta automática só move o cursor; não gera turno."""
    order = int(state.get("automatic_emitted_order", 0) or 0)
    if not order or not rows:
        return False

    index = next(
        (idx for idx, item in enumerate(rows)
         if int(item.get("order", 0) or 0) == order),
        None,
    )
    if index is None:
        raise RuntimeError(
            f"Linha automática {order} não encontrada na versão atual do roteiro."
        )
    completed = {
        int(value) for value in (state.get("completed_orders", []) or [])
        if str(value).strip()
    }
    completed.add(order)
    state["completed_orders"] = sorted(completed)
    state["automatic_emitted_order"] = 0
    state["awaiting_reply_order"] = 0
    state["line_dialogue"] = []
    state["index"] = next(
        (idx for idx, item in enumerate(rows)
         if int(item.get("order", 0) or 0) > order
         and int(item.get("order", 0) or 0) not in completed),
        len(rows),
    )
    state["completed"] = state["index"] >= len(rows)
    state["current_order"] = (
        int(rows[state["index"]].get("order", 0) or 0)
        if not state["completed"] else 0
    )
    return True


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




# Marcações sonoras inline usam §SOM§ no próprio texto da FALA-GUIA.
# O detector não interpreta parênteses nem altera o texto autoral.
_INLINE_SOUND_RE = re.compile(r"§([^§\r\n]{1,80})§")


def inline_sounds_from_guide(speech_guide: str) -> list[str]:
    """Retorna sons na ordem autoral, sem o delimitador e sem duplicatas."""
    found: list[str] = []
    for match in _INLINE_SOUND_RE.finditer(str(speech_guide or "")):
        sound = match.group(1).strip()
        if sound and sound.casefold() not in {item.casefold() for item in found}:
            found.append(sound)
    return found


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
        "Preserve obrigações IMEDIATAS explícitas da FALA-GUIA, mas nunca insira uma pergunta, uma história ou fala de personagem secundário apenas para cumprir uma sugestão opcional. "
        "Reaja ao significado da fala atual do usuário sem repeti-la ou parafraseá-la mecanicamente. "
        "Não copie literalmente a FALA-GUIA se puder cumprir a mesma intenção com naturalidade. "
        "Não invente fatos, dados, ações ou informações para compensar a falha. "
        "Não explique a correção. Preserve os canais que já estão coerentes. "
        "[PENSAMENTO] é opcional e pode expressar emoções, dúvidas ou conflitos internos sem gerar ação ou fala; "
        "não o acrescente apenas para completar o formato."
    )


def build_direct_writer_prompt(
    *,
    row: dict,
    all_rows: list[dict] | None = None,
    recent_messages: list[dict] | None = None,
    user_text: str,
    user_scene_direction: str = "",
    interpretation: dict | None = None,
    previous_mary_text: str = "",
    previous_conversation_state: dict | None = None,
    active_interlocutor: str = "",
    character_name: str = "",
    handoff_text: str = "",
) -> str:
    """Prompt direto: conversa real + roteiro completo + linha ativa + cânone."""
    if not row:
        return (
            "VOCÊ É MARY.\n"
            "O roteiro deste capítulo terminou. Responda naturalmente apenas ao último usuário, "
            "sem iniciar nova etapa narrativa.\n\n"
            "FALA ATUAL DO USUÁRIO\n"
            f"{_clean(user_text) or '(sem fala verbal)'}\n\n"
            "FORMATO PADRÃO\n[FALA] fala de Mary. Outros canais somente se necessários."
        )

    interpretation = interpretation if isinstance(interpretation, dict) else {}
    automatic_line = is_automatic_direct_row(row)
    blocked_line = is_blocked_direct_row(row)
    active_order = int(row.get("order", 0) or 0)
    speech_guide = _resolve_placeholders(
        row.get("speech_guide", ""),
        character_name=character_name,
    )
    interpret_match = re.fullmatch(r"interpretar(?:\s*:\s*(.*))?", speech_guide.strip(), flags=re.I | re.S)
    interpret_mode = bool(interpret_match)
    interpret_direction = (interpret_match.group(1) or "").strip() if interpret_match else ""
    action_guide = _clean(row.get("action_guide"))
    thought_disabled = is_direct_thought_disabled(row)
    thought_guide = "" if thought_disabled else _clean(row.get("thought_guide"))
    inline_sounds = inline_sounds_from_guide(speech_guide)
    # A nova marcação na FALA-GUIA prevalece; a coluna legada é usada
    # apenas quando esta linha não define sons inline.
    onomatopoeia = "" if inline_sounds else _clean(row.get("onomatopoeia"))

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
        "CONVERSA REAL — FONTE PRINCIPAL DE CONTINUIDADE\n"
        "==================================================\n"
        + conversation_text
        + "\n\n"
        + (
            "TRANSIÇÃO DO CAPÍTULO ANTERIOR — CONTEXTO, NÃO NOVA MISSÃO\n"
            + _clean(handoff_text)
            + "\nUse apenas para continuar os fatos e responder à última fala quando pertinente. "
            "A transição não é uma nova intervenção do usuário, não exige repetir falas "
            "nem autoriza antecipar ações. A linha ativa e a conversa atual determinam "
            "o que fazer; prevalecem fatos confirmados e limites de REVELACAO.\n\n"
            if _clean(handoff_text) and _clean(handoff_text) != "(nenhum)"
            else ""
        )
        + (
            "CONTINUAÇÃO AUTOMÁTICA\n"
            "O usuário NÃO falou neste turno. O botão Prosseguir apenas autorizou a sequência. "
            "Esta linha é conduzida pelo roteiro sem nova fala do usuário. Mary realiza as "
            "ações da DESCRIÇÃO-GUIA e a direção da FALA-GUIA, com PENSAMENTO-GUIA "
            "e ESTILO/ATITUDE definidos pela planilha. Pode conversar e atuar com outros "
            "personagens presentes, conforme a missão da linha, sem esperar resposta "
            "do usuário nem inventar falas dele. 'Prosseguir' é somente um controle. "
            "Quando a missão terminar em pedido ou pergunta a outro personagem, encerre "
            "a resposta com essa iniciativa já verbalizada e deixe a reação do destinatário "
            "para a próxima linha; não encene a resposta dele neste turno. "
            "Não execute acontecimentos de linhas futuras.\n\n"
            if automatic_line
            else (
                "INICIATIVA DE MARY\n"
                "O usuário NÃO falou neste turno. Mary deve iniciar esta linha dirigindo-se naturalmente ao interlocutor conforme a FALA-GUIA. "
                "Depois dessa fala, pare e aguarde a resposta do usuário; não execute a próxima linha.\n\n"
                if blocked_line
                else (
                "DIREÇÃO/ENCENAÇÃO ATUAL DO USUÁRIO:\n"
                + (_clean(user_scene_direction) or "(nenhuma)")
                + "\n\nFALA VERBAL ATUAL DO USUÁRIO:\n"
                + (_clean(user_text) or "(sem fala verbal)")
                + "\n\n"
                "Leia a entrada atual como continuação causal da conversa acima. Preserve a diferença entre encenação e fala, mas use ambas para compreender o sentido completo do turno. "
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
        "Fala-guia: " + ("Interpretar (modo técnico)" if interpret_mode else (speech_guide or "(nenhuma)")) + "\n"
        + "EXECUÇÃO DA LINHA: cumpra obrigações explícitas; 'pode' e 'se fizer sentido' não impõem ações. "
        "Personagens secundários podem participar quando a cena pedir, sem falar pelo usuário nem competir com a resposta dele.\n"

        + ("Direção autoral desta linha: " + interpret_direction + "\n" if interpret_direction else "")
        + (
            "SONS AUTORAIS INLINE — prioridade da FALA-GUIA: "
            + ", ".join(inline_sounds) + "\n"
            "Trechos delimitados por § são sons, não falas para copiar como instruções. "
            "Ao executar o acontecimento correspondente, reproduza exatamente o som escrito "
            "dentro de §, sem os símbolos §, na mesma sequência e junto ao evento que o produz. "
            "Não os mova para o fim, não os repita, não invente sons adicionais nem os "
            "atribua a outro personagem. Não transforme o som isolado em [AÇÃO]; "
            "quando for vocalização, apresente-o no canal [FALA] pertinente. "
            "Se a ação for condicional e não acontecer, não force sua execução só para produzir o som.\n"
            if inline_sounds else ""
        )
        + ("Descrição-guia: " + action_guide + "\n" if action_guide else "")
        + ("Pensamento-guia: SEM PENSAMENTO — não gere [PENSAMENTO] nesta linha.\n"
           if thought_disabled else ("Pensamento-guia: " + thought_guide + "\n" if thought_guide else ""))
        + (
            "Onomatopeia contextual: " + onomatopoeia + "\n"
            "Cada som pertence ao gesto ou à reação que o produz. Respeite primeiro "
            "o POSICIONAMENTO e o CANAL indicados na própria coluna ONOMATOPEIA; "
            "se indicar [FALA], coloque o som na fala do personagem pertinente, "
            "imediatamente depois da fala ou do evento indicado, e NÃO o migre para [AÇÃO]. "
            "Se não indicar canal, use o que melhor preserve a sequência da cena. "
            "Não atribua um som a quem só observa, não use colchetes decorativos "
            "nem liste sons no fim do turno. Não repita a ação apenas para inserir "
            "o som nem invente uma reação do interlocutor.\n"
            if onomatopoeia else ""
        )
        + "Estilo/atitude: " + (_clean(row.get("style")) or "natural") + "\n"
        "Revelação permitida nesta linha: " + (_clean(row.get("revelation_policy")) or "(sem restrição autoral específica)") + "\n\n"

        "CONTINUIDADE E AUTORIA: responda à entrada real; a linha ativa determina a missão "
        "e os três guias determinam cada canal. A memória preserva fatos, não cria tarefas. "
        "Não antecipe linhas, ultrapasse REVELACAO ou decida por personagens do usuário. "
        "Em linha automática, avance sem inventar fala do usuário; em linha bloqueada, Mary toma a iniciativa.\n\n"
        "CANAIS: [FALA] contém diálogo; identifique cada personagem que fale (Mary:, Silvia: etc.). "
        "[AÇÃO] é registro breve, não narração integral da cena: execute somente gestos da DESCRIÇÃO-GUIA "
        "e o mínimo necessário para concretizar ações assumidas na FALA-GUIA ou ONOMATOPEIA. "
        "Evite microgestos, adjetivos de clima, sensações, explicações e ações futuras. "
        "Não descreva antes o que será decidido ou dito em [FALA]. "
        + ("Nesta linha [PENSAMENTO] está DESATIVADO; emita somente os canais aplicáveis. "
           if thought_disabled else
           "[PENSAMENTO] é opcional, em primeira pessoa, orientado pelo PENSAMENTO-GUIA; "
           "pode conter emoções, dúvidas, memórias e conflitos sem produzir ação ou fala. ")
        + ("" if thought_disabled else
           "Quando apresentado no início da resposta, retrata o instante ANTES das falas e ações novas "
           "deste turno: não narre como já ocorrida a reação posterior de Silvia, uma decisão ainda "
           "não tomada ou acontecimentos que só serão revelados ao longo desta mesma resposta. ")
        + "Não misture os canais. Repita [FALA] ou [AÇÃO] sempre que alternar entre eles; "
        "não escreva fala de personagem dentro de [AÇÃO]."
    )

