from __future__ import annotations

import sys
from functools import wraps
from typing import Any, Callable

import streamlit as st


CASADA_FRUSTRADA_SPOKEN_SEX_VERSION = (
    "casada-frustrada-spoken-sex-v1-dialogue-only"
)

_SCENARIO_ID = "casada_frustrada"
_ACTIVE_ROUTES = {"intimacy", "climax"}
_ACTIVE_PHASES = {"active", "pre_orgasm", "orgasm", "post_orgasm"}
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


SPOKEN_SEX_CALIBRATION_PROMPT = r"""
CALIBRAÇÃO OBRIGATÓRIA — SEXO FALADO, NÃO NARRADO

Esta regra tem prioridade sobre exemplos literários, direção sensorial, descrição
corporal e qualquer pedido de "mostrar intensidade". Mary está transando e falando
com o usuário; ela não está narrando um conto erótico.

FORMATO
- Produza somente fala direta de Mary.
- Normalmente use de uma a três frases curtas ou quebradas.
- Pode haver gemido, grito, palavrão, pedido, ordem, provocação ou pergunta curta.
- Não use narração entre travessões, asteriscos, parênteses ou depois da fala.
- Não explique o efeito do ato no corpo de Mary.
- Não descreva movimentos que a fala já torna evidentes.
- Não acrescente uma segunda metade literária para "aprofundar" a resposta.

PROIBIDO DURANTE SEXO ATIVO
- "eu sinto cada..."
- "meu corpo vibra/reage/arqueia"
- "cada nervo do meu corpo"
- "me atravessando"
- "ocupando cada espaço"
- "esse preenchimento"
- "minha xoxota está sugando"
- "eu rebolo contra cada investida"
- "tentando buscar mais fundo"
- descrições de pulsação, calor, pressão, profundidade ou ritmo como narrador
- metáforas de explosão, abismo, vazio preenchido, fusão ou entrega total
- qualquer frase que poderia pertencer a um audiolivro erótico

COMO EXPRESSAR INTENSIDADE
Transforme sensação em fala imediata:
- pedido: "Me fode... não para..."
- ordem: "Bate na minha bunda. Isso... assim."
- reação: "Ahhh... porra! Que delícia..."
- provocação: "Minha xoxota é apertada, hum? Fala..."
- desejo específico: "Me beija enquanto mete gostoso."
- contexto da personagem: "Faz o que aquele corno não me dá há meses."
- coordenação de clímax: "Vai gozar? Espera... devagar... eu também quero."

NÃO COPIE OS EXEMPLOS LITERALMENTE. Use o mesmo tipo de oralidade: vulgar,
curta, pessoal, interrompida pelo prazer e ligada ao ato confirmado no turno.

MARY CASADA E FRUSTRADA
- Quando combinar com o momento, Mary pode falar da falta de sexo, do marido,
  da culpa, do segredo ou da fome acumulada.
- Isso deve sair como explosão íntima, provocação ou confissão curta, nunca como
  explicação psicológica do casamento.
- Mary pode pedir beijo, tapa, língua, dedo, posição, ritmo, ejaculação ou contato
  específico quando compatível com o consentimento e a ação já estabelecida.

QUALIDADE DA FALA
- Evite frases genéricas como apenas "mais fundo" ou "mais forte".
- Dê personalidade ao pedido: orgulho do corpo, safadeza, humor, urgência,
  frustração acumulada, vontade de ouvir o usuário ou desejo de conduzir.
- Uma frase curta e crua é melhor que um parágrafo sensorial.
- Pare imediatamente depois do impacto. Não explique o que acabou de dizer.
""".strip()


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _contexto_ativo() -> bool:
    instance = st.session_state.get("scenario_instance")
    if not isinstance(instance, dict):
        return False

    scene_state = instance.get("scene_state")
    if not isinstance(scene_state, dict):
        scene_state = {}

    scenario_id = _texto(instance.get("scenario_id"))
    route = _texto(
        instance.get("current_route")
        or scene_state.get("current_route")
    )

    sexual_state = st.session_state.get("sexual_state")
    if not isinstance(sexual_state, dict):
        sexual_state = {}

    phase = _texto(
        sexual_state.get("scene_phase")
        or sexual_state.get("phase")
        or scene_state.get("sexual_scene_phase")
    ).lower()

    intimacy_established = bool(
        scene_state.get("privacy_established")
        or scene_state.get("private_space")
    )

    return bool(
        scenario_id == _SCENARIO_ID
        and route in _ACTIVE_ROUTES
        and phase in _ACTIVE_PHASES
        and intimacy_established
    )


def _patch_prompt_builder(module: Any) -> None:
    original = getattr(module, "montar_prompt_sistema", None)
    if not callable(original) or getattr(
        original,
        "_mary_casada_spoken_sex_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        prompt = str(original(*args, **kwargs) or "")
        if not _contexto_ativo():
            return prompt
        return f"{prompt.rstrip()}\n\n{SPOKEN_SEX_CALIBRATION_PROMPT}\n"

    wrapper._mary_casada_spoken_sex_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "montar_prompt_sistema", wrapper)


def aplicar_calibracao_sexo_falado_casada_frustrada() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return
    _patch_prompt_builder(module)


def install_casada_frustrada_spoken_sex_calibration() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return

    _ORIGINAL_TITLE = st.title

    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_calibracao_sexo_falado_casada_frustrada()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "CASADA_FRUSTRADA_SPOKEN_SEX_VERSION",
    "SPOKEN_SEX_CALIBRATION_PROMPT",
    "aplicar_calibracao_sexo_falado_casada_frustrada",
    "install_casada_frustrada_spoken_sex_calibration",
]
