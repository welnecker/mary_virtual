from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import streamlit as st

from scenarios.service import (
    continuar_cenario_para_usuario,
    reiniciar_cenario_para_usuario,
)
from ui.professional_experience import install_professional_experience


# O app.py importa este módulo em toda execução. A instalação apenas substitui
# pontos de apresentação do Streamlit; não executa componentes antes do
# st.set_page_config e não interfere nos motores narrativos.
install_professional_experience()


ACTION_PLAY = "play"
ACTION_UNLOCK = "unlock"

ScenarioMenuAction = dict[str, str]


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _inteiro(valor: Any, *, padrao: int = 0) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def formatar_preco(
    *,
    price_cents: int,
    currency: str = "BRL",
) -> str:
    price_cents = max(0, _inteiro(price_cents))
    currency = (_texto(currency) or "BRL").upper()
    valor = price_cents / 100
    if currency == "BRL":
        numero = f"{valor:,.2f}"
        numero = (
            numero.replace(",", "TEMP")
            .replace(".", ",")
            .replace("TEMP", ".")
        )
        return f"R$ {numero}"
    return f"{currency} {valor:.2f}"


def _resolver_card(cenario: dict[str, Any]) -> dict[str, str]:
    card = cenario.get("card")
    if not isinstance(card, dict):
        card = {}
    return {
        "title": (
            _texto(card.get("title"))
            or _texto(cenario.get("card_title"))
            or _texto(cenario.get("title"))
        ),
        "subtitle": (
            _texto(card.get("subtitle"))
            or _texto(cenario.get("card_subtitle"))
            or _texto(cenario.get("short_description"))
        ),
        "image": (
            _texto(card.get("image"))
            or _texto(cenario.get("card_image"))
        ),
        "badge": (
            _texto(card.get("badge"))
            or _texto(cenario.get("card_badge"))
        ),
        "button_label_free": (
            _texto(card.get("button_label_free"))
            or _texto(cenario.get("button_label_free"))
            or "Jogar gratuitamente"
        ),
        "button_label_locked": (
            _texto(card.get("button_label_locked"))
            or _texto(cenario.get("button_label_locked"))
            or "Desbloquear"
        ),
        "button_label_unlocked": (
            _texto(card.get("button_label_unlocked"))
            or _texto(cenario.get("button_label_unlocked"))
            or "Jogar"
        ),
    }


def _imagem_existe(image_path: str) -> bool:
    image_path = _texto(image_path)
    if not image_path:
        return False
    if image_path.startswith(("http://", "https://")):
        return True
    return Path(image_path).is_file()


def _rotulo_acesso(cenario: dict[str, Any]) -> str:
    access_status = _texto(cenario.get("access_status")).lower()
    if access_status == "free":
        return "Acesso gratuito"
    if access_status == "unlocked":
        return "História desbloqueada"
    if access_status == "unavailable":
        return "Indisponível"

    price_cents = _inteiro(cenario.get("price_cents"))
    currency = _texto(cenario.get("currency")) or "BRL"
    if price_cents > 0:
        return formatar_preco(
            price_cents=price_cents,
            currency=currency,
        )
    return "Acesso bloqueado"


def _rotulo_botao(
    *,
    cenario: dict[str, Any],
    card: dict[str, str],
) -> str:
    access_status = _texto(cenario.get("access_status")).lower()
    if access_status == "free":
        return card["button_label_free"]
    if access_status == "unlocked":
        return card["button_label_unlocked"]
    return card["button_label_locked"]


def _continuar_historia(
    *,
    cenario: dict[str, Any],
) -> None:
    sessao = cenario.get("active_session")
    if not isinstance(sessao, dict):
        st.error("Não foi possível localizar a história iniciada.")
        return

    user_id = _texto(sessao.get("user_id"))
    scenario_session_id = _texto(sessao.get("scenario_session_id"))
    if not user_id or not scenario_session_id:
        st.error("A sessão narrativa está incompleta.")
        return

    try:
        instancia, mensagens = continuar_cenario_para_usuario(
            user_id=user_id,
            scenario_session_id=scenario_session_id,
            unlocked_scenario_ids=set(),
        )
    except (ValueError, PermissionError) as exc:
        st.error(str(exc))
        return

    st.session_state["scenario_instance"] = instancia
    st.session_state["selected_scenario_id"] = _texto(
        instancia.get("scenario_id")
    )
    st.session_state["scenario_selector_visible"] = False
    st.session_state["messages"] = mensagens
    st.session_state["initial_message_created"] = bool(
        mensagens or instancia.get("opening_sent")
    )
    st.session_state["history_restored"] = True
    st.rerun()


def _preparar_reinicio(
    *,
    cenario: dict[str, Any],
) -> bool:
    sessao = cenario.get("active_session")
    if not isinstance(sessao, dict):
        return True

    user_id = _texto(sessao.get("user_id"))
    scenario_session_id = _texto(sessao.get("scenario_session_id"))
    if not user_id or not scenario_session_id:
        return True

    try:
        reiniciar_cenario_para_usuario(
            user_id=user_id,
            scenario_session_id=scenario_session_id,
        )
    except ValueError as exc:
        st.error(str(exc))
        return False
    return True


def _render_card_copy(
    *,
    card: dict[str, str],
    access_label: str,
) -> None:
    badge = html.escape(card["badge"] or "História")
    title = html.escape(card["title"])
    subtitle = html.escape(card["subtitle"])
    access = html.escape(access_label)

    st.markdown(
        (
            '<div class="mary-card-shell">'
            f'<span class="mary-card-badge">{badge}</span>'
            f'<div class="mary-card-title">{title}</div>'
            f'<div class="mary-card-copy">{subtitle}</div>'
            f'<div class="mary-card-access">{access}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _renderizar_card(
    cenario: dict[str, Any],
) -> ScenarioMenuAction | None:
    scenario_id = _texto(cenario.get("scenario_id"))
    if not scenario_id:
        return None

    card = _resolver_card(cenario)
    allowed = bool(cenario.get("allowed", False))
    access_status = _texto(
        cenario.get("access_status", "locked")
    ).lower()
    can_continue = bool(cenario.get("can_continue", False))

    with st.container(border=True):
        if _imagem_existe(card["image"]):
            st.image(card["image"], use_container_width=True)

        _render_card_copy(
            card=card,
            access_label=_rotulo_acesso(cenario),
        )

        if can_continue:
            interaction_count = _inteiro(cenario.get("interaction_count"))
            st.caption(
                f"Em andamento · {interaction_count} interações"
            )
            coluna_continuar, coluna_reiniciar = st.columns(2)

            with coluna_continuar:
                continuar = st.button(
                    "Continuar",
                    key="scenario_continue_" + scenario_id,
                    type="primary",
                    use_container_width=True,
                )
            with coluna_reiniciar:
                reiniciar = st.button(
                    "Reiniciar",
                    key="scenario_restart_" + scenario_id,
                    use_container_width=True,
                )

            if continuar:
                _continuar_historia(cenario=cenario)
                return None
            if reiniciar:
                if not _preparar_reinicio(cenario=cenario):
                    return None
                return {
                    "action": ACTION_PLAY,
                    "scenario_id": scenario_id,
                }
            return None

        button_label = _rotulo_botao(
            cenario=cenario,
            card=card,
        )
        if access_status == "unavailable":
            st.button(
                button_label,
                key="scenario_unavailable_" + scenario_id,
                disabled=True,
                use_container_width=True,
            )
            return None

        clicked = st.button(
            button_label,
            key="scenario_card_" + scenario_id,
            type="primary" if allowed else "secondary",
            use_container_width=True,
        )
        if not clicked:
            return None
        return {
            "action": ACTION_PLAY if allowed else ACTION_UNLOCK,
            "scenario_id": scenario_id,
        }


def renderizar_menu_cenarios(
    cenarios: list[dict[str, Any]],
    *,
    titulo: str = "Escolha uma história",
    descricao: str = (
        "Cada história é uma experiência independente com Mary."
    ),
    quantidade_colunas: int = 2,
) -> ScenarioMenuAction | None:
    title = html.escape(_texto(titulo) or "Escolha uma história")
    copy = html.escape(_texto(descricao))
    st.markdown(
        (
            '<section class="mary-catalog-hero">'
            '<div class="mary-catalog-eyebrow">Experiências com Mary</div>'
            f'<div class="mary-catalog-title">{title}</div>'
            f'<div class="mary-catalog-copy">{copy}</div>'
            "</section>"
        ),
        unsafe_allow_html=True,
    )

    if not isinstance(cenarios, list) or not cenarios:
        st.info("Nenhuma história está disponível neste momento.")
        return None

    quantidade_colunas = max(
        1,
        min(
            _inteiro(quantidade_colunas, padrao=2),
            4,
        ),
    )
    colunas = st.columns(quantidade_colunas, gap="large")

    for indice, cenario in enumerate(cenarios):
        if not isinstance(cenario, dict):
            continue
        coluna = colunas[indice % quantidade_colunas]
        with coluna:
            acao = _renderizar_card(cenario)
        if acao is not None:
            return acao
    return None


__all__ = [
    "ACTION_PLAY",
    "ACTION_UNLOCK",
    "ScenarioMenuAction",
    "formatar_preco",
    "renderizar_menu_cenarios",
]
