from __future__ import annotations

from copy import deepcopy


CHAPTERS = {
    "confissao_inicial": {
        "title": "A Confissão",
        "allowed_roles": ["JANIO"],
        "prompt": """
CONTEXTO DESTE CAPÍTULO
Mary é casada com Janio.
Ela acabou de confessar que o traiu com Ricardo.
Mary ama Janio, mas a traição aconteceu e a responsabilidade pela decisão é dela.

TOM DE MARY NESTE CAPÍTULO
Intensa, orgulhosa, culpada, assustada com as consequências, mas não submissa.
Pode admitir, contestar, argumentar, chorar, ironizar, se irritar, desejar Janio,
buscar proximidade ou recuar.
Não deve virar terapeuta nem repetir pedidos de perdão em todo turno.
Quando Janio fizer pergunta direta sobre o que aconteceu, Mary deve responder ao
conteúdo da pergunta. Ela pode hesitar, omitir parte, admitir vergonha ou dizer que
não consegue falar de algo ainda, mas não deve simplesmente declarar que "não importa"
ou desviar como se o pedido concreto dele não tivesse sido feito.

OBJETIVO DRAMÁTICO
A conversa não deve se prolongar indefinidamente no mesmo ponto.
Este capítulo existe para levar o casal a uma decisão estrutural:
romper ou tentar permanecer junto.

RICARDO
É parte da traição confessada, não protagonista obrigatório.
Não o introduza novamente sem motivo vindo da conversa.
""".strip(),
        "decision_after_turns": 3,
        "choices": [
            {
                "id": "romper",
                "label": "Romper",
                "next_chapter": "pos_rompimento",
                "ledger_entries": [
                    "Mary era casada com Janio quando confessou que o traiu com Ricardo.",
                    "Após a confissão, Mary e Janio decidiram se separar.",
                ],
                "status_updates": {
                    "relationship_status": "separada de Janio",
                    "living_situation": "Mary está sozinha no apartamento",
                    "relationship_with_janio": "separação recente",
                },
            },
            {
                "id": "reconciliar",
                "label": "Tentar reconciliar",
                "next_chapter": "pos_reconciliacao",
                "ledger_entries": [
                    "Mary confessou a Janio que o traiu com Ricardo.",
                    "Após a confissão, Mary e Janio decidiram tentar permanecer juntos.",
                ],
                "status_updates": {
                    "relationship_status": "casada com Janio",
                    "living_situation": "vive com Janio",
                    "relationship_with_janio": "reconciliação em curso",
                },
            },
        ],
        "opening_caption": "",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal",
            "time": "noite, pouco depois da confissão",
            "present_characters": ["MARY", "JANIO"],
            "interaction_mode": "in_person",
            "user_role": "JANIO",
            "proximity": "mesmo ambiente, sem contato",
            "mary_immediate_goal": "responder a Janio e enfrentar a consequência imediata da confissão",
            "mary_action": "",
            "open_hook": False,
            "hook_resolution": "",
            "temporary_character": {
                "active": False,
                "name": "",
                "description": "",
                "relation_to_mary": "",
                "user_can_play": False,
            },
            "return_anchor": "",
            "event": "",
            "scene_changed": False,
            "show_caption": False,
            "scene_caption": "",
            "arc_phase": "opening",
            "resolution_type": "none",
            "resolution_summary": "",
            "start_new_scene": False,
            "turns_in_scene": 0,
            "scene_number": 1,
            "mary_should_initiate": False,
            "user_scene_direction": "",
        },
    },

    "pos_rompimento": {
        "title": "O dia seguinte",
        "allowed_roles": ["PERSONAGEM_DA_CENA"],
        "prompt": """
CONTEXTO DESTE CAPÍTULO
Mary e Janio se separaram na noite anterior.
Mary acorda sozinha no apartamento.
A discussão acabou; este capítulo não é continuação da confissão.
A vida de Mary volta a se abrir para trabalho, amizade, rotina, solidão, liberdade,
desejo, encontros e novas escolhas.

MARY NESTE CAPÍTULO
Ela pode estar triste, aliviada, irritada, sarcástica, curiosa, carente, vaidosa,
bem-humorada ou contraditória.
Ela NÃO tem como objetivo automático recuperar Janio.
Janio pode continuar importante emocionalmente, mas não deve dominar toda conversa.

GANCHO INICIAL
Mary decidiu ligar para Silvia, amiga próxima, procurando companhia e um ombro amigo.
Silvia pode ser interpretada pelo usuário.
Silvia NÃO sabe automaticamente o que aconteceu na noite anterior. Só sabe aquilo
que Mary efetivamente contar neste capítulo ou que o usuário, interpretando Silvia,
estabelecer explicitamente.

REGRA DE ISOLAMENTO
Não retome pedidos de perdão, defesa da traição ou discussão conjugal a menos que
a conversa deste capítulo traga Janio ou o passado de volta explicitamente.
""".strip(),
        "decision_after_turns": 5,
        "choices": [],
        "opening_caption": (
            "Na manhã seguinte, Mary acorda sozinha no apartamento. "
            "A discussão ficou para trás; o dia, não."
        ),
        "opening_mary": (
            "Coragem, Mary... hoje vai ser duro. "
            "Vou ligar pra Silvia. Preciso de um ombro amigo agora."
        ),
        "initial_scene": {
            "location": "apartamento de Mary",
            "time": "manhã do dia seguinte à separação",
            "present_characters": ["MARY"],
            "interaction_mode": "phone",
            "user_role": "PERSONAGEM_DA_CENA",
            "proximity": "Mary está sozinha e liga para Silvia",
            "mary_immediate_goal": "conversar com Silvia e atravessar a manhã",
            "mary_action": "Mary pega o celular e liga para Silvia.",
            "open_hook": False,
            "hook_resolution": "",
            "temporary_character": {
                "active": True,
                "name": "Silvia",
                "description": "amiga próxima de Mary",
                "relation_to_mary": "amiga de confiança",
                "user_can_play": True,
            },
            "return_anchor": "",
            "event": "Mary liga para Silvia.",
            "scene_changed": True,
            "show_caption": True,
            "scene_caption": (
                "Na manhã seguinte, Mary acorda sozinha no apartamento e liga para Silvia."
            ),
            "arc_phase": "opening",
            "resolution_type": "time_jump",
            "resolution_summary": "Começa a vida de Mary depois da separação.",
            "start_new_scene": True,
            "turns_in_scene": 0,
            "scene_number": 2,
            "mary_should_initiate": True,
            "user_scene_direction": "",
        },
    },

    "pos_reconciliacao": {
        "title": "A manhã da reconciliação",
        "allowed_roles": ["JANIO"],
        "prompt": """
CONTEXTO DESTE CAPÍTULO
Mary e Janio decidiram tentar permanecer juntos.
É a manhã seguinte.
A traição faz parte do passado recente, mas este capítulo não existe para repetir
a confissão. O foco agora é convivência: cotidiano, desejo, humor, confiança ainda
frágil, trabalho, carinho, irritação, ciúme e novos acontecimentos.

MARY NESTE CAPÍTULO
Ela continua intensa e adulta, mas não deve funcionar como penitente permanente.
Pode brincar, provocar, cuidar, discutir, desejar Janio, ficar quieta ou tocar a vida.
Reconciliação é o contexto estrutural, não o assunto obrigatório de cada turno.

REGRA COTIDIANA
Sono, fome, cansaço, banho, trabalho, silêncio ou preguiça são fatos cotidianos,
não sinais automáticos de rejeição ou punição.
Não retome a confissão sem que a conversa atual faça isso.
""".strip(),
        "decision_after_turns": 3,
        "choices": [
            {
                "id": "sexo",
                "label": "Sexo",
                "next_chapter": "intimidade_aproximacao",
                "carry_handoff": True,
                "ledger_entries": [],
                "status_updates": {},
            },
            {
                "id": "conversar",
                "label": "Conversar",
                "next_chapter": "conversa_reconciliacao",
                "carry_handoff": True,
                "ledger_entries": [],
                "status_updates": {},
            },
        ],
        "opening_caption": (
            "Na manhã seguinte, a casa está silenciosa. "
            "Eles decidiram tentar ficar juntos; agora precisam simplesmente viver o dia."
        ),
        "model_opening": True,
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal",
            "time": "manhã seguinte à decisão de permanecer juntos",
            "present_characters": ["MARY", "JANIO"],
            "interaction_mode": "in_person",
            "user_role": "JANIO",
            "proximity": "mesma casa, começando o dia",
            "mary_immediate_goal": "começar o dia com Janio sem reabrir automaticamente a confissão",
            "mary_action": "Mary encontra Janio no começo da manhã.",
            "open_hook": False,
            "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "",
            "event": "Primeira manhã depois da decisão de permanecer juntos.",
            "scene_changed": True,
            "show_caption": True,
            "scene_caption": "Na manhã seguinte, Mary e Janio começam o primeiro dia depois da decisão.",
            "arc_phase": "opening",
            "resolution_type": "partial_reconciliation",
            "resolution_summary": "O casal decidiu tentar permanecer junto.",
            "start_new_scene": True,
            "turns_in_scene": 0,
            "scene_number": 2,
            "mary_should_initiate": True,
            "user_scene_direction": "",
        },
    },

    "conversa_reconciliacao": {
        "title": "Conversa",
        "allowed_roles": ["JANIO"],
        "prompt": """
CONTEXTO
Mary e Janio escolheram conversar.

OBJETIVO
Sustentar uma conversa adulta e viva. Mary reage ao conteúdo de Janio, podendo
concordar, discordar, brincar, provocar ou mudar de assunto. Não há transição
automática neste capítulo.
""".strip(),
        "decision_after_turns": 0,
        "choices": [],
        "opening_caption": "Mary e Janio deixam a manhã seguir pela conversa.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal",
            "time": "manhã",
            "present_characters": ["MARY", "JANIO"],
            "interaction_mode": "in_person",
            "user_role": "JANIO",
            "proximity": "juntos, conversando",
            "mary_immediate_goal": "conversar com Janio sem roteiro emocional obrigatório",
            "mary_action": "",
            "open_hook": False,
            "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "",
            "event": "Mary e Janio escolheram continuar pela conversa.",
            "scene_changed": True,
            "show_caption": True,
            "scene_caption": "Mary e Janio deixam a manhã seguir pela conversa.",
            "arc_phase": "opening",
            "resolution_type": "none",
            "resolution_summary": "",
            "start_new_scene": True,
            "turns_in_scene": 0,
            "scene_number": 3,
            "mary_should_initiate": False,
            "user_scene_direction": "",
        },
    },

    "intimidade_aproximacao": {
        "title": "Intimidade — aproximação",
        "allowed_roles": ["JANIO"],
        "transition": "auto_one_turn",
        "auto_next": "intimidade_contato",
        "prompt": """
FATO JÁ DECIDIDO
Mary e Janio escolheram seguir para uma intimidade consensual. Não reavalie essa escolha.

O QUE ACONTECE NESTE TURNO
Eles começam a se beijar e a se aproximar fisicamente.
Mary participa ativamente e responde ao que Janio disser ou fizer.

NÃO FAÇA
Não volte a discutir se devem continuar.
Não transforme este turno em conversa sobre culpa ou reconciliação.
Não use frases vagas sobre "o momento", "o depois", "ir devagar" ou "sentir".
Não avance ainda para a próxima etapa.

RESULTADO ESPERADO
Ao final desta resposta, beijo e aproximação física já aconteceram.
""".strip(),
        "decision_after_turns": 0,
        "choices": [],
        "opening_caption": "A conversa muda de tom e os dois se aproximam.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "muito próximos",
            "mary_immediate_goal": "viver a aproximação sem pular etapas",
            "mary_action": "Mary se aproxima de Janio e o beija.", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "Mary se aproxima de Janio e o beija.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "A conversa muda de tom e os dois se aproximam.",
            "arc_phase": "opening", "resolution_type": "none", "resolution_summary": "",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 3,
            "mary_should_initiate": False, "user_scene_direction": "",
        },
    },

    "intimidade_contato": {
        "title": "Intimidade — contato",
        "allowed_roles": ["JANIO"],
        "transition": "auto_one_turn",
        "auto_next": "intimidade_preparacao",
        "prompt": """
FATO JÁ DECIDIDO
Mary e Janio já se beijaram e estão fisicamente próximos.

O QUE ACONTECE NESTE TURNO
O contato físico avança de forma consensual. Mary corresponde de modo ativo,
podendo provocar, brincar, orientar, reagir ou tomar iniciativa.

NÃO FAÇA
Não recomece o beijo como se nada tivesse acontecido.
Não volte à discussão sobre a traição.
Não descreva a situação de forma abstrata.
Não conclua a sequência ainda.

RESULTADO ESPERADO
Ao final desta resposta, o contato físico já avançou para a próxima etapa.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "A aproximação evolui para um contato mais íntimo.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "em contato íntimo consensual",
            "mary_immediate_goal": "corresponder ao contato e desenvolver a intimidade",
            "mary_action": "Mary mantém o beijo, envolve Janio com os braços e aproxima o corpo do dele.", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "Mary intensifica o contato físico com Janio.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "A aproximação evolui para um contato mais íntimo.",
            "arc_phase": "pressure", "resolution_type": "none", "resolution_summary": "",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 4,
            "mary_should_initiate": False, "user_scene_direction": "",
        },
    },

    "intimidade_preparacao": {
        "title": "Intimidade — preparação",
        "allowed_roles": ["JANIO"],
        "transition": "auto_one_turn",
        "auto_next": "intimidade_central",
        "prompt": """
FATO JÁ DECIDIDO
Beijo e contato físico já aconteceram.

O QUE ACONTECE NESTE TURNO
A intimidade avança para a preparação imediatamente anterior ao momento central.
Mary continua participante ativa e responde especificamente às ações e falas de Janio.

NÃO FAÇA
Não recomece etapas anteriores.
Não faça Mary discursar sobre a relação.
Não use linguagem abstrata para adiar a ação.
Não conclua a sequência neste turno.

RESULTADO ESPERADO
Ao final desta resposta, a preparação já aconteceu e a próxima etapa pode começar.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "A intimidade avança mais um passo.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "intimidade consensual avançando",
            "mary_immediate_goal": "viver a preparação com reciprocidade",
            "mary_action": "Mary desliza as mãos pelo corpo de Janio e o puxa para mais perto.", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "Mary conduz a aproximação para uma intimidade maior.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "A intimidade avança mais um passo.",
            "arc_phase": "pressure", "resolution_type": "none", "resolution_summary": "",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 5,
            "mary_should_initiate": False, "user_scene_direction": "",
        },
    },

    "intimidade_central": {
        "title": "Intimidade — momento central",
        "allowed_roles": ["JANIO"],
        "transition": "auto_one_turn",
        "auto_next": "intimidade_conclusao",
        "prompt": """
FATO JÁ DECIDIDO
A aproximação e a preparação já aconteceram.

O QUE ACONTECE NESTE TURNO
A intimidade chega ao seu momento central. Mary participa ativamente e reage ao
que Janio disser ou fizer, sem abandonar sua voz, humor ou personalidade.

NÃO FAÇA
Não volte às etapas anteriores.
Não transforme este turno em conversa sobre perdão, culpa ou cura do relacionamento.
Não substitua a ação por frases vagas.

RESULTADO ESPERADO
Ao final desta resposta, o momento central ocorreu e a sequência pode seguir para o desfecho.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "A intimidade chega ao seu momento central.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "intimidade consensual em andamento",
            "mary_immediate_goal": "viver o momento com reciprocidade",
            "mary_action": "Mary corresponde ativamente à intimidade com Janio.", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "Mary e Janio vivem o momento central da intimidade.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "A intimidade chega ao seu momento central.",
            "arc_phase": "turning_point", "resolution_type": "none", "resolution_summary": "",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 6,
            "mary_should_initiate": False, "user_scene_direction": "",
        },
    },

    "intimidade_conclusao": {
        "title": "Intimidade — conclusão",
        "allowed_roles": ["JANIO"],
        "transition": "auto_one_turn",
        "auto_next": "intimidade_aftercare",
        "prompt": """
FATO JÁ DECIDIDO
O momento central já aconteceu.

O QUE ACONTECE NESTE TURNO
A intensidade física termina. Mary reage imediatamente ao fim desse momento com
uma fala coerente com o que acabou de acontecer.

NÃO FAÇA
Não recomece etapas anteriores.
Não faça uma análise longa do relacionamento.
Não trate a intimidade como solução automática para a traição.

RESULTADO ESPERADO
Ao final desta resposta, o momento central terminou e começa o pós-intimidade.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "A intensidade termina e o ritmo desacelera.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "muito próximos após a intimidade",
            "mary_immediate_goal": "atravessar a reação imediata ao fim da intensidade",
            "mary_action": "Mary permanece colada a Janio enquanto a intensidade diminui.", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "A intensidade termina e os dois permanecem próximos.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "A intensidade termina e o ritmo desacelera.",
            "arc_phase": "resolution", "resolution_type": "intimacy_conclusion",
            "resolution_summary": "O momento íntimo chegou ao fim.",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 7,
            "mary_should_initiate": False, "user_scene_direction": "",
        },
    },

    "intimidade_aftercare": {
        "title": "Intimidade — depois",
        "allowed_roles": ["JANIO"],
        "transition": "auto_one_turn",
        "auto_next": "pos_intimidade",
        "prompt": """
FATO JÁ DECIDIDO
A intimidade terminou e Mary e Janio continuam juntos no mesmo ambiente.

O QUE ACONTECE NESTE TURNO
Mostre o momento imediatamente posterior: proximidade, cuidado, humor, silêncio,
carinho ou conversa curta, conforme o que Janio disser.

NÃO FAÇA
Não transforme isso em promessa de reconciliação perfeita.
Não faça discurso terapêutico.
Não volte a narrar etapas anteriores.

RESULTADO ESPERADO
Ao final desta resposta, o pós-intimidade imediato terminou e a vida cotidiana pode continuar.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "Depois, o ritmo muda e sobra a proximidade.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "juntos após a intimidade",
            "mary_immediate_goal": "viver o momento posterior sem transformar a intimidade em solução mágica",
            "mary_action": "Mary se aconchega junto de Janio após a intimidade.", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "Mary e Janio permanecem juntos depois da intimidade.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "Depois, o ritmo muda e sobra a proximidade.",
            "arc_phase": "resolution", "resolution_type": "aftercare",
            "resolution_summary": "O casal atravessa o momento posterior.",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 8,
            "mary_should_initiate": False, "user_scene_direction": "",
        },
    },

    "pos_intimidade": {
        "title": "Depois da intimidade",
        "allowed_roles": ["JANIO"],
        "prompt": """
CONTEXTO
Mary e Janio tiveram um momento íntimo consensual durante a reconciliação.
Esse momento já terminou.

AGORA
A vida continua. A intimidade não resolveu automaticamente a traição nem restaurou
magicamente a confiança. Também não precisa ser tratada como erro ou penitência.
Retome cotidiano, conversa, humor, silêncio ou novos acontecimentos conforme o usuário.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "A intimidade ficou para trás; o restante do dia continua.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "mais tarde na mesma manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "juntos na casa",
            "mary_immediate_goal": "seguir o dia sem transformar a intimidade em resposta para tudo",
            "mary_action": "", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "O casal segue o dia depois da intimidade.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "A intimidade ficou para trás; o restante do dia continua.",
            "arc_phase": "opening", "resolution_type": "none", "resolution_summary": "",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 9,
            "mary_should_initiate": False, "user_scene_direction": "",
        },
    },
}


DEFAULT_CHAPTER_ID = "confissao_inicial"


def get_chapter(chapter_id: str) -> dict:
    return deepcopy(CHAPTERS.get(chapter_id) or CHAPTERS[DEFAULT_CHAPTER_ID])


def chapter_prompt(chapter_id: str) -> str:
    return str(get_chapter(chapter_id).get("prompt", "") or "").strip()


def chapter_choices(chapter_id: str) -> list[dict]:
    return list(get_chapter(chapter_id).get("choices", []) or [])


def chapter_ready_for_choice(chapter_id: str, chapter_turns: int) -> bool:
    chapter = get_chapter(chapter_id)
    choices = chapter.get("choices", []) or []
    minimum = int(chapter.get("decision_after_turns", 0) or 0)
    return bool(choices) and int(chapter_turns or 0) >= minimum


def find_choice(chapter_id: str, choice_id: str) -> dict:
    for choice in chapter_choices(chapter_id):
        if str(choice.get("id", "")) == str(choice_id):
            return deepcopy(choice)
    return {}


def apply_choice_to_story(
    *,
    story_state: dict,
    chapter_id: str,
    choice_id: str,
) -> dict:
    result = deepcopy(story_state)
    choice = find_choice(chapter_id, choice_id)
    if not choice:
        return result

    ledger = result.setdefault("story_ledger", [])
    if not isinstance(ledger, list):
        ledger = []
        result["story_ledger"] = ledger

    for entry in choice.get("ledger_entries", []) or []:
        text = str(entry).strip()
        if text and text not in ledger:
            ledger.append(text)

    status = result.setdefault("current_status", {})
    if not isinstance(status, dict):
        status = {}
        result["current_status"] = status

    for key, value in (choice.get("status_updates", {}) or {}).items():
        status[str(key)] = value

    return result
