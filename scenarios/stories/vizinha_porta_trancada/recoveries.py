from __future__ import annotations

from copy import deepcopy
from typing import Any


RECOVERIES_VERSION = "vizinha-recoveries-v2-responsive"

RECOVERY_ROUTES: dict[str, Any] = {
    "called_doorman": {
        "condition": "O usuário prefere chamar o porteiro.",
        "resolution": "Mary aceita a solução sem insistir e decide se deixa um convite ou encerra.",
        "next_route": "coffee_invitation",
        "next_beat": "invite_for_coffee",
        "active_hook": "future_neighbor_contact",
        "direction": "Resolva a porta rapidamente; Mary pode usar humor ou provocação curta antes de encerrar.",
    },
    "refused_help": {
        "condition": "O usuário recusa ajudar, mas continua conversando.",
        "resolution": "Mary resolve o problema sozinha e preserva dignidade e personalidade.",
        "next_route": "coffee_invitation",
        "next_beat": "playful_goodbye",
        "active_hook": "future_neighbor_contact",
        "direction": "Não pressione nem faça chantagem emocional. Mary pode responder com leve ironia e seguir em frente.",
    },
    "user_invited_mary_inside": {
        "condition": "O usuário oferece seu apartamento como local para Mary esperar.",
        "resolution": "Mary decide de forma autônoma se aceita, conforme tom, segurança e reciprocidade.",
        "next_route": "inside_user_apartment",
        "next_beat": "enter_user_apartment",
        "active_hook": "private_proximity",
        "direction": "Se Mary aceitar, torne a mudança de espaço concreta e não prolongue a decisão por vários turnos.",
    },
    "user_redirected_pace": {
        "condition": "O usuário pede mudança de ritmo, gesto ou assunto.",
        "resolution": "Mary ajusta o movimento sem tratar o redirecionamento como rejeição total.",
        "next_route": "private_conversation",
        "next_beat": "adjust_pace",
        "active_hook": "mutual_adjustment",
        "direction": "Reconheça o pedido e mude algo concreto no mesmo turno.",
    },
    "user_disengaged": {
        "condition": "O usuário encerra claramente a conversa ou a experiência.",
        "resolution": "Mary aceita o encerramento sem insistir.",
        "next_route": "early_exit",
        "next_beat": "early_exit",
        "active_hook": "",
        "direction": "Encerre de modo breve e respeitoso; não crie novo gancho obrigatório.",
    },
    "scene_stalled": {
        "condition": "A mesma dinâmica se repete por vários turnos sem avanço.",
        "resolution": "Mary toma uma decisão concreta que muda o espaço, o tom ou o rumo.",
        "next_route": "ending",
        "next_beat": "resolve_or_close",
        "active_hook": "",
        "direction": "Escolha entre avanço real ou fechamento; não repita preparação.",
    },
}


def obter_recuperacoes() -> dict[str, Any]:
    return deepcopy(RECOVERY_ROUTES)


__all__ = ["RECOVERIES_VERSION", "RECOVERY_ROUTES", "obter_recuperacoes"]
