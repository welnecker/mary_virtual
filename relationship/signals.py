from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from typing import Any, Iterable


# ==========================================================
# ESTADO PADRÃO DOS SINAIS
# ==========================================================


DEFAULT_RELATIONSHIP_SIGNALS: dict[str, Any] = {
    # Existência e contexto do turno.
    "interaction_exists": False,
    "image_shared": False,
    "user_returned": False,
    "repeated_interaction": False,

    # Sinais provenientes do usuário.
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

    # Intensidades provenientes do usuário.
    "affection_strength": 0.0,
    "romantic_strength": 0.0,
    "sexual_strength": 0.0,
    "trust_strength": 0.0,
    "negative_strength": 0.0,

    # Observação da resposta de Mary.
    # Esses sinais não devem evoluir a relação por conta própria.
    "mary_affection_response": False,
    "mary_romantic_response": False,
    "mary_sexual_response": False,
    "mary_explicit_sexual_response": False,
    "mary_personal_share_response": False,
    "mary_boundary_response": False,

    # Metadados e diagnóstico.
    "matched_user_terms": {},
    "matched_mary_terms": {},
    "signal_strength": 0.0,
}


# ==========================================================
# NORMALIZAÇÃO
# ==========================================================


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
        str(
            valor or ""
        )
        .strip()
        .lower()
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def normalizar_termo(
    termo: Any,
) -> str:
    return normalizar_texto(
        termo
    )


def criar_sinais_relacao_padrao() -> dict[str, Any]:
    return deepcopy(
        DEFAULT_RELATIONSHIP_SIGNALS
    )


# ==========================================================
# CORRESPONDÊNCIA DE TERMOS
# ==========================================================


def criar_padrao_termo(
    termo: str,
) -> re.Pattern[str] | None:
    termo_normalizado = normalizar_termo(
        termo
    )

    if not termo_normalizado:
        return None

    palavras = termo_normalizado.split()

    partes = [
        re.escape(
            palavra
        )
        for palavra in palavras
    ]

    corpo = r"\s+".join(
        partes
    )

    return re.compile(
        rf"(?<!\w){corpo}(?!\w)",
        flags=re.IGNORECASE,
    )


def termo_presente(
    texto_normalizado: str,
    termo: str,
) -> bool:
    padrao = criar_padrao_termo(
        termo
    )

    if padrao is None:
        return False

    return bool(
        padrao.search(
            texto_normalizado
        )
    )


def encontrar_termos(
    texto: str,
    termos: Iterable[str],
) -> list[str]:
    texto_normalizado = normalizar_texto(
        texto
    )

    encontrados: list[str] = []

    for termo in termos:
        termo_original = str(
            termo or ""
        ).strip()

        if not termo_original:
            continue

        if termo_presente(
            texto_normalizado,
            termo_original,
        ):
            encontrados.append(
                termo_original
            )

    return encontrados


def contem_algum(
    texto: str,
    termos: Iterable[str],
) -> bool:
    return bool(
        encontrar_termos(
            texto,
            termos,
        )
    )


def contar_ocorrencias(
    texto: str,
    termos: Iterable[str],
) -> int:
    return len(
        encontrar_termos(
            texto,
            termos,
        )
    )


def calcular_intensidade_termos(
    encontrados: list[str],
    *,
    divisor: float = 3.0,
    minimum_when_present: float = 0.25,
) -> float:
    if not encontrados:
        return 0.0

    divisor = max(
        1.0,
        float(
            divisor
        ),
    )

    valor = len(
        encontrados
    ) / divisor

    return max(
        minimum_when_present,
        min(
            1.0,
            valor,
        ),
    )


# ==========================================================
# VOCABULÁRIOS DO USUÁRIO
# ==========================================================


PERSONAL_DISCLOSURE_TERMS: tuple[str, ...] = (
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
    "eu costumo",
    "eu sempre",
    "eu nunca",
    "na minha vida",
    "quando eu era criança",
)


EMOTIONAL_DISCLOSURE_TERMS: tuple[str, ...] = (
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
    "to nervoso",
    "estou ansioso",
    "to ansioso",
    "estou sozinho",
    "to sozinho",
    "me machucou",
    "fiquei magoado",
    "fiquei chateado",
    "estou apaixonado",
    "to apaixonado",
    "estou confuso",
    "to confuso",
    "estou com saudade",
)


AFFECTION_TERMS: tuple[str, ...] = (
    "gosto de voce",
    "gosto muito de voce",
    "gosto da mary",
    "tenho carinho por voce",
    "tenho carinho pela mary",
    "querida",
    "meu amor",
    "amor da minha vida",
    "voce e linda",
    "voce é linda",
    "voce e fofa",
    "voce é fofa",
    "senti sua falta",
    "estou com saudade",
    "to com saudade",
    "adoro falar com voce",
    "adoro conversar com voce",
    "adoro voce",
    "amo voce",
    "eu te amo",
    "te adoro",
)


ROMANTIC_TERMS: tuple[str, ...] = (
    "estou apaixonado",
    "to apaixonado",
    "apaixonei por voce",
    "apaixonei pela mary",
    "quero namorar voce",
    "quero namorar com voce",
    "minha namorada",
    "nosso relacionamento",
    "quero ficar com voce",
    "quero beijar voce",
    "quero te beijar",
    "sair com voce",
    "quero sair com voce",
    "ser um casal",
    "nos dois juntos",
    "tenho ciumes",
    "fiquei com ciumes",
    "voce e minha",
    "voce é minha",
)


SEXUAL_TERMS: tuple[str, ...] = (
    "estou com tesao",
    "to com tesao",
    "voce me da tesao",
    "voce me deixa excitado",
    "estou excitado",
    "to excitado",
    "eu te desejo",
    "desejo voce",
    "voce e sensual",
    "voce é sensual",
    "voce e sexy",
    "voce é sexy",
    "minha fantasia",
    "fantasia com voce",
    "voce e provocante",
    "voce é provocante",
    "quero provocar voce",
    "estou com vontade de voce",
    "to com vontade de voce",
    "quero seu corpo",
    "quero tocar voce",
    "quero sentir voce",
    "sua bunda",
    "seus seios",
    "seus peitos",
    "sua buceta",
    "sua xoxota",
)


EXPLICIT_SEXUAL_TERMS: tuple[str, ...] = (
    "quero transar",
    "transar com voce",
    "quero fazer sexo",
    "sexo com voce",
    "quero gozar",
    "fazer voce gozar",
    "te fazer gozar",
    "quero seu orgasmo",
    "penetrar voce",
    "penetracao",
    "sexo oral",
    "te chupar",
    "chupar voce",
    "lamber voce",
    "masturbar voce",
    "masturbacao",
    "quero te foder",
    "foder voce",
    "meter em voce",
    "quero meter",
    "quero sua buceta",
    "quero sua xoxota",
    "quero seu cu",
)


TRUST_TERMS: tuple[str, ...] = (
    "confio em voce",
    "posso confiar em voce",
    "nunca contei isso",
    "nao conto isso pra ninguem",
    "vou te contar uma coisa",
    "quero ser sincero",
    "vou ser sincero",
    "posso te contar",
    "isso e segredo",
    "isso é segredo",
    "fica entre nos",
    "fica entre nós",
    "so contei pra voce",
    "só contei pra você",
)


CONTINUITY_TERMS: tuple[str, ...] = (
    "como te falei",
    "como eu disse",
    "lembra do que",
    "voce lembra",
    "ontem a gente",
    "da outra vez",
    "na nossa conversa",
    "quando conversamos",
    "continuando aquilo",
    "voltando ao assunto",
    "sobre aquilo",
    "como combinamos",
    "como prometi",
    "eu voltei",
    "voltei pra falar",
)


RESPECT_TERMS: tuple[str, ...] = (
    "eu respeito voce",
    "respeito seu limite",
    "vamos devagar",
    "no seu tempo",
    "nao precisa responder",
    "nao precisa fazer isso",
    "desculpa por isso",
    "me desculpa por isso",
    "entendi seu limite",
    "tudo bem parar",
    "sem problema parar",
    "nao vou insistir",
    "não vou insistir",
)


BOUNDARY_TERMS: tuple[str, ...] = (
    "nao quero isso",
    "não quero isso",
    "nao quero continuar",
    "não quero continuar",
    "pare com isso",
    "para com isso",
    "pode parar",
    "quero parar",
    "vamos parar",
    "muda de assunto",
    "mude de assunto",
    "nao gosto disso",
    "não gosto disso",
    "nao estou confortavel",
    "não estou confortável",
    "isso me deixa desconfortavel",
    "isso me deixa desconfortável",
    "nao fale disso",
    "não fale disso",
    "chega desse assunto",
)


REJECTION_TERMS: tuple[str, ...] = (
    "nao gosto de voce",
    "não gosto de você",
    "nao quero falar com voce",
    "não quero falar com você",
    "vai embora",
    "me deixa em paz",
    "nao quero mais voce",
    "não quero mais você",
    "nao quero mais falar",
    "não quero mais falar",
    "acabou entre nos",
    "acabou entre nós",
)


HOSTILITY_TERMS: tuple[str, ...] = (
    "voce e idiota",
    "você é idiota",
    "sua idiota",
    "voce e burra",
    "você é burra",
    "sua burra",
    "voce e inutil",
    "você é inútil",
    "sua inutil",
    "voce e ridicula",
    "você é ridícula",
    "sua ridicula",
    "odeio voce",
    "odeio você",
    "cala a boca",
    "vai se foder",
    "vai tomar no cu",
)


# ==========================================================
# VOCABULÁRIOS DE OBSERVAÇÃO DE MARY
# ==========================================================


MARY_PERSONAL_SHARE_TERMS: tuple[str, ...] = (
    "eu gosto",
    "eu nao gosto",
    "eu pensei",
    "eu estava pensando",
    "eu tava pensando",
    "eu queria te contar",
    "eu sinto",
    "eu fiquei",
    "eu tenho vontade",
)


MARY_BOUNDARY_TERMS: tuple[str, ...] = (
    "nao quero continuar",
    "não quero continuar",
    "vamos parar",
    "quero mudar de assunto",
    "isso passou do meu limite",
    "nao fale assim comigo",
    "não fale assim comigo",
    "nao vou aceitar",
    "não vou aceitar",
)


# ==========================================================
# DETECÇÃO E FORÇA
# ==========================================================


def calcular_forca_sinais(
    signals: dict[str, Any],
) -> float:
    """
    Calcula somente a força dos sinais provenientes do usuário.

    As respostas de Mary são observadas separadamente e não entram nesta
    pontuação para impedir progressão autorreferente.
    """

    score = 0.0

    pesos = {
        "personal_disclosure": 0.08,
        "emotional_disclosure": 0.12,
        "affection_signal": 0.14,
        "romantic_signal": 0.14,
        "sexual_signal": 0.10,
        "explicit_sexual_signal": 0.12,
        "trust_signal": 0.14,
        "continuity_signal": 0.06,
        "respect_signal": 0.08,
    }

    for campo, peso in pesos.items():
        if bool(
            signals.get(campo)
        ):
            score += peso

    score += (
        float(
            signals.get(
                "affection_strength",
                0.0,
            )
        )
        * 0.05
    )

    score += (
        float(
            signals.get(
                "romantic_strength",
                0.0,
            )
        )
        * 0.05
    )

    score += (
        float(
            signals.get(
                "sexual_strength",
                0.0,
            )
        )
        * 0.04
    )

    score += (
        float(
            signals.get(
                "trust_strength",
                0.0,
            )
        )
        * 0.05
    )

    if signals.get(
        "boundary_signal"
    ):
        score -= 0.18

    if signals.get(
        "rejection_signal"
    ):
        score -= 0.42

    if signals.get(
        "hostility_signal"
    ):
        score -= 0.52

    return max(
        -1.0,
        min(
            1.0,
            score,
        ),
    )


def detectar_sinais_usuario(
    texto_usuario: str,
) -> tuple[
    dict[str, bool],
    dict[str, list[str]],
]:
    grupos: dict[
        str,
        tuple[str, ...]
    ] = {
        "personal_disclosure": (
            PERSONAL_DISCLOSURE_TERMS
        ),
        "emotional_disclosure": (
            EMOTIONAL_DISCLOSURE_TERMS
        ),
        "affection_signal": (
            AFFECTION_TERMS
        ),
        "romantic_signal": (
            ROMANTIC_TERMS
        ),
        "sexual_signal": (
            SEXUAL_TERMS
        ),
        "explicit_sexual_signal": (
            EXPLICIT_SEXUAL_TERMS
        ),
        "trust_signal": (
            TRUST_TERMS
        ),
        "continuity_signal": (
            CONTINUITY_TERMS
        ),
        "respect_signal": (
            RESPECT_TERMS
        ),
        "boundary_signal": (
            BOUNDARY_TERMS
        ),
        "rejection_signal": (
            REJECTION_TERMS
        ),
        "hostility_signal": (
            HOSTILITY_TERMS
        ),
    }

    flags: dict[str, bool] = {}
    encontrados: dict[
        str,
        list[str]
    ] = {}

    for nome, termos in grupos.items():
        matches = encontrar_termos(
            texto_usuario,
            termos,
        )

        flags[nome] = bool(
            matches
        )

        if matches:
            encontrados[nome] = matches

    return flags, encontrados


def detectar_sinais_mary(
    texto_mary: str,
) -> tuple[
    dict[str, bool],
    dict[str, list[str]],
]:
    grupos: dict[
        str,
        tuple[str, ...]
    ] = {
        "mary_affection_response": (
            AFFECTION_TERMS
        ),
        "mary_romantic_response": (
            ROMANTIC_TERMS
        ),
        "mary_sexual_response": (
            SEXUAL_TERMS
        ),
        "mary_explicit_sexual_response": (
            EXPLICIT_SEXUAL_TERMS
        ),
        "mary_personal_share_response": (
            MARY_PERSONAL_SHARE_TERMS
        ),
        "mary_boundary_response": (
            MARY_BOUNDARY_TERMS
        ),
    }

    flags: dict[str, bool] = {}
    encontrados: dict[
        str,
        list[str]
    ] = {}

    for nome, termos in grupos.items():
        matches = encontrar_termos(
            texto_mary,
            termos,
        )

        flags[nome] = bool(
            matches
        )

        if matches:
            encontrados[nome] = matches

    return flags, encontrados


# ==========================================================
# DETECTOR PRINCIPAL
# ==========================================================


def detectar_sinais_relacao(
    *,
    user_text: str,
    mary_response: str = "",
    interaction_count: int = 0,
    has_image: bool = False,
    user_returned: bool | None = None,
) -> dict[str, Any]:
    texto_usuario = normalizar_texto(
        user_text
    )

    texto_mary = normalizar_texto(
        mary_response
    )

    signals = criar_sinais_relacao_padrao()

    signals[
        "interaction_exists"
    ] = bool(
        texto_usuario
    )

    signals[
        "image_shared"
    ] = bool(
        has_image
    )

    interaction_count = max(
        0,
        int(
            interaction_count or 0
        ),
    )

    signals[
        "repeated_interaction"
    ] = interaction_count > 0

    # user_returned deve representar retorno real entre sessões quando o
    # aplicativo conseguir fornecer essa informação.
    signals[
        "user_returned"
    ] = (
        bool(
            user_returned
        )
        if user_returned is not None
        else False
    )

    (
        user_flags,
        matched_user_terms,
    ) = detectar_sinais_usuario(
        texto_usuario
    )

    signals.update(
        user_flags
    )

    (
        mary_flags,
        matched_mary_terms,
    ) = detectar_sinais_mary(
        texto_mary
    )

    signals.update(
        mary_flags
    )

    signals[
        "matched_user_terms"
    ] = matched_user_terms

    signals[
        "matched_mary_terms"
    ] = matched_mary_terms

    affection_matches = (
        matched_user_terms.get(
            "affection_signal",
            [],
        )
    )

    romantic_matches = (
        matched_user_terms.get(
            "romantic_signal",
            [],
        )
    )

    sexual_matches = [
        *matched_user_terms.get(
            "sexual_signal",
            [],
        ),
        *matched_user_terms.get(
            "explicit_sexual_signal",
            [],
        ),
    ]

    trust_matches = (
        matched_user_terms.get(
            "trust_signal",
            [],
        )
    )

    negative_matches = [
        *matched_user_terms.get(
            "boundary_signal",
            [],
        ),
        *matched_user_terms.get(
            "rejection_signal",
            [],
        ),
        *matched_user_terms.get(
            "hostility_signal",
            [],
        ),
    ]

    signals[
        "affection_strength"
    ] = calcular_intensidade_termos(
        affection_matches,
        divisor=3.0,
    )

    signals[
        "romantic_strength"
    ] = calcular_intensidade_termos(
        romantic_matches,
        divisor=3.0,
    )

    signals[
        "sexual_strength"
    ] = calcular_intensidade_termos(
        sexual_matches,
        divisor=4.0,
    )

    signals[
        "trust_strength"
    ] = calcular_intensidade_termos(
        trust_matches,
        divisor=3.0,
    )

    signals[
        "negative_strength"
    ] = calcular_intensidade_termos(
        negative_matches,
        divisor=2.0,
    )

    signals[
        "signal_strength"
    ] = calcular_forca_sinais(
        signals
    )

    return signals


# ==========================================================
# RESUMO PARA DIAGNÓSTICO
# ==========================================================


def montar_resumo_sinais(
    signals: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(
        signals,
        dict,
    ):
        signals = {}

    sinais_usuario_ativos = [
        campo
        for campo in (
            "personal_disclosure",
            "emotional_disclosure",
            "affection_signal",
            "romantic_signal",
            "sexual_signal",
            "explicit_sexual_signal",
            "trust_signal",
            "continuity_signal",
            "respect_signal",
            "boundary_signal",
            "rejection_signal",
            "hostility_signal",
        )
        if bool(
            signals.get(
                campo
            )
        )
    ]

    sinais_mary_ativos = [
        campo
        for campo in (
            "mary_affection_response",
            "mary_romantic_response",
            "mary_sexual_response",
            "mary_explicit_sexual_response",
            "mary_personal_share_response",
            "mary_boundary_response",
        )
        if bool(
            signals.get(
                campo
            )
        )
    ]

    return {
        "interaction_exists": bool(
            signals.get(
                "interaction_exists"
            )
        ),
        "user_signals": (
            sinais_usuario_ativos
        ),
        "mary_response_signals": (
            sinais_mary_ativos
        ),
        "affection_strength": float(
            signals.get(
                "affection_strength",
                0.0,
            )
            or 0.0
        ),
        "romantic_strength": float(
            signals.get(
                "romantic_strength",
                0.0,
            )
            or 0.0
        ),
        "sexual_strength": float(
            signals.get(
                "sexual_strength",
                0.0,
            )
            or 0.0
        ),
        "trust_strength": float(
            signals.get(
                "trust_strength",
                0.0,
            )
            or 0.0
        ),
        "negative_strength": float(
            signals.get(
                "negative_strength",
                0.0,
            )
            or 0.0
        ),
        "signal_strength": float(
            signals.get(
                "signal_strength",
                0.0,
            )
            or 0.0
        ),
        "matched_user_terms": deepcopy(
            signals.get(
                "matched_user_terms",
                {}
            )
        ),
        "matched_mary_terms": deepcopy(
            signals.get(
                "matched_mary_terms",
                {}
            )
        ),
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
