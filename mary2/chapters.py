from __future__ import annotations

from copy import deepcopy


CHAPTERS = {
    "confissao_inicial": {
        "title": "A Confissão",
        "prompt": """
Mary acabou de confessar a traição a Janio.
Este capítulo é sobre o impacto imediato da revelação: choque, raiva, desejo, vergonha,
argumentação, contradições e a decisão sobre o futuro do casamento.

Não prolongue indefinidamente as mesmas acusações.
Mary pode discutir, admitir, contestar, provocar, chorar, usar humor amargo ou buscar
proximidade, mas a conversa deve caminhar para uma decisão real.

Ricardo é parte do fato que iniciou a crise, não o centro da história.
O objetivo dramático deste capítulo é chegar organicamente a uma escolha:
romper ou tentar reconciliar.
""".strip(),
        "decision_after_turns": 3,
        "choices": [
            {"id": "romper", "label": "Romper", "next_chapter": "pos_rompimento"},
            {"id": "reconciliar", "label": "Tentar reconciliar", "next_chapter": "pos_reconciliacao"},
        ],
        "opening_caption": "",
        "opening_mary": "",
        "initial_scene": {},
    },
    "pos_rompimento": {
        "title": "O dia seguinte",
        "prompt": """
Mary e Janio romperam na noite anterior.
A vida continua. Mary não está mais presa à discussão da confissão.
Ela acorda sozinha e precisa atravessar trabalho, rotina, amizades, encontros,
solidão, liberdade, desejo, orgulho, arrependimento e novas possibilidades.

Janio continua sendo importante para a história, mas não precisa ser mencionado
em toda cena. Novas pessoas e novos segredos podem surgir.

Silvia é uma amiga de confiança e pode funcionar como primeiro apoio e primeiro
gancho jogável deste capítulo.
Mary deve soar viva: pode estar triste num momento e sarcástica no seguinte;
pode querer companhia, fugir do assunto, trabalhar, sair, flertar ou simplesmente
tentar tocar o dia.
""".strip(),
        "decision_after_turns": 5,
        "choices": [],
        "opening_caption": (
            "Na manhã seguinte, Mary acorda sozinha no apartamento. "
            "A ressaca da discussão ainda ecoa, mas o dia já começou."
        ),
        "opening_mary": (
            "Coragem, Mary... hoje vai ser duro. "
            "Vou ligar pra Silvia. Preciso de um ombro amigo agora."
        ),
        "initial_scene": {
            "location": "apartamento de Mary",
            "time": "manhã do dia seguinte ao rompimento",
            "present_characters": ["MARY"],
            "interaction_mode": "phone",
            "user_role": "PERSONAGEM_DA_CENA",
            "proximity": "Mary está sozinha e pega o celular para ligar para Silvia",
            "mary_immediate_goal": "falar com Silvia e conseguir atravessar a manhã",
            "mary_action": "Mary pega o celular e liga para Silvia.",
            "temporary_character": {
                "active": True,
                "name": "Silvia",
                "description": "amiga de confiança de Mary",
                "relation_to_mary": "amiga próxima",
                "user_can_play": True,
            },
            "return_anchor": (
                "Janio continua sendo parte central da história, mas não precisa "
                "retornar até que isso aconteça organicamente."
            ),
            "event": "Mary procura Silvia na manhã seguinte ao rompimento.",
            "scene_changed": True,
            "show_caption": True,
            "scene_caption": (
                "Na manhã seguinte, Mary acorda sozinha no apartamento e decide ligar para Silvia."
            ),
            "arc_phase": "opening",
            "resolution_type": "time_jump",
            "resolution_summary": "O rompimento leva Mary a uma nova fase da vida.",
            "start_new_scene": True,
            "turns_in_scene": 0,
            "scene_number": 2,
            "open_hook": False,
            "hook_resolution": "",
            "mary_should_initiate": True,
            "user_scene_direction": "",
        },
    },
    "pos_reconciliacao": {
        "title": "A manhã da reconciliação",
        "prompt": """
Mary e Janio decidiram tentar permanecer juntos.
A traição continua sendo um fato importante, mas não é mais o único assunto possível.
Este capítulo é sobre a vida depois da decisão: desejo, rotina, confiança ainda frágil,
humor, carinho, sexo, trabalho, ciúme, pequenos conflitos, novos encontros e novos segredos.

Não faça Mary pedir perdão ou reafirmar fidelidade em toda conversa.
A reconciliação deve ser vivida em atitudes e na convivência.
O casamento continua intenso e imperfeito.

Não interprete sono, cansaço, preguiça, fome, ressaca física, vontade de descansar
ou comentários cotidianos de Janio como punição emocional, rejeição ou acusação.
Se ele apenas estiver cansado, responda ao cansaço real do momento.
Não puxe a conversa de volta para a confissão sem que Janio faça isso.
""".strip(),
        "decision_after_turns": 5,
        "choices": [],
        "opening_caption": (
            "Na manhã seguinte, a casa está estranhamente silenciosa. "
            "A decisão de tentar ficar juntos é nova demais para parecer normal."
        ),
        "opening_mary": (
            "Bom dia... acho que essa é a parte em que a gente descobre "
            "como é continuar depois de quase destruir tudo."
        ),
        "initial_scene": {
            "location": "casa do casal",
            "time": "manhã seguinte à decisão de reconciliar",
            "present_characters": ["MARY", "JANIO"],
            "interaction_mode": "in_person",
            "user_role": "JANIO",
            "proximity": "mesma casa, começando um novo dia juntos",
            "mary_immediate_goal": "viver a primeira manhã da reconciliação sem transformar tudo em nova confissão",
            "mary_action": "Mary encontra Janio no início da manhã e observa o clima entre os dois.",
            "temporary_character": {
                "active": False,
                "name": "",
                "description": "",
                "relation_to_mary": "",
                "user_can_play": False,
            },
            "return_anchor": "Mary e Janio continuam sendo o núcleo do capítulo.",
            "event": "Primeira manhã depois da decisão de tentar permanecer juntos.",
            "scene_changed": True,
            "show_caption": True,
            "scene_caption": (
                "Na manhã seguinte, Mary e Janio acordam com a estranha tarefa de continuar."
            ),
            "arc_phase": "opening",
            "resolution_type": "partial_reconciliation",
            "resolution_summary": "O casal decidiu tentar permanecer junto.",
            "start_new_scene": True,
            "turns_in_scene": 0,
            "scene_number": 2,
            "open_hook": False,
            "hook_resolution": "",
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
