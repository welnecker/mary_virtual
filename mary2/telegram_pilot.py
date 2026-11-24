"""Piloto Telegram isolado do estado narrativo principal.

Sem worker contínuo: fragmento Streamlit consulta getUpdates enquanto a sessão está aberta.
Nunca registra token ou mensagens em logs. Não usar em produção multiusuário sem
persistência transacional de offset/estado e um serviço receptor durável.
"""
from __future__ import annotations

from copy import deepcopy
import re

import json
from typing import Any
import requests
import streamlit as st

from direct_script import load_direct_script_rows, build_direct_writer_prompt, hurt_loop_max_interactions
from direct_semantic_director import validate_direct_semantic_turn
from openrouter_client import chat
from output_filter import parse_mary_components, sanitize_mary_output, looks_like_action_narration

_TIMEOUT = 15
_SCRIPT = "Celular1"
_TAB = "MARY_CELULAR"
_RECEIVED_TAB = "MARY_CELULAR_RECEBIDO"
_RECEIVED_SCRIPT = "Recebido1"


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


def _rows(script_name: str = _SCRIPT, worksheet_name: str = _TAB) -> list[dict]:
    creds, sheet_id = _credentials()
    rows = load_direct_script_rows(
        service_account_info=creds,
        spreadsheet_id=sheet_id,
        worksheet_name=worksheet_name,
        script_name=script_name,
    )
    if not rows:
        raise RuntimeError(
            f"Nenhuma linha executável de ROTEIRO={script_name} na aba {worksheet_name}."
        )
    return rows


def _state() -> dict:
    if "_mary_telegram_pilot" not in st.session_state:
        st.session_state["_mary_telegram_pilot"] = {
            "index": 0, "history": [], "offset": 0, "last_message_id": 0,
            "status": "idle", "script_name": "", "trigger_id": "",
            "outcome": "", "worksheet_name": _TAB, "incoming": False,
            "loop": {"active": False, "attempts": 0}, "initialized": False,
        }
    return st.session_state["_mary_telegram_pilot"]


def _allowed_chat() -> int:
    value = _secret("TELEGRAM_CHAT_ID")
    if not value or not value.lstrip("-").isdigit():
        raise RuntimeError("Configure TELEGRAM_CHAT_ID nos Secrets após identificar o chat.")
    return int(value)


def _classify_final_reply(user_text: str, history: list[dict], model: str) -> str:
    """Somente aceite inequívoco confirma o encontro; a dúvida reprova."""
    if not user_text.strip():
        return "RECUO"
    context = "\n".join(
        f"{item.get('role', '')}: {item.get('content', '')}"
        for item in history[-4:]
    )
    result = chat(
        api_key=_secret("OPENROUTER_API_KEY"), model=model,
        messages=[
            {"role": "system", "content": (
                "Classifique EXCLUSIVAMENTE a última mensagem de Donisete sobre o "
                "encontro proposto por Mary. Responda uma palavra: ACEITE ou RECUO. "
                "ACEITE somente quando ele aceita explicitamente encontrar Mary. "
                "RECUO para recusa, hesitação, ironia, mudança de assunto ou resposta ambígua. "
                "Nunca deduza aceite da intenção de Mary ou de mensagens anteriores."
            )},
            {"role": "user", "content": (
                "Conversa recente:\n" + context +
                "\n\nÚltima resposta de Donisete:\n" + user_text
            )},
        ],
        temperature=0, call_type="TELEGRAM_OUTCOME",
    )
    normalized = str(result or "").strip().upper()
    if normalized not in {"ACEITE", "RECUO"}:
        raise RuntimeError("Classificação inconclusiva; a chamada não avançou.")
    return normalized


def _generate(
    row: dict, rows: list[dict], history: list[dict],
    user_text: str, model: str, outcome: str = "",
) -> str:
    active_row = dict(row)
    if outcome:
        # Respeita os dois ramos autorais da própria planilha; não inventa uma
        # missão nova para o roteiro quando a decisão já está escrita na linha.
        guide = str(row.get("speech_guide", "") or "")
        label = "ACEITE:" if outcome == "ACEITE" else "RECUO:"
        other = "RECUO:" if outcome == "ACEITE" else "ACEITE:"
        pattern = re.compile(re.escape(label) + r"\s*(.*?)(?=" + re.escape(other) + r"|\Z)", re.I | re.S)
        match = pattern.search(guide)
        if not match:
            raise RuntimeError("A linha final não descreve o ramo autoral selecionado.")
        fragment = match.group(1).strip()
        fragment = re.sub(r"\n+\s*Não antecipar.*$", "", fragment, flags=re.I | re.S)
        active_row["speech_guide"] = (
            "Interpretar: Mary responde à mensagem real de Donisete. "
            + fragment + " Não antecipar acontecimentos posteriores."
        )
    prompt = build_direct_writer_prompt(
        row=active_row, all_rows=rows, recent_messages=history[-10:],
        user_text=user_text, active_interlocutor="Donisete",
        character_name="Donisete",
    )
    prompt += (
        "\n\nCANAL TELEGRAM: somente a fala verbal de Mary será enviada. "
        "Escreva [FALA] como mensagem natural, concisa, sem narração de gestos, "
        "digitação, celular ou aplicativo. Não antecipe linhas futuras; "
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
        row=active_row, interpretation={}, mary_text=speech,
        mary_thought=parts.get("thought", ""),
        mary_action=parts.get("action", ""),
        user_text=user_text, user_scene_direction="",
        line_dialogue=[],
    )
    if not validation.get("fulfilled", False) or validation.get("parse_error"):
        raise RuntimeError("Diretor semântico não aprovou a mensagem; nada foi enviado.")
    return speech


def _emotional_assessment(
    row: dict, loop_state: dict, user_text: str, history: list[dict],
    model: str,
) -> dict:
    """Mesma interpretação dos critérios autorais do motor direto; sem gatilhos fixos."""
    author_loop = dict(row.get("_emotional_loop_row") or {})
    if not user_text.strip() or not author_loop:
        return {}
    negative = str(loop_state.get("negative_rule") or row.get("negative_prompt") or "")
    hurt = str(loop_state.get("hurt_style") or row.get("hurt_style") or "")
    loop_guide = str(author_loop.get("speech_guide") or "")
    if not (negative or hurt):
        return {}
    recent = "\n".join(
        str(item.get("role", "")) + ": " + str(item.get("content", ""))
        for item in history[-6:]
    )
    raw = chat(
        api_key=_secret("OPENROUTER_API_KEY"),
        model=_secret("MARY_DIRECTOR_MODEL") or model,
        messages=[
            {"role": "system", "content": (
                "Você é o mesmo classificador de fatos emocionais do roteiro direto "
                "Mary Core 2. Compare apenas a fala atual com as condições autorais "
                "de PROMPT NEGATIVO, ORGULHO FERIDO e LOOP. "
                "Responda APENAS JSON com booleanos violation, frustration, "
                "repair_attempt, forgiven, rejected e texto repair_evidence. "
                "violation=true somente se afrontar limites explícitos; "
                "frustration=true somente se contrariar expectativa concreta autoral. "
                "Não trate humor ou recusa cordial como ofensa automática. "
                "rejected exige rejeição pessoal inequívoca. "
                "forgiven=true somente após evidência concreta de reparação "
                "relacionada ao conflito, citada literalmente em repair_evidence. "
                "Não force perdão nem invente fatos ou condições."
            )},
            {"role": "user", "content": (
                "PROMPT NEGATIVO DE ORIGEM: " + negative +
                "\nORGULHO FERIDO DE ORIGEM: " + hurt +
                "\nFALA-GUIA DO LOOP: " + loop_guide +
                "\nCONTEXTO RECENTE:\n" + recent[-3000:] +
                "\nLOOP ATIVO: " + str(bool(loop_state.get("active"))) +
                "\nÚLTIMA MENSAGEM DE DONISETE: " + user_text
            )},
        ],
        temperature=0, call_type="TELEGRAM_EMOTION",
    )
    match = re.search(r"\{[\s\S]*\}", str(raw or ""))
    if not match:
        raise RuntimeError("Diretor emocional sem JSON. Mensagem ainda pendente.")
    try:
        parsed = json.loads(match.group(0))
    except ValueError as exc:
        raise RuntimeError("Diretor emocional retornou JSON inválido.") from exc
    return parsed if isinstance(parsed, dict) else {}


def _prepare_emotional_row(
    row: dict, state: dict, user_text: str, model: str
) -> tuple[dict, dict, bool]:
    """Decide sobre LOOP antes de enviar; a atualização só vale após sendMessage."""
    loop = deepcopy(state.get("loop") or {"active": False, "attempts": 0})
    guide = dict(row.get("_emotional_loop_row") or {})
    if not guide:
        return row, loop, False
    assessment = _emotional_assessment(
        row, loop, user_text, list(state.get("history", [])), model
    )
    repairing = (
        bool(loop.get("active"))
        and assessment.get("forgiven") is True
        and isinstance(assessment.get("repair_evidence"), str)
        and len(assessment["repair_evidence"].strip()) >= 5
        and assessment["repair_evidence"].strip().casefold() in user_text.casefold()
    )
    if repairing:
        loop = {"active": False, "attempts": 0}
        return row, loop, False
    if not loop.get("active") and any(
        assessment.get(key) is True for key in ("violation", "frustration", "rejected")
    ):
        loop = {
            "active": True, "attempts": 0,
            "max_attempts": hurt_loop_max_interactions(guide),
            "negative_rule": str(row.get("negative_prompt") or ""),
            "hurt_style": str(row.get("hurt_style") or ""),
            "origin_order": int(row.get("order") or 0),
        }
    if not loop.get("active"):
        return row, loop, False
    max_attempts = max(1, int(loop.get("max_attempts", 3) or 3))
    loop["attempts"] = min(max_attempts, int(loop.get("attempts", 0)) + 1)
    resolved = dict(guide)
    resolved["permanent_memory"] = str(row.get("permanent_memory") or "")
    resolved["physical_memory"] = str(row.get("physical_memory") or "")
    resolved["instant_memory"] = (
        str(guide.get("instant_memory") or "") or str(row.get("instant_memory") or "")
    )
    resolved["negative_prompt"] = str(guide.get("negative_prompt") or "") or str(loop["negative_rule"])
    resolved["hurt_style"] = str(guide.get("hurt_style") or "") or str(loop["hurt_style"])
    resolved["style"] = (
        str(resolved.get("style") or "") + " ORGULHO FERIDO AUTORAL: "
        + resolved["hurt_style"]
    ).strip()
    return resolved, loop, loop["attempts"] >= max_attempts


def _send_emotional_reply(
    row: dict, rows: list[dict], state: dict, chat_id: int,
    model: str, user_text: str,
) -> bool:
    emotional_row, new_loop, exhausted = _prepare_emotional_row(
        row, state, user_text, model
    )
    if not new_loop.get("active"):
        state["loop"] = new_loop
        return False
    speech = _generate(emotional_row, rows, list(state["history"]), user_text, model)
    reply = _telegram("sendMessage", {"chat_id": chat_id, "text": speech})
    state["last_message_id"] = int(reply.get("result", {}).get("message_id", 0) or 0)
    state["history"].append({"role": "user", "content": user_text})
    state["history"].append({"role": "assistant", "content": speech})
    state["loop"] = new_loop
    if exhausted:
        state["status"] = "rejected" if not state.get("incoming") else "finished"
        state["outcome"] = "LOOP_EXHAUSTED"
    return True


def _send_line(
    rows: list[dict], state: dict, chat_id: int, model: str,
    user_text: str = "",
) -> None:
    index = int(state["index"])
    if index >= len(rows):
        raise RuntimeError("O roteiro do celular já terminou.")
    row = rows[index]
    is_final = index == len(rows) - 1
    outcome = (
        _classify_final_reply(user_text, list(state["history"]), model)
        if is_final and "ACEITE:" in str(row.get("speech_guide", "")).upper() else ""
    )
    speech = _generate(row, rows, list(state["history"]), user_text, model, outcome)
    result = _telegram("sendMessage", {"chat_id": chat_id, "text": speech})
    msg = result.get("result", {})
    state["last_message_id"] = int(msg.get("message_id", 0) or 0)
    if user_text:
        state["history"].append({"role": "user", "content": user_text})
    state["history"].append({"role": "assistant", "content": speech})
    state["index"] += 1  # Envio efetivo e aprovado precede avanço.
    if is_final:
        state["outcome"] = outcome
        if state.get("incoming"):
            state["status"] = "finished"
        else:
            state["status"] = "approved" if outcome == "ACEITE" else "rejected"


def telegram_call_status(trigger_id: str) -> str:
    """Consulta o estado sem criar uma chamada nem enviar mensagens."""
    state = _state()
    if state.get("trigger_id") != trigger_id:
        return "idle"
    return str(state.get("status", "idle"))


def _latest_offset() -> int:
    updates = _telegram("getUpdates", {"timeout": 0, "limit": 100}).get("result", [])
    return max((int(event["update_id"]) for event in updates), default=-1) + 1


def ensure_telegram_call(trigger_id: str, script_name: str, model: str) -> str:
    """Inicia uma vez após a publicação da linha-gatilho automática."""
    if not trigger_id or not script_name:
        raise ValueError("Identificador da chamada e roteiro são obrigatórios.")
    state = _state()
    if state.get("trigger_id") == trigger_id and state.get("status") != "idle":
        return str(state["status"])
    if state.get("status") in {"active", "rejected"} and state.get("trigger_id") != trigger_id:
        raise RuntimeError("Há outra chamada pendente. Conclua-a antes de iniciar outra.")
    rows = _rows(script_name)
    chat_id = _allowed_chat()
    offset = _latest_offset()  # Descarta respostas anteriores à chamada.
    state.clear()
    state.update({
        "index": 0, "history": [], "offset": offset, "last_message_id": 0,
        "status": "starting", "script_name": script_name, "trigger_id": trigger_id,
        "outcome": "", "worksheet_name": _TAB, "incoming": False,
        "loop": {"active": False, "attempts": 0}, "initialized": True,
    })
    try:
        _send_line(rows, state, chat_id, model)
    except Exception:
        # Uma falha de rede após envio pode ser ambígua: não duplicar automaticamente.
        state["status"] = "start_error"
        raise
    state["status"] = "active"
    return "active"


def _restart_call(model: str) -> None:
    state = _state()
    trigger_id = str(state.get("trigger_id", "") or "")
    script_name = str(state.get("script_name", "") or "")
    if not trigger_id or not script_name:
        raise RuntimeError("Nenhum roteiro vinculado para reiniciar.")
    # Recomeço narrativo, sem alterar o cursor de MINHA_SUGESTAO.
    state["status"] = "idle"
    ensure_telegram_call(trigger_id, script_name, model)


def _check_reply(model: str) -> str:
    state = _state()
    if state.get("status") != "active":
        return "Aguardando início de chamada."
    chat_id = _allowed_chat()
    data = _telegram("getUpdates", {
        "offset": int(state["offset"]), "timeout": 0, "limit": 50,
    }).get("result", [])
    pending = [
        event for event in data
        if event.get("message", {}).get("chat", {}).get("id") == chat_id
        and event.get("message", {}).get("text")
        and not str(event["message"]["text"]).startswith("/")
        and int(event["message"].get("message_id", 0)) > state["last_message_id"]
    ]
    if not pending:
        if data:
            state["offset"] = max(int(x["update_id"]) for x in data) + 1
        return "Nenhuma mensagem nova do chat autorizado."
    event = pending[0]
    _send_line(
        _rows(str(state["script_name"]), str(state.get("worksheet_name") or _TAB)), state, chat_id, model,
        str(event["message"]["text"]),
    )
    state["offset"] = int(event["update_id"]) + 1
    return "Resposta recebida e interpretada pela Mary."


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
                    for item in updates
                    if item.get("message", {}).get("chat", {}).get("type") == "private"
                })
                if ids:
                    st.info("IDs detectados: " + ", ".join(str(i) for i in ids)
                            + ". Configure somente o seu em TELEGRAM_CHAT_ID.")
                else:
                    st.warning("Nenhum chat identificado. Envie nova mensagem e tente novamente.")
            except Exception as exc:
                st.error(str(exc))
        return

    state = _state()
    status = str(state.get("status", "idle"))
    script_name = str(state.get("script_name") or _SCRIPT)
    st.caption(f"Roteiro {script_name} · próxima linha {int(state['index']) + 1}")
    if status == "idle":
        if st.button("Telegram — Chamar (teste manual)", key="telegram_call", use_container_width=True):
            try:
                ensure_telegram_call("manual_pilot", _SCRIPT, model)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    elif status == "active":
        st.info("Conversa em andamento. Respostas automáticas enquanto o Streamlit estiver aberto.")
        _telegram_reply_monitor(model)
    elif status == "approved":
        st.success("Encontro confirmado. Chamada aprovada.")
    elif status == "rejected":
        st.warning("Conversa encerrada sem confirmação. Roteiro principal bloqueado.")
        if st.button("Reiniciar Celular", key="telegram_retry", use_container_width=True):
            try:
                _restart_call(model)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    elif status == "start_error":
        st.error("Início da chamada inconclusivo. Verifique o Telegram antes de reiniciar.")
        if st.button("Reiniciar chamada", key="telegram_recover", use_container_width=True):
            try:
                _restart_call(model)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


@st.fragment(run_every="3s")
def _telegram_reply_monitor(model: str) -> None:
    """Polling limitado à sessão aberta; não é um worker de Telegram."""
    state = _state()
    if state.get("status") != "active":
        return
    st.caption("Aguardando resposta pelo Telegram · verificação automática a cada 3 s")
    if st.button("Verificar agora", key="telegram_check", use_container_width=True):
        pass  # A chamada abaixo ocorre também no clique, sem duplicar a consulta.
    try:
        notice = _check_reply(model)
        if _state().get("status") == "approved":
            st.rerun()  # Libera a progressão principal após conclusão aprovada.
        if _state().get("status") == "rejected":
            st.rerun()  # Exibe reinício do roteiro sem liberar a cena principal.
        if notice.startswith("Resposta recebida"):
            st.success(notice)
    except Exception as exc:
        # O erro não altera o offset nem o cursor; a mensagem pode ser reprocessada.
        # A interface permite verificar a causa sem expor o token.
        st.error(f"Falha ao processar resposta do Telegram: {exc}")
