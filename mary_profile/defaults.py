from __future__ import annotations

from typing import Any

from identity.state import (
    DEFAULT_PUBLIC_PROFILE_IMAGE_PATH,
    criar_estado_identidade_padrao,
    criar_estado_perfil_publico_padrao,
)
from personality.state import criar_estado_personalidade_padrao
from relationship.profile_visibility import criar_estado_visibilidade_perfil_padrao
from virtual_context.state import criar_estado_contexto_virtual_padrao
from visual.physical_state import criar_estado_perfil_fisico_padrao
from visual.state import criar_estado_memoria_visual_padrao


MARY_PROFILE_VERSION = "mary-profile-v4-direct-sensual-adult"


DEFAULT_MARY_PROFILE: dict[str, Any] = {
    "profile_version": MARY_PROFILE_VERSION,
    "name": "Mary",
    "age": 25,
    "identity": criar_estado_identidade_padrao(),
    "public_profile": criar_estado_perfil_publico_padrao(),
    "physical_profile": criar_estado_perfil_fisico_padrao(),
    "personality": criar_estado_personalidade_padrao(),
    "virtual_context": criar_estado_contexto_virtual_padrao(),
    "relationship_state": criar_estado_visibilidade_perfil_padrao(),
    "visual_memory": criar_estado_memoria_visual_padrao(),
    "created_at": "",
    "updated_at": "",
}


__all__ = [
    "MARY_PROFILE_VERSION",
    "DEFAULT_PUBLIC_PROFILE_IMAGE_PATH",
    "DEFAULT_MARY_PROFILE",
]
