from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from typing import Any, Iterable


DEFAULT_RELATIONSHIP_SIGNALS: dict[str, Any] = {
    "interaction_exists": False,
    "image_shared": False,
    "user_returned": False,
    "repeated_interaction": False,
    "personal_disclosure": False,
    "emotional_disclosure": False,
    "affection_signal": False,
    "romantic_signal": False,
    "sexual_signal": False,
    "explicit_sexual_signal": False,
    "trust_signal": False,
    "continuity_signal": False,
    "respect_signal": False,
    "boundary_signal": False,
    "rejection_signal": False,
    "hostility_signal": False,
    "hesitation_signal": False,
    "playful_signal": False,
    "analytical_signal": False,
    "user_orgasm_warning": False,
    "user_orgasm_done": False,
    "affection_strength": 0.0,
    "romantic_strength": 0.0,
    "sexual_strength": 0.0,
    "trust_strength": 0.0,
    "negative_strength": 0.0,
    "mary_affection_response": False,
    "mary_romantic_response": False,
    "mary_sexual_response": False,
    "mary_explicit_sexual_response": False,
    "mary_personal_share_response": False,
    "mary_boundary_response": False,
    "mary_orgasm_warning": False,
    "mary_orgasm_done": False,
    "matched_user_terms": {},
    "matched_mary_terms": {},
    "signal_strength": 0.0,
}


def remover_acentos(texto: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def normalizar_texto(valor: Any) -> str:
    text = remover_acentos(str(valor or "").strip().lower())
    return re.sub(r"\s+", " ", text).strip()


def normalizar_termo(termo: Any) -> str:
    return normalizar_texto(termo)


def criar_sinais_relacao_padrao() -> dict[str, Any]:
    return deepcopy(DEFAULT_RELATIONSHIP_SIGNALS)


def criar_padrao_termo(termo: str) -> re.Pattern[str] | None:
    normalized = normalizar_termo(termo)
    if not normalized:
        return None
    body = r"\s+".join(re.escape(word) for word in normalized.split())
    return re.compile(rf"(?<!\w){body}(?!\w)", flags=re.IGNORECASE)


def termo_presente(texto_normalizado: str, termo: str) -> bool:
    pattern = criar_padrao_termo(termo)
    return bool(pattern and pattern.search(normalizar_texto(texto_normalizado)))


def encontrar_termos(texto: str, termos: Iterable[str]) -> list[str]:
    normalized = normalizar_texto(texto)
    matches: list[str] = []
    for term in termos:
        original = str(term or "").strip()
        if original and termo_presente(normalized, original):
            matches.append(original)
    return matches


def contem_algum(texto: str, termos: Iterable[str]) -> bool:
    return bool(encontrar_termos(texto, termos))


def contar_ocorrencias(texto: str, termos: Iterable[str]) -> int:
    return len(encontrar_termos(texto, termos))


def calcular_intensidade_termos(
    encontrados: list[str],
    *,
    divisor: float = 3.0,
    minimum_when_present: float = 0.25,
) -> float:
    if not encontrados:
        return 0.0
    return max(
        minimum_when_present,
        min(1.0, len(encontrados) / max(1.0, float(divisor))),
    )


PERSONAL_DISCLOSURE_TERMS = (
    "meu nome", "eu trabalho", "eu estudo", "eu moro", "minha familia",
    "meu pai", "minha mae", "meu filho", "minha filha", "meu passado",
    "aconteceu comigo", "quando eu era", "eu gosto de", "eu nao gosto de",
    "na minha vida",
)

EMOTIONAL_DISCLOSURE_TERMS = (
    "estou triste", "to triste", "estou feliz", "to feliz", "estou cansado",
    "to cansado", "estou preocupado", "estou com medo", "tenho medo",
    "me sinto", "sinto falta", "estou nervoso", "estou ansioso",
    "estou sozinho", "fiquei magoado", "fiquei chateado", "estou confuso",
    "estou com saudade",
)

AFFECTION_TERMS = (
    "gosto de voce", "adoro voce", "amo voce", "eu te amo", "te adoro",
    "meu amor", "querida", "voce e linda", "voce e fofa",
    "senti sua falta", "estou com saudade", "tenho carinho por voce",
)

ROMANTIC_TERMS = (
    "estou apaixonado", "to apaixonado", "apaixonei por voce",
    "quero namorar", "quero ficar com voce", "quero te beijar",
    "quero beijar voce", "quero sair com voce", "ser um casal",
    "tenho ciumes", "fiquei com ciumes",
)

SEXUAL_TERMS = (
    "tesao", "excitado", "excitada", "sensual", "sexy", "provocante",
    "desejo voce", "eu te desejo", "quero seu corpo", "quero tocar voce",
    "quero sentir voce", "molhada", "duro", "bunda", "peito", "peitos",
    "buceta", "xoxota", "pau", "cu", "gemer", "rebolar",
)

EXPLICIT_SEXUAL_TERMS = (
    "quero transar", "fazer sexo", "transar com voce", "quero te foder",
    "foder voce", "quero meter", "meter em voce", "penetrar voce",
    "penetracao", "sexo oral", "te chupar", "chupar voce", "lamber voce",
    "masturbar voce", "quero gozar", "fazer voce gozar", "te fazer gozar",
    "quero sua buceta", "quero sua xoxota", "quero seu cu",
)

USER_ORGASM_WARNING_TERMS = (
    "vou gozar", "eu vou gozar", "to quase", "tô quase", "quase gozando",
)

USER_ORGASM_DONE_TERMS = (
    "to gozando", "tô gozando", "estou gozando", "gozei", "eu gozei",
    "cheguei la", "cheguei lá", "meu orgasmo veio",
)

TRUST_TERMS = (
    "confio em voce", "posso confiar em voce", "nunca contei isso",
    "vou te contar uma coisa", "quero ser sincero", "posso te contar",
    "isso e segredo", "fica entre nos", "so contei pra voce",
)

CONTINUITY_TERMS = (
    "como te falei", "como eu disse", "lembra do que", "voce lembra",
    "da outra vez", "na nossa conversa", "continuando aquilo",
    "voltando ao assunto", "como combinamos", "eu voltei",
)

RESPECT_TERMS = (
    "eu respeito voce", "respeito seu limite", "vamos devagar",
    "no seu tempo", "nao precisa fazer isso", "desculpa por isso",
    "entendi seu limite", "tudo bem parar", "nao vou insistir",
)

BOUNDARY_TERMS = (
    "para", "pare", "pode parar", "quero parar", "vamos parar",
    "nao quero isso", "nao quero continuar", "nao gosto disso",
    "nao estou confortavel", "isso me deixa desconfortavel",
    "muda de assunto", "mude de assunto", "nao fale disso", "chega",
)

REJECTION_TERMS = (
    "nao gosto de voce", "nao quero falar com voce", "me deixa em paz",
    "nao quero mais voce", "nao quero mais falar", "acabou entre nos",
    "vai embora",
)

HOSTILITY_TERMS = (
    "voce e idiota", "sua idiota", "voce e burra", "sua burra",
    "voce e inutil", "sua inutil", "voce e ridicula", "sua ridicula",
    "odeio voce", "cala a boca",
)

HESITATION_TERMS = (
    "calma", "devagar", "espera", "nao sei", "talvez", "estou em duvida",
    "preciso pensar", "um pouco mais devagar", "ainda nao",
)

PLAYFUL_TERMS = (
    "haha", "kkk", "rsrs", "brincadeira", "to brincando", "duvido",
    "quero ver", "e mesmo", "provoca", "atrevida", "safada",
)

ANALYTICAL_TERMS = (
    "como funciona", "por que", "qual a logica", "explique", "me explica",
    "o que isso significa", "vamos analisar", "tecnicamente",
)

MARY_PERSONAL_SHARE_TERMS = (
    "eu gosto", "eu nao gosto", "eu penso", "eu sinto", "eu fiquei",
    "eu quero", "eu tenho vontade", "eu decidi",
)

MARY_BOUNDARY_TERMS = (
    "nao quero continuar", "vamos parar", "quero mudar de assunto",
    "isso passou do meu limite", "nao fale assim comigo", "nao vou aceitar",
)

MARY_ORGASM_WARNING_TERMS = USER_ORGASM_WARNING_TERMS
MARY_ORGASM_DONE_TERMS = USER_ORGASM_DONE_TERMS + (
    "me fez gozar", "eu gozo", "gozando agora",
)


def _detectar_grupos(
    text: str,
    groups: dict[str, tuple[str, ...]],
) -> tuple[dict[str, bool], dict[str, list[str]]]:
    flags: dict[str, bool] = {}
    matched: dict[str, list[str]] = {}
    for name, terms in groups.items():
        found = encontrar_termos(text, terms)
        flags[name] = bool(found)
        if found:
            matched[name] = found
    return flags, matched


def detectar_sinais_usuario(
    texto_usuario: str,
) -> tuple[dict[str, bool], dict[str, list[str]]]:
    groups = {
        "personal_disclosure": PERSONAL_DISCLOSURE_TERMS,
        "emotional_disclosure": EMOTIONAL_DISCLOSURE_TERMS,
        "affection_signal": AFFECTION_TERMS,
        "romantic_signal": ROMANTIC_TERMS,
        "sexual_signal": SEXUAL_TERMS,
        "explicit_sexual_signal": EXPLICIT_SEXUAL_TERMS,
        "trust_signal": TRUST_TERMS,
        "continuity_signal": CONTINUITY_TERMS,
        "respect_signal": RESPECT_TERMS,
        "boundary_signal": BOUNDARY_TERMS,
        "rejection_signal": REJECTION_TERMS,
        "hostility_signal": HOSTILITY_TERMS,
        "hesitation_signal": HESITATION_TERMS,
        "playful_signal": PLAYFUL_TERMS,
        "analytical_signal": ANALYTICAL_TERMS,
        "user_orgasm_warning": USER_ORGASM_WARNING_TERMS,
        "user_orgasm_done": USER_ORGASM_DONE_TERMS,
    }
    flags, matched = _detectar_grupos(texto_usuario, groups)

    # Prioridade semântica: hesitação não é recusa, limite não é rejeição pessoal.
    if flags.get("hostility_signal"):
        flags["rejection_signal"] = True
    if flags.get("rejection_signal"):
        flags["boundary_signal"] = True
    if flags.get("boundary_signal"):
        flags["hesitation_signal"] = False

    # "Vou gozar" é pré-orgasmo, nunca conclusão.
    if flags.get("user_orgasm_done"):
        flags["user_orgasm_warning"] = False
    if flags.get("user_orgasm_warning") or flags.get("user_orgasm_done"):
        flags["sexual_signal"] = True
        flags["explicit_sexual_signal"] = True

    return flags, matched


def detectar_sinais_mary(
    texto_mary: str,
) -> tuple[dict[str, bool], dict[str, list[str]]]:
    groups = {
        "mary_affection_response": AFFECTION_TERMS,
        "mary_romantic_response": ROMANTIC_TERMS,
        "mary_sexual_response": SEXUAL_TERMS,
        "mary_explicit_sexual_response": EXPLICIT_SEXUAL_TERMS,
        "mary_personal_share_response": MARY_PERSONAL_SHARE_TERMS,
        "mary_boundary_response": MARY_BOUNDARY_TERMS,
        "mary_orgasm_warning": MARY_ORGASM_WARNING_TERMS,
        "mary_orgasm_done": MARY_ORGASM_DONE_TERMS,
    }
    flags, matched = _detectar_grupos(texto_mary, groups)
    if flags.get("mary_orgasm_done"):
        flags["mary_orgasm_warning"] = False
    if flags.get("mary_orgasm_warning") or flags.get("mary_orgasm_done"):
        flags["mary_sexual_response"] = True
        flags["mary_explicit_sexual_response"] = True
    return flags, matched


def calcular_forca_sinais(signals: dict[str, Any]) -> float:
    score = 0.0
    weights = {
        "personal_disclosure": 0.08,
        "emotional_disclosure": 0.12,
        "affection_signal": 0.14,
        "romantic_signal": 0.16,
        "sexual_signal": 0.12,
        "explicit_sexual_signal": 0.18,
        "trust_signal": 0.14,
        "continuity_signal": 0.06,
        "respect_signal": 0.08,
        "playful_signal": 0.04,
    }
    for field, weight in weights.items():
        if signals.get(field):
            score += weight
    score += float(signals.get("affection_strength", 0.0) or 0.0) * 0.05
    score += float(signals.get("romantic_strength", 0.0) or 0.0) * 0.06
    score += float(signals.get("sexual_strength", 0.0) or 0.0) * 0.08
    score += float(signals.get("trust_strength", 0.0) or 0.0) * 0.05

    if signals.get("hesitation_signal"):
        score -= 0.03
    if signals.get("boundary_signal"):
        score -= 0.12
    if signals.get("rejection_signal"):
        score -= 0.30
    if signals.get("hostility_signal"):
        score -= 0.52
    return max(-1.0, min(1.0, score))


def detectar_sinais_relacao(
    *,
    user_text: str,
    mary_response: str = "",
    interaction_count: int = 0,
    has_image: bool = False,
    user_returned: bool | None = None,
) -> dict[str, Any]:
    signals = criar_sinais_relacao_padrao()
    user_text = normalizar_texto(user_text)
    mary_response = normalizar_texto(mary_response)

    signals["interaction_exists"] = bool(user_text)
    signals["image_shared"] = bool(has_image)
    signals["repeated_interaction"] = max(0, int(interaction_count or 0)) > 0
    signals["user_returned"] = bool(user_returned) if user_returned is not None else False

    user_flags, user_matches = detectar_sinais_usuario(user_text)
    mary_flags, mary_matches = detectar_sinais_mary(mary_response)
    signals.update(user_flags)
    signals.update(mary_flags)
    signals["matched_user_terms"] = user_matches
    signals["matched_mary_terms"] = mary_matches

    affection_matches = user_matches.get("affection_signal", [])
    romantic_matches = user_matches.get("romantic_signal", [])
    sexual_matches = [
        *user_matches.get("sexual_signal", []),
        *user_matches.get("explicit_sexual_signal", []),
        *user_matches.get("user_orgasm_warning", []),
        *user_matches.get("user_orgasm_done", []),
    ]
    trust_matches = user_matches.get("trust_signal", [])
    negative_matches = [
        *user_matches.get("boundary_signal", []),
        *user_matches.get("rejection_signal", []),
        *user_matches.get("hostility_signal", []),
    ]

    signals["affection_strength"] = calcular_intensidade_termos(affection_matches)
    signals["romantic_strength"] = calcular_intensidade_termos(romantic_matches)
    signals["sexual_strength"] = calcular_intensidade_termos(
        sexual_matches,
        divisor=3.0,
        minimum_when_present=0.40,
    )
    signals["trust_strength"] = calcular_intensidade_termos(trust_matches)
    signals["negative_strength"] = calcular_intensidade_termos(
        negative_matches,
        divisor=2.0,
    )

    if signals.get("explicit_sexual_signal"):
        signals["sexual_strength"] = max(0.70, signals["sexual_strength"])
    if signals.get("user_orgasm_warning"):
        signals["sexual_strength"] = max(0.90, signals["sexual_strength"])
    if signals.get("user_orgasm_done"):
        signals["sexual_strength"] = 1.0

    signals["signal_strength"] = calcular_forca_sinais(signals)
    return signals


def montar_resumo_sinais(signals: dict[str, Any] | None) -> dict[str, Any]:
    data = signals if isinstance(signals, dict) else {}
    user_fields = (
        "personal_disclosure", "emotional_disclosure", "affection_signal",
        "romantic_signal", "sexual_signal", "explicit_sexual_signal",
        "trust_signal", "continuity_signal", "respect_signal",
        "boundary_signal", "rejection_signal", "hostility_signal",
        "hesitation_signal", "playful_signal", "analytical_signal",
        "user_orgasm_warning", "user_orgasm_done",
    )
    mary_fields = (
        "mary_affection_response", "mary_romantic_response",
        "mary_sexual_response", "mary_explicit_sexual_response",
        "mary_personal_share_response", "mary_boundary_response",
        "mary_orgasm_warning", "mary_orgasm_done",
    )
    return {
        "interaction_exists": bool(data.get("interaction_exists")),
        "user_signals": [field for field in user_fields if data.get(field)],
        "mary_response_signals": [field for field in mary_fields if data.get(field)],
        "affection_strength": float(data.get("affection_strength", 0.0) or 0.0),
        "romantic_strength": float(data.get("romantic_strength", 0.0) or 0.0),
        "sexual_strength": float(data.get("sexual_strength", 0.0) or 0.0),
        "trust_strength": float(data.get("trust_strength", 0.0) or 0.0),
        "negative_strength": float(data.get("negative_strength", 0.0) or 0.0),
        "signal_strength": float(data.get("signal_strength", 0.0) or 0.0),
        "matched_user_terms": deepcopy(data.get("matched_user_terms", {})),
        "matched_mary_terms": deepcopy(data.get("matched_mary_terms", {})),
    }


__all__ = [
    "DEFAULT_RELATIONSHIP_SIGNALS",
    "PERSONAL_DISCLOSURE_TERMS",
    "EMOTIONAL_DISCLOSURE_TERMS",
    "AFFECTION_TERMS",
    "ROMANTIC_TERMS",
    "SEXUAL_TERMS",
    "EXPLICIT_SEXUAL_TERMS",
    "TRUST_TERMS",
    "CONTINUITY_TERMS",
    "RESPECT_TERMS",
    "BOUNDARY_TERMS",
    "REJECTION_TERMS",
    "HOSTILITY_TERMS",
    "MARY_PERSONAL_SHARE_TERMS",
    "MARY_BOUNDARY_TERMS",
    "remover_acentos",
    "normalizar_texto",
    "normalizar_termo",
    "criar_sinais_relacao_padrao",
    "criar_padrao_termo",
    "termo_presente",
    "encontrar_termos",
    "contem_algum",
    "contar_ocorrencias",
    "calcular_intensidade_termos",
    "calcular_forca_sinais",
    "detectar_sinais_usuario",
    "detectar_sinais_mary",
    "detectar_sinais_relacao",
    "montar_resumo_sinais",
]
