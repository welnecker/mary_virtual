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

from direct_script import (
    load_direct_script_rows, build_direct_writer_prompt, hurt_loop_max_interactions,
    ensure_direct_state, register_direct_user_reply, current_direct_row,
    mark_direct_line_emitted,
)
from direct_semantic_director import validate_direct_semantic_turn
from user_understanding_audit import analyze_user_understanding
from openrouter_client import chat
from output_filter import parse_mary_components, sanitize_mary_output, looks_like_action_narration

_TIMEOUT = 15
_SCRIPT = "Celular1"
_TAB = "MARY_CELULAR"
_RECEIVED_TAB = "MARY_CELULAR_RECEBIDO"
_RECEIVED_SCRIPT = "Recebido1"

_TARGET_RECEIVED = re.compile(r"celular_rec([1-9]\d*)", re.I)
_TARGET_OUTGOING = re.compile(r"celular([1-9]\d*)", re.I)


def resolve_telegram_script(marker: str) -> tuple[str, str, bool]:
    """Traduz exclusivamente a coluna TELEGRAM do roteiro mãe."""
    marker = str(marker or "").strip()
    incoming_match = _TARGET_RECEIVED.fullmatch(marker)
    if incoming_match:
        return _RECEIVED_TAB, f"Recebido{incoming_match.group(1)}", True
    outgoing_match = _TARGET_OUTGOING.fullmatch(marker)
    if outgoing_match:
        return _TAB, f"Celular{outgoing_match.group(1)}", False
    raise ValueError(f"Marcador TELEGRAM desconhecido: {marker!r}")


# Identidade definida pela cena principal; nunca presumir o nome do usuário.
_NAME = r"([A-ZÀ-Ý][A-Za-zÀ-ÿ'’-]{1,39}(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'’-]{1,39})?)"
_CALL_PATTERNS = [
    re.compile(r"\b(?:ligar|telefonar|chamar|mandar\s+(?:mensagem|um\s+recado))\s+(?:para|pro|pra|ao|à)\s+" + _NAME, re.I),
    re.compile(r"\b" + _NAME + r"\s+(?:tá|está|anda)\s+(?:me\s+)?(?:ligando|chamando|mandando\s+mensagem)", re.I),
    re.compile(r"\b(?:chamada|ligação|mensagem)\s+(?:do|da|de)\s+" + _NAME, re.I),
    re.compile(r"\b(?:é|eh)\s+(?:o|a)?\s*" + _NAME + r"\s+(?:me\s+)?(?:ligando|chamando|mandando)", re.I),
]


def extract_call_interlocutor(row: dict, mary_speech: str = "") -> str:
    """Extrai a identidade declarada quando Mary pega/atende o celular."""
    fields = [
        str(mary_speech or ""),
        str((row or {}).get("speech_guide") or ""),
        str((row or {}).get("action_guide") or ""),
        str((row or {}).get("interlocutor_direction") or ""),
    ]
    for field in fields:
        for pattern in _CALL_PATTERNS:
            found = pattern.search(field)
            if found:
                name = found.group(1).strip(" .,!?:;-")
                if name and name.casefold() not in {"mary", "telegram", "celular"}:
                    return name
    return ""



def _secret(name: str) -> str:
    try:
        return str(st.secrets.get(name, "") or "").strip()
    except Exception:
        return ""


def _telegram(method: str, payload: dict | None = None) -> dict:
    token = _secret("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Configure TELEGRAM_BOT_TOKEN nos Secrets.")
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/{method}",
            json=payload or {}, timeout=_TIMEOUT,
        )
    except requests.RequestException as exc:
        # Exceções de requests podem incluir a URL com o TOKEN do bot.
        raise RuntimeError(
            f"Falha de rede do Telegram em {method} ({type(exc).__name__})."
        ) from None
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
            "interlocutor": "",
        }
    return st.session_state["_mary_telegram_pilot"]


def _allowed_chat() -> int:
    value = _secret("TELEGRAM_CHAT_ID")
    if not value or not value.lstrip("-").isdigit():
        raise RuntimeError("Configure TELEGRAM_CHAT_ID nos Secrets após identificar o chat.")
    return int(value)


def _classify_final_reply(user_text: str, history: list[dict], model: str, interlocutor: str = "interlocutor") -> str:
    """Confere o acordo estabelecido durante a chamada, não só a despedida."""
    if not user_text.strip():
        raise RuntimeError("Mensagem final ausente; não é possível concluir a chamada.")
    # Uma confirmação pode ocorrer na resposta à linha 3 ou 4. Na linha 5,
    # o interlocutor pode apenas se despedir. A decisão deve respeitar
    # todo o diálogo efetivo e eventuais revogações posteriores.
    context = "\n".join(
        ("MARY: " if item.get("role") == "assistant" else "DONISETE: ")
        + str(item.get("content", ""))
        for item in history[-20:]
        if isinstance(item, dict) and str(item.get("content", "")).strip()
    )
    result = chat(
        api_key=_secret("OPENROUTER_API_KEY"), model=model,
        messages=[
            {"role": "system", "content": (
                "Você avalia o RESULTADO ATUAL do convite para encontro no deck "
                "da conversa inteira entre Mary e o interlocutor indicado, na ordem cronológica. "
                "Retorne exclusivamente ACEITE ou RECUO, sem explicações. "
                "ACEITE se o interlocutor aceitou claramente o encontro em QUALQUER "
                "mensagem anterior ou na última, e não retirou depois esse aceite. "
                "A confirmação de Mary sobre local e horário reforça que houve acordo, "
                "mas não substitui um aceite real do interlocutor. "
                "Uma despedida posterior como 'tchau', 'até logo' ou 'tá bom' "
                "NÃO cancela um encontro previamente confirmado. "
                "RECUO se não houve aceite inequívoco, se há apenas hesitação, "
                "ou se o interlocutor REVOGOU explicitamente a confirmação após aceitá-la. "
                "Uma recusa ANTERIOR superada por aceite claro posterior não é recuo. "
                "Não confunda concordar com outro assunto com aceitar o encontro. "
                "Não invente consentimento: exija evidência literal na fala do interlocutor."
            )},
            {"role": "user", "content": (
                "INTERLOCUTOR DEFINIDO PELA CENA: " + interlocutor + "\nDIÁLOGO EM ORDEM CRONOLÓGICA:\n" + context +
                "\n\nÚLTIMA MENSAGEM DO INTERLOCUTOR:\n" + user_text +
                "\n\nQual é o estado FINAL do acordo sobre o encontro?"
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
    incoming: bool = False, interlocutor: str = "",
) -> str:
    active_row = dict(row)
    interlocutor = str(interlocutor or "interlocutor").strip()
    # Na primeira linha recebida, o usuário JÁ falou pelo Telegram.
    # PROSSEGUIR=bloqueado significa iniciativa de Mary só na chamada
    # originada pelo Streamlit. Não suprima a mensagem real do destinatário.
    if incoming and user_text.strip() and not history:
        active_row["interaction_mode"] = ""
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
            "Interpretar: Mary responde à mensagem real de " + interlocutor + ". "
            + fragment + " Não antecipar acontecimentos posteriores."
        )
    previous_mary = next(
        (str(item.get("content") or "") for item in reversed(history)
         if item.get("role") == "assistant"), ""
    )
    understanding = {}
    if user_text.strip():
        understanding = analyze_user_understanding(
            api_key=_secret("OPENROUTER_API_KEY"),
            model=_secret("MARY_DIRECTOR_MODEL") or model,
            fallback_model=_secret("MARY_FALLBACK_MODEL") or None,
            user_text=user_text, user_scene_direction="",
            previous_mary_text=previous_mary,
            recent_messages=history[-10:],
            active_interlocutor=interlocutor,
            instant_memory=str(active_row.get("instant_memory") or ""),
            permanent_memory=str(active_row.get("permanent_memory") or ""),
            physical_memory=str(active_row.get("physical_memory") or ""),
            initial_description=str(active_row.get("initial_description") or ""),
            revelation_policy=str(active_row.get("revelation_policy") or ""),
        )
    prompt = build_direct_writer_prompt(
        row=active_row, all_rows=rows, recent_messages=history[-10:],
        user_text=user_text, active_interlocutor=interlocutor,
        character_name=interlocutor, interpretation=understanding,
        previous_mary_text=previous_mary,
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
        row=active_row, interpretation=understanding, mary_text=speech,
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
    model: str, interlocutor: str = "interlocutor",
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
                "\nINTERLOCUTOR DA CHAMADA: " + interlocutor + "\nÚLTIMA MENSAGEM: " + user_text
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
        row, loop, user_text, list(state.get("history", [])), model,
        str(state.get("interlocutor") or "interlocutor"),
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
    # Cada tentativa interpreta somente a missão autoral daquele estágio.
    # O Diretor não deve exigir os três acontecimentos do LOOP em um turno.
    raw_loop_guide = str(guide.get("speech_guide") or "")
    loop_sentences = re.split(r"(?<=[.!?])\s+", raw_loop_guide)
    markers = {
        1: r"\b(?:primeir[ao]|1[ªº]|1\.?)\b",
        2: r"\b(?:segund[ao]|2[ªº]|2\.?)\b",
        3: r"\b(?:terceir[ao]|3[ªº]|3\.?)\b",
    }
    step_pattern = markers.get(int(loop["attempts"]))
    step_sentence = next(
        (sentence for sentence in loop_sentences
         if step_pattern and re.search(step_pattern, sentence, re.I)),
        "",
    )
    if step_sentence:
        resolved["speech_guide"] = "Interpretar: " + step_sentence.strip()
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
    speech = _generate(
        emotional_row, rows, list(state["history"]), user_text, model,
        incoming=bool(state.get("incoming")),
        interlocutor=str(state.get("interlocutor") or ""),
    )
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
    # Reusa exatamente o estado de progressão do roteiro direto. O avanço
    # ocorre em cópia; a versão vigente só muda após sendMessage confirmado.
    narrative = {
        "direct_script": deepcopy(state.get("direct_script"))
    }
    direct_state = ensure_direct_state(narrative, rows)
    if user_text and state.get("history"):
        register_direct_user_reply(direct_state, rows, user_text)
    row = current_direct_row(rows, direct_state)
    if not row:
        raise RuntimeError("O roteiro do celular já terminou.")
    index = int(direct_state["index"])
    is_final = index == len(rows) - 1
    outcome = (
        _classify_final_reply(user_text, list(state["history"]), model,
                              str(state.get("interlocutor") or "interlocutor"))
        if is_final and "ACEITE:" in str(row.get("speech_guide", "")).upper()
        else ""
    )
    speech = _generate(
        row, rows, list(state["history"]), user_text, model, outcome,
        incoming=bool(state.get("incoming")),
        interlocutor=str(state.get("interlocutor") or ""),
    )
    result = _telegram("sendMessage", {"chat_id": chat_id, "text": speech})
    mark_direct_line_emitted(direct_state, row, rows)
    state["direct_script"] = deepcopy(direct_state)
    msg = result.get("result", {})
    state["last_message_id"] = int(msg.get("message_id", 0) or 0)
    if user_text:
        state["history"].append({"role": "user", "content": user_text})
    state["history"].append({"role": "assistant", "content": speech})
    # O índice da próxima mensagem é derivado do cursor autoral, e não
    # de uma contagem independente do Telegram.
    state["index"] = int(direct_state["index"])
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


def release_telegram_call(trigger_id: str) -> None:
    """Libera o bot para mensagens espontâneas após o retorno à cena principal."""
    state = _state()
    if state.get("trigger_id") == trigger_id and state.get("status") == "approved":
        state["status"] = "finished"


def recheck_rejected_encounter(model: str) -> str:
    """Reavalia uma conclusão antiga sem reenviar fala nem avançar linha."""
    state = _state()
    if (
        state.get("status") != "rejected"
        or state.get("incoming")
        or state.get("outcome") != "RECUO"
        or len(state.get("history") or []) < 2
        or not bool((state.get("direct_script") or {}).get("completed"))
    ):
        raise RuntimeError("Não há conclusão de encontro válida para reavaliar.")
    history = list(state["history"])
    last_user_index = next(
        (idx for idx in range(len(history) - 1, -1, -1)
         if history[idx].get("role") == "user"), None
    )
    if last_user_index is None:
        raise RuntimeError("Resposta final do interlocutor indisponível.")
    outcome = _classify_final_reply(
        str(history[last_user_index].get("content") or ""),
        history[:last_user_index], model,
    )
    if outcome == "ACEITE":
        state["outcome"] = "ACEITE"
        state["status"] = "approved"
    return outcome


def _latest_offset() -> int:
    # Offset negativo consulta somente a atualização mais recente, evitando
    # reabrir conversas a partir de centenas de updates antigos no servidor.
    updates = _telegram("getUpdates", {
        "offset": -1, "timeout": 0, "limit": 1,
    }).get("result", [])
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


def _start_received(event: dict, model: str) -> None:
    """Uma nova mensagem autorizada inicia o roteiro Recebido1 sem tocar no principal."""
    state = _state()
    if state.get("status") not in {"idle", "finished"}:
        return
    text = str(event.get("message", {}).get("text") or "").strip()
    if not text or (text.startswith("/") and text.lower() != "/mary"):
        return
    # Depois de uma despedida, mensagens tardias pertencem à conversa
    # encerrada. Somente /mary é um gatilho inequívoco de nova chamada.
    if state.get("status") == "finished" and text.lower() != "/mary":
        return
    rows = _rows(_RECEIVED_SCRIPT, _RECEIVED_TAB)
    chat_id = _allowed_chat()
    temporary = {
        "index": 0, "history": [], "offset": int(event["update_id"]) + 1,
        "last_message_id": 0, "status": "starting",
        "script_name": _RECEIVED_SCRIPT,
        "worksheet_name": _RECEIVED_TAB,
        "trigger_id": "received:" + str(event["update_id"]),
        "incoming": True, "loop": {"active": False, "attempts": 0},
        "outcome": "", "initialized": True,
    }
    initial_message = "Oi, Mary." if text.lower() == "/mary" else text
    # Se houve erro do Redator ou Diretor, o offset anterior é preservado;
    # a mensagem pode ser tentada novamente no próximo polling.
    if not _send_emotional_reply(rows[0], rows, temporary, chat_id, model, initial_message):
        _send_line(rows, temporary, chat_id, model, initial_message)
    if temporary["status"] == "starting":
        temporary["status"] = "active"
    state.clear()
    state.update(temporary)


def _check_reply(model: str) -> str:
    state = _state()
    status = str(state.get("status", "idle"))
    if status not in {"active", "idle", "finished"}:
        return "Aguardando conclusão da chamada atual."
    chat_id = _allowed_chat()
    data = _telegram("getUpdates", {
        "offset": int(state.get("offset", 0)), "timeout": 0, "limit": 50,
    }).get("result", [])
    pending = [
        event for event in data
        if event.get("message", {}).get("chat", {}).get("id") == chat_id
        and event.get("message", {}).get("text")
        and int(event["message"].get("message_id", 0)) > int(state.get("last_message_id", 0))
        and (
            not str(event["message"]["text"]).startswith("/")
            or str(event["message"]["text"]).strip().lower() == "/mary"
        )
    ]
    if not pending:
        if data:
            state["offset"] = max(int(x["update_id"]) for x in data) + 1
        return "Nenhuma mensagem nova do chat autorizado."
    event = pending[0]
    if status == "finished" and str(event["message"]["text"]).strip().lower() != "/mary":
        # Consumir a atualização sem responder e sem reiniciar o roteiro.
        # Não tratar uma resposta atrasada como uma nova chamada.
        state["offset"] = int(event["update_id"]) + 1
        return "Roteiro encerrado. Para iniciar nova conversa, envie /mary."
    if status in {"idle", "finished"}:
        _start_received(event, model)
        return "Chamada recebida; Mary respondeu pela linha 1 de Recebido1."
    rows = _rows(
        str(state["script_name"]),
        str(state.get("worksheet_name") or _TAB),
    )
    row = rows[int(state["index"])]
    user_text = str(event["message"]["text"])
    if user_text.strip().lower() == "/mary":
        user_text = "Oi, Mary."
    if not _send_emotional_reply(row, rows, state, chat_id, model, user_text):
        _send_line(rows, state, chat_id, model, user_text)
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
        st.caption("Disponível: uma mensagem sua inicia Recebido1 no Telegram.")
        if st.button("Telegram — Chamar (teste manual)", key="telegram_call", use_container_width=True):
            try:
                ensure_telegram_call("manual_pilot", _SCRIPT, model)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    elif status == "active":
        st.info("Conversa em andamento. Respostas automáticas enquanto o Streamlit estiver aberto.")
    elif status == "finished":
        st.success("Conversa encerrada. Para iniciar outra chamada, envie /mary ao bot.")
    elif status == "approved":
        st.success("Encontro confirmado. Chamada aprovada.")
        if str(state.get("trigger_id")) == "manual_pilot":
            if st.button("Liberar Telegram para chamadas recebidas", key="telegram_manual_release", use_container_width=True):
                release_telegram_call("manual_pilot")
                st.rerun()
    elif status == "rejected":
        st.warning("Conversa encerrada sem confirmação. Roteiro principal bloqueado.")
        if (
            not state.get("incoming")
            and state.get("outcome") == "RECUO"
            and bool((state.get("direct_script") or {}).get("completed"))
        ):
            if st.button("Reavaliar encontro sem reiniciar", key="telegram_recheck", use_container_width=True):
                try:
                    outcome = recheck_rejected_encounter(model)
                    if outcome == "ACEITE":
                        st.rerun()
                    else:
                        st.warning("Não foi encontrado aceite inequívoco na conversa.")
                except Exception as exc:
                    st.error(f"Falha na reavaliação: {exc}")
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
    # Um único monitor para a sessão, tanto na espera quanto durante chamadas.
    if status in {"active", "idle", "finished"}:
        _telegram_reply_monitor(model)


@st.fragment(run_every="3s")
def _telegram_reply_monitor(model: str) -> None:
    """Recebe chamadas e respostas enquanto a sessão Streamlit está conectada."""
    state = _state()
    if state.get("status") not in {"idle", "active", "finished"}:
        return
    # Baseline apenas na primeira execução da sessão: mensagens muito antigas
    # não devem iniciar inesperadamente uma nova história ao implantar a branch.
    if not state.get("initialized"):
        try:
            state["offset"] = _latest_offset()
            state["initialized"] = True
        except Exception as exc:
            st.error(f"Não foi possível inicializar o monitor Telegram: {exc}")
            return
    st.caption("Telegram ativo · consulta automática a cada 3 segundos")
    st.button("Verificar agora", key="telegram_check", use_container_width=True)
    try:
        before = str(state.get("status", "idle"))
        notice = _check_reply(model)
        after = str(_state().get("status", "idle"))
        if before != after:
            st.rerun()
        if notice.startswith(("Resposta recebida", "Chamada recebida")):
            st.success(notice)
    except Exception as exc:
        st.error(f"Falha ao processar mensagem do Telegram: {exc}")
