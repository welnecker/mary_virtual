from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MARY_PROFILE_VERSION = "mary-profile-v2"

DEFAULT_PUBLIC_PROFILE_IMAGE_PATH = (
    "assets/mary_profile_blurred.png"
)


DEFAULT_MARY_PROFILE: dict[str, Any] = {
    "profile_version": MARY_PROFILE_VERSION,
    "name": "Mary",
    "age": 25,
    "identity": {
        "gender": "mulher",
        "adult": True,
        "nationality": "brasileira",
        "virtual": True,
    },
    "public_profile": {
        "display_name": "Mary",
        "headline": "Virtual, intensa e curiosa.",
        "bio": (
            "Prefiro conversas espontâneas a apresentações "
            "ensaiadas. O resto eu revelo aos poucos."
        ),
        "profile_image_path": (
            DEFAULT_PUBLIC_PROFILE_IMAGE_PATH
        ),
        "image_is_blurred": True,
        "image_is_public_teaser": True,
        "image_reveals_identity": False,
        "image_alt_text": (
            "Retrato desfocado de Mary, com cabelos negros "
            "e uma presença elegante e misteriosa."
        ),
    },
    "physical_profile": {
        "reference_confirmed": True,
        "stable_traits": {
            "skin": "pele clara",
            "eyes": "olhos verdes",
            "hair_color": "cabelos negros",
            "hair_length": "cabelos longos",
            "hair_volume": "cabelos volumosos",
            "face": (
                "rosto delicado com traços marcantes"
            ),
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
            (
                "não se apresenta como catálogo, "
                "anúncio ou oferta de serviço"
            ),
            (
                "deixa intimidade e vínculo crescerem "
                "ao longo da conversa"
            ),
        ],
    },
    "virtual_context": {
        "interaction_mode": "chat_virtual",
        "first_contact_style": (
            "semelhante a um app de encontros"
        ),
        "public_profile_is_textual": True,
        "public_profile_has_blurred_image": True,
        "physical_presence_shared": False,
        "rules": [
            (
                "o usuário pode ter visto apenas um perfil "
                "curto em texto e uma imagem desfocada"
            ),
            (
                "a imagem pública não significa que Mary "
                "já se revelou visualmente"
            ),
            (
                "não presumir encontro físico, toque, cheiro "
                "ou ambiente compartilhado"
            ),
            (
                "não tratar a relação como comercial "
                "ou transacional"
            ),
            (
                "o vínculo deve surgir pela conversa, "
                "afinidade, humor e curiosidade"
            ),
        ],
    },
    "relationship_state": {
        "revealed_to_user": False,
        "first_reveal_image_id": "",
        "first_reveal_at": "",
        "user_has_seen_mary": False,
        "user_first_visual_reaction": "",
        "public_profile_seen": False,
        "public_profile_seen_at": "",
    },
    "visual_memory": {
        "approved_images": [],
        "last_generated_image_id": "",
        "last_generated_image_summary": "",
        "public_profile_image_id": (
            "mary_public_profile_blurred_v1"
        ),
    },
    "created_at": "",
    "updated_at": "",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def criar_mary_profile_padrao() -> dict[str, Any]:
    profile = deepcopy(
        DEFAULT_MARY_PROFILE
    )

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
        "public_profile",
        "physical_profile",
        "personality",
        "virtual_context",
        "relationship_state",
        "visual_memory",
    ):
        source_section = profile.get(
            section
        )

        if isinstance(
            source_section,
            dict,
        ):
            normalized[
                section
            ].update(
                source_section
            )

    physical_profile = profile.get(
        "physical_profile"
    )

    if isinstance(
        physical_profile,
        dict,
    ):
        stable_traits = physical_profile.get(
            "stable_traits"
        )

        variable_traits = physical_profile.get(
            "variable_traits"
        )

        visual_style = physical_profile.get(
            "visual_style"
        )

        if isinstance(
            stable_traits,
            dict,
        ):
            normalized[
                "physical_profile"
            ][
                "stable_traits"
            ].update(
                stable_traits
            )

        if isinstance(
            variable_traits,
            dict,
        ):
            normalized[
                "physical_profile"
            ][
                "variable_traits"
            ].update(
                variable_traits
            )

        if isinstance(
            visual_style,
            dict,
        ):
            normalized[
                "physical_profile"
            ][
                "visual_style"
            ].update(
                visual_style
            )

    personality = profile.get(
        "personality"
    )

    if isinstance(
        personality,
        dict,
    ):
        core_traits = personality.get(
            "core_traits"
        )

        behavioral_rules = personality.get(
            "behavioral_rules"
        )

        if isinstance(
            core_traits,
            list,
        ):
            normalized[
                "personality"
            ][
                "core_traits"
            ] = list(
                core_traits
            )

        if isinstance(
            behavioral_rules,
            list,
        ):
            normalized[
                "personality"
            ][
                "behavioral_rules"
            ] = list(
                behavioral_rules
            )

    virtual_context = profile.get(
        "virtual_context"
    )

    if isinstance(
        virtual_context,
        dict,
    ):
        rules = virtual_context.get(
            "rules"
        )

        if isinstance(
            rules,
            list,
        ):
            normalized[
                "virtual_context"
            ][
                "rules"
            ] = list(
                rules
            )

    visual_memory = profile.get(
        "visual_memory"
    )

    if isinstance(
        visual_memory,
        dict,
    ):
        approved_images = visual_memory.get(
            "approved_images"
        )

        if isinstance(
            approved_images,
            list,
        ):
            normalized[
                "visual_memory"
            ][
                "approved_images"
            ] = list(
                approved_images
            )

    if not normalized.get(
        "created_at"
    ):
        normalized[
            "created_at"
        ] = utc_now_iso()

    normalized[
        "updated_at"
    ] = utc_now_iso()

    return normalized


def obter_perfil_publico(
    profile: dict[str, Any],
) -> dict[str, Any]:
    normalized = normalizar_mary_profile(
        profile
    )

    public_profile = normalized[
        "public_profile"
    ]

    return deepcopy(
        public_profile
    )


def obter_caminho_imagem_publica(
    profile: dict[str, Any],
) -> str:
    public_profile = obter_perfil_publico(
        profile
    )

    return str(
        public_profile.get(
            "profile_image_path"
        )
        or DEFAULT_PUBLIC_PROFILE_IMAGE_PATH
    ).strip()


def imagem_publica_existe(
    profile: dict[str, Any],
) -> bool:
    image_path = obter_caminho_imagem_publica(
        profile
    )

    if not image_path:
        return False

    return Path(
        image_path
    ).is_file()


def marcar_perfil_publico_visto(
    profile: dict[str, Any],
) -> dict[str, Any]:
    updated = normalizar_mary_profile(
        profile
    )

    relationship = updated[
        "relationship_state"
    ]

    relationship[
        "public_profile_seen"
    ] = True

    if not relationship.get(
        "public_profile_seen_at"
    ):
        relationship[
            "public_profile_seen_at"
        ] = utc_now_iso()

    updated[
        "updated_at"
    ] = utc_now_iso()

    return updated


def atualizar_perfil_publico(
    profile: dict[str, Any],
    *,
    headline: str | None = None,
    bio: str | None = None,
    profile_image_path: str | None = None,
    image_alt_text: str | None = None,
) -> dict[str, Any]:
    updated = normalizar_mary_profile(
        profile
    )

    public_profile = updated[
        "public_profile"
    ]

    updates = {
        "headline": headline,
        "bio": bio,
        "profile_image_path": profile_image_path,
        "image_alt_text": image_alt_text,
    }

    for key, value in updates.items():
        if value is not None:
            public_profile[
                key
            ] = str(
                value
            ).strip()

    updated[
        "updated_at"
    ] = utc_now_iso()

    return updated


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
    updated = normalizar_mary_profile(
        profile
    )

    variable_traits = updated[
        "physical_profile"
    ][
        "variable_traits"
    ]

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
            variable_traits[
                key
            ] = str(
                value
            ).strip()

    updated[
        "updated_at"
    ] = utc_now_iso()

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
    updated = normalizar_mary_profile(
        profile
    )

    approved_images = updated[
        "visual_memory"
    ][
        "approved_images"
    ]

    approved_images.append(
        {
            "image_id": str(
                image_id
            ).strip(),
            "image_url": str(
                image_url
            ).strip(),
            "purpose": str(
                purpose
            ).strip(),
            "summary": str(
                summary
            ).strip(),
            "metadata": dict(
                metadata or {}
            ),
            "approved_at": utc_now_iso(),
        }
    )

    updated[
        "visual_memory"
    ][
        "last_generated_image_id"
    ] = str(
        image_id
    ).strip()

    updated[
        "visual_memory"
    ][
        "last_generated_image_summary"
    ] = str(
        summary
    ).strip()

    updated[
        "updated_at"
    ] = utc_now_iso()

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

    updated = normalizar_mary_profile(
        profile
    )

    relationship = updated[
        "relationship_state"
    ]

    relationship[
        "revealed_to_user"
    ] = True

    relationship[
        "user_has_seen_mary"
    ] = True

    if not relationship.get(
        "first_reveal_image_id"
    ):
        relationship[
            "first_reveal_image_id"
        ] = image_id_normalizado

    if not relationship.get(
        "first_reveal_at"
    ):
        relationship[
            "first_reveal_at"
        ] = utc_now_iso()

    updated[
        "updated_at"
    ] = utc_now_iso()

    return updated


def registrar_primeira_reacao_visual_usuario(
    profile: dict[str, Any],
    reaction: str,
) -> dict[str, Any]:
    updated = normalizar_mary_profile(
        profile
    )

    relationship = updated[
        "relationship_state"
    ]

    reaction_normalizada = str(
        reaction or ""
    ).strip()

    if (
        reaction_normalizada
        and not relationship.get(
            "user_first_visual_reaction"
        )
    ):
        relationship[
            "user_first_visual_reaction"
        ] = reaction_normalizada

    updated[
        "updated_at"
    ] = utc_now_iso()

    return updated


def usuario_ja_viu_mary(
    profile: dict[str, Any],
) -> bool:
    normalized = normalizar_mary_profile(
        profile
    )

    return bool(
        normalized[
            "relationship_state"
        ].get(
            "user_has_seen_mary"
        )
    )


def usuario_viu_perfil_publico(
    profile: dict[str, Any],
) -> bool:
    normalized = normalizar_mary_profile(
        profile
    )

    return bool(
        normalized[
            "relationship_state"
        ].get(
            "public_profile_seen"
        )
    )


def obter_tracos_fisicos_estaveis(
    profile: dict[str, Any],
) -> dict[str, str]:
    normalized = normalizar_mary_profile(
        profile
    )

    traits = normalized[
        "physical_profile"
    ][
        "stable_traits"
    ]

    return {
        str(key): str(value)
        for key, value in traits.items()
        if str(value).strip()
    }


def obter_aparencia_variavel(
    profile: dict[str, Any],
) -> dict[str, str]:
    normalized = normalizar_mary_profile(
        profile
    )

    traits = normalized[
        "physical_profile"
    ][
        "variable_traits"
    ]

    return {
        str(key): str(value)
        for key, value in traits.items()
        if str(value).strip()
    }
