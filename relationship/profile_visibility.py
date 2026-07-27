from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_PROFILE_VISIBILITY_STATE: dict[str, Any] = {
    "revealed_to_user": False,
    "first_reveal_image_id": "",
    "first_reveal_at": "",
    "user_has_seen_mary": False,
    "user_first_visual_reaction": "",
    "public_profile_seen": False,
    "public_profile_seen_at": "",
    "private_details_revealed": {"tattoo": False},
    "private_details_revealed_at": {"tattoo": ""},
}


def criar_estado_visibilidade_perfil_padrao() -> dict[str, Any]:
    return deepcopy(DEFAULT_PROFILE_VISIBILITY_STATE)


__all__ = [
    "DEFAULT_PROFILE_VISIBILITY_STATE",
    "criar_estado_visibilidade_perfil_padrao",
]
