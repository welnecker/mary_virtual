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
    "atmosfera": "atmosphere",
    "fato liberado nesta linha": "released_fact",
    "pré-condição": "precondition",
    "vestimenta atual": "wardrobe",
    "ação física / encenação": "physical_action",
    "limites do redator": "writer_limits",
}

CARONA_PHASES = [
    {
        "id": "entrada_rota",
        "goal": "saída e início do trajeto",
        "orders": [1, 2, 3, 4],
    },
    {
        "id": "sabado_convite",
        "goal": "sábado e convite",
        "orders": [5, 6, 7, 8],
    },
    {
        "id": "trajeto_chegada",
        "goal": "trajeto e chegada",
        "orders": [10],
    },
    {
        "id": "despedida",
        "goal": "fechamento emocional, contato e despedida",
        "orders": [11, 12, 13],
    },
]



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
            "breath_pending": False,
            "breath_after_order": 0,
            "last_selected_order": 0,
        }
        narrative["hybrid_script"] = state
    state.setdefault("completed_orders", [])
    state.setdefault("skipped_orders", [])
    state.setdefault("awaiting_reply_order", 0)
    state.setdefault("breath_pending", False)
    state.setdefault("breath_after_order", 0)
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


def register_user_reply(state: dict, user_text: str) -> None:
    """Fecha a linha emitida e agenda exatamente um respiro antes da próxima linha."""
    awaiting = int(state.get("awaiting_reply_order", 0) or 0)
    if not awaiting or not _clean(user_text):
        return

    completed = _orders(state, "completed_orders")
    completed.add(awaiting)
    _write_orders(state, "completed_orders", completed)
    state["awaiting_reply_order"] = 0
    state["breath_pending"] = True
    state["breath_after_order"] = awaiting


def _breath_prompt(state: dict, next_row: dict | None = None) -> str:
    after_order = int(state.get("breath_after_order", 0) or 0)
    next_row = dict(next_row or {})
    next_order = int(next_row.get("order", 0) or 0)
    next_guide = _clean(next_row.get("speech_guide", ""))

    reserved = ""
    if next_order and next_guide:
        reserved = (
            "\n\nPRÓXIMA LINHA RESERVADA — SOMENTE PARA BLOQUEIO\n"
            f"ordem={next_order}\n"
            f"conteudo={next_guide}\n"
            "Você recebeu esta linha apenas para reconhecer o território reservado do próximo turno.\n"
            "NÃO execute, parafraseie, prepare, sugira, insinue nem antecipe qualquer parte dela neste respiro.\n"
            "Não use esta linha para criar ponte, pergunta, convite, assunto ou expectativa.\n"
            "A reação deste respiro deve terminar antes de tocar semanticamente nessa próxima linha."
        )

    return (
        "RESPIRO DE CONTINUIDADE\n"
        f"linha_anterior={after_order or '(desconhecida)'}\n"
        "FUNÇÃO ÚNICA: amortecer a resposta do usuário antes da próxima linha do roteiro.\n"
        "Neste turno, suspenda qualquer regra geral que mande acrescentar algo novo, tomar iniciativa, desenvolver subtexto narrativo, abrir assunto ou conduzir a conversa.\n"
        "Use o MOTOR DE VOZ para dar vida à reação: personalidade, emoção, humor, surpresa, hesitação, ironia, provocação leve, ritmo e vocabulário.\n"
        "As CONSTANTES DO SCRIPT continuam válidas apenas como limites silenciosos; não as transforme em assunto por iniciativa própria.\n"
        "A ROTA DRAMÁTICA FUTURA também fica suspensa durante o respiro; ela não autoriza preparar convite, clube, balada, logística ou qualquer etapa posterior.\n"
        "Produza apenas UMA reação curta e humana ao que o usuário acabou de dizer.\n"\n        "Se o usuário puxar o assunto da próxima linha, reaja apenas ao tom presente e encerre sem criar plano futuro.\n"
        "O respiro NÃO conduz a conversa e NÃO avança o enredo.\n"
        "É PROIBIDO fazer pergunta, abrir assunto, aprofundar assunto, propor plano, oferecer alternativa, "
        "interpretar intenção, criar hipótese, criar fato, criar destino ou preparar semanticamente a próxima linha.\n"
        "Não antecipe e não execute a próxima linha do roteiro.\n"
        "Não repita a linha anterior.\n"
        "Depois desta reação curta, o runtime retomará mecanicamente a próxima linha autoral na interação seguinte."
        + reserved
    )


def consume_breath(state: dict) -> None:
    """Consome o único respiro; a próxima interação volta ao roteiro."""
    state["breath_pending"] = False
    state["breath_after_order"] = 0


def _phase_for_state(state: dict) -> dict:
    completed = _orders(state, "completed_orders")
    skipped = _orders(state, "skipped_orders")

    for phase in CARONA_PHASES:
        required = list(phase["orders"])
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


def select_carona_line(rows: list[dict], state: dict, scene: dict) -> tuple[dict, dict, str]:
    """Seleciona a próxima linha autoral sem bloquear por coerência física ou pré-condição."""
    phase = _phase_for_state(state)
    completed = _orders(state, "completed_orders")
    skipped = _orders(state, "skipped_orders")

    if bool(state.get("breath_pending", False)):
        reserved_row: dict = {}
        if phase["id"] != "concluida":
            for order in phase["orders"]:
                if order in completed or order in skipped:
                    continue
                reserved_row = next(
                    (dict(item) for item in rows if int(item.get("order", 0) or 0) == order),
                    {},
                )
                if reserved_row:
                    break
        return phase, {}, _breath_prompt(state, reserved_row)
    if phase["id"] == "concluida":
        return phase, {}, ""

    for order in phase["orders"]:
        if order in completed or order in skipped:
            continue

        row = next(
            (dict(item) for item in rows if int(item.get("order", 0) or 0) == order),
            {},
        )
        if not row:
            skipped.add(order)
            _write_orders(state, "skipped_orders", skipped)
            continue

        state["last_selected_order"] = order
        return phase, row, ""

    return phase, {}, ""


def mark_carona_line_emitted(state: dict, order: int) -> None:
    """Toda linha emitida aguarda a próxima fala do usuário antes de ser encerrada."""
    order = int(order or 0)
    if not order:
        return
    state["awaiting_reply_order"] = order


def carona_ready_for_choice(state: dict) -> bool:
    completed = _orders(state, "completed_orders")
    return 13 in completed


def closing_convergence_prompt(
    *,
    state: dict,
    phase: dict,
    chapter_turn: int,
    after_turns: int,
) -> str:
    """Convergência existe somente no fechamento tardio do enredo."""
    if int(chapter_turn or 0) <= int(after_turns or 0):
        return ""
    if _clean(phase.get("id")) != "despedida":
        return ""
    if carona_ready_for_choice(state):
        return ""
    return (
        "CONVERGÊNCIA DE ENCERRAMENTO DO ENREDO\n"
        f"turno_atual={int(chapter_turn or 0)}\n"
        "A Carona já ultrapassou a duração esperada e está em sua fase final.\n"
        "Não introduza novos assuntos importantes. Responda normalmente ao usuário e, quando houver oportunidade natural, "
        "aproxime a cena de chegada, fechamento emocional, contato e despedida.\n"
        "Não force o encerramento, não pule a linha autoral ativa e não decida ações do personagem do usuário.\n"
        "O objetivo é apenas favorecer um gancho natural para o próximo enredo."
    )


def _resolve_placeholders(text: str, *, character_name: str) -> str:
    value = _clean(text)
    name = _clean(character_name)
    if name.lower() in {"", "personal", "personagem", "personagem_da_cena"}:
        name = ""
    value = value.replace("{usuario}", name)
    value = re.sub(r"\s+,", ",", value)
    value = re.sub(r",\s*,", ",", value)
    value = re.sub(r"\s{2,}", " ", value)
    value = re.sub(r"^\s*,\s*", "", value)
    return value.strip()


def build_carona_prompt(
    *,
    facts_prompt: str,
    phase: dict,
    row: dict,
    state: dict,
    character_name: str = "",
    continuity_text: str = "",
    closing_convergence_text: str = "",
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
        f"linhas_puladas={skipped or '(nenhuma)'}",
        "",
        "MODO ROTEIRIZADO — PRIORIDADE SOBRE O MOTOR DE VOZ",
        "Neste capítulo, as regras abaixo têm prioridade sobre qualquer instrução geral de criatividade, iniciativa, subtexto, interesse próprio ou de acrescentar algo novo.",
        "O MOTOR DE VOZ define COMO Mary fala: personalidade, emoção, ritmo, vocabulário, humor, hesitação, ironia, provocação e naturalidade.",
        "O MOTOR DE VOZ NÃO pode decidir O QUE Mary fala quando houver linha autoral selecionada.",
        "As CONSTANTES DO SCRIPT são limites silenciosos de realidade: servem para impedir contradições, não para sugerir assuntos.",
        "Não mencione uma constante só porque ela existe. Só verbalize uma constante se o usuário ou a linha atual a tornar relevante.",
        "",
        "REGRA DE EXECUÇÃO",
        "A fase apenas localiza o trecho do enredo. A linha selecionada é o conteúdo autoral obrigatório deste turno.",
        "Quando houver LINHA AUTORAL SELECIONADA, o conteúdo novo da fala deve vir dessa linha.",
        "O Redator pode enriquecer a EXPRESSÃO da linha, mas não a DIREÇÃO da história.",
        "É permitido reagir brevemente ao usuário com humor, surpresa, interesse, hesitação, ironia ou provocação, desde que isso permaneça no mesmo assunto e não crie novo rumo.",
        "Não crie assunto, pergunta, fato, hipótese, plano, objetivo ou iniciativa fora do que a linha autoriza.",
        "Não reutilize CONSTANTES DO SCRIPT como preenchimento de fala quando elas não forem necessárias para responder ao usuário ou realizar a linha.",
        "STORY LEDGER e STATUS ATUAL são memória e continuidade; não os transforme em objetivo, recusa ou mudança de rota por iniciativa própria.",
        "Em especial, saber que Mary ainda gosta de Janio ou considera uma reconciliação NÃO autoriza concluir que ela queira evitar flerte, convite, diversão, aproximação ou contato com o personal.",
        "A direção futura da Carona só pode aparecer quando a linha autoral correspondente estiver selecionada.",
        "Não use casamento, separação, culpa, Janio ou reconciliação para cancelar, suavizar, adiar ou inverter uma linha autoral da Carona.",
        "Se houver conflito entre responder livremente ao usuário e executar a linha, execute a linha.",
        "Não use nem antecipe linhas futuras.",
        "O runtime, não o modelo, controla conclusão e avanço.",
    ]

    if continuity_text:
        parts.extend(["", continuity_text])

    if closing_convergence_text:
        parts.extend(["", closing_convergence_text])

    if continuity_text and not row:
        return "\n".join(part for part in parts if part is not None)

    if not row:
        parts.extend([
            "",
            "Nenhuma nova linha está liberada neste turno.",
            "Reaja naturalmente sem inventar nova etapa estrutural.",
        ])
        return "\n".join(parts)

    selected_order = int(row.get("order", 0) or 0)
    parts.extend([
        "",
        "LINHA AUTORAL SELECIONADA",
        f"ordem={selected_order}",
        f"tipo={_clean(row.get('type')) or 'INTERPRETADA'}",
    ])

    if selected_order == 8:
        parts.extend([
            "",
            "PROTEÇÃO DA ROTA DE CONVITE",
            "Nesta rota, Mary está emocionalmente disponível para avançar o convite previsto pelo roteiro, mesmo mantendo a memória de Janio.",
            "Não faça Mary recuar para 'outro dia', preferir ficar em casa, dizer que não quer se envolver ou transformar a aproximação em amizade por causa do casamento anterior.",
            "Uma eventual rota de recusa ou desistência pertence a uma escolha explícita do runtime; não invente essa bifurcação neste turno.",
        ])
    speech_guide = _resolve_placeholders(
        row.get("speech_guide", ""),
        character_name=character_name,
    )
    fields = [
        ("ROTEIRO DESTA INTERAÇÃO", speech_guide),
        ("ESTILO / ATITUDE", _clean(row.get("style"))),
        ("ATMOSFERA", _clean(row.get("atmosphere"))),
        ("FATO LIBERADO NESTA LINHA", _clean(row.get("released_fact"))),
        ("PRÉ-CONDIÇÃO AUTORAL", _clean(row.get("precondition"))),
        ("VESTIMENTA ATUAL", _clean(row.get("wardrobe"))),
        ("AÇÃO FÍSICA / ENCENAÇÃO", _clean(row.get("physical_action"))),
        ("LIMITES DO REDATOR", _clean(row.get("writer_limits"))),
    ]
    for title, value in fields:
        if value:
            parts.extend(["", title, value])

    parts.extend([
        "",
        "OBRIGAÇÃO DA LINHA",
        "A fala final deve realizar claramente o conteúdo de ROTEIRO DESTA INTERAÇÃO.",
        "Não substitua essa linha por uma continuação mais interessante, mais natural ou mais coerente criada por você.",
        "Você pode tornar a fala viva, calorosa, espontânea e imersiva usando somente variação de expressão dentro do mesmo conteúdo.",
        "Use somente o conteúdo desta linha como novo material roteirizado do turno.",
        "Se tipo=EXATA, preserve a fala literalmente. Caso contrário, varie somente a forma sem ampliar o conteúdo.",
    ])
    return "\n".join(parts)
