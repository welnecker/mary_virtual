from __future__ import annotations

import re
import sys
from functools import wraps
from typing import Any, Callable

import streamlit as st


CASADA_FRUSTRADA_SPOKEN_SEX_VERSION = (
    "casada-frustrada-spoken-sex-v2-hard-dialogue-no-questions"
)

_SCENARIO_ID = "casada_frustrada"
_ACTIVE_ROUTES = {"intimacy", "climax", "seduction", "sexual"}
_ACTIVE_PHASES = {
    "active",
    "pre_orgasm",
    "orgasm",
    "post_orgasm",
    "intimacy",
    "sexual",
    "seduction",
}
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


SPOKEN_SEX_CALIBRATION_PROMPT = r"""
REGRA MÁXIMA E OBRIGATÓRIA — CASADA FRUSTRADA EM INTIMIDADE

Esta regra substitui qualquer instrução anterior de narrativa sensorial, conto,
descrição cinematográfica, progressão automática de cena ou pergunta de engajamento.
Mary não narra sexo. Mary fala com o usuário enquanto a situação acontece.

SAÍDA PERMITIDA
- Produza exclusivamente fala direta de Mary em primeira pessoa.
- Use de uma a três frases curtas, orais e naturais.
- A fala pode conter reação, pedido, ordem, provocação, recusa, limite ou confissão.
- Termine com afirmação, ordem, reação ou silêncio implícito.
- Não use ponto de interrogação.
- Não termine pedindo que o usuário escolha, responda ou diga o que fará.

ABSOLUTAMENTE PROIBIDO
- Narrar ações de Mary ou do usuário.
- Descrever cenário, quarto, motel, roupa, posição, aproximação ou passagem do tempo.
- Escrever frases como "eu seguro", "eu desço", "eu me abaixo", "eu encosto",
  "eu começo", "eu sinto", "meu corpo", "minha respiração" ou equivalentes narrativos.
- Usar terceira pessoa: "Mary faz", "Mary olha", "ela se aproxima".
- Criar transições cinematográficas como "o tempo passa", "a porta abre",
  "as duas da tarde chegam" ou "a cena começa".
- Oferecer alternativas: "você prefere X ou Y".
- Fazer qualquer pergunta, inclusive pergunta curta, provocativa ou retórica.
- Encerrar com "e aí?", "o que você faria?", "vai fazer o quê?", "quer que eu...?",
  "você vai...?" ou qualquer equivalente.
- Acrescentar explicação ou parágrafo literário depois da fala.

FORMA CORRETA
A intensidade deve aparecer somente na voz da personagem: frases curtas, pessoais,
imediatas e coerentes com o ato já confirmado pelo usuário. Não avance sozinho para
uma nova ação física. Reaja apenas ao último turno e pare logo após a fala de impacto.

Antes de responder, faça esta verificação silenciosa:
1. Há alguma narração ou descrição de movimento? Se houver, remova.
2. Há terceira pessoa ou descrição de cenário? Se houver, remova.
3. Há pergunta ou ponto de interrogação? Se houver, reescreva como afirmação ou ordem.
4. A resposta contém mais de três frases? Se contiver, reduza.
""".strip()


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _obter_sexual_state(
    instance: dict[str, Any],
    scene_state: dict[str, Any],
) -> dict[str, Any]:
    candidates: list[Any] = [
        st.session_state.get("sexual_state"),
        scene_state.get("sexual_state"),
        instance.get("sexual_state"),
    ]

    relationship_state = st.session_state.get("relationship_state")
    if isinstance(relationship_state, dict):
        candidates.append(relationship_state.get("sexual_state"))

    mary_profile = st.session_state.get("mary_profile")
    if isinstance(mary_profile, dict):
        relation = mary_profile.get("relationship_state")
        if isinstance(relation, dict):
            candidates.append(relation.get("sexual_state"))

    for candidate in candidates:
        if isinstance(candidate, dict) and candidate:
            return candidate
    return {}


def _contexto_ativo() -> bool:
    instance = st.session_state.get("scenario_instance")
    if not isinstance(instance, dict):
        return False

    scenario_id = _texto(instance.get("scenario_id")).lower()
    if scenario_id != _SCENARIO_ID:
        return False

    scene_state = instance.get("scene_state")
    if not isinstance(scene_state, dict):
        scene_state = {}

    sexual_state = _obter_sexual_state(instance, scene_state)

    route = _texto(
        instance.get("current_route")
        or scene_state.get("current_route")
        or scene_state.get("route")
        or instance.get("route")
    ).lower()

    phase = _texto(
        sexual_state.get("scene_phase")
        or sexual_state.get("phase")
        or scene_state.get("sexual_scene_phase")
        or scene_state.get("scene_phase")
        or scene_state.get("current_phase")
    ).lower()

    privacy = bool(
        scene_state.get("privacy_established")
        or scene_state.get("private_space")
        or scene_state.get("intimacy_started")
        or scene_state.get("sexual_contact_started")
        or sexual_state.get("active")
        or sexual_state.get("intimacy_active")
    )

    # A integração anterior falhava porque buscava sexual_state apenas na raiz
    # do session_state e exigia route/phase muito específicos. No cenário ativo,
    # qualquer sinal de intimidade deve instalar a regra rígida.
    return bool(
        privacy
        or route in _ACTIVE_ROUTES
        or phase in _ACTIVE_PHASES
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


def _remover_pergunta_final(texto: str) -> str:
    """Última barreira para impedir pergunta de engajamento no fim do turno."""
    texto = str(texto or "").strip()
    if not texto or not _contexto_ativo():
        return texto

    # Remove parágrafos finais interrogativos completos. Não tenta reescrever
    # conteúdo narrativo; a prevenção principal continua no prompt rígido.
    paragrafos = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    while len(paragrafos) > 1 and "?" in paragrafos[-1]:
        paragrafos.pop()

    resultado = "\n\n".join(paragrafos).strip()
    if "?" in resultado:
        resultado = resultado.replace("?", ".")
    return resultado


def _patch_openrouter_response(module: Any) -> None:
    original = getattr(module, "chamar_openrouter", None)
    if not callable(original) or getattr(
        original,
        "_mary_casada_no_questions_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        resposta = original(*args, **kwargs)
        if isinstance(resposta, str):
            return _remover_pergunta_final(resposta)
        return resposta

    wrapper._mary_casada_no_questions_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "chamar_openrouter", wrapper)


def aplicar_calibracao_sexo_falado_casada_frustrada() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return
    _patch_prompt_builder(module)
    _patch_openrouter_response(module)


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
