from __future__ import annotations

import re
import unicodedata
from typing import Any


DEFAULT_RELATIONSHIP_SIGNALS: dict[str, Any] = {
    "interaction_exists": False,
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
    "user_returned": False,
    "image_shared": False,
    "signal_strength": 0.0,
}


def remover_acentos(
    texto: str,
) -> str:
    normalizado = unicodedata.normalize(
        "NFKD",
        str(texto or ""),
    )

    return "".join(
        caractere
        for caractere in normalizado
        if not unicodedata.combining(
            caractere
        )
    )


def normalizar_texto(
    valor: Any,
) -> str:
    texto = remover_acentos(
        str(valor or "").strip().lower()
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def contem_algum(
    texto: str,
    termos: tuple[str, ...] | list[str],
) -> bool:
    texto_normalizado = normalizar_texto(
        texto
    )

    return any(
        normalizar_texto(termo)
        in texto_normalizado
        for termo in termos
        if str(termo or "").strip()
    )


def contar_ocorrencias(
    texto: str,
    termos: tuple[str, ...] | list[str],
) -> int:
    texto_normalizado = normalizar_texto(
        texto
    )

    return sum(
        1
        for termo in termos
        if (
            str(termo or "").strip()
            and normalizar_texto(termo)
            in texto_normalizado
        )
    )


PERSONAL_DISCLOSURE_TERMS = (
    "eu trabalho",
    "eu estudo",
    "minha familia",
    "meu pai",
    "minha mae",
    "meu filho",
    "minha filha",
    "meu passado",
    "quando eu era",
    "aconteceu comigo",
    "eu moro",
    "minha cidade",
    "meu nome",
    "eu tenho",
    "eu gosto de",
    "eu nao gosto de",
)


EMOTIONAL_DISCLOSURE_TERMS = (
    "estou triste",
    "to triste",
    "estou feliz",
    "to feliz",
    "estou cansado",
    "to cansado",
    "estou preocupado",
    "to preocupado",
    "estou com medo",
    "tenho medo",
    "me sinto",
    "sinto falta",
    "estou nervoso",
    "estou ansioso",
    "estou sozinho",
    "me machucou",
    "fiquei magoado",
)


AFFECTION_TERMS = (
    "gosto de voce",
    "gosto muito de voce",
    "gosto da mary",
    "carinho",
    "querida",
    "meu amor",
    "amor",
    "linda",
    "fofa",
    "senti sua falta",
    "saudade",
    "adoro falar com voce",
    "adoro conversar com voce",
)


ROMANTIC_TERMS = (
    "apaixonado",
    "apaixonei",
    "namorar",
    "namorada",
    "relacionamento",
    "ficar com voce",
    "beijar voce",
    "te beijar",
    "encontro",
    "sair com voce",
    "casal",
    "ciumes",
    "ciúmes",
)


SEXUAL_TERMS = (
    "tesao",
    "tesão",
    "desejo",
    "excitada",
    "excitado",
    "sensual",
    "sexy",
    "fantasia",
    "provocante",
    "provocacao",
    "provocação",
    "vontade de voce",
)


EXPLICIT_SEXUAL_TERMS = (
    "sexo",
    "transar",
    "gozar",
    "orgasmo",
    "penetracao",
    "penetração",
    "sexo oral",
    "masturbacao",
    "masturbação",
)


TRUST_TERMS = (
    "confio em voce",
    "posso confiar",
    "nunca contei isso",
    "nao conto isso pra ninguem",
    "vou te contar uma coisa",
    "quero ser sincero",
    "vou ser sincero",
    "posso te contar",
    "segredo",
)


CONTINUITY_TERMS = (
    "como te falei",
    "como eu disse",
    "lembra",
    "voce lembra",
    "ontem",
    "da outra vez",
    "na nossa conversa",
    "quando conversamos",
    "de novo",
    "voltei",
)


RESPECT_TERMS = (
    "tudo bem",
    "sem problema",
    "respeito",
    "vamos devagar",
    "no seu tempo",
    "nao precisa",
    "não precisa",
    "desculpa",
    "me desculpa",
    "entendi",
)


BOUNDARY_TERMS = (
    "nao quero",
    "não quero",
    "para",
    "pare",
    "vamos parar",
    "muda de assunto",
    "nao gosto disso",
    "não gosto disso",
    "nao estou confortavel",
    "não estou confortável",
)


REJECTION_TERMS = (
    "nao gosto de voce",
    "não gosto de você",
    "nao quero falar com voce",
    "não quero falar com você",
    "vai embora",
    "me deixa",
    "nao quero mais",
    "não quero mais",
)


HOSTILITY_TERMS = (
    "idiota",
    "burra",
    "inutil",
    "inútil",
    "ridicula",
    "ridícula",
    "odeio voce",
    "odeio você",
    "cala a boca",
)


def calcular_forca_sinais(
    signals: dict[str, Any],
) -> float:
    score = 0.0

    pesos = {
        "personal_disclosure": 0.10,
        "emotional_disclosure": 0.15,
        "affection_signal": 0.15,
        "romantic_signal": 0.15,
        "sexual_signal": 0.10,
        "explicit_sexual_signal": 0.15,
        "trust_signal": 0.15,
        "continuity_signal": 0.05,
        "respect_signal": 0.05,
    }

    for campo, peso in pesos.items():
        if bool(
            signals.get(campo)
        ):
            score += peso

    if signals.get(
        "boundary_signal"
    ):
        score -= 0.10

    if signals.get(
        "rejection_signal"
    ):
        score -= 0.30

    if signals.get(
        "hostility_signal"
    ):
        score -= 0.35

    return max(
        -1.0,
        min(
            1.0,
            score,
        ),
    )


def detectar_sinais_relacao(
    *,
    user_text: str,
    mary_response: str = "",
    interaction_count: int = 0,
    has_image: bool = False,
) -> dict[str, Any]:
    texto_usuario = normalizar_texto(
        user_text
    )

    texto_mary = normalizar_texto(
        mary_response
    )

    contexto = "\n".join(
        (
            texto_usuario,
            texto_mary,
        )
    )

    signals = dict(
        DEFAULT_RELATIONSHIP_SIGNALS
    )

    signals[
        "interaction_exists"
    ] = bool(
        texto_usuario
    )

    signals[
        "personal_disclosure"
    ] = contem_algum(
        texto_usuario,
        PERSONAL_DISCLOSURE_TERMS,
    )

    signals[
        "emotional_disclosure"
    ] = contem_algum(
        texto_usuario,
        EMOTIONAL_DISCLOSURE_TERMS,
    )

    signals[
        "affection_signal"
    ] = contem_algum(
        contexto,
        AFFECTION_TERMS,
    )

    signals[
        "romantic_signal"
    ] = contem_algum(
        contexto,
        ROMANTIC_TERMS,
    )

    signals[
        "sexual_signal"
    ] = contem_algum(
        contexto,
        SEXUAL_TERMS,
    )

    signals[
        "explicit_sexual_signal"
    ] = contem_algum(
        contexto,
        EXPLICIT_SEXUAL_TERMS,
    )

    signals[
        "trust_signal"
    ] = contem_algum(
        texto_usuario,
        TRUST_TERMS,
    )

    signals[
        "continuity_signal"
    ] = (
        contem_algum(
            texto_usuario,
            CONTINUITY_TERMS,
        )
        or interaction_count > 1
    )

    signals[
        "respect_signal"
    ] = contem_algum(
        texto_usuario,
        RESPECT_TERMS,
    )

    signals[
        "boundary_signal"
    ] = contem_algum(
        texto_usuario,
        BOUNDARY_TERMS,
    )

    signals[
        "rejection_signal"
    ] = contem_algum(
        texto_usuario,
        REJECTION_TERMS,
    )

    signals[
        "hostility_signal"
    ] = contem_algum(
        texto_usuario,
        HOSTILITY_TERMS,
    )

    signals[
        "user_returned"
    ] = interaction_count > 0

    signals[
        "image_shared"
    ] = bool(
        has_image
    )

    signals[
        "signal_strength"
    ] = calcular_forca_sinais(
        signals
    )

    return signals
