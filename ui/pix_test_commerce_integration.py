from __future__ import annotations

import hashlib
import secrets
import sys
from functools import wraps
from typing import Any, Callable

import streamlit as st

import ui.scenario_menu as scenario_menu


PIX_TEST_COMMERCE_VERSION = "pix-test-commerce-v1-session-entitlements"

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _modo_teste_ativado() -> bool:
    try:
        return bool(st.secrets.get("PIX_TEST_MODE", True))
    except Exception:
        return True


def _entitlements() -> set[str]:
    raw = st.session_state.get("pix_test_entitlements", [])
    if not isinstance(raw, (list, tuple, set)):
        raw = []
    return {_texto(item) for item in raw if _texto(item)}


def _salvar_entitlements(values: set[str]) -> None:
    st.session_state["pix_test_entitlements"] = sorted(values)


def _usuario_atual_id() -> str:
    usuario = (
        st.session_state.get("persistent_user")
        or st.session_state.get("auth_user")
        or {}
    )
    if not isinstance(usuario, dict):
        return ""
    return _texto(usuario.get("user_id"))


def _purchase_store() -> dict[str, dict[str, Any]]:
    store = st.session_state.get("pix_test_purchases")
    if not isinstance(store, dict):
        store = {}
        st.session_state["pix_test_purchases"] = store
    return store


def _criar_txid(*, user_id: str, scenario_id: str) -> str:
    nonce = secrets.token_hex(5).upper()
    material = f"{user_id}|{scenario_id}|{nonce}".encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()[:10].upper()
    return f"MARY{digest}"


def _obter_ou_criar_compra(
    *,
    user_id: str,
    cenario: dict[str, Any],
) -> dict[str, Any]:
    scenario_id = _texto(cenario.get("scenario_id"))
    store = _purchase_store()
    key = f"{user_id}:{scenario_id}"
    existing = store.get(key)
    if isinstance(existing, dict) and _texto(existing.get("status")) != "expired":
        return existing

    compra = {
        "purchase_id": "pur_" + secrets.token_hex(8),
        "user_id": user_id,
        "scenario_id": scenario_id,
        "product_id": _texto(cenario.get("product_id")),
        "amount_cents": int(cenario.get("price_cents", 0) or 0),
        "currency": _texto(cenario.get("currency")) or "BRL",
        "txid": _criar_txid(user_id=user_id, scenario_id=scenario_id),
        "status": "pending",
    }
    store[key] = compra
    st.session_state["pix_test_purchases"] = store
    return compra


def _codigo_pix_teste(compra: dict[str, Any]) -> str:
    amount = int(compra.get("amount_cents", 0) or 0) / 100
    return (
        "PIX-TESTE|"
        f"TXID={_texto(compra.get('txid'))}|"
        f"VALOR={amount:.2f}|"
        f"PRODUTO={_texto(compra.get('product_id'))}"
    )


def _formatar_preco(compra: dict[str, Any]) -> str:
    return scenario_menu.formatar_preco(
        price_cents=int(compra.get("amount_cents", 0) or 0),
        currency=_texto(compra.get("currency")) or "BRL",
    )


def _renderizar_checkout_teste(cenario: dict[str, Any]) -> None:
    user_id = _usuario_atual_id()
    scenario_id = _texto(cenario.get("scenario_id"))
    titulo = _texto(cenario.get("title")) or scenario_id

    if not user_id:
        st.error("Não foi possível identificar a conta atual para criar a cobrança.")
        return

    if not _modo_teste_ativado():
        st.warning(
            "A cobrança Pix real ainda não foi configurada. "
            "Ative PIX_TEST_MODE para validar o fluxo de compra."
        )
        return

    compra = _obter_ou_criar_compra(user_id=user_id, cenario=cenario)

    with st.container(border=True):
        st.markdown(f"### Desbloquear {titulo}")
        st.caption("Ambiente de teste — nenhum pagamento real será realizado.")
        st.write(f"**Valor:** {_formatar_preco(compra)}")
        st.write(f"**Pedido:** `{_texto(compra.get('purchase_id'))}`")
        st.write(f"**TXID:** `{_texto(compra.get('txid'))}`")
        st.code(_codigo_pix_teste(compra), language=None)
        st.caption(
            "Na integração real, este campo será substituído pelo Pix copia e cola "
            "gerado pelo provedor para este pedido."
        )

        if st.button(
            "Simular pagamento confirmado",
            key="pix_test_confirm_" + scenario_id,
            type="primary",
            use_container_width=True,
        ):
            compra["status"] = "paid"
            store = _purchase_store()
            store[f"{user_id}:{scenario_id}"] = compra
            st.session_state["pix_test_purchases"] = store

            unlocked = _entitlements()
            unlocked.add(scenario_id)
            _salvar_entitlements(unlocked)
            st.session_state["pix_test_last_unlocked"] = scenario_id
            st.rerun()

        if st.button(
            "Cancelar",
            key="pix_test_cancel_" + scenario_id,
            use_container_width=True,
        ):
            st.session_state.pop("pix_test_checkout_scenario_id", None)
            st.rerun()


def _adicionar_desbloqueios(kwargs: dict[str, Any]) -> dict[str, Any]:
    result = dict(kwargs)
    current = result.get("unlocked_scenario_ids")
    unlocked = set(current) if isinstance(current, (set, list, tuple)) else set()
    unlocked.update(_entitlements())
    result["unlocked_scenario_ids"] = unlocked
    return result


def _patch_access_function(module: Any, name: str) -> None:
    original = getattr(module, name, None)
    if not callable(original) or getattr(original, "_mary_pix_test_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return original(*args, **_adicionar_desbloqueios(kwargs))

    wrapper._mary_pix_test_wrapped = True  # type: ignore[attr-defined]
    setattr(module, name, wrapper)


def _patch_menu_renderer(module: Any) -> None:
    original = getattr(module, "renderizar_menu_cenarios", None)
    if not callable(original) or getattr(original, "_mary_pix_test_wrapped", False):
        return

    @wraps(original)
    def wrapper(cenarios: list[dict[str, Any]], *args: Any, **kwargs: Any) -> Any:
        last_unlocked = _texto(st.session_state.pop("pix_test_last_unlocked", ""))
        if last_unlocked:
            st.success("Pagamento confirmado. A história foi desbloqueada para esta conta.")

        checkout_id = _texto(st.session_state.get("pix_test_checkout_scenario_id"))
        if checkout_id:
            cenario = next(
                (
                    item
                    for item in cenarios
                    if isinstance(item, dict)
                    and _texto(item.get("scenario_id")) == checkout_id
                ),
                None,
            )
            if isinstance(cenario, dict):
                _renderizar_checkout_teste(cenario)
                return None
            st.session_state.pop("pix_test_checkout_scenario_id", None)

        action = original(cenarios, *args, **kwargs)
        if not isinstance(action, dict):
            return action
        if _texto(action.get("action")) != scenario_menu.ACTION_UNLOCK:
            return action

        scenario_id = _texto(action.get("scenario_id"))
        st.session_state["pix_test_checkout_scenario_id"] = scenario_id
        st.rerun()
        return None

    wrapper._mary_pix_test_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "renderizar_menu_cenarios", wrapper)


def aplicar_integracao_pix_teste() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return

    for function_name in (
        "listar_cenarios_para_usuario",
        "iniciar_cenario_para_usuario",
    ):
        _patch_access_function(module, function_name)

    _patch_menu_renderer(module)


def install_pix_test_commerce_integration() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return

    _ORIGINAL_TITLE = st.title

    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_integracao_pix_teste()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "PIX_TEST_COMMERCE_VERSION",
    "aplicar_integracao_pix_teste",
    "install_pix_test_commerce_integration",
]
