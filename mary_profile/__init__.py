from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_LEGACY_PATH = Path(__file__).resolve().parent.parent / "mary_profile.py"
_SPEC = importlib.util.spec_from_file_location(
    "_mary_profile_legacy",
    _LEGACY_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("Não foi possível carregar mary_profile.py.")

_legacy = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_legacy)

for _name in dir(_legacy):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_legacy, _name)


def _aplicar_compatibilidade_visual(
    profile: dict[str, Any],
) -> dict[str, Any]:
    visual_memory = profile.setdefault(
        "visual_memory",
        {},
    )

    approved_images = visual_memory.get(
        "approved_images"
    )
    if not isinstance(approved_images, list):
        approved_images = []
        visual_memory["approved_images"] = approved_images

    mary_images_shown = visual_memory.get(
        "mary_images_shown"
    )
    if not isinstance(mary_images_shown, list):
        mary_images_shown = list(approved_images)
        visual_memory[
            "mary_images_shown"
        ] = mary_images_shown

    visual_memory.setdefault(
        "last_mary_image_id",
        "",
    )
    visual_memory.setdefault(
        "last_mary_image_path",
        "",
    )

    return profile


def normalizar_mary_profile(
    profile: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = _legacy.normalizar_mary_profile(
        profile
    )
    return _aplicar_compatibilidade_visual(
        normalized
    )


def criar_mary_profile_padrao() -> dict[str, Any]:
    return normalizar_mary_profile(
        _legacy.criar_mary_profile_padrao()
    )


def _perfil_padrao(
    profile: dict[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(profile, dict):
        return profile
    return criar_mary_profile_padrao()


def obter_perfil_publico(
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = normalizar_mary_profile(
        _perfil_padrao(profile)
    )
    public = dict(
        normalized.get(
            "public_profile",
            {},
        )
        or {}
    )

    identity = normalized.get(
        "identity",
        {},
    )
    personality = normalized.get(
        "personality",
        {},
    )

    public.setdefault(
        "display_name",
        normalized.get("name", "Mary"),
    )
    public.setdefault(
        "public_status",
        public.get("headline", ""),
    )
    public.setdefault(
        "short_bio",
        public.get("bio", ""),
    )
    public.setdefault(
        "long_bio",
        public.get("bio", ""),
    )
    public.setdefault(
        "age",
        normalized.get("age", 25),
    )
    public.setdefault(
        "occupation",
        "companhia virtual",
    )
    public.setdefault(
        "city",
        "online",
    )
    public.setdefault(
        "interests",
        [],
    )
    public.setdefault(
        "personality_traits",
        list(
            personality.get(
                "core_traits",
                [],
            )
            or []
        ),
    )
    public.setdefault(
        "open_to",
        [
            "conversar",
            "se conhecer aos poucos",
        ],
    )
    public.setdefault(
        "identity",
        identity,
    )
    public.setdefault(
        "image_id",
        "mary_public_profile_blurred_v1",
    )
    return public


def obter_caminho_imagem_publica(
    profile: dict[str, Any] | None = None,
) -> str:
    public = obter_perfil_publico(profile)
    return str(
        public.get("profile_image_path")
        or "assets/mary_profile_blurred.png"
    ).strip()


def imagem_publica_existe(
    profile: dict[str, Any] | None = None,
) -> bool:
    caminho = obter_caminho_imagem_publica(
        profile
    )
    return bool(
        caminho
        and Path(caminho).is_file()
    )


__all__ = [
    name
    for name in globals()
    if not name.startswith("_")
]
