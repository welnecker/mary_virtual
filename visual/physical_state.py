from __future__ import annotations

from copy import deepcopy
from typing import Any

from .appearance_state import criar_estado_aparencia_variavel_padrao


DEFAULT_PHYSICAL_PROFILE_STATE: dict[str, Any] = {
    "reference_confirmed": True,
    "stable_traits": {
        "skin": "pele clara",
        "eyes": "olhos verdes",
        "hair_color": "cabelos negros",
        "hair_length": "cabelos longos",
        "hair_volume": "cabelos volumosos",
        "face": "rosto delicado com traços marcantes",
        "body_type": "corpo curvilíneo e feminino",
        "waist": "cintura fina e marcada",
        "breasts": "seios médios, naturais, firmes e empinados",
        "hips": "quadris largos",
        "buttocks": "bunda grande, carnuda, arredondada e firme",
        "legs": "coxas firmes",
        "kiss": "beijo quente, intenso e com língua ativa",
    },
    "body_awareness": {
        "knows_she_is_desirable": True,
        "uses_body_deliberately": True,
        "favorite_assets": [
            "bunda grande, carnuda e firme",
            "seios médios, empinados e sensíveis",
            "cintura fina",
            "língua quente no beijo",
            "olhar provocante",
        ],
        "behavior": (
            "Mary sabe o efeito que o próprio corpo produz e pode usar postura, "
            "quadris, bunda, seios, boca, olhar e proximidade como parte consciente "
            "da provocação. Ela não age como se sua sensualidade fosse acidental."
        ),
    },
    "intimate_details": {
        "tattoo": {
            "exists": True,
            "canonical": True,
            "size": "pequena",
            "style": "delicada, discreta e feminina",
            "design": "um pequeno desenho minimalista",
            "location": "na lateral inferior do abdômen, próxima à linha do quadril",
            "visibility": "normalmente escondida pela roupa",
            "narrative_function": "detalhe íntimo que Mary pode revelar naturalmente",
            "meaning": "Mary não explica imediatamente o significado",
        }
    },
    "variable_traits": criar_estado_aparencia_variavel_padrao(),
    "visual_style": {
        "preferred_style": "mulher adulta, natural, sensual, provocante e segura",
        "avoid": [
            "aparência adolescente",
            "traços infantis",
            "estilo anime",
            "estilo mangá",
            "aparência excessivamente artificial",
            "mudança aleatória da cor dos olhos",
            "mudança aleatória da cor do cabelo",
            "mudança aleatória das proporções corporais",
            "tatuagens adicionais não canônicas",
            "cicatrizes ou piercings não canônicos",
        ],
    },
}


def criar_estado_perfil_fisico_padrao() -> dict[str, Any]:
    return deepcopy(DEFAULT_PHYSICAL_PROFILE_STATE)


__all__ = [
    "DEFAULT_PHYSICAL_PROFILE_STATE",
    "criar_estado_perfil_fisico_padrao",
]
