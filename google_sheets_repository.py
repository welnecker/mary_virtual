from __future__ import annotations
from config import MARY_SPREADSHEET_ID

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import gspread
import streamlit as st
from gspread import Spreadsheet, Worksheet
from gspread.exceptions import (
    APIError,
    SpreadsheetNotFound,
    WorksheetNotFound,
)


USERS_SHEET = "USERS"
SESSIONS_SHEET = "SESSIONS"
INTERACTIONS_SHEET = "INTERACTIONS"
USER_VISUAL_PROFILE_SHEET = "USER_VISUAL_PROFILE"
MARY_RELATIONSHIP_SHEET = "MARY_RELATIONSHIP"
MEMORIES_SHEET = "MEMORIES"


class GoogleSheetsRepositoryError(RuntimeError):
    """Erro de persistência na planilha do projeto."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def gerar_id(prefixo: str) -> str:
    return f"{prefixo}_{uuid.uuid4().hex}"


def gerar_token_usuario() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex


def gerar_hash_token(token: str) -> str:
    token_limpo = str(token or "").strip()

    if not token_limpo:
        return ""

    return hashlib.sha256(
        token_limpo.encode("utf-8")
    ).hexdigest()


def serializar_json(valor: Any) -> str:
    if valor is None:
        return ""

    return json.dumps(
        valor,
        ensure_ascii=False,
        separators=(",", ":"),
    )


@st.cache_resource(show_spinner=False)
def obter_planilha() -> Spreadsheet:
    try:
        credenciais = dict(
            st.secrets["gcp_service_account"]
        )

        spreadsheet_id = str(
            MARY_SPREADSHEET_ID or ""
        ).strip()

        if not spreadsheet_id:
            raise GoogleSheetsRepositoryError(
                "MARY_SPREADSHEET_ID não foi definido "
                "no arquivo config.py."
            )

        cliente = gspread.service_account_from_dict(
            credenciais
        )

        return cliente.open_by_key(
            spreadsheet_id
        )

    except KeyError as exc:
        raise GoogleSheetsRepositoryError(
            "O bloco [gcp_service_account] não foi "
            "encontrado nos secrets do Streamlit."
        ) from exc

    except SpreadsheetNotFound as exc:
        raise GoogleSheetsRepositoryError(
            "A planilha não foi encontrada ou não foi "
            "compartilhada com o client_email da conta "
            "de serviço."
        ) from exc

    except APIError as exc:
        raise GoogleSheetsRepositoryError(
            f"Erro da API do Google Sheets: {exc}"
        ) from exc

    except Exception as exc:
        if isinstance(
            exc,
            GoogleSheetsRepositoryError,
        ):
            raise

        raise GoogleSheetsRepositoryError(
            f"Não foi possível conectar à planilha: {exc}"
        ) from exc


def obter_aba(nome: str) -> Worksheet:
    try:
        return obter_planilha().worksheet(nome)

    except WorksheetNotFound as exc:
        raise GoogleSheetsRepositoryError(
            f"A aba {nome!r} não foi encontrada."
        ) from exc

    except APIError as exc:
        raise GoogleSheetsRepositoryError(
            f"Não foi possível acessar a aba {nome!r}: {exc}"
        ) from exc


def obter_cabecalhos(
    worksheet: Worksheet,
) -> list[str]:
    cabecalhos = [
        str(valor).strip()
        for valor in worksheet.row_values(1)
    ]

    if not cabecalhos:
        raise GoogleSheetsRepositoryError(
            f"A aba {worksheet.title!r} não possui "
            "cabeçalhos na linha 1."
        )

    return cabecalhos


def montar_linha_por_cabecalho(
    worksheet: Worksheet,
    dados: dict[str, Any],
) -> list[Any]:
    cabecalhos = obter_cabecalhos(worksheet)

    return [
        dados.get(cabecalho, "")
        for cabecalho in cabecalhos
    ]


def adicionar_registro(
    nome_aba: str,
    dados: dict[str, Any],
) -> None:
    worksheet = obter_aba(nome_aba)
    linha = montar_linha_por_cabecalho(
        worksheet,
        dados,
    )

    try:
        worksheet.append_row(
            linha,
            value_input_option="RAW",
        )

    except APIError as exc:
        raise GoogleSheetsRepositoryError(
            f"Não foi possível gravar na aba "
            f"{nome_aba!r}: {exc}"
        ) from exc


def buscar_registro(
    nome_aba: str,
    *,
    coluna: str,
    valor: str,
) -> dict[str, Any] | None:
    worksheet = obter_aba(nome_aba)
    registros = worksheet.get_all_records(
        default_blank="",
    )

    valor_procurado = str(valor or "").strip()

    for registro in registros:
        if str(
            registro.get(coluna, "")
        ).strip() == valor_procurado:
            return dict(registro)

    return None


def buscar_linha(
    worksheet: Worksheet,
    *,
    coluna: str,
    valor: str,
) -> tuple[int, dict[str, Any]] | None:
    cabecalhos = obter_cabecalhos(worksheet)

    if coluna not in cabecalhos:
        raise GoogleSheetsRepositoryError(
            f"A coluna {coluna!r} não existe na aba "
            f"{worksheet.title!r}."
        )

    registros = worksheet.get_all_records(
        default_blank="",
    )

    valor_procurado = str(valor or "").strip()

    for indice, registro in enumerate(
        registros,
        start=2,
    ):
        if str(
            registro.get(coluna, "")
        ).strip() == valor_procurado:
            return indice, dict(registro)

    return None


def atualizar_registro(
    nome_aba: str,
    *,
    coluna_chave: str,
    valor_chave: str,
    alteracoes: dict[str, Any],
) -> bool:
    worksheet = obter_aba(nome_aba)

    resultado = buscar_linha(
        worksheet,
        coluna=coluna_chave,
        valor=valor_chave,
    )

    if resultado is None:
        return False

    numero_linha, _ = resultado
    cabecalhos = obter_cabecalhos(worksheet)

    atualizacoes: list[dict[str, Any]] = []

    for coluna, valor in alteracoes.items():
        if coluna not in cabecalhos:
            continue

        numero_coluna = cabecalhos.index(
            coluna
        ) + 1

        endereco = gspread.utils.rowcol_to_a1(
            numero_linha,
            numero_coluna,
        )

        atualizacoes.append(
            {
                "range": endereco,
                "values": [[valor]],
            }
        )

    if not atualizacoes:
        return True

    try:
        worksheet.batch_update(
            atualizacoes,
            value_input_option="RAW",
        )

    except APIError as exc:
        raise GoogleSheetsRepositoryError(
            f"Não foi possível atualizar a aba "
            f"{nome_aba!r}: {exc}"
        ) from exc

    return True


# =========================================================
# USERS
# =========================================================


def criar_usuario_anonimo() -> tuple[dict[str, Any], str]:
    agora = utc_now_iso()
    token = gerar_token_usuario()
    token_hash = gerar_hash_token(token)

    usuario = {
        "user_id": gerar_id("usr"),
        # O token puro fica apenas na URL do usuário.
        # Na planilha é armazenado somente o hash.
        "user_token": token_hash,
        "created_at": agora,
        "updated_at": agora,
        "status": "active",
        "name": "",
        "preferred_name": "",
        "first_access_at": agora,
        "last_access_at": agora,
        "access_count": 1,
        "profile_version": 1,
    }

    adicionar_registro(
        USERS_SHEET,
        usuario,
    )

    return usuario, token


def obter_usuario_por_token(
    token: str,
) -> dict[str, Any] | None:
    token_hash = gerar_hash_token(token)

    if not token_hash:
        return None

    return buscar_registro(
        USERS_SHEET,
        coluna="user_token",
        valor=token_hash,
    )


def registrar_novo_acesso_usuario(
    usuario: dict[str, Any],
) -> dict[str, Any]:
    user_id = str(
        usuario.get("user_id", "")
    ).strip()

    if not user_id:
        raise GoogleSheetsRepositoryError(
            "O usuário não possui user_id."
        )

    try:
        quantidade_atual = int(
            usuario.get("access_count", 0)
            or 0
        )
    except (TypeError, ValueError):
        quantidade_atual = 0

    agora = utc_now_iso()

    atualizar_registro(
        USERS_SHEET,
        coluna_chave="user_id",
        valor_chave=user_id,
        alteracoes={
            "updated_at": agora,
            "last_access_at": agora,
            "access_count": quantidade_atual + 1,
        },
    )

    usuario_atualizado = dict(usuario)
    usuario_atualizado["updated_at"] = agora
    usuario_atualizado["last_access_at"] = agora
    usuario_atualizado[
        "access_count"
    ] = quantidade_atual + 1

    return usuario_atualizado


def atualizar_usuario(
    user_id: str,
    *,
    name: str | None = None,
    preferred_name: str | None = None,
    status: str | None = None,
    profile_version: int | None = None,
) -> bool:
    alteracoes: dict[str, Any] = {
        "updated_at": utc_now_iso(),
    }

    if name is not None:
        alteracoes["name"] = str(name).strip()

    if preferred_name is not None:
        alteracoes["preferred_name"] = str(
            preferred_name
        ).strip()

    if status is not None:
        alteracoes["status"] = str(
            status
        ).strip()

    if profile_version is not None:
        alteracoes["profile_version"] = int(
            profile_version
        )

    return atualizar_registro(
        USERS_SHEET,
        coluna_chave="user_id",
        valor_chave=user_id,
        alteracoes=alteracoes,
    )


# =========================================================
# SESSIONS
# =========================================================


def criar_sessao(
    *,
    user_id: str,
    model: str,
    prompt_version: str,
    app_version: str,
) -> dict[str, Any]:
    agora = utc_now_iso()

    sessao = {
        "session_id": gerar_id("ses"),
        "user_id": user_id,
        "started_at": agora,
        "last_activity_at": agora,
        "ended_at": "",
        "model": model,
        "prompt_version": prompt_version,
        "app_version": app_version,
        "status": "active",
    }

    adicionar_registro(
        SESSIONS_SHEET,
        sessao,
    )

    return sessao


def atualizar_atividade_sessao(
    session_id: str,
) -> None:
    atualizar_registro(
        SESSIONS_SHEET,
        coluna_chave="session_id",
        valor_chave=session_id,
        alteracoes={
            "last_activity_at": utc_now_iso(),
        },
    )


def encerrar_sessao(
    session_id: str,
) -> None:
    agora = utc_now_iso()

    atualizar_registro(
        SESSIONS_SHEET,
        coluna_chave="session_id",
        valor_chave=session_id,
        alteracoes={
            "last_activity_at": agora,
            "ended_at": agora,
            "status": "ended",
        },
    )


# =========================================================
# INTERACTIONS
# =========================================================


def salvar_interacao(
    *,
    interaction_id: str,
    session_id: str,
    user_id: str,
    timestamp: str,
    user_text: str,
    mary_response: str,
    model: str,
    prompt_version: str,
    response_time_ms: int | None,
    image_sent: bool,
    image_width: int | None,
    image_height: int | None,
    image_size_bytes: int | None,
    image_mime_type: str | None,
    mary_asked_name: bool,
    error: str,
) -> None:
    registro = {
        "interaction_id": interaction_id,
        "session_id": session_id,
        "user_id": user_id,
        "timestamp": timestamp,
        "user_text": user_text,
        "mary_response": mary_response,
        "model": model,
        "prompt_version": prompt_version,
        "response_time_ms": (
            response_time_ms
            if response_time_ms is not None
            else ""
        ),
        "image_sent": bool(image_sent),
        "image_width": (
            image_width
            if image_width is not None
            else ""
        ),
        "image_height": (
            image_height
            if image_height is not None
            else ""
        ),
        "image_size_bytes": (
            image_size_bytes
            if image_size_bytes is not None
            else ""
        ),
        "image_mime_type": (
            image_mime_type or ""
        ),
        "mary_asked_name": bool(
            mary_asked_name
        ),
        "error": str(error or ""),
    }

    adicionar_registro(
        INTERACTIONS_SHEET,
        registro,
    )

    atualizar_atividade_sessao(
        session_id
    )


# =========================================================
# USER_VISUAL_PROFILE
# =========================================================


def salvar_perfil_visual_usuario(
    *,
    visual_profile_id: str,
    user_id: str,
    version: int,
    reference_image_id: str,
    reference_confirmed: bool,
    stable_traits: Any,
    variable_traits: Any,
    current_appearance: Any,
    first_impression: str,
    active: bool = True,
) -> None:
    agora = utc_now_iso()

    adicionar_registro(
        USER_VISUAL_PROFILE_SHEET,
        {
            "visual_profile_id": visual_profile_id,
            "user_id": user_id,
            "version": version,
            "created_at": agora,
            "updated_at": agora,
            "reference_image_id": reference_image_id,
            "reference_confirmed": bool(
                reference_confirmed
            ),
            "stable_traits_json": serializar_json(
                stable_traits
            ),
            "variable_traits_json": serializar_json(
                variable_traits
            ),
            "current_appearance_json": serializar_json(
                current_appearance
            ),
            "first_impression": first_impression,
            "active": bool(active),
        },
    )


# =========================================================
# MARY_RELATIONSHIP
# =========================================================


def criar_relacionamento_mary(
    *,
    user_id: str,
) -> dict[str, Any]:
    agora = utc_now_iso()

    relacionamento = {
        "user_id": user_id,
        "created_at": agora,
        "updated_at": agora,
        "mary_revealed": False,
        "first_mary_image_id": "",
        "first_reveal_at": "",
        "user_has_seen_mary": False,
        "user_first_visual_reaction": "",
        "relationship_summary": "",
    }

    adicionar_registro(
        MARY_RELATIONSHIP_SHEET,
        relacionamento,
    )

    return relacionamento


def obter_ou_criar_relacionamento_mary(
    user_id: str,
) -> dict[str, Any]:
    existente = buscar_registro(
        MARY_RELATIONSHIP_SHEET,
        coluna="user_id",
        valor=user_id,
    )

    if existente is not None:
        return existente

    return criar_relacionamento_mary(
        user_id=user_id
    )


# =========================================================
# MEMORIES
# =========================================================


def salvar_memoria(
    *,
    user_id: str,
    memory_type: str,
    content: str,
    importance: int,
    source_interaction_id: str = "",
    active: bool = True,
) -> dict[str, Any]:
    agora = utc_now_iso()

    memoria = {
        "memory_id": gerar_id("mem"),
        "user_id": user_id,
        "created_at": agora,
        "updated_at": agora,
        "memory_type": str(
            memory_type
        ).strip(),
        "content": str(content).strip(),
        "importance": int(importance),
        "source_interaction_id": str(
            source_interaction_id
        ).strip(),
        "active": bool(active),
    }

    adicionar_registro(
        MEMORIES_SHEET,
        memoria,
    )

    return memoria

def encerrar_sessoes_ativas_usuario(
    user_id: str,
) -> None:
    worksheet = obter_aba(SESSIONS_SHEET)
    cabecalhos = obter_cabecalhos(worksheet)

    registros = worksheet.get_all_records(
        default_blank="",
    )

    agora = utc_now_iso()
    atualizacoes: list[dict[str, Any]] = []

    for numero_linha, registro in enumerate(
        registros,
        start=2,
    ):
        mesmo_usuario = (
            str(registro.get("user_id", "")).strip()
            == str(user_id).strip()
        )

        sessao_ativa = (
            str(registro.get("status", "")).strip().lower()
            == "active"
        )

        if not mesmo_usuario or not sessao_ativa:
            continue

        for coluna, valor in {
            "last_activity_at": agora,
            "ended_at": agora,
            "status": "ended",
        }.items():
            if coluna not in cabecalhos:
                continue

            numero_coluna = cabecalhos.index(coluna) + 1
            endereco = gspread.utils.rowcol_to_a1(
                numero_linha,
                numero_coluna,
            )

            atualizacoes.append(
                {
                    "range": endereco,
                    "values": [[valor]],
                }
            )

    if not atualizacoes:
        return

    try:
        worksheet.batch_update(
            atualizacoes,
            value_input_option="RAW",
        )

    except APIError as exc:
        raise GoogleSheetsRepositoryError(
            "Não foi possível encerrar as sessões "
            f"anteriores do usuário: {exc}"
        ) from exc
