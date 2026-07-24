from __future__ import annotations

from typing import Any

import google_sheets_repository as sheets_repository
import ui.scenario_catalog_persistence as catalog_persistence


SCENARIO_CATALOG_VISIBILITY_FIX_VERSION = (
    "scenario-catalog-visibility-fix-v1-blank-flags-default-active"
)

_INSTALLED = False
_NORMALIZED = False


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _booleano_com_padrao(value: Any, *, default: bool = False) -> bool:
    """Célula vazia significa ausência de override, não FALSE."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)

    text = _texto(value).lower()
    if not text:
        return default
    if text in {
        "true", "1", "sim", "yes", "verdadeiro", "active", "ativo",
        "published", "publicado",
    }:
        return True
    if text in {
        "false", "0", "nao", "não", "no", "falso", "inactive",
        "inativo", "unpublished", "nao_publicado", "não_publicado",
    }:
        return False
    return default


def normalizar_flags_catalogo_vazias() -> int:
    """Preenche flags vazias existentes uma única vez, sem reativar bloqueios explícitos."""
    global _NORMALIZED
    if _NORMALIZED:
        return 0
    _NORMALIZED = True

    try:
        rows = sheets_repository.obter_registros_aba(
            catalog_persistence.SCENARIOS_SHEET
        )
    except Exception:
        return 0

    updated = 0
    for row in rows:
        scenario_id = _texto(row.get("scenario_id"))
        if not scenario_id:
            continue

        changes: dict[str, Any] = {}
        if not _texto(row.get("status")):
            changes["status"] = "active"
        if not _texto(row.get("published")):
            changes["published"] = True
        if not _texto(row.get("active")):
            changes["active"] = True

        if not changes:
            continue

        changes["updated_at"] = sheets_repository.utc_now_iso()
        try:
            sheets_repository.atualizar_registro(
                catalog_persistence.SCENARIOS_SHEET,
                coluna_chave="scenario_id",
                valor_chave=scenario_id,
                alteracoes=changes,
            )
            updated += 1
        except Exception:
            # A correção lógica já mantém o catálogo embarcado visível.
            continue

    return updated


def install_scenario_catalog_visibility_fix() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    # O módulo já está importado pelo pacote ui. A troca entra antes da primeira
    # chamada do catálogo e corrige tanto a sincronização quanto os overrides.
    catalog_persistence._booleano = _booleano_com_padrao
    normalizar_flags_catalogo_vazias()
    _INSTALLED = True


__all__ = [
    "SCENARIO_CATALOG_VISIBILITY_FIX_VERSION",
    "install_scenario_catalog_visibility_fix",
    "normalizar_flags_catalogo_vazias",
]
