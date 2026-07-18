from prompts.base import obter_prompt_base
from prompts.emotional import (
    EMOTIONAL_STAGE_ACQUAINTANCE,
    EMOTIONAL_STAGE_CONNECTION,
    EMOTIONAL_STAGE_DEEP_BOND,
    EMOTIONAL_STAGE_FIRST_CONTACT,
    EMOTIONAL_STAGE_INTIMACY,
    EMOTIONAL_STAGE_ORDER,
    limitar_transicao_emocional,
    normalizar_estagio_emocional,
    obter_prompt_emocional,
)
from prompts.sexual import (
    SEXUAL_LEVEL_ATTRACTION,
    SEXUAL_LEVEL_DEEP_INTIMACY,
    SEXUAL_LEVEL_DESIRE,
    SEXUAL_LEVEL_FLIRT,
    SEXUAL_LEVEL_INTIMACY,
    SEXUAL_LEVEL_NONE,
    montar_contexto_estado_sexual,
    normalizar_fase_sexual,
    normalizar_nivel_sexual,
    obter_prompt_sexual,
)
from prompts.voice import (
    contar_cliches_ia,
    encontrar_cliches_ia,
    obter_prompt_voz,
)


__all__ = [
    "obter_prompt_base",
    "obter_prompt_voz",
    "contar_cliches_ia",
    "encontrar_cliches_ia",
    "EMOTIONAL_STAGE_FIRST_CONTACT",
    "EMOTIONAL_STAGE_ACQUAINTANCE",
    "EMOTIONAL_STAGE_CONNECTION",
    "EMOTIONAL_STAGE_INTIMACY",
    "EMOTIONAL_STAGE_DEEP_BOND",
    "EMOTIONAL_STAGE_ORDER",
    "normalizar_estagio_emocional",
    "limitar_transicao_emocional",
    "obter_prompt_emocional",
    "SEXUAL_LEVEL_NONE",
    "SEXUAL_LEVEL_ATTRACTION",
    "SEXUAL_LEVEL_FLIRT",
    "SEXUAL_LEVEL_DESIRE",
    "SEXUAL_LEVEL_INTIMACY",
    "SEXUAL_LEVEL_DEEP_INTIMACY",
    "normalizar_nivel_sexual",
    "normalizar_fase_sexual",
    "montar_contexto_estado_sexual",
    "obter_prompt_sexual",
]
