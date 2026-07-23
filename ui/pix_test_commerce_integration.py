from __future__ import annotations

import secrets
import sys
from functools import wraps
from typing import Any, Callable

import streamlit as st

import ui.scenario_menu as scenario_menu
from commerce.mercado_pago_orders import (
    MercadoPagoOrdersError,
    criar_order_pix_teste,
    decodificar_qr_base64,
    extrair_pagamento_pix,
    obter_order,
)
from repositories.scenario_session_repository import obter_sessao_cenario


PIX_TEST_COMMERCE_VERSION = "pix-test-commerce-v3-mercado-pago-orders-credits"
PAID_SCENARIO_ID = "casada_frustrada"

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _modo_teste_ativado() -> bool:
    try:
        return bool(st.secrets.get("PIX_TEST_MODE", True))
    except Exception:
        return True


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
    store = st.session_state.get("pix_mp_test_purchases")
    if not isinstance(store, dict):
        store = {}
        st.session_state["pix_mp_test_purchases"] = store
    return store


def _credit_store() -> dict[str, dict[str, Any]]:
    store = st.session_state.get("pix_mp_test_credits")
    if not isinstance(store, dict):
        store = {}
        st.session_state["pix_mp_test_credits"] = store
    return store


def _store_key(user_id: str, scenario_id: str) -> str:
    return f"{_texto(user_id)}:{_texto(scenario_id)}"


def _reconciliar_credito(user_id: str, scenario_id: str) -> dict[str, Any] | None:
    key = _store_key(user_id, scenario_id)
    credits = _credit_store()
    credit = credits.get(key)
    if not isinstance(credit, dict):
        return None

    if _texto(credit.get("status")) == "in_use":
        session_id = _texto(credit.get("scenario_session_id"))
        if session_id:
            try:
                sessao = obter_sessao_cenario(session_id)
            except Exception:
                sessao = None
            if isinstance(sessao, dict):
                status = _texto(sessao.get("status")).lower()
                ending_sent = bool(sessao.get("ending_sent"))
                if (status and status != "active") or ending_sent:
                    credit["status"] = "consumed"
                    credit["consumed_reason"] = (
                        "ending_sent" if ending_sent else f"session_{status}"
                    )
                    credits[key] = credit
                    st.session_state["pix_mp_test_credits"] = credits
    return credit


def _cenario_tem_credito(user_id: str, scenario_id: str) -> bool:
    credit = _reconciliar_credito(user_id, scenario_id)
    return isinstance(credit, dict) and _texto(credit.get("status")) in {
        "available",
        "in_use",
    }


def _entitlements() -> set[str]:
    user_id = _usuario_atual_id()
    if not user_id:
        return set()
    return (
        {PAID_SCENARIO_ID}
        if _cenario_tem_credito(user_id, PAID_SCENARIO_ID)
        else set()
    )


def _obter_ou_criar_compra(
    *,
    user_id: str,
    cenario: dict[str, Any],
) -> dict[str, Any]:
    scenario_id = _texto(cenario.get("scenario_id"))
    key = _store_key(user_id, scenario_id)
    store = _purchase_store()
    existing = store.get(key)
    credit = _reconciliar_credito(user_id, scenario_id)

    if isinstance(credit, dict) and _texto(credit.get("status")) in {
        "available",
        "in_use",
    }:
        return existing if isinstance(existing, dict) else {}

    if isinstance(existing, dict) and _texto(existing.get("status")) in {
        "pending",
        "action_required",
    }:
        return existing

    compra = {
        "purchase_id": "pur_" + secrets.token_hex(8),
        "user_id": user_id,
        "scenario_id": scenario_id,
        "product_id": _texto(cenario.get("product_id")),
        "amount_cents": int(cenario.get("price_cents", 0) or 0),
        "currency": _texto(cenario.get("currency")) or "BRL",
        "idempotency_key": secrets.token_hex(16),
        "status": "pending",
        "order_id": "",
        "payment_id": "",
        "qr_code": "",
        "qr_code_base64": "",
        "ticket_url": "",
    }
    store[key] = compra
    st.session_state["pix_mp_test_purchases"] = store
    return compra


def _salvar_compra(compra: dict[str, Any]) -> None:
    key = _store_key(
        _texto(compra.get("user_id")),
        _texto(compra.get("scenario_id")),
    )
    store = _purchase_store()
    store[key] = dict(compra)
    st.session_state["pix_mp_test_purchases"] = store


def _criar_order_se_necessario(compra: dict[str, Any]) -> dict[str, Any]:
    if _texto(compra.get("order_id")):
        return compra

    order = criar_order_pix_teste(
        purchase_id=_texto(compra.get("purchase_id")),
        amount_cents=int(compra.get("amount_cents", 0) or 0),
        idempotency_key=_texto(compra.get("idempotency_key")),
    )
    payment = extrair_pagamento_pix(order)
    compra.update(
        {
            "order_id": payment["order_id"],
            "payment_id": payment["payment_id"],
            "status": payment["status"] or "pending",
            "status_detail": payment["status_detail"],
            "qr_code": payment["qr_code"],
            "qr_code_base64": payment["qr_code_base64"],
            "ticket_url": payment["ticket_url"],
        }
    )
    _salvar_compra(compra)
    return compra


def _conceder_credito(compra: dict[str, Any]) -> None:
    user_id = _texto(compra.get("user_id"))
    scenario_id = _texto(compra.get("scenario_id"))
    key = _store_key(user_id, scenario_id)
    credits = _credit_store()
    current = credits.get(key)
    if isinstance(current, dict) and _texto(current.get("status")) in {
        "available",
        "in_use",
    }:
        return
    credits[key] = {
        "credit_id": "crd_" + secrets.token_hex(8),
        "purchase_id": _texto(compra.get("purchase_id")),
        "user_id": user_id,
        "scenario_id": scenario_id,
        "status": "available",
        "scenario_session_id": "",
    }
    st.session_state["pix_mp_test_credits"] = credits


def _verificar_pagamento(compra: dict[str, Any]) -> bool:
    order_id = _texto(compra.get("order_id"))
    if not order_id:
        return False
    order = obter_order(order_id)
    payment = extrair_pagamento_pix(order)
    compra.update(
        {
            "payment_id": payment["payment_id"] or _texto(compra.get("payment_id")),
            "status": payment["status"] or _texto(compra.get("status")),
            "status_detail": payment["status_detail"],
            "qr_code": payment["qr_code"] or _texto(compra.get("qr_code")),
            "qr_code_base64": payment["qr_code_base64"]
            or _texto(compra.get("qr_code_base64")),
            "ticket_url": payment["ticket_url"] or _texto(compra.get("ticket_url")),
        }
    )
    _salvar_compra(compra)
    if payment["approved"]:
        _conceder_credito(compra)
        st.session_state["pix_test_last_unlocked"] = _texto(
            compra.get("scenario_id")
        )
        return True
    return False


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
        st.warning("PIX_TEST_MODE está desativado. A produção ainda não foi habilitada.")
        return

    compra = _obter_ou_criar_compra(user_id=user_id, cenario=cenario)
    try:
        compra = _criar_order_se_necessario(compra)
    except MercadoPagoOrdersError as exc:
        st.error(str(exc))
        if st.button("Voltar", key="pix_mp_error_back_" + scenario_id):
            st.session_state.pop("pix_test_checkout_scenario_id", None)
            st.rerun()
        return

    with st.container(border=True):
        st.markdown(f"### Desbloquear {titulo}")
        st.caption(
            "Ambiente de teste do Mercado Pago — nenhum dinheiro real será movimentado."
        )
        st.write(f"**Valor:** {_formatar_preco(compra)}")
        st.write(f"**Pedido interno:** `{_texto(compra.get('purchase_id'))}`")
        st.write(f"**Order Mercado Pago:** `{_texto(compra.get('order_id'))}`")
        st.write(
            f"**Status:** `{_texto(compra.get('status')) or 'pending'}` "
            f"· `{_texto(compra.get('status_detail')) or 'aguardando'}`"
        )

        qr_bytes = decodificar_qr_base64(_texto(compra.get("qr_code_base64")))
        if qr_bytes:
            st.image(qr_bytes, width=280)
        qr_code = _texto(compra.get("qr_code"))
        if qr_code:
            st.markdown("**Pix copia e cola de teste**")
            st.code(qr_code, language=None)
        ticket_url = _texto(compra.get("ticket_url"))
        if ticket_url:
            st.link_button(
                "Abrir página de pagamento de teste",
                ticket_url,
                use_container_width=True,
            )

        if st.button(
            "Verificar pagamento",
            key="pix_mp_verify_" + scenario_id,
            type="primary",
            use_container_width=True,
        ):
            try:
                approved = _verificar_pagamento(compra)
            except MercadoPagoOrdersError as exc:
                st.error(str(exc))
            else:
                if approved:
                    st.session_state.pop("pix_test_checkout_scenario_id", None)
                    st.rerun()
                st.info(
                    "O Mercado Pago ainda não marcou a order como aprovada. "
                    "Aguarde alguns segundos e verifique novamente."
                )

        if st.button(
            "Cancelar e voltar",
            key="pix_mp_cancel_" + scenario_id,
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


def _marcar_credito_em_uso(instancia: Any) -> None:
    if not isinstance(instancia, dict):
        return
    user_id = _texto(instancia.get("user_id"))
    scenario_id = _texto(instancia.get("scenario_id"))
    session_id = _texto(instancia.get("scenario_session_id"))
    if scenario_id != PAID_SCENARIO_ID or not user_id or not session_id:
        return
    key = _store_key(user_id, scenario_id)
    credits = _credit_store()
    credit = credits.get(key)
    if not isinstance(credit, dict):
        return
    if _texto(credit.get("status")) == "available":
        credit["status"] = "in_use"
        credit["scenario_session_id"] = session_id
        credits[key] = credit
        st.session_state["pix_mp_test_credits"] = credits


def _patch_access_function(module: Any, name: str) -> None:
    original = getattr(module, name, None)
    if not callable(original) or getattr(original, "_mary_pix_test_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **_adicionar_desbloqueios(kwargs))
        if name == "iniciar_cenario_para_usuario":
            _marcar_credito_em_uso(result)
        elif name == "continuar_cenario_para_usuario" and isinstance(result, tuple):
            _marcar_credito_em_uso(result[0] if result else None)
        return result

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
            st.success(
                "Pagamento de teste confirmado. Uma experiência foi liberada para esta conta."
            )

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
        "continuar_cenario_para_usuario",
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
