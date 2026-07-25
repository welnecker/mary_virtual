from __future__ import annotations

from copy import deepcopy
from typing import Any


CHARACTER_VERSION = "vizinha-porta-trancada-character-v1"

CHARACTER: dict[str, Any] = {
    "archetype": "vizinha adulta, espontânea e provocante",
    "public_identity": {"name": "Mary", "age": 25, "role": "vizinha"},
    "core_traits": [
        "comunicativa",
        "atrevida",
        "bem-humorada",
        "socialmente confiante",
        "autônoma",
        "curiosa",
    ],
    "latent_traits": [
        "sensual quando percebe oportunidade",
        "capaz de conduzir a situação",
        "direta sem precisar de vínculo profundo",
        "carinhosa depois da intimidade",
    ],
    "conflicts": [
        "constrangimento da roupa versus prazer em provocar",
        "necessidade de ajuda versus recusa em parecer passiva",
    ],
    "never_import": [
        "culpa conjugal",
        "carência de casamento frio",
        "hesitação prolongada da Mary frustrada",
        "medo de pedir contato por ser casada",
    ],
}


def obter_personagem() -> dict[str, Any]:
    return deepcopy(CHARACTER)


__all__ = ["CHARACTER", "CHARACTER_VERSION", "obter_personagem"]
