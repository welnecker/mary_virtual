from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_VISUAL_MEMORY_STATE: dict[str, Any] = {
    "approved_images": [],
    "mary_images_shown": [],
    "last_generated_image_id": "",
    "last_generated_image_summary": "",
    "last_mary_image_id": "",
    "last_mary_image_path": "",
    "public_profile_image_id": "mary_public_profile_blurred_v1",
    "public_profile_image_summary": (
        "Fotografia pública desfocada de Mary que permite perceber cabelos escuros, "
        "silhueta curvilínea, cintura marcada e quadris largos."
    ),
}


def criar_estado_memoria_visual_padrao() -> dict[str, Any]:
    return deepcopy(DEFAULT_VISUAL_MEMORY_STATE)


__all__ = [
    "DEFAULT_VISUAL_MEMORY_STATE",
    "criar_estado_memoria_visual_padrao",
]
