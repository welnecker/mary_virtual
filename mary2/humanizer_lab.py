"""Laboratório A/B do Redator Mary vs. Humanizer (execução independente)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import gspread
import streamlit as st

from direct_script import build_direct_writer_prompt, load_direct_script_catalog, load_direct_script_rows
from openrouter_client import chat

SHEET_NAME = "HUMANIZER"
COLUMNS = [
    "timestamp", "test_id", "capitulo", "linha", "modelo", "fala_usuario",
    "contexto", "fala_guia", "original", "humanizer", "preferida",
    "naturalidade_original", "naturalidade_humanizer", "fidelidade_roteiro", "observacoes",
]

# Regras experimentais selecionadas e adaptadas de blader/humanizer (MIT).
# Origem: https://github.com/blader/humanizer
HUMANIZER_MARY = """
HUMANIZAÇÃO DE DIÁLOGO — MARY (camada de estilo, subordinada ao roteiro)
- Responda primeiro ao sentido concreto da última fala/pergunta do interlocutor.
- Evite repetir a mesma informação, frase, reação ou justificativa da resposta anterior.
- Evite frases genéricas de assistente, explicações didáticas, conclusões e dramaticidade decorativa.
- Varie comprimento e cadência de frases; permita coloquialidade, pausas e imperfeições naturais.
- Preserve o temperamento pedido na linha: não torne Mary sempre gentil, engraçada ou provocante.
- Não acrescente fatos, ações físicas, sentimentos ou revelações fora do que a linha autoriza.
- Preserve exatamente o contrato de saída definido pelo Redator.
- Não imite artificialmente informalidade usando gírias, reticências ou risadas em excesso.
"""

st.set_page_config(page_title="Mary | Laboratório Humanizer", page_icon="🧪", layout="wide")
st.title("🧪 Mary — Laboratório Humanizer")
st.caption("Teste isolado: não avança capítulos, não modifica checkpoints ou INTERACTIONS.")

def _credentials():
    raw = (st.secrets.get("GOOGLE_CREDS_JSON")
           or st.secrets.get("gcp_service_account")
           or st.secrets.get("GOOGLE_SERVICE_ACCOUNT"))
    if not raw:
        raise ValueError("Credenciais do Google Sheets não configuradas neste app.")
    obj = json.loads(raw) if isinstance(raw, str) else dict(raw)
    if isinstance(obj.get("private_key"), str):
        obj["private_key"] = obj["private_key"].replace("\\n", "\n")
    return obj

@st.cache_data(ttl=120, show_spinner=False)
def _catalog():
    return load_direct_script_catalog(
        service_account_info=_credentials(),
        spreadsheet_id=str(st.secrets.get("MARY_SHEETS_ID", "")),
        worksheet_name="MINHA_SUGESTAO",
    )

@st.cache_data(ttl=120, show_spinner=False)
def _rows(script_name):
    return load_direct_script_rows(
        service_account_info=_credentials(),
        spreadsheet_id=str(st.secrets.get("MARY_SHEETS_ID", "")),
        worksheet_name="MINHA_SUGESTAO",
        script_name=script_name,
    )

def _write_review(data):
    book = gspread.service_account_from_dict(_credentials()).open_by_key(
        str(st.secrets.get("MARY_SHEETS_ID", ""))
    )
    tab = book.worksheet(SHEET_NAME)  # aba criada antecipadamente; não alterar schema existente
    tab.append_row([str(data.get(k, "")) for k in COLUMNS], value_input_option="RAW")

try:
    key = str(st.secrets.get("OPENROUTER_API_KEY", "")).strip()
    if not key:
        st.error("Configure OPENROUTER_API_KEY nos Secrets deste laboratório.")
        st.stop()
    catalog = _catalog()
    options = [str(r.get("script_id", "")) for r in catalog if r.get("script_id")]
    if not options:
        st.error("Nenhum capítulo identificado em MINHA_SUGESTAO.")
        st.stop()
    chapter = st.selectbox("Capítulo", options)
    rows = _rows(chapter)
    if not rows:
        st.warning("Sem linhas executáveis neste capítulo.")
        st.stop()
    line_index = st.selectbox("Linha do roteiro", range(len(rows)), format_func=lambda i:
        str(rows[i].get("order")) + " — " + str(rows[i].get("speech_guide", ""))[:100])
    row = rows[line_index]
except Exception as exc:
    st.error(f"Falha ao carregar roteiro: {exc}")
    st.stop()

model = st.text_input("Modelo OpenRouter (o mesmo nas duas versões)", value="google/gemini-3-flash-preview")
temperature = st.slider("Temperatura (mesma nas duas versões)", 0.0, 1.5, 0.7, 0.05)
user_text = st.text_area("Última fala do interlocutor", height=90)
recent = st.text_area("Contexto conversacional anterior (opcional; texto manual)", height=140,
    help="Copie algumas falas anteriores. O laboratório não consulta nem altera INTERACTIONS.")
interpretation = st.text_area("Interpretação / obrigação direta (opcional)", height=70,
    help="Informe qual pergunta ou ação Mary deve responder. Não executa a Compreensão.")
st.info("Ambas as versões usam o mesmo roteiro e contexto. Este é um teste do Redator; não reproduz automaticamente a Compreensão e o Diretor.")
if st.button("Gerar A e B", type="primary"):
    if not (user_text.strip() or row.get("interaction_mode", "").lower() in {"automatico", "automático", "automatic"}):
        st.warning("Informe uma fala para linhas interativas.")
    else:
        try:
            recent_messages = [{"role":"assistant","content": recent}] if recent.strip() else []
            parsed_interpretation = {
                "user_obligation": {"exists": bool(interpretation.strip()), "requirement": interpretation},
                "move": interpretation,
            }
            prompt = build_direct_writer_prompt(
                row=row, recent_messages=recent_messages,
                user_text=user_text, interpretation=parsed_interpretation,
                previous_mary_text=recent, active_interlocutor="PERSONAGEM_DA_CENA",
            )
            common = {"api_key": key, "model": model, "temperature": temperature, "max_tokens": 1000}
            a = chat(messages=[{"role":"user", "content":prompt}], **common)
            b = chat(messages=[{"role":"user", "content":prompt + "\n\n" + HUMANIZER_MARY}], **common)
            st.session_state["humanizer_pair"] = {
                "timestamp":datetime.now(timezone.utc).isoformat(),
                "test_id":str(uuid4()), "capitulo":chapter,
                "linha":str(row.get("order")), "modelo":model, "fala_usuario":user_text,
                "contexto":recent, "fala_guia":str(row.get("speech_guide","")),
                "original":a, "humanizer":b,
            }
        except Exception as exc:
            st.error(f"Falha durante a geração: {exc}")

pair = st.session_state.get("humanizer_pair")
if pair:
    st.subheader("Comparação")
    st.caption("Caso " + pair["test_id"] + " · " + pair["capitulo"] + " · linha " + pair["linha"])
    left,right = st.columns(2)
    with left:
        st.markdown("#### A — Mary original")
        st.text_area("Resposta original", pair["original"], height=320, disabled=True)
    with right:
        st.markdown("#### B — Mary + Humanizer")
        st.text_area("Resposta humanizada", pair["humanizer"], height=320, disabled=True)
    with st.form("review", clear_on_submit=False):
        preferida = st.radio("Qual resposta você prefere?", ["A", "B", "Empate"], horizontal=True)
        a_score = st.slider("Naturalidade A", 1, 5, 3)
        b_score = st.slider("Naturalidade B", 1, 5, 3)
        faithful = st.selectbox("Ambas respeitaram o roteiro?", ["Não avaliado", "Sim", "Somente A", "Somente B", "Nenhuma"])
        notes = st.text_area("Observações autorais")
        submitted = st.form_submit_button("Salvar avaliação em HUMANIZER")
    if submitted:
        try:
            reviewed = dict(pair)
            reviewed.update(preferida=preferida, naturalidade_original=a_score,
                            naturalidade_humanizer=b_score, fidelidade_roteiro=faithful,
                            observacoes=notes)
            _write_review(reviewed)
            st.success("Avaliação registrada na aba HUMANIZER.")
            st.session_state.pop("humanizer_pair", None)
        except Exception as exc:
            st.error(f"Não foi possível salvar a avaliação: {exc}")
st.caption("Regras adaptadas do projeto blader/humanizer (licença MIT). Este laboratório não altera a aplicação principal.")
