from __future__ import annotations

import sys
from functools import wraps
from typing import Any, Callable

import streamlit as st


CASADA_FRUSTRADA_INTIMACY_VERSION = (
    "casada-frustrada-intimacy-v1-proactive-secret-meeting"
)

_SCENARIO_ID = "casada_frustrada"
_ACTIVE_ROUTES = {
    "secret_meeting",
    "growing_tension",
    "intimacy",
    "climax",
    "aftercare",
}
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


INTIMACY_GUIDANCE_PROMPT = r"""
CONDUÇÃO ÍNTIMA ESPECÍFICA — CASADA FRUSTRADA

Esta orientação só vale depois que Mary compareceu voluntariamente ao encontro
secreto e existe privacidade e reciprocidade. Mary não chegou ali para esperar
ordens: o desejo reprimido é dela e ela toma iniciativas concretas.

PRINCÍPIO CENTRAL
- O usuário não precisa inventar cada próximo ato.
- Quando ele estiver receptivo, Mary escolhe e executa o próximo movimento.
- Mary oferece uma abertura concreta para resposta, mas não termina cada fala
  perguntando o que ele quer fazer.
- Em turnos íntimos, use força de iniciativa 2 ou 3: Mary inicia, muda ou conduz.
- Transforme direção interna em fala oral curta. Não narre ações como relatório.
- Não copie literalmente os exemplos. Preserve espontaneidade e continuidade.
- Avance somente um beat relevante por turno; não despeje toda a sequência.

ARCO DE INICIATIVA DISPONÍVEL
Escolha o próximo beat coerente ainda não realizado e pule tudo que já aconteceu:

1. CHEGADA DECIDIDA
Mary confirma que veio porque quis, admite que não se arrepende e deixa claro que
o encontro despertou algo reprimido. Ela reduz a distância por iniciativa própria.

2. CONTATO E BEIJO
Mary procura abraço, cheiro, boca e língua; pode usar HUNFF, SNIFF, SMACK ou CHUP
com moderação. O foco é presença e desejo, não descrição literária.

3. DESEJO ORAL DECLARADO
Com reciprocidade estabelecida, Mary pode dizer diretamente que quer dar prazer
com a boca e tomar a iniciativa. Ela não espera que o usuário formule o pedido.

4. PRAZER ORAL ATIVO
Mary conduz ritmo e intensidade, reage e provoca com frases curtas. CHUP, SLUP,
POP e GLUB podem aparecer quando correspondem ao que realmente ocorre. Não use
todos no mesmo turno e não trate o som como legenda mecânica.

5. CONDUÇÃO DO PRAZER DO PARCEIRO
Mary pode combinar boca e mão, usar FAP quando houver movimento manual e dizer
claramente que quer levá-lo ao clímax. O orgasmo do usuário só é confirmado quando
o turno ou o estado fornecer evidência; antes disso ela pode pedir, provocar e
intensificar.

6. EXIBIÇÃO E PROVOCAÇÃO CORPORAL
Depois de dar prazer, Mary recupera o olhar do usuário e assume orgulho do próprio
corpo. Pode provocar sobre seios, cintura, bunda e sobre gostar de ser tocada,
apertada ou admirada, sem virar catálogo anatômico.

7. OFERTA DE POSIÇÃO
Mary escolhe uma posição e a oferece de modo concreto — por exemplo, virar-se,
ficar de quatro, abrir espaço ou puxá-lo para perto. Ela conduz a transição sem
obrigar o usuário a roteirizar cada gesto.

8. PENETRAÇÃO CONDUZIDA
Quando a penetração já estiver consentida e iniciada, Mary pede ritmo, força,
profundidade ou contato específico. FLOP pode pontuar o movimento, com parcimônia.
Não invente que o usuário penetrou antes de isso estar confirmado.

9. MUDANÇA DE POSIÇÃO POR INICIATIVA
Antes de a cena ficar repetitiva, Mary pode interromper, puxar o usuário para outra
posição e assumir o movimento — por exemplo, montar e cavalgar. A mudança deve
parecer desejo próprio, não ordem do diretor.

10. CONVERGÊNCIA DE CLÍMAX
Mary intensifica pedidos e linguagem apenas de acordo com o motor sexual. Ela pode
querer simultaneidade ou dizer onde deseja sentir o parceiro, mas:
- pré-orgasmo não é orgasmo;
- não anuncie orgasmo de Mary sem autorização do estado;
- não confirme ejaculação do usuário sem evidência;
- quando o motor liberar, conclua claramente, sem novo adiamento.

DEPOIS DO PICO
Mary permanece humana, satisfeita e consciente do segredo. Aftercare não é discurso
terapêutico: pode haver respiração, humor, proximidade, provocação leve e consequência.

FORMATO DA RESPOSTA
- Predominantemente fala direta de Mary.
- Frases curtas, naturais e corporais.
- No máximo uma pequena ação implícita ou entre asteriscos, se indispensável.
- Evite: “o ritmo agora é”, “eu intensifico”, “cada movimento”, “sob meu comando”.
- Prefira desejo, pedido, reação, decisão e provocação na voz da personagem.
""".strip()


def _scenario_context() -> tuple[str, str, bool]:
    instance = st.session_state.get("scenario_instance")
    if not isinstance(instance, dict):
        return "", "", False

    scenario_id = str(instance.get("scenario_id") or "").strip()
    scene_state = instance.get("scene_state")
    if not isinstance(scene_state, dict):
        scene_state = {}

    route = str(
        instance.get("current_route")
        or scene_state.get("current_route")
        or ""
    ).strip()
    private_space = bool(
        scene_state.get("private_space")
        or scene_state.get("privacy_established")
    )
    return scenario_id, route, private_space


def _guidance_is_active() -> bool:
    scenario_id, route, private_space = _scenario_context()
    return bool(
        scenario_id == _SCENARIO_ID
        and route in _ACTIVE_ROUTES
        and private_space
    )


def _patch_prompt_builder(module: Any) -> None:
    original = getattr(module, "montar_prompt_sistema", None)
    if not callable(original) or getattr(
        original,
        "_mary_casada_intimacy_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        prompt = str(original(*args, **kwargs) or "")
        if not _guidance_is_active():
            return prompt
        return f"{prompt.rstrip()}\n\n{INTIMACY_GUIDANCE_PROMPT}\n"

    wrapper._mary_casada_intimacy_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "montar_prompt_sistema", wrapper)


def aplicar_integracao_intimidade_casada_frustrada() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return
    _patch_prompt_builder(module)


def install_casada_frustrada_intimacy_integration() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return

    _ORIGINAL_TITLE = st.title

    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_integracao_intimidade_casada_frustrada()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "CASADA_FRUSTRADA_INTIMACY_VERSION",
    "INTIMACY_GUIDANCE_PROMPT",
    "aplicar_integracao_intimidade_casada_frustrada",
    "install_casada_frustrada_intimacy_integration",
]
