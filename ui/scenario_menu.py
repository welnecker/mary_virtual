from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st


ACTION_PLAY = "play"
ACTION_UNLOCK = "unlock"


ScenarioMenuAction = dict[str, str]


def _texto(
    valor: Any,
) -> str:
    return str(
        valor or ""
    ).strip()


def _inteiro(
    valor: Any,
    *,
    padrao: int = 0,
) -> int:
    try:
        return int(
            valor
        )
    except (
        TypeError,
        ValueError,
    ):
        return padrao


def formatar_preco(
    *,
    price_cents: int,
    currency: str = "BRL",
) -> str:
    price_cents = max(
        0,
        _inteiro(
            price_cents
        ),
    )

    currency = (
        _texto(
            currency
        )
        or "BRL"
    ).upper()

    valor = price_cents / 100

    if currency == "BRL":
        numero = f"{valor:,.2f}"
        numero = numero.replace(
            ",",
            "TEMP",
        ).replace(
            ".",
            ",",
        ).replace(
            "TEMP",
            ".",
        )
        return f"R$ {numero}"

    return f"{currency} {valor:.2f}"


def _resolver_card(
    cenario: dict[str, Any],
) -> dict[str, str]:
    card = cenario.get(
        "card"
    )

    if not isinstance(
        card,
        dict,
    ):
        card = {}

    return {
        "title": (
            _texto(
                card.get(
                    "title"
                )
            )
            or _texto(
                cenario.get(
                    "card_title"
                )
            )
            or _texto(
                cenario.get(
                    "title"
                )
            )
        ),
        "subtitle": (
            _texto(
                card.get(
                    "subtitle"
                )
            )
            or _texto(
                cenario.get(
                    "card_subtitle"
                )
            )
            or _texto(
                cenario.get(
                    "short_description"
                )
            )
        ),
        "image": (
            _texto(
                card.get(
                    "image"
                )
            )
            or _texto(
                cenario.get(
                    "card_image"
                )
            )
        ),
        "badge": (
            _texto(
                card.get(
                    "badge"
                )
            )
            or _texto(
                cenario.get(
                    "card_badge"
                )
            )
        ),
        "button_label_free": (
            _texto(
                card.get(
                    "button_label_free"
                )
            )
            or _texto(
                cenario.get(
                    "button_label_free"
                )
            )
            or "Jogar gratuitamente"
        ),
        "button_label_locked": (
            _texto(
                card.get(
                    "button_label_locked"
                )
            )
            or _texto(
                cenario.get(
                    "button_label_locked"
                )
            )
            or "Desbloquear"
        ),
        "button_label_unlocked": (
            _texto(
                card.get(
                    "button_label_unlocked"
                )
            )
            or _texto(
                cenario.get(
                    "button_label_unlocked"
                )
            )
            or "Jogar"
        ),
    }


def _imagem_existe(
    image_path: str,
) -> bool:
    image_path = _texto(
        image_path
    )

    if not image_path:
        return False

    if image_path.startswith(
        (
            "http://",
            "https://",
        )
    ):
        return True

    return Path(
        image_path
    ).is_file()


def _rotulo_acesso(
    cenario: dict[str, Any],
) -> str:
    access_status = _texto(
        cenario.get(
            "access_status"
        )
    ).lower()

    if access_status == "free":
        return "Acesso gratuito"

    if access_status == "unlocked":
        return "História desbloqueada"

    if access_status == "unavailable":
        return "Indisponível"

    price_cents = _inteiro(
        cenario.get(
            "price_cents"
        )
    )

    currency = _texto(
        cenario.get(
            "currency"
        )
    ) or "BRL"

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
    access_status = _texto(
        cenario.get(
            "access_status"
        )
    ).lower()

    if access_status == "free":
        return card[
            "button_label_free"
        ]

    if access_status == "unlocked":
        return card[
            "button_label_unlocked"
        ]

    return card[
        "button_label_locked"
    ]


def _renderizar_card(
    cenario: dict[str, Any],
) -> ScenarioMenuAction | None:
    scenario_id = _texto(
        cenario.get(
            "scenario_id"
        )
    )

    if not scenario_id:
        return None

    card = _resolver_card(
        cenario
    )

    allowed = bool(
        cenario.get(
            "allowed",
            False,
        )
    )

    access_status = _texto(
        cenario.get(
            "access_status",
            "locked",
        )
    ).lower()

    with st.container(
        border=True
    ):
        if _imagem_existe(
            card[
                "image"
            ]
        ):
            st.image(
                card[
                    "image"
                ],
                use_container_width=True,
            )

        if card[
            "badge"
        ]:
            st.caption(
                card[
                    "badge"
                ].upper()
            )

        st.markdown(
            f"### {card['title']}"
        )

        if card[
            "subtitle"
        ]:
            st.write(
                card[
                    "subtitle"
                ]
            )

        st.caption(
            _rotulo_acesso(
                cenario
            )
        )

        button_label = _rotulo_botao(
            cenario=cenario,
            card=card,
        )

        if access_status == "unavailable":
            st.button(
                button_label,
                key=(
                    "scenario_unavailable_"
                    + scenario_id
                ),
                disabled=True,
                use_container_width=True,
            )
            return None

        clicked = st.button(
            button_label,
            key=(
                "scenario_card_"
                + scenario_id
            ),
            type=(
                "primary"
                if allowed
                else "secondary"
            ),
            use_container_width=True,
        )

        if not clicked:
            return None

        return {
            "action": (
                ACTION_PLAY
                if allowed
                else ACTION_UNLOCK
            ),
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
    """
    Renderiza o catálogo em cards e retorna apenas a ação escolhida.

    Esta função não inicia histórias, não concede acesso e não processa
    pagamentos. Essas decisões permanecem fora da camada de interface.
    """

    st.markdown(
        f"## {_texto(titulo) or 'Escolha uma história'}"
    )

    if _texto(
        descricao
    ):
        st.caption(
            _texto(
                descricao
            )
        )

    if not isinstance(
        cenarios,
        list,
    ) or not cenarios:
        st.info(
            "Nenhuma história está disponível neste momento."
        )
        return None

    quantidade_colunas = max(
        1,
        min(
            _inteiro(
                quantidade_colunas,
                padrao=2,
            ),
            4,
        ),
    )

    colunas = st.columns(
        quantidade_colunas
    )

    for indice, cenario in enumerate(
        cenarios
    ):
        if not isinstance(
            cenario,
            dict,
        ):
            continue

        coluna = colunas[
            indice % quantidade_colunas
        ]

        with coluna:
            acao = _renderizar_card(
                cenario
            )

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
