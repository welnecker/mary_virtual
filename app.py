from __future__ import annotations

import streamlit as st

from config import APP_CAPTION, APP_TITLE, MAX_HISTORY_MESSAGES, MODEL_DEFAULT
from mary_prompt import montar_prompt_sistema
from openrouter_client import OpenRouterError, chamar_openrouter
from vision_utils import montar_mensagem_usuario, preparar_imagem


def exigir_senha_app() -> None:
    senha_correta = str(st.secrets.get("MARY_APP_PASSWORD", "") or "").strip()

    if not senha_correta:
        return

    if st.session_state.get("mary_app_autenticado") is True:
        return

    st.title("🔐 Acesso restrito")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar", use_container_width=True):
        if senha == senha_correta:
            st.session_state["mary_app_autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")

    st.stop()


def inicializar_sessao() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("pending_image", None)


def limpar_conversa() -> None:
    st.session_state["messages"] = []
    st.session_state["pending_image"] = None


def construir_historico_api() -> list[dict]:
    history = st.session_state["messages"][-MAX_HISTORY_MESSAGES:]
    return [
        {"role": item["role"], "content": item["content"]}
        for item in history
        if item.get("role") in {"user", "assistant"} and item.get("content")
    ]


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="💬", layout="centered")
    exigir_senha_app()
    inicializar_sessao()

    st.title(APP_TITLE)
    st.caption(APP_CAPTION)

    with st.sidebar:
        st.subheader("Configuração")
        model = st.text_input("Modelo OpenRouter", value=MODEL_DEFAULT)
        uploaded_file = st.file_uploader(
            "Mostrar uma fotografia para Mary",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=False,
        )
        if st.button("Limpar conversa", use_container_width=True):
            limpar_conversa()
            st.rerun()

    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Fotografia pronta para o próximo envio")

    prompt = st.chat_input("Fale com Mary...")

    if not prompt and uploaded_file is None:
        return

    if prompt is None:
        return

    prepared_image = None
    try:
        if uploaded_file is not None:
            prepared_image = preparar_imagem(uploaded_file)
    except ValueError as exc:
        st.error(str(exc))
        return

    user_display = prompt.strip() or "Olha isso pra mim, amor."
    st.session_state["messages"].append({"role": "user", "content": user_display})

    with st.chat_message("user"):
        st.markdown(user_display)
        if uploaded_file is not None:
            st.image(uploaded_file)

    api_key = str(st.secrets.get("OPENROUTER_API_KEY", "") or "")
    messages = [
        {"role": "system", "content": montar_prompt_sistema()},
        *construir_historico_api()[:-1],
        montar_mensagem_usuario(prompt, prepared_image),
    ]

    with st.chat_message("assistant"):
        with st.spinner("Mary está olhando..."):
            try:
                resposta = chamar_openrouter(
                    messages=messages,
                    model=model.strip() or MODEL_DEFAULT,
                    api_key=api_key,
                )
            except OpenRouterError as exc:
                st.error(str(exc))
                st.session_state["messages"].pop()
                return

        st.markdown(resposta)

    st.session_state["messages"].append(
        {"role": "assistant", "content": resposta}
    )


if __name__ == "__main__":
    main()
