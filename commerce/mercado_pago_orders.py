from __future__ import annotations

import base64
import uuid
from decimal import Decimal
from typing import Any

import requests
import streamlit as st


MERCADO_PAGO_ORDERS_VERSION = "mercado-pago-orders-v1-test-pix"
MERCADO_PAGO_API_BASE = "https://api.mercadopago.com"


class MercadoPagoOrdersError(RuntimeError):
    """Falha ao criar ou consultar uma order no Mercado Pago."""


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _access_token() -> str:
    try:
        token = _texto(st.secrets.get("MERCADO_PAGO_ACCESS_TOKEN"))
    except Exception as exc:
        raise MercadoPagoOrdersError(
            "O Access Token do Mercado Pago não está disponível nos Secrets."
        ) from exc
    if not token:
        raise MercadoPagoOrdersError(
            "MERCADO_PAGO_ACCESS_TOKEN não foi configurado nos Secrets."
        )
    return token


def _headers(*, idempotency_key: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {_access_token()}",
        "Content-Type": "application/json",
    }
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key
    return headers


def _request_json(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    try:
        response = requests.request(
            method,
            MERCADO_PAGO_API_BASE + path,
            headers=_headers(idempotency_key=idempotency_key),
            json=payload,
            timeout=25,
        )
    except requests.RequestException as exc:
        raise MercadoPagoOrdersError(
            f"Não foi possível comunicar com o Mercado Pago: {exc}"
        ) from exc

    try:
        data = response.json()
    except ValueError:
        data = {"message": response.text[:500]}

    if response.status_code >= 400:
        message = _texto(data.get("message")) or _texto(data.get("error"))
        details = data.get("errors") or data.get("cause") or data.get("details")
        if details:
            message = f"{message} | {details}" if message else str(details)
        raise MercadoPagoOrdersError(
            f"Mercado Pago retornou HTTP {response.status_code}: "
            f"{message or 'erro não detalhado'}"
        )

    if not isinstance(data, dict):
        raise MercadoPagoOrdersError("O Mercado Pago retornou uma resposta inválida.")
    return data


def criar_order_pix_teste(
    *,
    purchase_id: str,
    amount_cents: int,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    purchase_id = _texto(purchase_id)
    if not purchase_id:
        raise ValueError("purchase_id é obrigatório.")
    amount_cents = int(amount_cents or 0)
    if amount_cents <= 0:
        raise ValueError("O valor da cobrança deve ser maior que zero.")

    amount = str((Decimal(amount_cents) / Decimal(100)).quantize(Decimal("0.00")))
    key = _texto(idempotency_key) or str(uuid.uuid4())
    payload = {
        "type": "online",
        "processing_mode": "automatic",
        "external_reference": purchase_id,
        "total_amount": amount,
        "payer": {
            "email": "test_user_br@testuser.com",
            "first_name": "APRO",
        },
        "transactions": {
            "payments": [
                {
                    "amount": amount,
                    "payment_method": {
                        "id": "pix",
                        "type": "bank_transfer",
                    },
                }
            ]
        },
    }
    return _request_json(
        "POST",
        "/v1/orders",
        payload=payload,
        idempotency_key=key,
    )


def obter_order(order_id: str) -> dict[str, Any]:
    order_id = _texto(order_id)
    if not order_id:
        raise ValueError("order_id é obrigatório.")
    return _request_json("GET", f"/v1/orders/{order_id}")


def extrair_pagamento_pix(order: dict[str, Any] | None) -> dict[str, Any]:
    data = order if isinstance(order, dict) else {}
    transactions = data.get("transactions")
    payments: list[Any] = []
    if isinstance(transactions, dict):
        raw = transactions.get("payments")
        if isinstance(raw, list):
            payments = raw
    payment = payments[0] if payments and isinstance(payments[0], dict) else {}
    method = payment.get("payment_method")
    if not isinstance(method, dict):
        method = {}

    status = _texto(payment.get("status") or data.get("status")).lower()
    status_detail = _texto(
        payment.get("status_detail") or data.get("status_detail")
    ).lower()
    return {
        "order_id": _texto(data.get("id")),
        "payment_id": _texto(payment.get("id")),
        "external_reference": _texto(data.get("external_reference")),
        "status": status,
        "status_detail": status_detail,
        "approved": status in {"approved", "processed"},
        "qr_code": _texto(method.get("qr_code")),
        "qr_code_base64": _texto(method.get("qr_code_base64")),
        "ticket_url": _texto(method.get("ticket_url")),
    }


def decodificar_qr_base64(value: str) -> bytes | None:
    text = _texto(value)
    if not text:
        return None
    if "," in text and text.lower().startswith("data:"):
        text = text.split(",", 1)[1]
    try:
        return base64.b64decode(text, validate=True)
    except (ValueError, TypeError):
        return None


__all__ = [
    "MERCADO_PAGO_ORDERS_VERSION",
    "MercadoPagoOrdersError",
    "criar_order_pix_teste",
    "obter_order",
    "extrair_pagamento_pix",
    "decodificar_qr_base64",
]
