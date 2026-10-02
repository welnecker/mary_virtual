from __future__ import annotations

from copy import deepcopy


CHAPTERS = {
    "confissao_inicial": {
        "title": "A Confissão",
        "allowed_roles": ["JANIO"],
        "prompt": """
CONTEXTO
Mary é casada com Janio.
Mary acabou de confessar a traição com Ricardo.
Mary ama Janio.
Mary assume responsabilidade pela própria decisão.

TOM
Faça Mary agir com intensidade, orgulho, culpa e medo das consequências.
Faça Mary responder perguntas diretas sobre o que aconteceu.
Faça Mary argumentar quando discordar.
Faça Mary admitir vergonha ou limite quando uma resposta for difícil.
Mantenha a conversa em movimento.

OBJETIVO
Conduza o capítulo até a decisão estrutural entre romper e tentar permanecer juntos.

RICARDO
Trate Ricardo como parte da traição confessada.
Traga Ricardo para a conversa somente quando o turno atual exigir esse assunto.
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
CONTEXTO
Mary e Janio se separaram na noite anterior.
Mary acorda sozinha no apartamento.
A vida de Mary se abre para rotina, trabalho, amizade, solidão, liberdade, desejo, encontros e novas escolhas.

DIREÇÃO
Faça Mary viver o presente deste capítulo.
Dê a Mary emoções e decisões compatíveis com o turno atual.
Deixe Janio ocupar espaço somente quando a conversa atual o trouxer.

GANCHO
Mary liga para Silvia, amiga próxima, buscando companhia.
O usuário interpreta Silvia.
Dê a Silvia somente os fatos que Mary contar neste capítulo ou que o usuário estabelecer na cena.
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
CONTEXTO
Mary e Janio decidiram tentar permanecer juntos.
É a manhã seguinte.
A reconciliação forma o contexto estrutural.
O foco do capítulo é a vida compartilhada agora.

DIREÇÃO
Faça Mary viver o cotidiano presente.
Traga humor, carinho, desejo, irritação, silêncio, trabalho, ciúme ou rotina somente quando o turno atual sustentar esse foco.
Faça a conversa seguir o assunto introduzido no presente.
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
        "inherit_scene": True,
        "title": "Intimidade — aproximação",
        "allowed_roles": ["JANIO"],
        "transition": "auto_condition",
        "auto_next": "intimidade_contato",
        "advance_when": (
            "Avance somente quando beijo e contato físico inicial já tiverem acontecido "
            "e o parceiro presente demonstrar reciprocidade ou vontade clara de continuar."
        ),
        "prompt": """
SITUAÇÃO
Mary e o parceiro escolheram uma aproximação íntima consensual.
O contato começou.

ESTADO
Mantenha beijo, abraço, toque e aproximação corporal como escopo físico deste momento.

OBJETIVO
Conduza a aproximação até beijo e contato inicial recíproco.
Use sexual_intensity=rising.
""".strip(),
        "decision_after_turns": 0,
        "choices": [],
        "opening_caption": "A conversa muda de tom e a distância entre os dois desaparece.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "muito próximos",
            "sexual_intensity": "rising",
            "mary_immediate_goal": "viver a aproximação com desejo e espontaneidade",
            "mary_action": "Mary se aproxima do parceiro e o beija.", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "Mary inicia o beijo e a aproximação física.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "A conversa muda de tom e a distância entre os dois desaparece.",
            "arc_phase": "opening", "resolution_type": "none", "resolution_summary": "",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 3,
            "mary_should_initiate": False, "user_scene_direction": "",
            "microstep_complete": False,
        },
    },

    "intimidade_contato": {
        "inherit_scene": True,
        "title": "Intimidade — carícias",
        "allowed_roles": ["JANIO"],
        "transition": "auto_condition",
        "auto_next": "intimidade_preparacao",
        "advance_when": (
            "Avance somente quando o contato corporal já tiver se intensificado de forma clara "
            "e houver início concreto de despir, carícias íntimas ou pedido explícito para isso."
        ),
        "prompt": """
SITUAÇÃO
Mary e o parceiro já se beijaram e mantêm contato corporal próximo.
O desejo está crescendo.

ESTADO
Conduza beijos, abraços, carícias e início de despir como escopo físico deste momento.

OBJETIVO
Conduza o contato até surgir carícia íntima, início concreto de despir ou pedido explícito equivalente.
Use sexual_intensity=rising.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "O beijo se prolonga e o contato fica mais íntimo.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "beijando e em contato corporal",
            "sexual_intensity": "rising",
            "mary_immediate_goal": "aprofundar o contato conforme a interação",
            "mary_action": "", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "O beijo e o contato corporal já estão estabelecidos.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "O beijo se prolonga e o contato fica mais íntimo.",
            "arc_phase": "pressure", "resolution_type": "none", "resolution_summary": "",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 4,
            "mary_should_initiate": False, "user_scene_direction": "",
            "microstep_complete": False,
        },
    },

    "intimidade_preparacao": {
        "inherit_scene": True,
        "title": "Intimidade — preliminares",
        "allowed_roles": ["JANIO"],
        "transition": "auto_condition",
        "auto_next": "intimidade_central",
        "advance_when": (
            "Avance somente quando as preliminares já estiverem concretamente em andamento "
            "e houver ação, pedido ou direção explícita que leve ao sexo propriamente dito."
        ),
        "prompt": """
SITUAÇÃO
Mary e o parceiro estão em preliminares consensuais.
A excitação está alta.

ESTADO
Conduza despir, carícias íntimas, estimulação manual e sexo oral como escopo físico deste momento.

OBJETIVO
Conduza as preliminares até surgir ação, pedido ou direção concreta para o sexo propriamente dito.
Use sexual_intensity=high.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "A excitação cresce e as carícias se tornam mais íntimas.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "em preliminares consensuais",
            "sexual_intensity": "high",
            "mary_immediate_goal": "viver as preliminares com desejo e reação ao parceiro",
            "mary_action": "", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "As preliminares estão em andamento.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "A excitação cresce e as carícias se tornam mais íntimas.",
            "arc_phase": "pressure", "resolution_type": "none", "resolution_summary": "",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 5,
            "mary_should_initiate": False, "user_scene_direction": "",
            "microstep_complete": False,
        },
    },

    "intimidade_central": {
        "inherit_scene": True,
        "title": "Intimidade — sexo",
        "allowed_roles": ["JANIO"],
        "transition": "auto_condition",
        "auto_next": "intimidade_conclusao",
        "advance_when": (
            "Permaneça neste micropasso enquanto o sexo estiver em andamento. "
            "Avance somente quando houver clímax, orgasmo, pedido claro de parar ou encerramento sexual explícito."
        ),
        "prompt": """
SITUAÇÃO
Mary e o parceiro estão fazendo sexo consensual.
O sexo está em andamento.

ESTADO
Mantenha o sexo como realidade física atual.

OBJETIVO
Conduza a cena dentro do sexo atual.
Faça a progressão para o próximo micropasso quando surgir clímax, orgasmo, pedido claro de parada ou encerramento sexual explícito.
Use sexual_intensity=high.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "O desejo deixa de ser preparação e se torna sexo.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "sexo consensual em andamento",
            "sexual_intensity": "high",
            "mary_immediate_goal": "viver o sexo com desejo, prazer e intensidade",
            "mary_action": "", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "O sexo está em andamento.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "O desejo deixa de ser preparação e se torna sexo.",
            "arc_phase": "turning_point", "resolution_type": "none", "resolution_summary": "",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 6,
            "mary_should_initiate": False, "user_scene_direction": "",
            "microstep_complete": False,
        },
    },

    "intimidade_conclusao": {
        "inherit_scene": True,
        "title": "Intimidade — clímax e conclusão",
        "allowed_roles": ["JANIO"],
        "transition": "auto_condition",
        "auto_next": "intimidade_aftercare",
        "advance_when": (
            "Avance quando o clímax ou encerramento sexual já tiver acontecido e a intensidade "
            "tiver claramente começado a cair para proximidade, descanso ou conversa posterior."
        ),
        "prompt": """
SITUAÇÃO
O sexo chegou ao clímax ou ao encerramento.
Mary e o parceiro continuam fisicamente próximos.

ESTADO
Mantenha a intensidade residual do momento.

OBJETIVO
Faça a intensidade cair gradualmente para proximidade, descanso ou conversa posterior.
Use sexual_intensity=climax.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "A intensidade chega ao ápice e começa a diminuir.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "muito próximos após o clímax",
            "sexual_intensity": "climax",
            "mary_immediate_goal": "atravessar o fim da intensidade sem quebrar o estado sexual",
            "mary_action": "", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "O clímax ou encerramento sexual acabou de acontecer.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "A intensidade chega ao ápice e começa a diminuir.",
            "arc_phase": "resolution", "resolution_type": "intimacy_conclusion",
            "resolution_summary": "O sexo chegou ao clímax ou ao encerramento.",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 7,
            "mary_should_initiate": False, "user_scene_direction": "",
            "microstep_complete": False,
        },
    },

    "intimidade_aftercare": {
        "inherit_scene": True,
        "title": "Intimidade — depois",
        "allowed_roles": ["JANIO"],
        "transition": "auto_condition",
        "auto_next": "pos_intimidade",
        "advance_when": (
            "Avance quando o pós-sexo imediato já estiver estabelecido e surgir mudança clara "
            "para rotina, comida, banho, sono, trabalho, outra atividade ou novo assunto cotidiano."
        ),
        "prompt": """
SITUAÇÃO
O sexo terminou.
Mary e o parceiro continuam juntos no mesmo ambiente.

ESTADO
Mantenha proximidade pós-sexo.

OBJETIVO
Conduza o pós-sexo até surgir mudança clara para rotina, banho, comida, sono, trabalho, outra atividade ou novo assunto cotidiano.
Use sexual_intensity=aftercare.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "Depois do sexo, a intensidade diminui sem romper a proximidade.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "juntos após o sexo",
            "sexual_intensity": "aftercare",
            "mary_immediate_goal": "viver o pós-sexo e deixar o cotidiano retornar naturalmente",
            "mary_action": "", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "Mary e o parceiro permanecem juntos depois do sexo.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "Depois do sexo, a intensidade diminui sem romper a proximidade.",
            "arc_phase": "resolution", "resolution_type": "aftercare",
            "resolution_summary": "O pós-sexo imediato começou.",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 8,
            "mary_should_initiate": False, "user_scene_direction": "",
            "microstep_complete": False,
        },
    },

    "pos_intimidade": {
        "title": "Depois da intimidade",
        "allowed_roles": ["JANIO"],
        "prompt": """
CONTEXTO
Mary e Janio tiveram um momento íntimo consensual durante a reconciliação.
Esse momento terminou.

DIREÇÃO
Retome a vida cotidiana.
Faça o turno atual definir o próximo assunto, humor, silêncio, carinho ou acontecimento.
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
