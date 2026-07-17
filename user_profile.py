from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


# Estados resumidos para diagnóstico e compatibilidade.
# Eles não representam uma sequência obrigatória.
ONBOARDING_FIRST_CONTACT = "first_contact"
ONBOARDING_NAME_KNOWN = "name_known"
ONBOARDING_USER_VISUAL_KNOWN = "user_visual_known"
ONBOARDING_MARY_REVEALED = "mary_revealed"
ONBOARDING_RELATIONSHIP_DEVELOPING = "relationship_developing"

# Mantidos temporariamente para compatibilidade com código anterior.
ONBOARDING_ASK_NAME = ONBOARDING_FIRST_CONTACT
ONBOARDING_REQUEST_USER_PHOTO = "request_user_photo"
ONBOARDING_CONFIRM_USER_PHOTO = "confirm_user_photo"
ONBOARDING_MARY_MAY_REVEAL = "mary_may_reveal"
ONBOARDING_COMPLETE = ONBOARDING_RELATIONSHIP_DEVELOPING


DEFAULT_USER_PROFILE: dict[str, Any] = {
    # Será substituído pelo user_id persistente após carregar USERS.
    "profile_id": "",
    "name": "",
    "preferred_name": "",
    "onboarding_stage": ONBOARDING_FIRST_CONTACT,
    "created_at": "",
    "updated_at": "",
    "milestones": {
        "has_interacted": False,
        "name_known": False,
        "visual_reference_confirmed": False,
        "mary_revealed": False,
    },
    "visual_profile": {
        "reference_confirmed": False,
        "reference_version": 0,
        "reference_image_id": "",
        "stable_traits": [],
        "variable_traits": [],
        "current_appearance": {},
        "first_impression": "",
        "first_impression_created_at": "",
        "last_confirmed_at": "",
    },
    "mary_relationship": {
        "mary_revealed": False,
        "first_mary_image_id": "",
        "first_mary_image_reaction": "",
        "first_reveal_at": "",
        "started_at": "",
    },
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def criar_perfil_padrao(
    profile_id: str = "",
) -> dict[str, Any]:
    profile = deepcopy(DEFAULT_USER_PROFILE)
    now = utc_now_iso()

    profile["profile_id"] = str(profile_id or "").strip()
    profile["created_at"] = now
    profile["updated_at"] = now
    profile["mary_relationship"]["started_at"] = now

    return profile


def converter_booleano(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor

    texto = str(valor or "").strip().lower()

    return texto in {
        "true",
        "1",
        "sim",
        "yes",
        "verdadeiro",
    }


def calcular_estagio_resumido(
    profile: dict[str, Any],
) -> str:
    """
    Calcula um estado resumido apenas para diagnóstico.

    O resultado não obriga Mary a executar a próxima ação.
    """

    nome_conhecido = bool(
        str(
            profile.get("preferred_name")
            or profile.get("name")
            or ""
        ).strip()
    )

    visual_profile = profile.get("visual_profile")

    if not isinstance(visual_profile, dict):
        visual_profile = {}

    referencia_visual_confirmada = converter_booleano(
        visual_profile.get("reference_confirmed")
    )

    mary_relationship = profile.get("mary_relationship")

    if not isinstance(mary_relationship, dict):
        mary_relationship = {}

    mary_revelada = converter_booleano(
        mary_relationship.get("mary_revealed")
    )

    milestones = profile.get("milestones")

    if not isinstance(milestones, dict):
        milestones = {}

    houve_interacao = converter_booleano(
        milestones.get("has_interacted")
    )

    acontecimentos = sum(
        [
            nome_conhecido,
            referencia_visual_confirmada,
            mary_revelada,
        ]
    )

    if acontecimentos >= 2:
        return ONBOARDING_RELATIONSHIP_DEVELOPING

    if mary_revelada:
        return ONBOARDING_MARY_REVEALED

    if referencia_visual_confirmada:
        return ONBOARDING_USER_VISUAL_KNOWN

    if nome_conhecido:
        return ONBOARDING_NAME_KNOWN

    if houve_interacao:
        return ONBOARDING_FIRST_CONTACT

    return ONBOARDING_FIRST_CONTACT


def sincronizar_marcos(
    profile: dict[str, Any],
) -> dict[str, Any]:
    milestones = profile.setdefault(
        "milestones",
        {},
    )

    visual_profile = profile.setdefault(
        "visual_profile",
        {},
    )

    mary_relationship = profile.setdefault(
        "mary_relationship",
        {},
    )

    milestones["name_known"] = bool(
        str(
            profile.get("preferred_name")
            or profile.get("name")
            or ""
        ).strip()
    )

    milestones[
        "visual_reference_confirmed"
    ] = converter_booleano(
        visual_profile.get("reference_confirmed")
    )

    milestones["mary_revealed"] = converter_booleano(
        mary_relationship.get("mary_revealed")
    )

    milestones.setdefault(
        "has_interacted",
        False,
    )

    profile["onboarding_stage"] = calcular_estagio_resumido(
        profile
    )

    return profile


def normalizar_perfil(
    profile: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = criar_perfil_padrao()

    if not isinstance(profile, dict):
        return normalized

    for key in (
        "profile_id",
        "name",
        "preferred_name",
        "onboarding_stage",
        "created_at",
        "updated_at",
    ):
        if key in profile:
            normalized[key] = profile[key]

    milestones = profile.get("milestones")

    if isinstance(milestones, dict):
        normalized["milestones"].update(
            milestones
        )

    visual_profile = profile.get(
        "visual_profile"
    )

    if isinstance(visual_profile, dict):
        normalized["visual_profile"].update(
            visual_profile
        )

    mary_relationship = profile.get(
        "mary_relationship"
    )

    if isinstance(mary_relationship, dict):
        normalized["mary_relationship"].update(
            mary_relationship
        )

    normalized["profile_id"] = str(
        normalized.get("profile_id")
        or ""
    ).strip()

    normalized["name"] = str(
        normalized.get("name")
        or ""
    ).strip()

    normalized["preferred_name"] = str(
        normalized.get("preferred_name")
        or ""
    ).strip()

    if not normalized.get("created_at"):
        normalized["created_at"] = utc_now_iso()

    if not normalized[
        "mary_relationship"
    ].get("started_at"):
        normalized[
            "mary_relationship"
        ]["started_at"] = utc_now_iso()

    normalized = sincronizar_marcos(
        normalized
    )

    normalized["updated_at"] = utc_now_iso()

    return normalized


def definir_profile_id(
    profile: dict[str, Any],
    profile_id: str,
) -> dict[str, Any]:
    profile_id_normalizado = str(
        profile_id or ""
    ).strip()

    if not profile_id_normalizado:
        raise ValueError(
            "Informe um profile_id válido."
        )

    updated = normalizar_perfil(
        profile
    )

    updated["profile_id"] = profile_id_normalizado
    updated["updated_at"] = utc_now_iso()

    return updated


def definir_nome(
    profile: dict[str, Any],
    name: str,
) -> dict[str, Any]:
    normalized_name = " ".join(
        str(name or "").strip().split()
    )

    if len(normalized_name) < 2:
        raise ValueError(
            "Informe um nome válido."
        )

    updated = normalizar_perfil(
        profile
    )

    updated["name"] = normalized_name
    updated["preferred_name"] = normalized_name
    updated["milestones"]["name_known"] = True

    updated = sincronizar_marcos(
        updated
    )

    updated["updated_at"] = utc_now_iso()

    return updated


def definir_nome_preferido(
    profile: dict[str, Any],
    preferred_name: str,
) -> dict[str, Any]:
    normalized_name = " ".join(
        str(preferred_name or "").strip().split()
    )

    if len(normalized_name) < 2:
        raise ValueError(
            "Informe um nome válido."
        )

    updated = normalizar_perfil(
        profile
    )

    updated["preferred_name"] = normalized_name
    updated["milestones"]["name_known"] = True

    updated = sincronizar_marcos(
        updated
    )

    updated["updated_at"] = utc_now_iso()

    return updated


def obter_nome_usado_por_mary(
    profile: dict[str, Any],
) -> str:
    preferred_name = str(
        profile.get("preferred_name")
        or ""
    ).strip()

    if preferred_name:
        return preferred_name

    return str(
        profile.get("name")
        or ""
    ).strip()


def marcar_interacao_realizada(
    profile: dict[str, Any],
) -> dict[str, Any]:
    updated = normalizar_perfil(
        profile
    )

    updated["milestones"][
        "has_interacted"
    ] = True

    updated = sincronizar_marcos(
        updated
    )

    updated["updated_at"] = utc_now_iso()

    return updated


def avancar_onboarding(
    profile: dict[str, Any],
    stage: str,
) -> dict[str, Any]:
    """
    Mantido por compatibilidade.

    O estágio informado é aceito como indicação diagnóstica,
    mas não cria uma obrigação sequencial para Mary.
    """

    updated = normalizar_perfil(
        profile
    )

    stage_normalizado = str(
        stage or ""
    ).strip()

    if stage_normalizado:
        updated[
            "onboarding_stage"
        ] = stage_normalizado

    updated["updated_at"] = utc_now_iso()

    return updated


def confirmar_referencia_visual(
    profile: dict[str, Any],
    *,
    image_id: str,
    stable_traits: list[str],
    variable_traits: list[str] | None = None,
    current_appearance: dict[str, Any] | None = None,
    first_impression: str = "",
) -> dict[str, Any]:
    image_id_normalizado = str(
        image_id or ""
    ).strip()

    if not image_id_normalizado:
        raise ValueError(
            "Informe um image_id válido."
        )

    updated = normalizar_perfil(
        profile
    )

    visual = updated["visual_profile"]

    visual["reference_confirmed"] = True

    visual["reference_version"] = (
        int(
            visual.get(
                "reference_version",
                0,
            )
            or 0
        )
        + 1
    )

    visual[
        "reference_image_id"
    ] = image_id_normalizado

    visual["stable_traits"] = [
        str(item).strip()
        for item in stable_traits
        if str(item).strip()
    ]

    visual["variable_traits"] = [
        str(item).strip()
        for item in (
            variable_traits or []
        )
        if str(item).strip()
    ]

    visual["current_appearance"] = dict(
        current_appearance or {}
    )

    visual["last_confirmed_at"] = utc_now_iso()

    first_impression_normalizada = str(
        first_impression or ""
    ).strip()

    if (
        first_impression_normalizada
        and not visual.get(
            "first_impression"
        )
    ):
        visual[
            "first_impression"
        ] = first_impression_normalizada

        visual[
            "first_impression_created_at"
        ] = utc_now_iso()

    updated["milestones"][
        "visual_reference_confirmed"
    ] = True

    updated = sincronizar_marcos(
        updated
    )

    updated["updated_at"] = utc_now_iso()

    return updated


def atualizar_aparencia_atual(
    profile: dict[str, Any],
    current_appearance: dict[str, Any],
) -> dict[str, Any]:
    updated = normalizar_perfil(
        profile
    )

    updated["visual_profile"][
        "current_appearance"
    ] = dict(
        current_appearance or {}
    )

    updated["updated_at"] = utc_now_iso()

    return updated


def marcar_mary_revelada(
    profile: dict[str, Any],
    *,
    image_id: str,
) -> dict[str, Any]:
    image_id_normalizado = str(
        image_id or ""
    ).strip()

    if not image_id_normalizado:
        raise ValueError(
            "Informe um image_id válido."
        )

    updated = normalizar_perfil(
        profile
    )

    relationship = updated[
        "mary_relationship"
    ]

    relationship["mary_revealed"] = True

    if not relationship.get(
        "first_mary_image_id"
    ):
        relationship[
            "first_mary_image_id"
        ] = image_id_normalizado

    if not relationship.get(
        "first_reveal_at"
    ):
        relationship[
            "first_reveal_at"
        ] = utc_now_iso()

    updated["milestones"][
        "mary_revealed"
    ] = True

    updated = sincronizar_marcos(
        updated
    )

    updated["updated_at"] = utc_now_iso()

    return updated


def registrar_reacao_primeira_imagem_mary(
    profile: dict[str, Any],
    reaction: str,
) -> dict[str, Any]:
    reaction_normalizada = str(
        reaction or ""
    ).strip()

    updated = normalizar_perfil(
        profile
    )

    relationship = updated[
        "mary_relationship"
    ]

    if (
        reaction_normalizada
        and not relationship.get(
            "first_mary_image_reaction"
        )
    ):
        relationship[
            "first_mary_image_reaction"
        ] = reaction_normalizada

    updated["updated_at"] = utc_now_iso()

    return updated
