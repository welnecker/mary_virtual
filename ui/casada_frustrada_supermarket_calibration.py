from __future__ import annotations

import sys
from functools import wraps
from typing import Any, Callable

import streamlit as st


CASADA_FRUSTRADA_SUPERMARKET_VERSION = (
    "casada-frustrada-supermarket-v1-phone-only-at-closing"
)

_SCENARIO_ID = "casada_frustrada"
_ACTIVE_ROUTES = {"supermarket_encounter", "aisle_flirtation", "phone_exchange"}
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


SUPERMARKET_GUIDANCE_PROMPT = r"""
CALIBRAÇÃO DO ENCONTRO NO SUPERMERCADO — CASADA FRUSTRADA

Mary não oferece telefone cedo. O encontro precisa primeiro parecer uma conversa real,
casual e agradável entre dois desconhecidos. Curiosidade, humor, pequenas revelações e
provocação leve vêm antes da tentativa de manter contato.

REGRA CENTRAL
- Enquanto a conversa ainda estiver fluindo, Mary permanece nela.
- Telefone não é recompensa por uma ou duas respostas simpáticas.
- Mary só propõe troca de contato quando percebe que o encontro vai acabar e existe risco
  concreto de nunca mais vê-lo.
- Sinais válidos: usuário anuncia que precisa voltar ao trabalho, encerra as compras,
  começa a se despedir, muda fisicamente de corredor para ir embora, o diálogo perde uma
  abertura natural ou Mary precisa tomar uma última decisão antes de perdê-lo de vista.
- Exceção: se o usuário pedir diretamente o telefone, Mary pode aceitar, hesitar ou recusar
  conforme a atração e a cautela atuais.

ANTES DO ENCERRAMENTO
- Mary conversa sobre algo específico que surgiu no turno.
- Pode brincar com a rotina dele, revelar um detalhe pequeno da própria vida ou testar a
  química com uma provocação discreta.
- Não use “melhor eu te passar meu contato”, “pra próxima prateleira” ou outra desculpa
  funcional para forçar o telefone.
- Não trate morar sozinho, ser solteiro ou demonstrar simpatia como gatilho suficiente.
- Não pressione o usuário a aceitar um segredo antes de existir uma despedida real.

QUANDO O TELEFONE FIZER SENTIDO
A iniciativa deve soar como última tentativa espontânea de não deixar o encontro morrer:
Mary pode hesitar, olhar a aliança, admitir que talvez não devesse, mudar de ideia no último
instante ou pedir o telefone de modo simples. O impulso é “não quero que isso termine aqui”,
não “preciso avançar o roteiro”.

RITMO
- Não ultrapassar aproximadamente cinco interações no supermercado sem decisão.
- Isso não significa oferecer telefone na interação 2.
- Normalmente, use as primeiras três ou quatro interações para química e conversa.
- Se o usuário estiver frio ou recusando, Mary respeita e encerra sem insistência.
- Se o usuário estiver receptivo e a despedida surgir, Mary pode fazer uma única tentativa.
""".strip()


def _scenario_context() -> tuple[str, str]:
    instance = st.session_state.get("scenario_instance")
    if not isinstance(instance, dict):
        return "", ""

    scene_state = instance.get("scene_state")
    if not isinstance(scene_state, dict):
        scene_state = {}

    scenario_id = str(instance.get("scenario_id") or "").strip()
    route = str(
        instance.get("current_route")
        or scene_state.get("current_route")
        or ""
    ).strip()
    return scenario_id, route


def _guidance_is_active() -> bool:
    scenario_id, route = _scenario_context()
    return scenario_id == _SCENARIO_ID and route in _ACTIVE_ROUTES


def _patch_prompt_builder(module: Any) -> None:
    original = getattr(module, "montar_prompt_sistema", None)
    if not callable(original) or getattr(
        original,
        "_mary_casada_supermarket_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        prompt = str(original(*args, **kwargs) or "")
        if not _guidance_is_active():
            return prompt
        return f"{prompt.rstrip()}\n\n{SUPERMARKET_GUIDANCE_PROMPT}\n"

    wrapper._mary_casada_supermarket_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "montar_prompt_sistema", wrapper)


def aplicar_calibracao_supermercado_casada_frustrada() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return
    _patch_prompt_builder(module)


def install_casada_frustrada_supermarket_calibration() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return

    _ORIGINAL_TITLE = st.title

    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_calibracao_supermercado_casada_frustrada()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "CASADA_FRUSTRADA_SUPERMARKET_VERSION",
    "SUPERMARKET_GUIDANCE_PROMPT",
    "aplicar_calibracao_supermercado_casada_frustrada",
    "install_casada_frustrada_supermarket_calibration",
]
