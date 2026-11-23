"""Piloto Telegram isolado do estado narrativo principal.

Sem worker contínuo: botão Chamar envia; botão Verificar respostas lê getUpdates.
Nunca registra token ou mensagens em logs. Não usar em produção multiusuário sem
persistência transacional de offset/estado e um serviço receptor durável.
"""
from __future__ import annotations

import json
from typing import Any
import requests
import streamlit as st

from direct_script import load_direct_script_rows, build_direct_writer_prompt
from direct_semantic_director import validate_direct_semantic_turn
from openrouter_client import chat
from output_filter import parse_mary_components, sanitize_mary_output, looks_like_action_narration

_TIMEOUT = 15
_SCRIPT = "Celular1"
_TAB = "MARY_CELULAR"


def _secret(name: str) -> str:
    try:
        return str(st.secrets.get(name, "") or "").strip()
    except Exception:
        return ""


def _telegram(method: str, payload: dict | None = None) -> dict:
    token = _secret("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Configure TELEGRAM_BOT_TOKEN nos Secrets.")
    response = requests.post(
        f"https://api.telegram.org/bot{token}/{method}",
        json=payload or {}, timeout=_TIMEOUT,
    )
    # Não expor URL com token no texto de erros.
    if not response.ok:
        raise RuntimeError(f"Telegram não aceitou {method} (HTTP {response.status_code}).")
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram retornou falha ao executar {method}.")
    return result


def _credentials() -> tuple[dict, str]:
    raw = (st.secrets.get("GOOGLE_CREDS_JSON")
           or st.secrets.get("gcp_service_account")
           or st.secrets.get("GOOGLE_SERVICE_ACCOUNT"))
    if isinstance(raw, str):
        raw = json.loads(raw)
    creds = dict(raw or {})
    if isinstance(creds.get("private_key"), str):
        creds["private_key"] = creds["private_key"].replace("\\n", "\n")
    sheet_id = _secret("MARY_SHEETS_ID")
    if not creds or not sheet_id:
        raise RuntimeError("Credenciais de Google Sheets ausentes.")
    return creds, sheet_id


def _rows() -> list[dict]:
    creds, sheet_id = _credentials()
    rows = load_direct_script_rows(
        service_account_info=creds,
        spreadsheet_id=sheet_id,
        worksheet_name=_TAB,
        script_name=_SCRIPT,
    )
    if not rows:
        raise RuntimeError("Preencha a aba MARY_CELULAR com ROTEIRO=Celular1 e FALA-GUIA.")
    return rows


def _state() -> dict:
    if "_mary_telegram_pilot" not in st.session_state:
        st.session_state["_mary_telegram_pilot"] = {
            "index": 0, "history": [], "offset": 0, "last_message_id": 0,
        }
    return st.session_state["_mary_telegram_pilot"]


def _allowed_chat() -> int:
    value = _secret("TELEGRAM_CHAT_ID")
    if not value or not value.lstrip("-").isdigit():
        raise RuntimeError("Configure TELEGRAM_CHAT_ID nos Secrets após identificar o chat.")
    return int(value)


def _generate(row: dict, rows: list[dict], history: list[dict], user_text: str, model: str) -> str:
    prompt = build_direct_writer_prompt(
        row=row, all_rows=rows, recent_messages=history[-10:],
        user_text=user_text, active_interlocutor="Donisete",
        character_name="Donisete",
    )
    prompt += (
        "\n\nCANAL TELEGRAM: somente a fala verbal de Mary será enviada. "
        "Escreva [FALA] com linguagem de mensagem natural e concisa. "
        "Não descreva que pega o celular, não antecipe linhas futuras; "
        "não invente resposta do destinatário."
    )
    messages = [{"role": "system", "content": prompt}]
    if user_text:
        messages.append({"role": "user", "content": user_text})
    raw = chat(
        api_key=_secret("OPENROUTER_API_KEY"), model=model,
        messages=messages, temperature=0.6, call_type="TELEGRAM_PILOT",
    )
    parts = parse_mary_components(raw)
    speech = sanitize_mary_output(parts.get("speech", ""))
    if not speech or looks_like_action_narration(speech):
        raise RuntimeError("A resposta foi retida: Mary não produziu fala limpa.")
    validation = validate_direct_semantic_turn(
        api_key=_secret("OPENROUTER_API_KEY"),
        model=_secret("MARY_DIRECTOR_MODEL") or model,
        fallback_model=_secret("MARY_FALLBACK_MODEL") or None,
        row=row, interpretation={}, mary_text=speech,
        mary_thought=parts.get("thought", ""),
        mary_action=parts.get("action", ""),
        user_text=user_text, user_scene_direction="",
        line_dialogue=[],
    )
    if not validation.get("fulfilled", False):
        raise RuntimeError("Diretor semântico não aprovou a mensagem; nada foi enviado.")
    return speech


def _send_line(rows: list[dict], state: dict, chat_id: int, model: str, user_text: str = "") -> None:
    index = int(state["index"])
    if index >= len(rows):
        raise RuntimeError("O roteiro Celular1 já terminou.")
    row = rows[index]
    speech = _generate(row, rows, list(state["history"]), user_text, model)
    result = _telegram("sendMessage", {"chat_id": chat_id, "text": speech})
    msg = result.get("result", {})
    state["last_message_id"] = int(msg.get("message_id", 0) or 0)
    if user_text:
        state["history"].append({"role": "user", "content": user_text})
    state["history"].append({"role": "assistant", "content": speech})
    state["index"] += 1  # Só avança depois do envio confirmado.


def render_telegram_sidebar(model: str) -> None:
    st.divider()
    st.subheader("Telegram — Mary")
    if not _secret("TELEGRAM_BOT_TOKEN"):
        st.caption("Configure TELEGRAM_BOT_TOKEN nos Secrets para habilitar o piloto.")
        return
    if not _secret("TELEGRAM_CHAT_ID"):
        st.caption("Abra @marycore2_bot, envie /start e clique em Identificar chat.")
        if st.button("Identificar chat Telegram", key="telegram_discover", use_container_width=True):
            try:
                updates = _telegram("getUpdates", {"timeout": 0, "limit": 25}).get("result", [])
                ids = sorted({
                    int(item.get("message", {}).get("chat", {}).get("id"))
                    for item in updates if item.get("message", {}).get("chat", {}).get("type") == "private"
                })
                if ids:
                    st.info("IDs detectados: " + ", ".join(str(i) for i in ids)
                            + ". Configure somente o seu em TELEGRAM_CHAT_ID.")
                else:
                    st.warning("Nenhum chat identificado. Envie uma nova mensagem ao bot e tente novamente.")
            except Exception as exc:
                st.error(str(exc))
        return
    state = _state()
    st.caption(f"Roteiro {_SCRIPT} · próxima linha {state['index'] + 1}")
    if st.button("Telegram — Chamar", key="telegram_call", use_container_width=True,
                 disabled=bool(state["history"])):
        try:
            _send_line(_rows(), state, _allowed_chat(), model)
            st.success("Mensagem enviada ao Telegram.")
        except Exception as exc:
            st.error(str(exc))
    if st.button("Verificar respostas", key="telegram_check", use_container_width=True):
        try:
            chat_id = _allowed_chat()
            data = _telegram("getUpdates", {
                "offset": state["offset"], "timeout": 0, "limit": 50,
            }).get("result", [])
            pending = [
                x for x in data
                if x.get("message", {}).get("chat", {}).get("id") == chat_id
                and x.get("message", {}).get("text")
                and not str(x["message"]["text"]).startswith("/")
                and int(x["message"].get("message_id", 0)) > state["last_message_id"]
            ]
            if not state["history"]:
                st.info("Primeiro clique em Telegram — Chamar.")
            elif pending:
                # Confirme apenas os updates efetivamente processados.
                event = pending[0]
                _send_line(_rows(), state, chat_id, model, str(event["message"]["text"]))
                state["offset"] = int(event["update_id"]) + 1
                st.success("Resposta recebida e interpretada pela Mary.")
            else:
                if data:
                    state["offset"] = max(int(x["update_id"]) for x in data) + 1
                st.info("Nenhuma nova resposta do chat autorizado.")
        except Exception as exc:
            st.error(str(exc))
    if st.button("Reiniciar piloto Telegram", key="telegram_reset", use_container_width=True):
        st.session_state.pop("_mary_telegram_pilot", None)
        st.info("Estado local reiniciado; mensagens já enviadas não são apagadas.")
