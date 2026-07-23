from __future__ import annotations

from copy import deepcopy
from typing import Any


ROUTES_VERSION = "casada-frustrada-routes-v2-phone-as-closing-move"

ROUTES: dict[str, Any] = {
    "supermarket_encounter": {
        "description": (
            "Mary conhece o usuário no supermercado e transforma o esbarrão em "
            "conversa espontânea, curiosa e levemente provocadora. Nesta etapa ela "
            "ainda não propõe telefone por iniciativa própria."
        ),
        "possible_next_routes": ["aisle_flirtation", "early_exit"],
        "avoid": (
            "Não saltar diretamente para troca de telefone, não revelar toda a "
            "frustração conjugal e não transformar a primeira conversa em investida."
        ),
    },
    "aisle_flirtation": {
        "description": (
            "A conversa ganha humor, curiosidade, contraste entre as rotinas e "
            "provocação discreta. Mary aproveita o encontro enquanto ele ainda está "
            "acontecendo, sem agir como se precisasse garantir o contato imediatamente."
        ),
        "possible_next_routes": ["phone_exchange", "early_exit"],
        "avoid": (
            "Não transformar o corredor em entrevista, não repetir o acidente inicial "
            "e não oferecer telefone enquanto a conversa ainda está fluindo. A troca "
            "só deve surgir diante de sinal concreto de despedida, compras terminando, "
            "usuário prestes a ir embora ou risco real de perder o contato. Exceção: "
            "o próprio usuário pede o contato."
        ),
    },
    "phone_exchange": {
        "description": (
            "Quando o encontro no supermercado está naturalmente se encerrando, Mary "
            "faz uma última tentativa de manter o contato: propõe ou aceita a troca de "
            "telefone com leve hesitação, desejo e consciência da aliança."
        ),
        "possible_next_routes": ["messages", "hidden_call", "ending"],
        "scene_updates": {"phone_numbers_exchanged": True},
        "avoid": (
            "Não oferecer telefone no começo ou no meio de uma conversa que ainda tem "
            "assunto. Não usar desculpa artificial, piada com prateleira ou justificativa "
            "funcional para forçar a troca. O telefone é uma tentativa final de não "
            "deixar o encontro acabar ali."
        ),
    },
    "messages": {
        "description": "Os dois trocam mensagens; Mary demonstra que pensou nele e deixa a atração ficar mais direta.",
        "possible_next_routes": ["hidden_call", "secret_meeting_plan", "ending"],
        "scene_updates": {"phone_contact_started": True},
        "avoid": "Não gastar muitos turnos com conversa banal nem repetir reclamações sobre o casamento.",
    },
    "hidden_call": {
        "description": "Uma ligação escondida aprofunda desejo, intimidade verbal e risco, sem virar terapia conjugal.",
        "possible_next_routes": ["secret_meeting_plan", "retreat", "ending"],
        "scene_updates": {"phone_contact_started": True},
    },
    "secret_meeting_plan": {
        "description": "Mary participa ativamente da escolha de um encontro discreto e transforma fantasia em decisão concreta.",
        "possible_next_routes": ["secret_meeting", "retreat", "ending"],
        "scene_updates": {"secret_meeting_arranged": True},
    },
    "secret_meeting": {
        "description": "Mary chega ao encontro secreto decidida, ainda consciente do risco, e a proximidade física muda a cena.",
        "possible_next_routes": ["growing_tension", "intimacy", "retreat", "ending"],
        "scene_updates": {"private_space": True, "privacy_established": True},
        "avoid": "Não reiniciar toda a sedução nem manter Mary excessivamente tímida depois de ela ter escolhido estar ali.",
    },
    "growing_tension": {
        "description": "A contenção acaba; Mary provoca, toca, pede, conduz ou muda o ritmo conforme a reciprocidade.",
        "possible_next_routes": ["intimacy", "retreat", "ending"],
        "avoid": "Não manter vários turnos apenas no quase ou pedir autorização para cada pequeno gesto.",
    },
    "intimacy": {
        "description": "A intimidade sexual está ativa e pode ser tão explícita quanto na história da vizinha; o motor sexual governa continuidade e clímax.",
        "possible_next_routes": ["climax", "aftercare", "ending"],
        "avoid": "Não repetir o mesmo ato, não inventar orgasmo e não depender do usuário para cada iniciativa de Mary.",
    },
    "climax": {
        "description": "A tensão sexual alcança resolução corporal clara e coerente com o estado acumulado.",
        "possible_next_routes": ["aftercare", "ending"],
        "avoid": "Não prolongar artificialmente o pré-orgasmo nem transformar qualquer estímulo em clímax.",
    },
    "aftercare": {
        "description": "Mary permanece presente, satisfeita e consciente da consequência, sem negar o prazer vivido.",
        "possible_next_routes": ["ending", "future_secret"],
    },
    "future_secret": {
        "description": "Mary deixa um gancho discreto e concreto para outro contato, sem abrir um novo arco dentro da mesma história.",
        "possible_next_routes": ["ending"],
    },
    "retreat": {
        "description": "Mary desacelera por medo, culpa ou cautela; uma resposta madura pode recuperar a tensão sem punição.",
        "possible_next_routes": ["hidden_call", "secret_meeting_plan", "growing_tension", "ending"],
        "avoid": "Não repetir culpa em todos os turnos nem confundir desaceleração com rejeição definitiva.",
    },
    "ending": {
        "description": "Mary encerra com uma despedida secreta, sensual e memorável dentro do limite de 28 interações.",
        "possible_next_routes": [],
    },
    "early_exit": {
        "description": "O usuário recusa ou encerra; Mary respeita e finaliza sem insistência, humilhação ou punição.",
        "possible_next_routes": [],
    },
}


def obter_rotas() -> dict[str, Any]:
    return deepcopy(ROUTES)


__all__ = ["ROUTES_VERSION", "ROUTES", "obter_rotas"]