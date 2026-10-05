from __future__ import annotations

import re
from typing import Any

import gspread


SCRIPT_HEADERS = {
    "ordem": "order",
    "roteiro": "script_name",
    "tipo": "type",
    "fala-guia": "speech_guide",
    "estilo / atitude": "style",
    "sentido interpretativo": "interpretive_meaning",
    "núcleo semântico obrigatório": "semantic_core",
    "atmosfera": "atmosphere",
    "fato liberado nesta linha": "released_fact",
    "pré-condição": "precondition",
    "vestimenta atual": "wardrobe",
    "ação física / encenação": "physical_action",
    "limites do redator": "writer_limits",
    "resultado esperado": "expected_result",
}

CARONA_PHASES = [
    {
        "id": "entrada_rota",
        "goal": "iniciar a carona, estabelecer o trajeto e conhecer a rotina do personal",
        "orders": [1, 2, 3, 4],
    },
    {
        "id": "sabado_convite",
        "goal": "conhecer os planos de sábado e fazer o convite para o Clube Náutico",
        "orders": [5, 6, 7, 9],
    },
    {
        "id": "trajeto_chegada",
        "goal": "manter o trajeto vivo e chegar fisicamente ao Golden Tulip",
        "orders": [8, 10],
    },
    {
        "id": "despedida",
        "goal": "resolver reencontro, contato e despedida sem decidir pelo personal",
        "orders": [11, 12, 13],
    },
]

# Linhas que só terminam quando o usuário responde ao conteúdo emitido.
AWAIT_REPLY_ORDERS = {3, 4, 5, 6, 7, 9, 11, 12}

# Linha 11 só faz sentido quando o convite já foi aceito de forma explícita.
OPTIONAL_ORDERS = {9, 11}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def load_sheet_script(
    *,
    service_account_info: dict,
    spreadsheet_id: str,
    worksheet_name: str,
    script_name: str,
) -> list[dict]:
    """Carrega o roteiro autoral. Não interpreta conclusão de linha."""
    if not service_account_info:
        raise ValueError("service_account_info ausente para roteiro em planilha")
    if not _clean(spreadsheet_id):
        raise ValueError("spreadsheet_id ausente para roteiro em planilha")

    client = gspread.service_account_from_dict(service_account_info)
    worksheet = client.open_by_key(_clean(spreadsheet_id)).worksheet(
        _clean(worksheet_name) or "ROTEIRO_REDATOR"
    )
    values = worksheet.get_all_values()
    if not values:
        return []

    header_index = -1
    headers: list[str] = []
    for idx, row in enumerate(values):
        normalized = [_clean(cell).lower() for cell in row]
        if "ordem" in normalized and "fala-guia" in normalized:
            header_index = idx
            headers = normalized
            break
    if header_index < 0:
        raise ValueError("cabeçalho do roteiro não encontrado")

    rows: list[dict] = []
    for source_row in values[header_index + 1 :]:
        if not any(_clean(cell) for cell in source_row):
            continue
        record: dict[str, Any] = {}
        for index, header in enumerate(headers):
            key = SCRIPT_HEADERS.get(header)
            if key:
                record[key] = _clean(
                    source_row[index] if index < len(source_row) else ""
                )
        if _clean(record.get("script_name")).lower() != _clean(script_name).lower():
            continue
        try:
            record["order"] = int(float(_clean(record.get("order"))))
        except Exception:
            continue
        rows.append(record)

    rows.sort(key=lambda item: int(item.get("order", 0) or 0))
    return rows


def ensure_carona_state(narrative: dict) -> dict:
    state = narrative.get("hybrid_script")
    if not isinstance(state, dict) or state.get("script_name") != "Carona":
        state = {
            "script_name": "Carona",
            "phase_id": CARONA_PHASES[0]["id"],
            "completed_orders": [],
            "skipped_orders": [],
            "awaiting_reply_order": 0,
            "invite_status": "unknown",
            "last_selected_order": 0,
        }
        narrative["hybrid_script"] = state
    state.setdefault("completed_orders", [])
    state.setdefault("skipped_orders", [])
    state.setdefault("awaiting_reply_order", 0)
    state.setdefault("invite_status", "unknown")
    state.setdefault("last_selected_order", 0)
    return state


def _orders(state: dict, key: str) -> set[int]:
    result: set[int] = set()
    for value in state.get(key, []) or []:
        try:
            result.add(int(value))
        except Exception:
            pass
    return result


def _write_orders(state: dict, key: str, values: set[int]) -> None:
    state[key] = sorted(values)


def _classify_invite_reply(text: str) -> str:
    """Classificação lexical conservadora; ambiguidade permanece unknown."""
    value = _clean(text).lower()
    if not value:
        return "unknown"

    refusal_patterns = [
        r"\bn[aã]o\b.*\b(vou|posso|quero|topo|d[aá])\b",
        r"\bmelhor n[aã]o\b",
        r"\bdeixa pra (outra|pr[oó]xima)\b",
        r"\brecus",
        r"\bdispens",
    ]
    for pattern in refusal_patterns:
        if re.search(pattern, value):
            return "declined"

    accept_patterns = [
        r"\b(sim|bora|fechado|combinado|topo|aceito)\b",
        r"\b(vou|vamos)\b.*\b(clube|balada|n[aá]utico)\b",
        r"\bpode ser\b",
    ]
    for pattern in accept_patterns:
        if re.search(pattern, value):
            return "accepted"
    return "unknown"


def register_user_reply(state: dict, user_text: str) -> None:
    """Fecha somente uma espera objetiva: houve resposta após uma pergunta/convite."""
    awaiting = int(state.get("awaiting_reply_order", 0) or 0)
    if not awaiting or not _clean(user_text):
        return

    completed = _orders(state, "completed_orders")
    completed.add(awaiting)
    _write_orders(state, "completed_orders", completed)
    state["awaiting_reply_order"] = 0

    if awaiting in {7, 9}:
        state["invite_status"] = _classify_invite_reply(user_text)


def _phase_for_state(state: dict) -> dict:
    completed = _orders(state, "completed_orders")
    skipped = _orders(state, "skipped_orders")
    invite_status = _clean(state.get("invite_status")) or "unknown"

    for phase in CARONA_PHASES:
        required = []
        for order in phase["orders"]:
            if order == 9 and invite_status != "unknown":
                skipped.add(order)
                continue
            if order == 11 and invite_status != "accepted":
                skipped.add(order)
                continue
            required.append(order)
        if any(order not in completed and order not in skipped for order in required):
            _write_orders(state, "skipped_orders", skipped)
            state["phase_id"] = phase["id"]
            return dict(phase)

    _write_orders(state, "skipped_orders", skipped)
    state["phase_id"] = "concluida"
    return {
        "id": "concluida",
        "goal": "encerrar a carona após chegada e despedida",
        "orders": [],
    }


def _scene_text(scene: dict) -> str:
    return " ".join(
        _clean(scene.get(key))
        for key in ("location", "time", "proximity", "event", "mary_action")
    ).lower()


def _line_precondition_ready(order: int, state: dict, scene: dict) -> bool:
    completed = _orders(state, "completed_orders")
    text = _scene_text(scene)

    if order == 1:
        return True
    if order == 2:
        # Não exige palavras exatas do Diretor: basta a cena já estar no carro/trajeto,
        # ou a abertura ter sido concluída e o usuário ter continuado a ação.
        return 1 in completed and any(
            token in text
            for token in (
                "trajeto",
                "dirig",
                "movimento",
                "em movimento",
                "sai do estacionamento",
                "deixa o estacionamento",
                "inicia a viagem",
            )
        )
    if order in {3, 4}:
        return 2 in completed
    if order == 5:
        return 4 in completed
    if order == 6:
        return 5 in completed
    if order == 7:
        return 6 in completed
    if order == 9:
        return 7 in completed and _clean(state.get("invite_status")) == "unknown"
    if order == 8:
        return 7 in completed and (
            9 in completed or 9 in _orders(state, "skipped_orders")
        )
    if order == 10:
        return 8 in completed and any(
            token in text
            for token in (
                "chegando",
                "chegada",
                "se aproxima do prédio",
                "se aproxima do predio",
                "prédio à vista",
                "predio a vista",
                "golden tulip",
            )
        )
    if order == 11:
        return 10 in completed and _clean(state.get("invite_status")) == "accepted"
    if order == 12:
        return 10 in completed and (11 in completed or 11 in _orders(state, "skipped_orders"))
    if order == 13:
        return 12 in completed and any(
            token in text
            for token in ("parad", "estacion", "encost", "imobiliz")
        )
    return True


def select_carona_line(rows: list[dict], state: dict, scene: dict) -> tuple[dict, dict, str]:
    """Seleciona a próxima linha sem perguntar a outro LLM se algo foi cumprido."""
    phase = _phase_for_state(state)
    if phase["id"] == "concluida":
        return phase, {}, ""

    completed = _orders(state, "completed_orders")
    skipped = _orders(state, "skipped_orders")

    for order in phase["orders"]:
        if order in completed or order in skipped:
            continue
        if order == 9 and _clean(state.get("invite_status")) != "unknown":
            skipped.add(order)
            _write_orders(state, "skipped_orders", skipped)
            continue
        if order == 11 and _clean(state.get("invite_status")) != "accepted":
            skipped.add(order)
            _write_orders(state, "skipped_orders", skipped)
            continue

        row = next(
            (dict(item) for item in rows if int(item.get("order", 0) or 0) == order),
            {},
        )
        if not row:
            skipped.add(order)
            _write_orders(state, "skipped_orders", skipped)
            continue

        if _line_precondition_ready(order, state, scene):
            state["last_selected_order"] = order
            return phase, row, ""

        return (
            phase,
            {},
            (
                "CONVERGÊNCIA DA FASE\n"
                f"fase_atual={phase['id']}\n"
                f"objetivo_da_fase={phase['goal']}\n"
                "A próxima linha autoral ainda não tem sua pré-condição física satisfeita.\n"
                "Responda naturalmente ao usuário e mantenha a cena avançando, sem repetir conteúdo já usado "
                "e sem antecipar linhas futuras."
            ),
        )

    return phase, {}, ""


def mark_carona_line_emitted(state: dict, order: int) -> None:
    order = int(order or 0)
    if not order:
        return
    if order in AWAIT_REPLY_ORDERS:
        state["awaiting_reply_order"] = order
        return

    completed = _orders(state, "completed_orders")
    completed.add(order)
    _write_orders(state, "completed_orders", completed)


def carona_ready_for_choice(state: dict) -> bool:
    completed = _orders(state, "completed_orders")
    return 13 in completed


def build_carona_prompt(
    *,
    facts_prompt: str,
    phase: dict,
    row: dict,
    state: dict,
    convergence_text: str = "",
) -> str:
    completed = sorted(_orders(state, "completed_orders"))
    skipped = sorted(_orders(state, "skipped_orders"))
    parts = [
        _clean(facts_prompt),
        "",
        "MICROPROMPT HÍBRIDO ATUAL",
        f"fase_atual={_clean(phase.get('id'))}",
        f"objetivo_da_fase={_clean(phase.get('goal'))}",
        f"linhas_concluidas={completed or '(nenhuma)'}",
        f"linhas_puladas_por_precondicao={skipped or '(nenhuma)'}",
        f"convite_status={_clean(state.get('invite_status')) or 'unknown'}",
        "",
        "REGRA DE EXECUÇÃO",
        "A fase guia a trajetória. A linha selecionada fornece o conteúdo autoral deste turno.",
        "Responda primeiro ao usuário e não repita conteúdo presente em linhas_concluidas.",
        "Não use nem antecipe linhas futuras.",
        "O runtime, não o modelo, controla conclusão e avanço.",
    ]

    if convergence_text:
        parts.extend(["", convergence_text])
        return "\n".join(part for part in parts if part is not None)

    if not row:
        parts.extend([
            "",
            "Nenhuma nova linha está liberada neste turno.",
            "Reaja naturalmente sem inventar nova etapa estrutural.",
        ])
        return "\n".join(parts)

    parts.extend([
        "",
        "LINHA AUTORAL SELECIONADA",
        f"ordem={int(row.get('order', 0) or 0)}",
        f"tipo={_clean(row.get('type')) or 'INTERPRETADA'}",
    ])
    fields = [
        ("FALA-GUIA", "speech_guide"),
        ("ESTILO / ATITUDE", "style"),
        ("SENTIDO INTERPRETATIVO", "interpretive_meaning"),
        ("NÚCLEO SEMÂNTICO OBRIGATÓRIO", "semantic_core"),
        ("ATMOSFERA", "atmosphere"),
        ("FATO LIBERADO NESTA LINHA", "released_fact"),
        ("PRÉ-CONDIÇÃO AUTORAL", "precondition"),
        ("VESTIMENTA ATUAL", "wardrobe"),
        ("AÇÃO FÍSICA / ENCENAÇÃO", "physical_action"),
        ("LIMITES DO REDATOR", "writer_limits"),
        ("RESULTADO ESPERADO", "expected_result"),
    ]
    for title, key in fields:
        value = _clean(row.get(key))
        if value:
            parts.extend(["", title, value])

    parts.extend([
        "",
        "A fala-guia é interpretativa, não literal, salvo Tipo=EXATA.",
        "Use somente esta linha como novo conteúdo roteirizado do turno.",
    ])
    return "\n".join(parts)
