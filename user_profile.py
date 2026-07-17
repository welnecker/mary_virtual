from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


ONBOARDING_ASK_NAME = "ask_name"
ONBOARDING_NAME_KNOWN = "name_known"
ONBOARDING_REQUEST_USER_PHOTO = "request_user_photo"
ONBOARDING_CONFIRM_USER_PHOTO = "confirm_user_photo"
ONBOARDING_USER_VISUAL_KNOWN = "user_visual_known"
ONBOARDING_MARY_MAY_REVEAL = "mary_may_reveal"
ONBOARDING_COMPLETE = "complete"


DEFAULT_USER_PROFILE: dict[str, Any] = {
    "profile_id": "primary_user",
    "name": "",
    "preferred_name": "",
    "onboarding_stage": ONBOARDING_ASK_NAME,
    "created_at": "",
    "updated_at": "",
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
        "started_at": "",
    },
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def criar_perfil_padrao() -> dict[str, Any]:
    profile = deepcopy(DEFAULT_USER_PROFILE)
    now = utc_now_iso()

    profile["created_at"] = now
    profile["updated_at"] = now
    profile["mary_relationship"]["started_at"] = now

    return profile


def normalizar_perfil(profile: dict[str, Any] | None) -> dict[str, Any]:
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

    visual_profile = profile.get("visual_profile")

    if isinstance(visual_profile, dict):
        normalized["visual_profile"].update(visual_profile)

    mary_relationship = profile.get("mary_relationship")

    if isinstance(mary_relationship, dict):
        normalized["mary_relationship"].update(mary_relationship)

    if not normalized["created_at"]:
        normalized["created_at"] = utc_now_iso()

    normalized["updated_at"] = utc_now_iso()

    return normalized


def definir_nome(
    profile: dict[str, Any],
    name: str,
) -> dict[str, Any]:
    normalized_name = " ".join((name or "").strip().split())

    if len(normalized_name) < 2:
        raise ValueError("Informe um nome válido.")

    updated = normalizar_perfil(profile)

    updated["name"] = normalized_name
    updated["preferred_name"] = normalized_name
    updated["onboarding_stage"] = ONBOARDING_NAME_KNOWN
    updated["updated_at"] = utc_now_iso()

    return updated


def definir_nome_preferido(
    profile: dict[str, Any],
    preferred_name: str,
) -> dict[str, Any]:
    normalized_name = " ".join((preferred_name or "").strip().split())

    if len(normalized_name) < 2:
        raise ValueError("Informe um nome válido.")

    updated = normalizar_perfil(profile)

    updated["preferred_name"] = normalized_name
    updated["updated_at"] = utc_now_iso()

    return updated


def obter_nome_usado_por_mary(profile: dict[str, Any]) -> str:
    preferred_name = str(profile.get("preferred_name", "") or "").strip()

    if preferred_name:
        return preferred_name

    return str(profile.get("name", "") or "").strip()


def avancar_onboarding(
    profile: dict[str, Any],
    stage: str,
) -> dict[str, Any]:
    updated = normalizar_perfil(profile)

    updated["onboarding_stage"] = stage
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
    updated = normalizar_perfil(profile)
    visual = updated["visual_profile"]

    visual["reference_confirmed"] = True
    visual["reference_version"] = int(
        visual.get("reference_version", 0)
    ) + 1
    visual["reference_image_id"] = image_id
    visual["stable_traits"] = list(stable_traits)
    visual["variable_traits"] = list(variable_traits or [])
    visual["current_appearance"] = dict(current_appearance or {})
    visual["last_confirmed_at"] = utc_now_iso()

    if first_impression and not visual.get("first_impression"):
        visual["first_impression"] = first_impression
        visual["first_impression_created_at"] = utc_now_iso()

    updated["onboarding_stage"] = ONBOARDING_USER_VISUAL_KNOWN
    updated["updated_at"] = utc_now_iso()

    return updated


def marcar_mary_revelada(
    profile: dict[str, Any],
    *,
    image_id: str,
) -> dict[str, Any]:
    updated = normalizar_perfil(profile)
    relationship = updated["mary_relationship"]

    relationship["mary_revealed"] = True
    relationship["first_mary_image_id"] = (
        relationship.get("first_mary_image_id") or image_id
    )

    updated["onboarding_stage"] = ONBOARDING_COMPLETE
    updated["updated_at"] = utc_now_iso()

    return updated
