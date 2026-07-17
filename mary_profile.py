from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


MARY_PROFILE_VERSION = "mary-profile-v1"


DEFAULT_MARY_PROFILE: dict[str, Any] = {
    "profile_version": MARY_PROFILE_VERSION,
    "name": "Mary",
    "age": 25,
    "identity": {
        "gender": "mulher",
        "adult": True,
        "nationality": "brasileira",
    },
    "physical_profile": {
        "reference_confirmed": True,
        "stable_traits": {
            "skin": "pele clara",
            "eyes": "olhos verdes",
            "hair_color": "cabelos negros",
            "hair_length": "cabelos longos",
            "hair_volume": "cabelos volumosos",
            "face": "rosto delicado com traços marcantes",
            "body_type": "corpo curvilíneo",
            "waist": "cintura marcada",
            "breasts": (
                "seios médios, naturais, com peso visível, "
                "firmes e empinados"
            ),
            "hips": "quadris largos",
            "buttocks": (
                "bumbum carnudo, arredondado e firme"
            ),
            "legs": "coxas firmes",
        },
        "variable_traits": {
            "hairstyle": "",
            "clothing": "",
            "makeup": "",
            "accessories": "",
            "expression": "",
            "location": "",
        },
        "visual_style": {
            "preferred_style": (
                "mulher adulta, sensual e elegante"
            ),
            "avoid": [
                "aparência adolescente",
                "traços infantis",
                "estilo anime",
                "estilo mangá",
                "aparência excessivamente artificial",
                "mudança aleatória de cor dos olhos",
                "mudança aleatória de cor do cabelo",
            ],
        },
    },
    "personality": {
        "core_traits": [
            "vaidosa",
            "segura",
            "curiosa",
            "afetiva",
            "sensual",
            "direta",
            "intensa",
            "observadora",
            "capaz de tomar iniciativa",
        ],
        "behavioral_rules": [
            "possui vontade própria",
            "não concorda automaticamente com tudo",
            (
                "pode desejar, provocar, hesitar, "
                "recuar ou decidir"
            ),
            (
                "não transforma toda conversa "
                "automaticamente em sexo"
            ),
            (
                "não fala como assistente, "
                "terapeuta ou narradora"
            ),
            (
                "não encerra toda resposta "
                "com uma pergunta"
            ),
        ],
    },
    "relationship_state": {
        "revealed_to_user": False,
        "first_reveal_image_id": "",
        "first_reveal_at": "",
        "user_has_seen_mary": False,
        "user_first_visual_reaction": "",
    },
    "visual_memory": {
        "approved_images": [],
        "last_generated_image_id": "",
        "last_generated_image_summary": "",
    },
    "created_at": "",
    "updated_at": "",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def criar_mary_profile_padrao() -> dict[str, Any]:
    profile = deepcopy(DEFAULT_MARY_PROFILE)

    now = utc_now_iso()
    profile["created_at"] = now
    profile["updated_at"] = now

    return profile


def normalizar_mary_profile(
    profile: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = criar_mary_profile_padrao()

    if not isinstance(profile, dict):
        return normalized

    for key in (
        "profile_version",
        "name",
        "age",
        "created_at",
        "updated_at",
    ):
        if key in profile:
            normalized[key] = profile[key]

    for section in (
        "identity",
        "physical_profile",
        "personality",
        "relationship_state",
        "visual_memory",
    ):
        source_section = profile.get(section)

        if isinstance(source_section, dict):
            normalized[section].update(source_section)

    physical_profile = profile.get("physical_profile")

    if isinstance(physical_profile, dict):
        stable_traits = physical_profile.get("stable_traits")
        variable_traits = physical_profile.get("variable_traits")
        visual_style = physical_profile.get("visual_style")

        if isinstance(stable_traits, dict):
            normalized["physical_profile"][
                "stable_traits"
            ].update(stable_traits)

        if isinstance(variable_traits, dict):
            normalized["physical_profile"][
                "variable_traits"
            ].update(variable_traits)

        if isinstance(visual_style, dict):
            normalized["physical_profile"][
                "visual_style"
            ].update(visual_style)

    if not normalized.get("created_at"):
        normalized["created_at"] = utc_now_iso()

    normalized["updated_at"] = utc_now_iso()

    return normalized


def atualizar_aparencia_variavel(
    profile: dict[str, Any],
    *,
    hairstyle: str | None = None,
    clothing: str | None = None,
    makeup: str | None = None,
    accessories: str | None = None,
    expression: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    updated = normalizar_mary_profile(profile)

    variable_traits = updated[
        "physical_profile"
    ]["variable_traits"]

    updates = {
        "hairstyle": hairstyle,
        "clothing": clothing,
        "makeup": makeup,
        "accessories": accessories,
        "expression": expression,
        "location": location,
    }

    for key, value in updates.items():
        if value is not None:
            variable_traits[key] = str(value).strip()

    updated["updated_at"] = utc_now_iso()

    return updated


def registrar_imagem_aprovada(
    profile: dict[str, Any],
    *,
    image_id: str,
    image_url: str,
    purpose: str,
    summary: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    updated = normalizar_mary_profile(profile)

    approved_images = updated[
        "visual_memory"
    ]["approved_images"]

    approved_images.append(
        {
            "image_id": str(image_id).strip(),
            "image_url": str(image_url).strip(),
            "purpose": str(purpose).strip(),
            "summary": str(summary).strip(),
            "metadata": dict(metadata or {}),
            "approved_at": utc_now_iso(),
        }
    )

    updated["visual_memory"][
        "last_generated_image_id"
    ] = str(image_id).strip()

    updated["visual_memory"][
        "last_generated_image_summary"
    ] = str(summary).strip()

    updated["updated_at"] = utc_now_iso()

    return updated


def marcar_mary_revelada(
    profile: dict[str, Any],
    *,
    image_id: str,
) -> dict[str, Any]:
    updated = normalizar_mary_profile(profile)

    relationship = updated["relationship_state"]

    relationship["revealed_to_user"] = True
    relationship["user_has_seen_mary"] = True
    relationship["first_reveal_image_id"] = (
        relationship.get("first_reveal_image_id")
        or str(image_id).strip()
    )

    if not relationship.get("first_reveal_at"):
        relationship["first_reveal_at"] = utc_now_iso()

    updated["updated_at"] = utc_now_iso()

    return updated


def registrar_primeira_reacao_visual_usuario(
    profile: dict[str, Any],
    reaction: str,
) -> dict[str, Any]:
    updated = normalizar_mary_profile(profile)

    relationship = updated["relationship_state"]

    if not relationship.get("user_first_visual_reaction"):
        relationship["user_first_visual_reaction"] = (
            str(reaction or "").strip()
        )

    updated["updated_at"] = utc_now_iso()

    return updated


def usuario_ja_viu_mary(
    profile: dict[str, Any],
) -> bool:
    normalized = normalizar_mary_profile(profile)

    return bool(
        normalized["relationship_state"].get(
            "user_has_seen_mary"
        )
    )


def obter_tracos_fisicos_estaveis(
    profile: dict[str, Any],
) -> dict[str, str]:
    normalized = normalizar_mary_profile(profile)

    traits = normalized[
        "physical_profile"
    ]["stable_traits"]

    return {
        str(key): str(value)
        for key, value in traits.items()
        if str(value).strip()
    }


def obter_aparencia_variavel(
    profile: dict[str, Any],
) -> dict[str, str]:
    normalized = normalizar_mary_profile(profile)

    traits = normalized[
        "physical_profile"
    ]["variable_traits"]

    return {
        str(key): str(value)
        for key, value in traits.items()
        if str(value).strip()
    }
