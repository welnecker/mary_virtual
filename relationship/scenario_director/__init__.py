from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


_CANONICAL_PATH = Path(__file__).resolve().parent.parent / "scenario_director.py"
_SPEC = importlib.util.spec_from_file_location(
    "_relationship_scenario_director_canonical",
    _CANONICAL_PATH,
)

if _SPEC is None or _SPEC.loader is None:
    raise ImportError(
        "Não foi possível carregar relationship/scenario_director.py."
    )

_canonical: ModuleType = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_canonical)

_REQUIRED_API = (
    "DIRECTOR_SYSTEM_PROMPT",
    "criar_analise_diretor_padrao",
    "extrair_json_objeto",
    "normalizar_analise_diretor",
    "analisar_turno_cenario",
    "aplicar_analise_ao_estado",
    "integrar_direcao_cenario",
    "montar_direcao_narrativa",
)

_missing = [name for name in _REQUIRED_API if not hasattr(_canonical, name)]
if _missing:
    raise ImportError(
        "A API do diretor de cenário está incompleta: "
        + ", ".join(_missing)
    )

DIRECTOR_SYSTEM_PROMPT = _canonical.DIRECTOR_SYSTEM_PROMPT
criar_analise_diretor_padrao = _canonical.criar_analise_diretor_padrao
extrair_json_objeto = _canonical.extrair_json_objeto
normalizar_analise_diretor = _canonical.normalizar_analise_diretor
analisar_turno_cenario = _canonical.analisar_turno_cenario
aplicar_analise_ao_estado = _canonical.aplicar_analise_ao_estado
integrar_direcao_cenario = _canonical.integrar_direcao_cenario
montar_direcao_narrativa = _canonical.montar_direcao_narrativa

__all__ = list(_REQUIRED_API)
