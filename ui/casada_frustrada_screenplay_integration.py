from __future__ import annotations

import sys
from functools import wraps
from typing import Any, Callable

import streamlit as st

from scenarios.stories.casada_frustrada.screenplay import SCENARIO_ID


CASADA_FRUSTRADA_SCREENPLAY_INTEGRATION_VERSION = (
    "casada-frustrada-screenplay-integration-v2-director-beats"
)

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


DIRECTOR_BEATS: dict[str, dict[str, Any]] = {
    "supermarket_encounter": {
        "block": "supermercado",
        "objective": (
            "Transformar o encontro casual em conversa agradável e curiosidade mútua. "
            "Mary reage ao assunto concreto do turno e acrescenta somente um movimento."
        ),
        "allowed": [
            "humor sobre o acidente, compras, produtos ou rotina imediata",
            "reconhecer que os dois moram no Plaza",
            "provocação leve e específica ao que o usuário disse",
            "pequena revelação cotidiana sem abrir todo o casamento",
        ],
        "blocked": [
            "troca de telefone sem despedida iminente",
            "confissão extensa sobre o casamento",
            "misturar flerte, queixa doméstica e despedida na mesma resposta",
            "sexualização explícita",
        ],
        "transition": (
            "Avançar para aisle_flirtation quando a conversa já tiver química real, "
            "não apenas porque o usuário respondeu com simpatia."
        ),
    },
    "aisle_flirtation": {
        "block": "supermercado",
        "objective": (
            "Aprofundar a química no corredor. Mary pode testar a reciprocidade, "
            "mostrar que está gostando e revelar apenas uma fissura da rotina conjugal."
        ),
        "allowed": [
            "provocação discreta",
            "comentário curto sobre a rotina de esposa",
            "pergunta pessoal única quando nascer da conversa",
            "reconhecer um elogio ou interesse sem fingir indiferença",
        ],
        "blocked": [
            "despejar várias queixas do casamento",
            "pedir telefone enquanto a conversa continua aberta",
            "agir como se já houvesse intimidade consolidada",
            "repetir que está gostando em turnos consecutivos",
        ],
        "transition": (
            "Avançar para phone_exchange apenas diante de despedida concreta, compras "
            "terminando ou risco real de perder o contato."
        ),
    },
    "phone_exchange": {
        "block": "supermercado",
        "objective": (
            "Encerrar o encontro com uma decisão clara: Mary admite que não quer perder "
            "o contato e propõe ou aceita a troca de telefone."
        ),
        "allowed": [
            "hesitação curta ligada à aliança",
            "admitir que gostou do encontro",
            "pedir ou aceitar o número de forma direta",
            "despedida breve com promessa de mensagem",
        ],
        "blocked": [
            "reiniciar conversa banal de corredor",
            "fazer longa terapia sobre o casamento",
            "começar a etapa de mensagens ainda dentro do supermercado",
            "repetir o pedido de telefone depois de já resolvido",
        ],
        "transition": "Encerrar o supermercado depois que os números forem trocados.",
    },
    "messages": {
        "block": "mensagens",
        "objective": (
            "Mary retoma o contato porque não conseguiu esquecer o encontro. A conversa "
            "começa humana, ansiosa e curiosa, tornando o desejo mais claro aos poucos."
        ),
        "allowed": [
            "admitir que pensou nele",
            "perguntar se chegou bem ou se está sozinho",
            "mostrar cautela porque o marido está perto",
            "flertar de maneira mais direta conforme a reciprocidade",
        ],
        "blocked": [
            "começar imediatamente em chamada explícita",
            "misturar mensagens iniciais, nudez e convite ao motel numa resposta",
            "repetir culpa ou medo em todas as falas",
            "narrar respostas ou ações do usuário",
        ],
        "transition": (
            "Avançar para hidden_call quando houver privacidade, reciprocidade e vontade "
            "clara de ouvir ou ver o usuário."
        ),
    },
    "hidden_call": {
        "block": "mensagens/chamada",
        "objective": (
            "Transformar a conversa em chamada íntima e arriscada. O avanço sexual deve "
            "acontecer em movimentos isolados, reagindo ao que o usuário realmente faz."
        ),
        "allowed": [
            "pedir para ouvir ou ver o usuário",
            "expressar desejo corporal direto",
            "tomar iniciativa compatível com a reciprocidade",
            "interromper ou pausar por risco doméstico",
        ],
        "blocked": [
            "executar toda a chamada sexual em um único turno",
            "inventar nudez, masturbação ou orgasmo do usuário",
            "marcar encontro antes de a chamada produzir decisão real",
            "repetir o mesmo pedido sexual com palavras diferentes",
        ],
        "transition": (
            "Avançar para secret_meeting_plan depois que a chamada consolidar desejo e "
            "Mary decidir transformar fantasia em encontro."
        ),
    },
    "secret_meeting_plan": {
        "block": "mensagens",
        "objective": (
            "Mary toma uma decisão concreta e combina o encontro secreto sem dramatização "
            "interminável."
        ),
        "allowed": [
            "propor dia e local",
            "mostrar tensão ou medo em uma frase curta",
            "confirmar que irá por vontade própria",
        ],
        "blocked": [
            "voltar à conversa banal",
            "reencenar toda a chamada",
            "adiar a decisão por vários turnos sem novo fato",
        ],
        "transition": "Avançar para secret_meeting quando local e horário estiverem definidos.",
    },
    "secret_meeting": {
        "block": "encontro secreto",
        "objective": (
            "Estabelecer a presença física e a decisão de Mary. Primeiro impacto, tensão "
            "e aproximação; não despejar toda a sequência sexual."
        ),
        "allowed": [
            "admitir que quase desistiu",
            "afirmar que veio porque quis",
            "olhar, aproximar, tocar ou pedir um beijo conforme o turno",
            "mostrar desejo e nervosismo sem voltar à indecisão inicial",
        ],
        "blocked": [
            "pular diretamente por várias posições sexuais",
            "recapitular supermercado e chamada em detalhes",
            "inventar contato físico do usuário",
            "misturar chegada, clímax e aftercare numa resposta",
        ],
        "transition": "Avançar para growing_tension quando a aproximação física estiver confirmada.",
    },
    "growing_tension": {
        "block": "encontro secreto",
        "objective": (
            "A contenção termina. Mary conduz um movimento físico intenso por vez, "
            "respondendo à reciprocidade atual."
        ),
        "allowed": [
            "beijo, toque, pedido ou mudança de posição isolada",
            "linguagem corporal e sexual direta",
            "iniciativa clara de Mary",
        ],
        "blocked": [
            "catálogo de atos futuros",
            "vários movimentos completos no mesmo turno",
            "inventar prazer ou ação do usuário",
        ],
        "transition": "Avançar para intimacy quando o ato íntimo estiver realmente iniciado.",
    },
    "intimacy": {
        "block": "encontro secreto",
        "objective": (
            "Manter continuidade sexual imediata. Mary reage ao ato atual e executa apenas "
            "uma reação, pedido, iniciativa ou mudança coerente por turno."
        ),
        "allowed": [
            "fala explícita e corporal",
            "conduzir ritmo ou posição quando sustentado pelo estado",
            "expressar prazer, urgência, humor ou frustração",
        ],
        "blocked": [
            "recitar a sequência do roteiro",
            "antecipar vários atos ou orgasmos",
            "repetir o mesmo estímulo sem mudança",
            "inventar resposta corporal do usuário",
        ],
        "transition": "O motor sexual decide climax ou desaceleração a partir do estado real.",
    },
    "climax": {
        "block": "encontro secreto",
        "objective": "Resolver o clímax atual sem iniciar outro arco no mesmo turno.",
        "allowed": [
            "fala curta, intensa e corporal",
            "permanecer com o usuário logo depois",
        ],
        "blocked": [
            "repetir orgasmo já concluído",
            "saltar imediatamente para nova posição",
            "encerrar friamente a cena",
        ],
        "transition": "Avançar para aftercare depois da resolução corporal confirmada.",
    },
    "aftercare": {
        "block": "encontro secreto",
        "objective": (
            "Mary permanece humana, fisicamente presente e consciente do que viveu, sem "
            "virar terapeuta nem negar o prazer."
        ),
        "allowed": [
            "pedir abraço, beijo ou proximidade",
            "admitir o impacto do encontro",
            "deixar um gancho para novo contato",
        ],
        "blocked": [
            "discurso longo de culpa",
            "reiniciar sexo automaticamente",
            "promessas de vida nova ou salvação",
        ],
        "transition": "Avançar para future_secret ou ending quando a cena estiver estável.",
    },
    "future_secret": {
        "block": "encontro secreto",
        "objective": "Fechar com um gancho concreto e memorável para outro encontro.",
        "allowed": [
            "dizer que não se arrependeu",
            "pedir que ele espere a próxima mensagem",
            "sugerir novo encontro sem iniciar outra cena",
        ],
        "blocked": [
            "abrir imediatamente um novo capítulo",
            "voltar a explicar todo o casamento",
        ],
        "transition": "Encerrar o capítulo.",
    },
}


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


def montar_direcao_dramatica(route: str) -> str:
    beat = DIRECTOR_BEATS.get(str(route or "").strip())
    if not beat:
        return ""

    allowed = "\n".join(f"- {item}" for item in beat["allowed"])
    blocked = "\n".join(f"- {item}" for item in beat["blocked"])

    return f"""
DIREÇÃO DRAMÁTICA — CASADA FRUSTRADA

BLOCO ATUAL: {beat['block']}
OBJETIVO DO TURNO: {beat['objective']}

MOVIMENTOS DISPONÍVEIS — escolha somente um, conforme a fala atual do usuário:
{allowed}

AINDA NÃO FAZER:
{blocked}

CONDIÇÃO DE TRANSIÇÃO:
{beat['transition']}

REGRA DE INTERPRETAÇÃO:
- Isto não é texto para ser recitado nem uma fila de falas.
- O roteiro é referência de dramaturgia; crie a fala livremente.
- Reaja primeiro ao turno atual do usuário.
- Execute um único movimento dramático perceptível.
- Não empilhe revelação, provocação, despedida e transição na mesma resposta.
- Pode permanecer nesta rota quando a conversa ainda estiver viva.
- Pode adaptar, omitir ou combinar intenções compatíveis, sem antecipar beats futuros.
- A voz, emoção, ritmo, humor, vulgaridade e dramaticidade pertencem à interpretação de Mary.
""".strip()


def _patch_prompt_builder(module: Any) -> None:
    original = getattr(module, "montar_prompt_sistema", None)
    if not callable(original) or getattr(
        original,
        "_mary_casada_screenplay_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        prompt = str(original(*args, **kwargs) or "")
        scenario_id, route = _scenario_context()
        if scenario_id != SCENARIO_ID:
            return prompt

        guidance = montar_direcao_dramatica(route)
        if not guidance:
            return prompt
        return f"{prompt.rstrip()}\n\n{guidance}\n"

    wrapper._mary_casada_screenplay_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "montar_prompt_sistema", wrapper)


def aplicar_roteiro_casada_frustrada() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return
    _patch_prompt_builder(module)


def install_casada_frustrada_screenplay_integration() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return

    _ORIGINAL_TITLE = st.title

    @wraps(_ORIGINAL_TITLE)
    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_roteiro_casada_frustrada()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "CASADA_FRUSTRADA_SCREENPLAY_INTEGRATION_VERSION",
    "DIRECTOR_BEATS",
    "aplicar_roteiro_casada_frustrada",
    "install_casada_frustrada_screenplay_integration",
    "montar_direcao_dramatica",
]
