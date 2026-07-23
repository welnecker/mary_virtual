from __future__ import annotations

from copy import deepcopy
from functools import wraps
from typing import Any, Callable

import scenarios.registry as scenario_registry


SCENARIO_DURATION_EXTENSION_VERSION = "scenario-duration-extension-v1-double-all"
DURATION_MULTIPLIER = 2
_MARKER = "_duration_multiplier_applied"
_INSTALLED = False


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def dobrar_duracao_configuracao(config: dict[str, Any]) -> dict[str, Any]:
    """Dobra a duração narrativa uma única vez, preservando o restante."""

    result = deepcopy(config if isinstance(config, dict) else {})
    if _safe_int(result.get(_MARKER), 0) == DURATION_MULTIPLIER:
        return result

    duration = result.get("duration")
    if not isinstance(duration, dict):
        duration = {}
        result["duration"] = duration

    for field in (
        "target_interactions",
        "soft_ending_start",
        "hard_ending_limit",
    ):
        current = _safe_int(duration.get(field), 0)
        if current > 0:
            duration[field] = current * DURATION_MULTIPLIER

    maximum = _safe_int(result.get("max_interactions"), 0)
    if maximum > 0:
        result["max_interactions"] = maximum * DURATION_MULTIPLIER

    phases = result.get("phases")
    if isinstance(phases, dict):
        for phase in phases.values():
            if not isinstance(phase, dict):
                continue
            target_range = phase.get("target_range")
            if isinstance(target_range, list) and len(target_range) == 2:
                phase["target_range"] = [
                    max(1, _safe_int(target_range[0], 1) * DURATION_MULTIPLIER),
                    max(1, _safe_int(target_range[1], 1) * DURATION_MULTIPLIER),
                ]

    rules = result.get("narrative_rules")
    if isinstance(rules, list):
        cleaned: list[str] = []
        for rule in rules:
            text = str(rule or "").strip()
            lower = text.casefold()
            if (
                "nunca ultrapassa" in lower
                or "a partir da interação" in lower
                or "a partir da interacao" in lower
            ):
                continue
            if text:
                cleaned.append(text)
        hard_limit = _safe_int(duration.get("hard_ending_limit"), 0)
        soft_start = _safe_int(duration.get("soft_ending_start"), 0)
        if hard_limit > 0:
            cleaned.append(
                f"A história nunca ultrapassa {hard_limit} interações válidas."
            )
        if soft_start > 0:
            cleaned.append(
                f"A partir da interação {soft_start}, cada turno deve aproximar a história da resolução."
            )
        result["narrative_rules"] = cleaned

    result[_MARKER] = DURATION_MULTIPLIER
    return result


def _wrap_config_loader(loader: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    if getattr(loader, "_mary_duration_doubled", False):
        return loader

    @wraps(loader)
    def wrapped(*args: Any, **kwargs: Any) -> dict[str, Any]:
        config = loader(*args, **kwargs)
        return dobrar_duracao_configuracao(config)

    setattr(wrapped, "_mary_duration_doubled", True)
    return wrapped


def install_scenario_duration_extension() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    loaders = getattr(scenario_registry, "SCENARIO_LOADERS", {})
    if isinstance(loaders, dict):
        for entry in loaders.values():
            if not isinstance(entry, dict):
                continue
            loader = entry.get("config_loader")
            if callable(loader):
                entry["config_loader"] = _wrap_config_loader(loader)

    _INSTALLED = True


__all__ = [
    "SCENARIO_DURATION_EXTENSION_VERSION",
    "DURATION_MULTIPLIER",
    "dobrar_duracao_configuracao",
    "install_scenario_duration_extension",
]
