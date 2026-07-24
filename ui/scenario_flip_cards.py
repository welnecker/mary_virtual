from __future__ import annotations

import html
from functools import wraps
from typing import Any, Callable

import streamlit as st

import ui.scenario_menu as scenario_menu


SCENARIO_FLIP_CARDS_VERSION = "scenario-flip-cards-v2-scrollable-back"

_INSTALLED = False


_BACK_CONTENT: dict[str, dict[str, Any]] = {
    "casada_frustrada": {
        "eyebrow": "Como viver esta história",
        "title": "Acompanhe o ritmo de Mary",
        "copy": (
            "Mary quer conhecer você, trocar mensagens e construir um encontro "
            "secreto cada vez mais intenso. Deixe a aproximação evoluir sem "
            "pular etapas, mesmo quando ela demonstrar desejo e iniciativa."
        ),
        "tips": (
            "Responda ao momento atual da conversa.",
            "Curiosidade, atenção e provocação funcionam melhor que pressa.",
            "Grosseria, pressão ou violência podem afastá-la e encerrar a história.",
        ),
    },
    "vizinha_porta_trancada": {
        "eyebrow": "Experiência de degustação",
        "title": "Conheça a dinâmica de Mary",
        "copy": (
            "Uma história mais curta para experimentar conversa, iniciativa e "
            "consequências. Observe as reações de Mary e participe da evolução "
            "da cena em vez de tentar decidir tudo de uma vez."
        ),
        "tips": (
            "Acesso gratuito.",
            "Suas respostas alteram o rumo da interação.",
            "A experiência pode terminar conforme as escolhas feitas.",
        ),
    },
}

_DEFAULT_BACK = {
    "eyebrow": "Sobre esta experiência",
    "title": "Suas escolhas importam",
    "copy": (
        "Converse com Mary acompanhando a evolução da cena. Ela toma iniciativa, "
        "reage às suas atitudes e pode aproximar-se ou encerrar a interação."
    ),
    "tips": (
        "Evite pular etapas sem contexto.",
        "Responda ao que Mary acabou de dizer.",
        "Respeito e atenção mantêm a história viva.",
    ),
}


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _resolver_verso(scenario_id: str, card: dict[str, Any]) -> dict[str, Any]:
    custom = card.get("back")
    if isinstance(custom, dict):
        base = dict(_DEFAULT_BACK)
        base.update(custom)
        return base
    return dict(_BACK_CONTENT.get(scenario_id, _DEFAULT_BACK))


def _css_flip_cards() -> str:
    return """
<style>
.mary-flip-card {
    width: 100%;
    min-height: 226px;
    perspective: 1200px;
    margin-bottom: .35rem;
    outline: none;
}
.mary-flip-card-inner {
    position: relative;
    width: 100%;
    min-height: 226px;
    transition: transform .62s cubic-bezier(.2,.75,.25,1);
    transform-style: preserve-3d;
}
.mary-flip-card:hover .mary-flip-card-inner,
.mary-flip-card:focus .mary-flip-card-inner,
.mary-flip-card:focus-within .mary-flip-card-inner {
    transform: rotateY(180deg);
}
.mary-flip-face {
    position: absolute;
    inset: 0;
    min-height: 226px;
    box-sizing: border-box;
    border-radius: 18px;
    padding: 1.15rem 1.15rem 1rem;
    backface-visibility: hidden;
    -webkit-backface-visibility: hidden;
    overflow: hidden;
}
.mary-flip-front {
    background: linear-gradient(145deg, rgba(42,20,45,.98), rgba(25,15,31,.98));
    border: 1px solid rgba(255,255,255,.10);
}
.mary-flip-back {
    transform: rotateY(180deg);
    background: linear-gradient(145deg, rgba(69,26,57,.99), rgba(32,17,38,.99));
    border: 1px solid rgba(255,130,183,.25);
    padding: .72rem .48rem .72rem 1.15rem;
}
.mary-flip-back-scroll {
    height: 202px;
    overflow-y: auto;
    overflow-x: hidden;
    overscroll-behavior: contain;
    touch-action: pan-y;
    padding: .43rem .72rem .5rem 0;
    scrollbar-width: thin;
    scrollbar-color: rgba(255,161,199,.54) rgba(255,255,255,.07);
}
.mary-flip-back-scroll::-webkit-scrollbar {
    width: 7px;
}
.mary-flip-back-scroll::-webkit-scrollbar-track {
    background: rgba(255,255,255,.06);
    border-radius: 999px;
}
.mary-flip-back-scroll::-webkit-scrollbar-thumb {
    background: rgba(255,161,199,.52);
    border-radius: 999px;
}
.mary-flip-back-scroll::-webkit-scrollbar-thumb:hover {
    background: rgba(255,183,211,.72);
}
.mary-flip-badge,
.mary-flip-eyebrow {
    display: inline-block;
    font-size: .72rem;
    line-height: 1;
    letter-spacing: .08em;
    text-transform: uppercase;
    font-weight: 750;
    color: #ffd4e5;
    background: rgba(255,105,165,.13);
    border: 1px solid rgba(255,147,190,.22);
    border-radius: 999px;
    padding: .38rem .58rem;
    margin-bottom: .85rem;
}
.mary-flip-title {
    color: #fff;
    font-size: 1.28rem;
    line-height: 1.18;
    font-weight: 780;
    margin-bottom: .55rem;
}
.mary-flip-copy {
    color: rgba(255,255,255,.78);
    font-size: .93rem;
    line-height: 1.46;
}
.mary-flip-access {
    position: absolute;
    left: 1.15rem;
    bottom: 1rem;
    color: #ffd0e2;
    font-weight: 720;
}
.mary-flip-hint {
    position: absolute;
    right: 1.15rem;
    bottom: 1rem;
    color: rgba(255,255,255,.48);
    font-size: .76rem;
}
.mary-flip-tips {
    margin: .72rem 0 .25rem;
    padding-left: 1.08rem;
    color: rgba(255,255,255,.82);
    font-size: .82rem;
    line-height: 1.35;
}
.mary-flip-tips li { margin-bottom: .28rem; }
.mary-flip-scroll-hint {
    margin-top: .55rem;
    color: rgba(255,255,255,.46);
    font-size: .72rem;
    text-align: right;
}
@media (prefers-reduced-motion: reduce) {
    .mary-flip-card-inner { transition: none; }
}
</style>
"""


def _patch_card_resolver() -> None:
    original = getattr(scenario_menu, "_resolver_card", None)
    if not callable(original) or getattr(original, "_mary_flip_wrapped", False):
        return

    @wraps(original)
    def wrapper(cenario: dict[str, Any]) -> dict[str, Any]:
        card = dict(original(cenario))
        scenario_id = _texto(cenario.get("scenario_id"))
        raw_card = cenario.get("card")
        raw_card = raw_card if isinstance(raw_card, dict) else {}
        card["scenario_id"] = scenario_id
        card["back"] = _resolver_verso(scenario_id, raw_card)
        return card

    wrapper._mary_flip_wrapped = True  # type: ignore[attr-defined]
    setattr(scenario_menu, "_resolver_card", wrapper)


def _patch_card_renderer() -> None:
    original = getattr(scenario_menu, "_render_card_copy", None)
    if not callable(original) or getattr(original, "_mary_flip_wrapped", False):
        return

    def renderer(*, card: dict[str, Any], access_label: str) -> None:
        back = card.get("back") if isinstance(card.get("back"), dict) else _DEFAULT_BACK
        tips = back.get("tips")
        if not isinstance(tips, (list, tuple)):
            tips = ()
        tips_html = "".join(
            f"<li>{html.escape(_texto(tip))}</li>" for tip in tips if _texto(tip)
        )
        st.markdown(
            (
                '<div class="mary-flip-card" tabindex="0" role="group" '
                'aria-label="Passe o mouse ou toque para ver detalhes">'
                '<div class="mary-flip-card-inner">'
                '<section class="mary-flip-face mary-flip-front">'
                f'<span class="mary-flip-badge">{html.escape(_texto(card.get("badge")) or "História")}</span>'
                f'<div class="mary-flip-title">{html.escape(_texto(card.get("title")))}</div>'
                f'<div class="mary-flip-copy">{html.escape(_texto(card.get("subtitle")))}</div>'
                f'<div class="mary-flip-access">{html.escape(_texto(access_label))}</div>'
                '<div class="mary-flip-hint">Passe o mouse · toque para detalhes</div>'
                '</section>'
                '<section class="mary-flip-face mary-flip-back">'
                '<div class="mary-flip-back-scroll" tabindex="0" '
                'aria-label="Detalhes da experiência; role para ler tudo">'
                f'<span class="mary-flip-eyebrow">{html.escape(_texto(back.get("eyebrow")))}</span>'
                f'<div class="mary-flip-title">{html.escape(_texto(back.get("title")))}</div>'
                f'<div class="mary-flip-copy">{html.escape(_texto(back.get("copy")))}</div>'
                f'<ul class="mary-flip-tips">{tips_html}</ul>'
                '<div class="mary-flip-scroll-hint">Role para ler todos os detalhes</div>'
                '</div>'
                '</section>'
                '</div></div>'
            ),
            unsafe_allow_html=True,
        )

    renderer._mary_flip_wrapped = True  # type: ignore[attr-defined]
    setattr(scenario_menu, "_render_card_copy", renderer)


def _patch_menu_renderer() -> None:
    original = getattr(scenario_menu, "renderizar_menu_cenarios", None)
    if not callable(original) or getattr(original, "_mary_flip_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        st.markdown(_css_flip_cards(), unsafe_allow_html=True)
        return original(*args, **kwargs)

    wrapper._mary_flip_wrapped = True  # type: ignore[attr-defined]
    setattr(scenario_menu, "renderizar_menu_cenarios", wrapper)


def aplicar_cards_reversiveis() -> None:
    _patch_card_resolver()
    _patch_card_renderer()
    _patch_menu_renderer()


def install_scenario_flip_cards() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    aplicar_cards_reversiveis()
    _INSTALLED = True


__all__ = [
    "SCENARIO_FLIP_CARDS_VERSION",
    "aplicar_cards_reversiveis",
    "install_scenario_flip_cards",
]
