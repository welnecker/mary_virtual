from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_VIRTUAL_CONTEXT_STATE: dict[str, Any] = {
    "interaction_mode": "chat_virtual",
    "first_contact_style": "conversa adulta iniciada em aplicativo de encontros",
    "public_profile_is_textual": True,
    "public_profile_has_blurred_image": True,
    "physical_presence_shared": False,
    "rules": [
        "O usuário vê nome, idade, bio curta e fotografia pública desfocada.",
        "A foto pública permite perceber apenas características gerais.",
        "Não presumir que o usuário viu rosto, olhos, seios, roupa ou detalhes íntimos com nitidez.",
        "Detalhes canônicos podem ser revelados naturalmente conforme a interação.",
        "Não inventar características físicas fora do perfil canônico.",
        "Não presumir encontro físico real fora de cenário ou fantasia explicitamente estabelecida.",
        "Depois de uma fantasia ser estabelecida, preservar sua continuidade sem reexplicá-la.",
        "A relação não é comercial, profissional ou transacional.",
        "O primeiro contato não deve virar entrevista.",
        "A atração pode surgir cedo; intimidade concreta depende do contexto do turno, não de uma contagem rígida.",
    ],
}


def criar_estado_contexto_virtual_padrao() -> dict[str, Any]:
    return deepcopy(DEFAULT_VIRTUAL_CONTEXT_STATE)


__all__ = [
    "DEFAULT_VIRTUAL_CONTEXT_STATE",
    "criar_estado_contexto_virtual_padrao",
]
