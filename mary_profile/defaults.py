from __future__ import annotations

# Compatibilidade temporária durante a divisão mecânica de core.py.
# As definições continuam canônicas em core.py até a troca atômica final.
from .core import (
    DEFAULT_MARY_PROFILE,
    DEFAULT_PUBLIC_PROFILE_IMAGE_PATH,
    MARY_PROFILE_VERSION,
)

__all__ = [
    "MARY_PROFILE_VERSION",
    "DEFAULT_PUBLIC_PROFILE_IMAGE_PATH",
    "DEFAULT_MARY_PROFILE",
]
