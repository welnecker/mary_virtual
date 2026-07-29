from __future__ import annotations

from typing import Any

import gspread
import streamlit as st
from gspread.exceptions import APIError, GSpreadException, SpreadsheetNotFound, WorksheetNotFound

from scenarios.stories.casada_frustrada.immersive_screenplay import (
    HIDDEN_CALL_DIALOGUE,
    MESSAGES_DIALOGUE,
    SECRET_MEETING_DIALOGUE,
    SECRET_MEETING_PLAN_DIALOGUE,
    SUPERMARKET_DIALOGUE,
)


SCREENPLAY_SPREADSHEET_ID = "1ldFgUbxaEgi13ltNgx991INXTAm3e4nuhB8bjnYSyZM"
SCREENPLAY_WORKSHEET = "MARY_FRUSTRADA_CAP_01"
SCREENPLAY_SOURCE_VERSION = "mary-frustrada-cap-01-google-sheets-v2"
SCREENPLAY_HEADERS = [
    "ordem",
    "cena",
    "rota",
    "beat",
    "tipo",
    "conteudo",
    "condicao",
    "funcao_dramatica",
    "proxima_rota",
    "ativo",
]


class ScreenplaySheetError(RuntimeError):
    """Falha ao ler ou inicializar o roteiro editorial no Google Sheets."""


@st.cache_resource(show_spinner=False)
def _obter_worksheet():
    try:
        credentials = dict(st.secrets["gcp_service_account"])
        client = gspread.service_account_from_dict(credentials)
        spreadsheet = client.open_by_key(SCREENPLAY_SPREADSHEET_ID)
        return spreadsheet.worksheet(SCREENPLAY_WORKSHEET)
    except KeyError as exc:
        raise ScreenplaySheetError(
            "O bloco [gcp_service_account] não foi encontrado nos secrets do Streamlit."
        ) from exc
    except SpreadsheetNotFound as exc:
        raise ScreenplaySheetError(
            "A planilha de roteiro não foi encontrada ou não foi compartilhada com a conta de serviço."
        ) from exc
    except WorksheetNotFound as exc:
        raise ScreenplaySheetError(
            f"A aba {SCREENPLAY_WORKSHEET!r} não foi encontrada na planilha de roteiro."
        ) from exc
    except (APIError, GSpreadException) as exc:
        raise ScreenplaySheetError(f"Falha de comunicação com o Google Sheets: {exc}") from exc
    except ScreenplaySheetError:
        raise
    except Exception as exc:
        raise ScreenplaySheetError(f"Não foi possível abrir o roteiro remoto: {exc}") from exc


def _normalizar_ativo(value: Any) -> bool:
    return str(value or "SIM").strip().casefold() in {
        "sim", "true", "1", "ativo", "yes", "on"
    }


def _normalizar_ordem(value: Any) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 999999


def _linhas_do_bloco(
    text: str,
    *,
    default_route: str,
    section_routes: dict[str, str] | None = None,
    next_routes: dict[str, str] | None = None,
    start_order: int,
) -> list[list[Any]]:
    section_routes = section_routes or {}
    next_routes = next_routes or {}
    rows: list[list[Any]] = []
    scene = ""
    route = default_route
    order = start_order

    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("ROTEIRO IMERSIVO"):
            continue

        if line.startswith("—"):
            content = line.lstrip("—").strip()
            row_type = "fala"
        elif line.startswith("-"):
            content = line.lstrip("-").strip()
            row_type = "regra"
        else:
            scene = line
            route = section_routes.get(scene, default_route)
            continue

        rows.append([
            order,
            scene,
            route,
            "",
            row_type,
            content,
            "",
            "",
            next_routes.get(scene, ""),
            "SIM",
        ])
        order += 10

    return rows


def _montar_seed_rows() -> list[list[Any]]:
    rows: list[list[Any]] = []
    rows.extend(_linhas_do_bloco(
        SUPERMARKET_DIALOGUE,
        default_route="supermarket_encounter",
        section_routes={
            "PRIMEIRO CONTATO": "supermarket_encounter",
            "PENSAMENTO APÓS A PRIMEIRA DESPEDIDA": "supermarket_encounter",
            "REENCONTRO": "aisle_flirtation",
            "ATÉ O CARRO": "phone_exchange",
            "PENSAMENTO DEPOIS DA TROCA": "phone_exchange",
            "REGRAS DO BLOCO": "phone_exchange",
        },
        next_routes={
            "PENSAMENTO APÓS A PRIMEIRA DESPEDIDA": "aisle_flirtation",
            "PENSAMENTO DEPOIS DA TROCA": "messages",
        },
        start_order=10,
    ))
    rows.extend(_linhas_do_bloco(
        MESSAGES_DIALOGUE,
        default_route="messages",
        next_routes={"PRIMEIRO CONTATO À DISTÂNCIA": "hidden_call"},
        start_order=1000,
    ))
    rows.extend(_linhas_do_bloco(
        HIDDEN_CALL_DIALOGUE,
        default_route="hidden_call",
        next_routes={"MÚTUA EXCITAÇÃO": "secret_meeting_plan"},
        start_order=2000,
    ))
    rows.extend(_linhas_do_bloco(
        SECRET_MEETING_PLAN_DIALOGUE,
        default_route="secret_meeting_plan",
        next_routes={"MANHÃ SEGUINTE": "secret_meeting"},
        start_order=3000,
    ))
    rows.extend(_linhas_do_bloco(
        SECRET_MEETING_DIALOGUE,
        default_route="secret_meeting",
        section_routes={
            "CHEGADA": "secret_meeting",
            "MARY DÁ PRAZER": "growing_tension",
            "MARY RECEBE PRAZER": "intimacy",
            "PENETRAÇÃO": "climax",
            "DESPEDIDA": "aftercare",
            "PONTE FINAL": "future_secret",
            "REGRAS DO BLOCO": "future_secret",
        },
        start_order=4000,
    ))
    return rows


def _escrever_intervalo(worksheet, range_name: str, values: list[list[Any]]) -> None:
    try:
        worksheet.update(
            values=values,
            range_name=range_name,
            value_input_option="RAW",
        )
    except TypeError:
        # Compatibilidade com versões antigas do gspread.
        worksheet.update(range_name, values, value_input_option="RAW")
    except (APIError, GSpreadException) as exc:
        raise ScreenplaySheetError(
            f"Não foi possível escrever o roteiro na aba {SCREENPLAY_WORKSHEET!r}: {exc}"
        ) from exc


def inicializar_aba_se_vazia() -> bool:
    """Copia o roteiro local quando a aba possui somente cabeçalhos ou está vazia."""
    worksheet = _obter_worksheet()

    try:
        values = worksheet.get_all_values()
    except (APIError, GSpreadException) as exc:
        raise ScreenplaySheetError(
            f"Não foi possível verificar a aba {SCREENPLAY_WORKSHEET!r}: {exc}"
        ) from exc

    if values and any(any(str(cell).strip() for cell in row) for row in values[1:]):
        return False

    if not values:
        _escrever_intervalo(worksheet, "A1:J1", [SCREENPLAY_HEADERS])
    else:
        current_headers = [str(value).strip() for value in values[0]]
        if current_headers[: len(SCREENPLAY_HEADERS)] != SCREENPLAY_HEADERS:
            raise ScreenplaySheetError(
                "Os cabeçalhos da aba de roteiro não correspondem ao contrato esperado. "
                f"Esperado: {SCREENPLAY_HEADERS}. Encontrado: {current_headers}."
            )

    rows = _montar_seed_rows()
    if not rows:
        raise ScreenplaySheetError("O roteiro local não gerou linhas para migração.")

    _escrever_intervalo(
        worksheet,
        f"A2:J{len(rows) + 1}",
        rows,
    )
    carregar_registros_roteiro.clear()
    return True


@st.cache_data(show_spinner=False, ttl=60)
def carregar_registros_roteiro() -> list[dict[str, Any]]:
    worksheet = _obter_worksheet()

    # A inicialização ocorre antes de get_all_records para evitar que uma aba
    # somente com cabeçalhos seja tratada silenciosamente como roteiro vazio.
    inicializar_aba_se_vazia()

    try:
        records = worksheet.get_all_records(default_blank="")
    except (APIError, GSpreadException) as exc:
        raise ScreenplaySheetError(
            f"Não foi possível ler os registros da aba {SCREENPLAY_WORKSHEET!r}: {exc}"
        ) from exc

    return [dict(record) for record in records]


def carregar_trecho_por_rota(route: str, current_beat: str = "") -> dict[str, Any]:
    route_id = str(route or "").strip()
    beat_id = str(current_beat or "").strip()
    selected: list[dict[str, Any]] = []

    for record in carregar_registros_roteiro():
        if str(record.get("rota", "")).strip() != route_id:
            continue
        if not _normalizar_ativo(record.get("ativo", "SIM")):
            continue
        content = str(record.get("conteudo", "")).strip()
        if content:
            selected.append(dict(record))

    selected.sort(key=lambda item: _normalizar_ordem(item.get("ordem")))

    lines: list[str] = []
    current_scene = None
    for record in selected:
        scene = str(record.get("cena", "")).strip()
        row_type = str(record.get("tipo", "fala")).strip().casefold()
        content = str(record.get("conteudo", "")).strip()
        row_beat = str(record.get("beat", "")).strip()
        condition = str(record.get("condicao", "")).strip()
        dramatic_function = str(record.get("funcao_dramatica", "")).strip()
        next_route = str(record.get("proxima_rota", "")).strip()

        if scene and scene != current_scene:
            if lines:
                lines.append("")
            lines.append(scene.upper())
            current_scene = scene

        prefix = {
            "fala": "—",
            "pensamento": "PENSAMENTO:",
            "acao": "AÇÃO:",
            "ação": "AÇÃO:",
            "regra": "REGRA:",
            "objetivo": "OBJETIVO:",
            "transicao": "TRANSIÇÃO:",
            "transição": "TRANSIÇÃO:",
        }.get(row_type, "—")
        lines.append(f"{prefix} {content}")

        metadata = []
        if row_beat:
            metadata.append(f"beat={row_beat}")
        if condition:
            metadata.append(f"condição={condition}")
        if dramatic_function:
            metadata.append(f"função={dramatic_function}")
        if next_route:
            metadata.append(f"próxima_rota={next_route}")
        if metadata:
            lines.append("[" + "; ".join(metadata) + "]")

    return {
        "version": SCREENPLAY_SOURCE_VERSION,
        "source": "google_sheets",
        "spreadsheet_id": SCREENPLAY_SPREADSHEET_ID,
        "worksheet": SCREENPLAY_WORKSHEET,
        "route": route_id,
        "current_beat": beat_id,
        "excerpt": "\n".join(lines).strip(),
        "rows": len(selected),
    }


__all__ = [
    "SCREENPLAY_SPREADSHEET_ID",
    "SCREENPLAY_WORKSHEET",
    "SCREENPLAY_SOURCE_VERSION",
    "ScreenplaySheetError",
    "inicializar_aba_se_vazia",
    "carregar_registros_roteiro",
    "carregar_trecho_por_rota",
]
