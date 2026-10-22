"""Laboratório A/B/C do Redator Mary vs. Humanizer (execução independente)."""
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
    "interpretativo", "naturalidade_interpretativo", "vencedor_por_canal",
]

# Regras experimentais selecionadas e adaptadas de blader/humanizer (MIT).
# Origem: https://github.com/blader/humanizer
HUMANIZER_MARY = """
CONTRATO EXPERIMENTAL: AJUSTE EXCLUSIVO DO CANAL [AÇÃO]
Preserve integralmente o comportamento original do Redator em [FALA] e [PENSAMENTO].
Não aplique humanização, redução de intensidade, simplificação ou padronização
ao texto desses dois canais. Siga neles a Fala-guia, o Pensamento-guia, o estilo
e o contexto como faria sem este complemento.

Somente para [AÇÃO]:
- Descrição-guia determina a encenação; não é convite à expansão literária.
- Descreva apenas os gestos e movimentos fisicamente autorizados pela linha.
- Use narração externa, em terceira pessoa (Mary/ela), nunca "eu"/"meus".
- Prefira uma frase objetiva; use no máximo duas frases curtas se necessário.
- Evite metáforas, dramatização ornamental, repetições e minúcias não solicitadas.
- Não invente gestos, expressões faciais, contato, lágrimas ou deslocamentos.
- Se Descrição-guia estiver vazia, não invente [AÇÃO] só para preencher o formato.
- Descrição inicial informa o contexto e não autoriza novas ações.

Não reescreva nem restrinja [FALA] e [PENSAMENTO] com estas regras de [AÇÃO].
Mantenha o formato exigido pelo Redator e os limites autorais de REVELACAO.
"""

# Terceira modalidade: mesma linha e fatos, mas atuação humana interpretativa.
# A iniciativa nova deve permanecer dentro das ações já autorizadas pelo roteiro.
HUMANIZER_INTERPRETATIVO = """
CONTRATO EXPERIMENTAL C — HÍBRIDO
O roteiro e REVELACAO continuam como autoridade. Preserve o acontecimento,
a continuidade e a personalidade indicados pela linha atual.

[AÇÃO] — MESMAS REGRAS DA VERSÃO B, SEM FLEXIBILIZAÇÃO:
- Descrição-guia determina a encenação; não é convite à expansão literária.
- Descreva apenas os gestos e movimentos fisicamente autorizados pela linha.
- Use narração externa, em terceira pessoa (Mary/ela), nunca "eu"/"meus".
- Prefira uma frase objetiva; use no máximo duas frases curtas se necessário.
- Evite metáforas, dramatização ornamental, repetições e minúcias não solicitadas.
- Não invente gestos, expressões faciais, contato, lágrimas ou deslocamentos.
- Se Descrição-guia estiver vazia, não invente [AÇÃO] só para preencher o formato.
- Descrição inicial informa o contexto e não autoriza novas ações.

[FALA] — MANTER A INTERPRETAÇÃO HUMANA DA VERSÃO C:
- Oralidade brasileira espontânea e individual, com variação orgânica de ritmo
  e intensidade. Responda ao sentido da fala atual do interlocutor, sem
  acrescentar informações de outro momento ou deslocar o foco da Fala-guia.
- Preserve sensorialidade e intensidade solicitadas pelo roteiro, sem clichês.

[PENSAMENTO] — MANTER A INTERPRETAÇÃO HUMANA DA VERSÃO C:
- Voz íntima de Mary, subjetiva e específica, evitando repetir a fala ou a ação.
- Preserve o grau emocional indicado no roteiro sem amplificá-lo.

Mantenha o formato original dos blocos. Não antecipe nenhuma linha futura.
"""

st.set_page_config(page_title="Mary | Laboratório Humanizer", page_icon="🧪", layout="wide")
st.title("🧪 Mary — Laboratório Humanizer")
st.caption("Comparação A/B/C isolada: não avança capítulos nem modifica checkpoints ou INTERACTIONS.")

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

model = st.text_input("Modelo OpenRouter (igual nas três versões)", value="google/gemini-3-flash-preview")
temperature = st.slider("Temperatura (igual nas três versões)", 0.0, 1.5, 0.7, 0.05)
user_text = st.text_area("Última fala do interlocutor", height=90)
recent = st.text_area("Contexto conversacional anterior (opcional; texto manual)", height=140,
    help="Copie algumas falas anteriores. O laboratório não consulta nem altera INTERACTIONS.")
interpretation = st.text_area("Interpretação / obrigação direta (opcional)", height=70,
    help="Informe qual pergunta ou ação Mary deve responder. Não executa a Compreensão.")
st.info("A = Redator original; B = concisão apenas em [AÇÃO]; C = híbrido: [AÇÃO] concisa da B e [FALA]/[PENSAMENTO] interpretativos. As três versões usam a mesma linha, o mesmo modelo e o mesmo contexto. Sem Compreensão ou Diretor automáticos.")
st.markdown("**Descrição-guia da linha:** " + (str(row.get("action_guide", "")).strip() or "*(vazia — não inventar ações na versão B)*"))
if st.button("Gerar A, B e C", type="primary"):
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
            interpretation_c = chat(messages=[{"role":"user", "content":prompt + "\n\n" + HUMANIZER_INTERPRETATIVO}], **common)
            st.session_state["humanizer_pair"] = {
                "timestamp":datetime.now(timezone.utc).isoformat(),
                "test_id":str(uuid4()), "capitulo":chapter,
                "linha":str(row.get("order")), "modelo":model, "fala_usuario":user_text,
                "contexto":recent, "fala_guia":str(row.get("speech_guide","")),
                "original":a, "humanizer":b, "interpretativo":interpretation_c,
            }
        except Exception as exc:
            st.error(f"Falha durante a geração: {exc}")

pair = st.session_state.get("humanizer_pair")
if pair:
    st.subheader("Comparação")
    st.caption("Caso " + pair["test_id"] + " · " + pair["capitulo"] + " · linha " + pair["linha"])
    a_col, b_col, c_col = st.columns(3)
    with a_col:
        st.markdown("#### A — Original")
        st.text_area("Resposta A", pair["original"], height=390, disabled=True)
    with b_col:
        st.markdown("#### B — Conciso")
        st.text_area("Resposta B", pair["humanizer"], height=390, disabled=True)
    with c_col:
        st.markdown("#### C — Híbrido interpretativo")
        st.text_area("Resposta C", pair["interpretativo"], height=390, disabled=True)
    with st.form("review", clear_on_submit=False):
        preferida = st.radio("Qual resposta você prefere?", ["A", "B", "C", "Empate"], horizontal=True)
        ca, cb, cc = st.columns(3)
        with ca:
            a_score = st.slider("Naturalidade A", 1, 5, 3)
        with cb:
            b_score = st.slider("Naturalidade B", 1, 5, 3)
        with cc:
            c_score = st.slider("Naturalidade C", 1, 5, 3)
        faithful = st.selectbox("Fidelidade ao roteiro", ["Não avaliado", "Todas", "A e B", "A e C", "B e C", "Somente A", "Somente B", "Somente C", "Nenhuma"])
        winner_action = st.selectbox("Melhor [AÇÃO]", ["Empate", "A", "B", "C"])
        winner_speech = st.selectbox("Melhor [FALA]", ["Empate", "A", "B", "C"])
        winner_thought = st.selectbox("Melhor [PENSAMENTO]", ["Empate", "A", "B", "C"])
        notes = st.text_area("Observações autorais")
        submitted = st.form_submit_button("Salvar avaliação em HUMANIZER")
    if submitted:
        try:
            reviewed = dict(pair)
            reviewed.update(preferida=preferida, naturalidade_original=a_score,
                            naturalidade_humanizer=b_score, naturalidade_interpretativo=c_score,
                            vencedor_por_canal=f"AÇÃO={winner_action}; FALA={winner_speech}; PENSAMENTO={winner_thought}",
                            fidelidade_roteiro=faithful, observacoes=notes)
            _write_review(reviewed)
            st.success("Avaliação registrada na aba HUMANIZER.")
            st.session_state.pop("humanizer_pair", None)
        except Exception as exc:
            st.error(f"Não foi possível salvar a avaliação: {exc}")
st.caption("Regras adaptadas do projeto blader/humanizer (licença MIT). Este laboratório não altera a aplicação principal.")
