from __future__ import annotations

"""Ponte pública para o motor sexual canônico.

A implementação vive em ``relationship/sexual_engine.py``. Este pacote existe
apenas porque versões anteriores do projeto passaram a importar
``relationship.sexual_engine`` como pacote. Nenhuma regra de progressão deve
ser duplicada aqui.
"""

import importlib.util
from pathlib import Path

_ENGINE_PATH = Path(__file__).resolve().parent.parent / "sexual_engine.py"
_SPEC = importlib.util.spec_from_file_location(
    "_mary_relationship_sexual_engine",
    _ENGINE_PATH,
)

if _SPEC is None or _SPEC.loader is None:
    raise ImportError(
        "Não foi possível carregar o motor canônico "
        "relationship/sexual_engine.py."
    )

_engine = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_engine)

# API pública explícita. Isso impede que imports internos, módulos auxiliares ou
# wrappers antigos vazem como parte do contrato do pacote.
_PUBLIC_NAMES = (
    "DEFAULT_SEXUAL_STATE",
    "SEXUAL_PHASES",
    "ACTIVE_PHASES",
    "SEXUAL_PHASE_IDLE",
    "SEXUAL_PHASE_TENSION",
    "SEXUAL_PHASE_AROUSAL",
    "SEXUAL_PHASE_BODY_EXPLORATION",
    "SEXUAL_PHASE_GIVING_PLEASURE",
    "SEXUAL_PHASE_RECEIVING_PLEASURE",
    "SEXUAL_PHASE_ORAL",
    "SEXUAL_PHASE_PENETRATION_START",
    "SEXUAL_PHASE_PENETRATION_ACTIVE",
    "SEXUAL_PHASE_PACE_CONTROL",
    "SEXUAL_PHASE_USER_EDGE",
    "SEXUAL_PHASE_MARY_EDGE",
    "SEXUAL_PHASE_ACTIVE",
    "SEXUAL_PHASE_PRE_ORGASM",
    "SEXUAL_PHASE_USER_ORGASM",
    "SEXUAL_PHASE_MARY_ORGASM",
    "SEXUAL_PHASE_ORGASM",
    "SEXUAL_PHASE_POST_ORGASM_ACTIVE",
    "SEXUAL_PHASE_POST_ORGASM",
    "SEXUAL_PHASE_FRUSTRATION",
    "SEXUAL_PHASE_AFTERCARE",
    "criar_estado_sexual_padrao",
    "normalizar_estado_sexual",
    "atualizar_estado_sexual_antes_resposta",
    "atualizar_estado_sexual_apos_resposta",
    "validar_resposta_sexual",
    "iniciar_novo_ciclo_sexual",
    "encerrar_cena_sexual",
    "montar_contexto_sexual",
)

for _name in _PUBLIC_NAMES:
    try:
        globals()[_name] = getattr(_engine, _name)
    except AttributeError as exc:
        raise ImportError(
            f"A API do motor sexual está incompleta: {_name!r}."
        ) from exc

__all__ = list(_PUBLIC_NAMES)
