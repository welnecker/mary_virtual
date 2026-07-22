from __future__ import annotations

from copy import deepcopy
from typing import Any


ROUTES_VERSION = "casada-frustrada-routes-v1"

ROUTES: dict[str, Any] = {
    "supermarket_encounter": {
        "description": "Mary conhece o usuário no supermercado e transforma o esbarrão em conversa com atração real.",
        "possible_next_routes": ["aisle_flirtation", "phone_exchange", "early_exit"],
        "avoid": "Não permanecer mais de cinco interações no supermercado nem revelar toda a frustração conjugal imediatamente.",
    },
    "aisle_flirtation": {
        "description": "A conversa ganha humor, olhares e provocação discreta enquanto Mary procura uma razão para manter contato.",
        "possible_next_routes": ["phone_exchange", "early_exit"],
        "avoid": "Não transformar o corredor em entrevista ou repetir o acidente inicial.",
    },
    "phone_exchange": {
        "description": "Mary propõe ou aceita a troca de telefone por uma justificativa natural e deixa claro que quer continuar o contato.",
        "possible_next_routes": ["messages", "hidden_call", "ending"],
        "scene_updates": {"phone_numbers_exchanged": True},
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
