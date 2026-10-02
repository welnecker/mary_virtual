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
        "decision_after_turns": 5,
        "choices": [],
        "opening_caption": (
            "Na manhã seguinte, a casa está silenciosa. "
            "Eles decidiram tentar ficar juntos; agora precisam simplesmente viver o dia."
        ),
        "opening_mary": (
            "Bom dia... acho que agora vem a parte difícil: parar de falar sobre ontem e viver hoje."
        ),
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
            "temporary_character": {
                "active": False,
                "name": "",
                "description": "",
                "relation_to_mary": "",
                "user_can_play": False,
            },
            "return_anchor": "",
            "event": "Primeira manhã depois da decisão de permanecer juntos.",
            "scene_changed": True,
            "show_caption": True,
            "scene_caption": (
                "Na manhã seguinte, Mary e Janio começam o primeiro dia depois da decisão."
            ),
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
