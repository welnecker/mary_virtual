from __future__ import annotations

"""API pública estável do repositório Google Sheets.

A implementação histórica permanece no arquivo ``google_sheets_repository.py``.
Este pacote funciona como ponte de compatibilidade, mas não reexporta mais todos
os nomes internos do módulo-base. Correções locais de leitura, sessão e relação
prevalecem explicitamente sobre a implementação antiga.
"""

import importlib.util
from pathlib import Path
from typing import Any


GOOGLE_SHEETS_REPOSITORY_VERSION = "google-sheets-repository-v3-explicit-api"

_BASE_PATH = Path(__file__).resolve().parent.parent / "google_sheets_repository.py"
_SPEC = importlib.util.spec_from_file_location(
    "_google_sheets_repository_base",
    _BASE_PATH,
)

if _SPEC is None or _SPEC.loader is None:
    raise ImportError("Não foi possível carregar o repositório do Google Sheets.")

_base = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_base)


# Nomes do módulo-base que fazem parte do contrato público real do projeto.
# A lista é explícita para impedir que imports como gspread, hashlib, json, st e
# helpers privados sejam expostos acidentalmente.
_BASE_PUBLIC_NAMES = (
    # Exceção e constantes de abas.
    "GoogleSheetsRepositoryError",
    "USERS_SHEET",
    "SESSIONS_SHEET",
    "INTERACTIONS_SHEET",
    "USER_VISUAL_PROFILE_SHEET",
    "MARY_RELATIONSHIP_SHEET",
    "MEMORIES_SHEET",
    # Utilidades estáveis.
    "utc_now_iso",
    "gerar_id",
    "gerar_token_usuario",
    "gerar_hash_token",
    "serializar_json",
    # Infraestrutura genérica de planilha.
    "obter_planilha",
    "obter_aba",
    "obter_cabecalhos",
    "montar_linha_por_cabecalho",
    "adicionar_registro",
    "buscar_registro",
    "buscar_linha",
    "atualizar_registro",
    # Usuários.
    "criar_usuario_anonimo",
    "obter_usuario_por_token",
    "registrar_novo_acesso_usuario",
    "atualizar_usuario",
    # Sessões.
    "atualizar_atividade_sessao",
    "encerrar_sessao",
    "encerrar_sessoes_ativas_usuario",
    # Interações e perfis.
    "salvar_interacao",
    "salvar_perfil_visual_usuario",
    # Memória legada. Novos fluxos devem preferir repositories.memory_repository.
    "salvar_memoria",
    # Reset e exclusão.
    "normalizar_user_id",
    "excluir_linhas_por_valor",
    "limpar_dados_interacao_usuario",
    "deletar_usuario_e_dados",
)

for _name in _BASE_PUBLIC_NAMES:
    if not hasattr(_base, _name):
        raise ImportError(
            f"A implementação do Google Sheets não possui a API esperada: {_name!r}."
        )
    globals()[_name] = getattr(_base, _name)


# Mantém referência ao leitor cacheado original para preservar .clear().
_obter_registros_cacheado_original = _base.obter_registros_aba


def _limpar_cache_registros() -> None:
    clear = getattr(_obter_registros_cacheado_original, "clear", None)
    if callable(clear):
        clear()


def obter_registros_aba(nome_aba: str) -> list[dict[str, Any]]:
    """Lê uma aba tolerando cabeçalhos vazios ou duplicados.

    A primeira ocorrência de cada cabeçalho é preservada. Isso mantém o app
    operacional durante migrações graduais da planilha sem permitir que duas
    colunas homônimas sobrescrevam silenciosamente uma à outra.
    """

    worksheet = _base.obter_aba(nome_aba)
    try:
        valores = worksheet.get_all_values()
    except Exception as exc:
        raise _base.GoogleSheetsRepositoryError(
            f"Não foi possível ler a aba {nome_aba!r}: {exc}"
        ) from exc

    if not valores:
        return []

    cabecalhos = [str(valor).strip() for valor in valores[0]]
    colunas_unicas: list[tuple[str, int]] = []
    vistos: set[str] = set()

    for indice, cabecalho in enumerate(cabecalhos):
        if not cabecalho or cabecalho in vistos:
            continue
        vistos.add(cabecalho)
        colunas_unicas.append((cabecalho, indice))

    registros: list[dict[str, Any]] = []
    for linha in valores[1:]:
        if not any(str(valor).strip() for valor in linha):
            continue
        registros.append(
            {
                cabecalho: linha[indice] if indice < len(linha) else ""
                for cabecalho, indice in colunas_unicas
            }
        )
    return registros


obter_registros_aba.clear = _limpar_cache_registros  # type: ignore[attr-defined]
# As funções genéricas do módulo-base chamam este leitor em tempo de execução.
_base.obter_registros_aba = obter_registros_aba


def listar_interacoes_usuario(
    user_id: str,
    *,
    limite: int = 50,
) -> list[dict[str, Any]]:
    user_id_normalizado = str(user_id or "").strip()
    if not user_id_normalizado:
        return []

    interacoes = [
        dict(registro)
        for registro in obter_registros_aba(_base.INTERACTIONS_SHEET)
        if str(registro.get("user_id") or "").strip() == user_id_normalizado
    ]
    interacoes.sort(key=lambda registro: str(registro.get("timestamp") or ""))
    return interacoes[-max(1, int(limite or 50)) :]


_base.listar_interacoes_usuario = listar_interacoes_usuario
_criar_sessao_original = _base.criar_sessao
_criar_relacionamento_original = _base.criar_relacionamento_mary
_obter_relacionamento_original = _base.obter_ou_criar_relacionamento_mary


def criar_sessao(
    *,
    user_id: str,
    model: str,
    prompt_version: str,
    app_version: str,
    session_id: str | None = None,
    started_at: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Aceita tanto a assinatura atual quanto a usada pelo app restaurado."""

    if not session_id and not started_at:
        return _criar_sessao_original(
            user_id=user_id,
            model=model,
            prompt_version=prompt_version,
            app_version=app_version,
        )

    agora = _base.utc_now_iso()
    sessao = {
        "session_id": str(session_id or _base.gerar_id("ses")).strip(),
        "user_id": str(user_id or "").strip(),
        "started_at": str(started_at or agora).strip(),
        "last_activity_at": agora,
        "ended_at": "",
        "model": model,
        "prompt_version": prompt_version,
        "app_version": app_version,
        "status": "active",
    }
    _base.adicionar_registro(_base.SESSIONS_SHEET, sessao)
    return sessao


def _relationship_id_padrao(user_id: str) -> str:
    return "rel_" + str(user_id or "").strip()


def _normalizar_relacionamento(
    registro: dict[str, Any] | None,
    *,
    user_id: str,
) -> dict[str, Any]:
    agora = _base.utc_now_iso()
    normalizado = dict(registro or {})
    normalizado.setdefault("relationship_id", _relationship_id_padrao(user_id))
    normalizado.setdefault("user_id", user_id)
    normalizado.setdefault("created_at", agora)
    normalizado.setdefault("updated_at", agora)
    normalizado.setdefault("mary_revealed", False)
    normalizado.setdefault("first_mary_image_id", "")
    normalizado.setdefault("first_reveal_at", "")
    normalizado.setdefault("user_has_seen_mary", False)
    normalizado.setdefault("user_first_visual_reaction", "")
    normalizado.setdefault("relationship_summary", "")
    return normalizado


def criar_relacionamento_mary(*, user_id: str) -> dict[str, Any]:
    user_id_normalizado = str(user_id or "").strip()
    if not user_id_normalizado:
        raise _base.GoogleSheetsRepositoryError("O user_id não foi informado.")

    normalizado = _normalizar_relacionamento(
        _criar_relacionamento_original(user_id=user_id_normalizado),
        user_id=user_id_normalizado,
    )
    _base.atualizar_registro(
        _base.MARY_RELATIONSHIP_SHEET,
        coluna_chave="user_id",
        valor_chave=user_id_normalizado,
        alteracoes={"relationship_id": normalizado["relationship_id"]},
    )
    return normalizado


def obter_ou_criar_relacionamento_mary(user_id: str) -> dict[str, Any]:
    user_id_normalizado = str(user_id or "").strip()
    if not user_id_normalizado:
        raise _base.GoogleSheetsRepositoryError("O user_id não foi informado.")

    existente = _obter_relacionamento_original(user_id_normalizado)
    normalizado = _normalizar_relacionamento(
        existente,
        user_id=user_id_normalizado,
    )
    relationship_id_existente = (
        str(existente.get("relationship_id") or "").strip()
        if isinstance(existente, dict)
        else ""
    )
    if not relationship_id_existente:
        _base.atualizar_registro(
            _base.MARY_RELATIONSHIP_SHEET,
            coluna_chave="user_id",
            valor_chave=user_id_normalizado,
            alteracoes={"relationship_id": normalizado["relationship_id"]},
        )
    return normalizado


def _resolver_user_id_por_identificador(identificador: str) -> str:
    valor = str(identificador or "").strip()
    if not valor:
        return ""

    por_relacionamento = _base.buscar_registro(
        _base.MARY_RELATIONSHIP_SHEET,
        coluna="relationship_id",
        valor=valor,
    )
    if isinstance(por_relacionamento, dict):
        encontrado = str(por_relacionamento.get("user_id") or "").strip()
        if encontrado:
            return encontrado
    return valor[4:] if valor.startswith("rel_") else valor


def atualizar_relacionamento_mary(
    identificador: str,
    alteracoes: dict[str, Any] | None = None,
    **campos: Any,
) -> dict[str, Any]:
    """Aceita relationship_id ou user_id e a interface histórica do app."""

    user_id_normalizado = _resolver_user_id_por_identificador(identificador)
    if not user_id_normalizado:
        raise _base.GoogleSheetsRepositoryError(
            "O relacionamento não possui identificador válido."
        )

    dados: dict[str, Any] = {}
    if isinstance(alteracoes, dict):
        dados.update(alteracoes)
    dados.update(campos)
    dados.pop("user_id", None)
    dados["updated_at"] = _base.utc_now_iso()

    existente = obter_ou_criar_relacionamento_mary(user_id_normalizado)
    _base.atualizar_registro(
        _base.MARY_RELATIONSHIP_SHEET,
        coluna_chave="user_id",
        valor_chave=user_id_normalizado,
        alteracoes=dados,
    )

    atualizado = dict(existente)
    atualizado.update(dados)
    atualizado["user_id"] = user_id_normalizado
    atualizado.setdefault("relationship_id", _relationship_id_padrao(user_id_normalizado))
    return atualizado


# Garante que chamadas internas futuras do módulo-base também usem os wrappers.
_base.criar_sessao = criar_sessao
_base.criar_relacionamento_mary = criar_relacionamento_mary
_base.obter_ou_criar_relacionamento_mary = obter_ou_criar_relacionamento_mary


__all__ = [
    "GOOGLE_SHEETS_REPOSITORY_VERSION",
    *_BASE_PUBLIC_NAMES,
    "obter_registros_aba",
    "listar_interacoes_usuario",
    "criar_sessao",
    "criar_relacionamento_mary",
    "obter_ou_criar_relacionamento_mary",
    "atualizar_relacionamento_mary",
]
