from __future__ import annotations

import os
from typing import Final


CONFIG_VERSION: Final[str] = "mary-config-v2-centralized-runtime"


def _env_text(name: str, default: str) -> str:
    value = str(os.getenv(name, "") or "").strip()
    return value or default


def _env_int(
    name: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    try:
        value = int(str(os.getenv(name, default)).strip())
    except (TypeError, ValueError):
        value = default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _env_float(
    name: str,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    try:
        value = float(str(os.getenv(name, default)).strip())
    except (TypeError, ValueError):
        value = default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = str(os.getenv(name, "") or "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "sim", "on"}:
        return True
    if raw in {"0", "false", "no", "nao", "não", "off"}:
        return False
    return default


# Aplicação e modelo.
APP_TITLE: Final[str] = _env_text("MARY_APP_TITLE", "Mary Virtual")
APP_CAPTION: Final[str] = _env_text(
    "MARY_APP_CAPTION",
    "Histórias interativas com texto, fotografia e voz.",
)
APP_VERSION: Final[str] = "mary-app-v2-professional-persistent"
PROMPT_VERSION: Final[str] = "mary-prompt-v6-memory-continuity"
MODEL_DEFAULT: Final[str] = _env_text(
    "MARY_MODEL_DEFAULT",
    "google/gemini-3-flash-preview",
)
OPENROUTER_URL: Final[str] = _env_text(
    "OPENROUTER_URL",
    "https://openrouter.ai/api/v1/chat/completions",
)
MARY_SPREADSHEET_ID: Final[str] = _env_text(
    "MARY_SPREADSHEET_ID",
    "1lOd92EhC-UZmK48kYS-Q_HYO9qpRU5BxpM2uUlVWD-g",
)
REQUEST_TIMEOUT_SECONDS: Final[int] = _env_int(
    "MARY_REQUEST_TIMEOUT_SECONDS",
    120,
    minimum=15,
    maximum=300,
)


# Contexto recente. O resumo, a continuidade e as memórias preservam fatos antigos;
# o histórico bruto não precisa carregar toda a história até o fim.
MAX_HISTORY_MESSAGES: Final[int] = _env_int(
    "MARY_MAX_HISTORY_MESSAGES",
    40,
    minimum=12,
    maximum=120,
)
RECENT_MESSAGES_PROMPT_LIMIT: Final[int] = _env_int(
    "MARY_RECENT_MESSAGES_PROMPT_LIMIT",
    8,
    minimum=4,
    maximum=16,
)


# Memória persistente.
MEMORY_PROMPT_LIMIT: Final[int] = _env_int(
    "MARY_MEMORY_PROMPT_LIMIT",
    8,
    minimum=1,
    maximum=16,
)
MEMORY_MAX_PER_USER: Final[int] = _env_int(
    "MARY_MEMORY_MAX_PER_USER",
    120,
    minimum=20,
    maximum=500,
)
MEMORY_EXPLICIT_CAPTURE_ENABLED: Final[bool] = _env_bool(
    "MARY_MEMORY_EXPLICIT_CAPTURE_ENABLED",
    True,
)
MEMORY_CONFIRMED_ONLY: Final[bool] = _env_bool(
    "MARY_MEMORY_CONFIRMED_ONLY",
    True,
)


# Ritmo narrativo. Cada cenário pode sobrescrever esses valores em duration.
SCENARIO_DEFAULT_TARGET_INTERACTIONS: Final[int] = _env_int(
    "MARY_SCENARIO_TARGET_INTERACTIONS",
    24,
    minimum=6,
    maximum=80,
)
SCENARIO_DEFAULT_SOFT_ENDING_START: Final[int] = _env_int(
    "MARY_SCENARIO_SOFT_ENDING_START",
    18,
    minimum=4,
    maximum=70,
)
SCENARIO_DEFAULT_HARD_ENDING_LIMIT: Final[int] = _env_int(
    "MARY_SCENARIO_HARD_ENDING_LIMIT",
    36,
    minimum=10,
    maximum=100,
)
SCENARIO_DEFAULT_ENDING_TURNS: Final[int] = _env_int(
    "MARY_SCENARIO_ENDING_TURNS",
    2,
    minimum=1,
    maximum=4,
)
SCENARIO_COUNT_POLICY_ENABLED: Final[bool] = _env_bool(
    "MARY_SCENARIO_COUNT_POLICY_ENABLED",
    True,
)
SCENARIO_REPETITION_GUARD_TURNS: Final[int] = _env_int(
    "MARY_SCENARIO_REPETITION_GUARD_TURNS",
    3,
    minimum=2,
    maximum=8,
)


# Voz. O perfil pode ser alterado na interface; este é apenas o padrão inicial.
MARY_VOICE_ENABLED_DEFAULT: Final[bool] = _env_bool(
    "MARY_VOICE_ENABLED_DEFAULT",
    True,
)
MARY_VOICE_AUTOPLAY_DEFAULT: Final[bool] = _env_bool(
    "MARY_VOICE_AUTOPLAY_DEFAULT",
    False,
)
MARY_VOICE_DEFAULT_PROFILE: Final[str] = _env_text(
    "MARY_VOICE_DEFAULT_PROFILE",
    "Quente",
)
MARY_VOICE_DEFAULT_RATE: Final[float] = _env_float(
    "MARY_VOICE_DEFAULT_RATE",
    0.87,
    minimum=0.60,
    maximum=1.40,
)
MARY_VOICE_DEFAULT_PITCH: Final[float] = _env_float(
    "MARY_VOICE_DEFAULT_PITCH",
    0.92,
    minimum=0.50,
    maximum=1.50,
)


# Imagens.
MAX_IMAGE_SIZE_MB: Final[int] = _env_int(
    "MARY_MAX_IMAGE_SIZE_MB",
    8,
    minimum=1,
    maximum=25,
)
MAX_IMAGE_DIMENSION: Final[int] = _env_int(
    "MARY_MAX_IMAGE_DIMENSION",
    1024,
    minimum=512,
    maximum=2048,
)
IMAGE_JPEG_QUALITY: Final[int] = _env_int(
    "MARY_IMAGE_JPEG_QUALITY",
    82,
    minimum=55,
    maximum=95,
)


__all__ = [
    "CONFIG_VERSION",
    "APP_TITLE",
    "APP_CAPTION",
    "APP_VERSION",
    "PROMPT_VERSION",
    "MODEL_DEFAULT",
    "OPENROUTER_URL",
    "MARY_SPREADSHEET_ID",
    "REQUEST_TIMEOUT_SECONDS",
    "MAX_HISTORY_MESSAGES",
    "RECENT_MESSAGES_PROMPT_LIMIT",
    "MEMORY_PROMPT_LIMIT",
    "MEMORY_MAX_PER_USER",
    "MEMORY_EXPLICIT_CAPTURE_ENABLED",
    "MEMORY_CONFIRMED_ONLY",
    "SCENARIO_DEFAULT_TARGET_INTERACTIONS",
    "SCENARIO_DEFAULT_SOFT_ENDING_START",
    "SCENARIO_DEFAULT_HARD_ENDING_LIMIT",
    "SCENARIO_DEFAULT_ENDING_TURNS",
    "SCENARIO_COUNT_POLICY_ENABLED",
    "SCENARIO_REPETITION_GUARD_TURNS",
    "MARY_VOICE_ENABLED_DEFAULT",
    "MARY_VOICE_AUTOPLAY_DEFAULT",
    "MARY_VOICE_DEFAULT_PROFILE",
    "MARY_VOICE_DEFAULT_RATE",
    "MARY_VOICE_DEFAULT_PITCH",
    "MAX_IMAGE_SIZE_MB",
    "MAX_IMAGE_DIMENSION",
    "IMAGE_JPEG_QUALITY",
]
