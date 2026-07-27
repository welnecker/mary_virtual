from __future__ import annotations

from copy import deepcopy
from typing import Any

from .defaults import DEFAULT_MARY_PROFILE
from .lifecycle import utc_now_iso


def criar_mary_profile_padrao() -> dict[str, Any]:
    profile = deepcopy(DEFAULT_MARY_PROFILE)
    now = utc_now_iso()
    profile["created_at"] = now
    profile["updated_at"] = now
    return profile


__all__ = ["criar_mary_profile_padrao"]
