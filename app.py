from __future__ import annotations
import time
import unicodedata

from copy import deepcopy
from typing import Any

import streamlit as st
import json
import hashlib

from config import (
    APP_CAPTION,
    APP_TITLE,
    APP_VERSION,
    MAX_HISTORY_MESSAGES,
    MODEL_DEFAULT,
    PROMPT_VERSION,
)
from google_sheets_repository import (
    GoogleSheetsRepositoryError,
    atualizar_usuario,
    criar_sessao,
    deletar_usuario_e_dados,
    encerrar_sessoes_ativas_usuario,
    gerar_id,
    limpar_dados_interacao_usuario,
    listar_interacoes_usuario,
    obter_ou_criar_relacionamento_mary,
)
from repositories.interaction_repository import (
    salvar_interacao,
)
from interaction_log import (
    adicionar_registro_sessao,
    criar_registro_interacao,
    criar_session_id,
    exportar_logs_json,
    exportar_logs_jsonl,
)
from mary_profile import (
    criar_mary_profile_padrao,
    imagem_publica_existe,
    marcar_perfil_publico_visto,
    normalizar_mary_profile,
    obter_caminho_imagem_publica,
    obter_perfil_publico,
)
from mary_prompt import montar_prompt_sistema
from openrouter_client import (
    OpenRouterError,
    chamar_openrouter,
)

from relationship import (
    atualizar_estado_relacao,
    atualizar_estado_sexual_antes_resposta,
    atualizar_estado_sexual_apos_resposta,
    criar_estado_relacao_padrao,
    detectar_sinais_relacao,
    montar_resumo_estado_relacao,
    normalizar_estado_relacao,
    planejar_direcao_turno,
    planejar_iniciativa_mary,
    sincronizar_direcao_apos_resposta,
    sincronizar_iniciativa_apos_resposta,
    validar_resposta_sexual,
)

from user_profile import (
    confirmar_referencia_visual,
    criar_perfil_padrao,
    definir_nome,
    marcar_interacao_realizada,
    normalizar_perfil,
    obter_nome_usado_por_mary,
)

from vision_utils import (
    montar_mensagem_usuario,
    preparar_imagem,
)

from scenarios.service import (
    ScenarioAccessError,
    iniciar_cenario_para_usuario,
    listar_cenarios_para_usuario,
)
from ui.login import (
    renderizar_tela_login,
)
from ui.scenario_menu import (
    ACTION_PLAY,
    ACTION_UNLOCK,
    renderizar_menu_cenarios,
)
from relationship.scenario_director import (
    analisar_turno_cenario,
    aplicar_analise_ao_estado,
    integrar_direcao_cenario,
    montar_direcao_narrativa,
)


def exigir_senha_app() -> None:
    senha_correta = str(
        st.secrets.get(
            "MARY_APP_PASSWORD",
            "",
        )
        or ""
    ).strip()

    if not senha_correta:
        return

    if st.session_state.get(
        "mary_app_autenticado"
    ) is True:
        return

    st.title("🔐 Acesso restrito")

    senha = st.text_input(
        "Senha",
        type="password",
    )

    if st.button(
        "Entrar",
        use_container_width=True,
        type="primary",
    ):
        if senha == senha_correta:
            st.session_state[
                "mary_app_autenticado"
            ] = True

            st.rerun()

        st.error("Senha incorreta.")

    st.stop()


def converter_booleano(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor

    texto = str(
        valor or ""
    ).strip().lower()

    return texto in {
        "true",
        "1",
        "sim",
        "yes",
        "verdadeiro",
    }


def inicializar_sessao_local() -> None:

    st.session_state.setdefault(
        "scenario_instance",
        None,
    )

    st.session_state.setdefault(
        "authenticated",
        False,
    )

    st.session_state.setdefault(
        "auth_user",
        None,
    )
    
    st.session_state.setdefault(
        "scenario_selector_visible",
        True,
    )
    st.session_state.setdefault(
        "messages",
        [],
    )

    st.session_state.setdefault(
        "pending_image",
        None,
    )

    st.session_state.setdefault(
        "history_restored",
        False,
    )

    if "user_profile" not in st.session_state:
        st.session_state[
            "user_profile"
        ] = criar_perfil_padrao()

    if "mary_profile" not in st.session_state:
        st.session_state[
            "mary_profile"
        ] = criar_mary_profile_padrao()
    else:
        st.session_state[
            "mary_profile"
        ] = normalizar_mary_profile(
            st.session_state["mary_profile"]
        )

    st.session_state.setdefault(
        "pending_user_image_confirmation",
        None,
    )

    st.session_state.setdefault(
        "pending_mary_image",
        None,
    )

    st.session_state.setdefault(
        "show_name_form",
        False,
    )

    st.session_state.setdefault(
        "initial_message_created",
        False,
    )

    st.session_state.setdefault(
        "interaction_logs",
        [],
    )

    st.session_state.setdefault(
        "persistence_initialized",
        False,
    )

    st.session_state.setdefault(
        "persistent_user",
        None,
    )

    st.session_state.setdefault(
        "persistent_session",
        None,
    )

    st.session_state.setdefault(
        "mary_relationship",
        None,
    )

    st.session_state.setdefault(
        "selected_scenario_id",
        "",
    )

    st.session_state.setdefault(
        "last_sexual_validation",
        {
            "valid": True,
            "errors": [],
        },
    )

    if "relationship_state" not in st.session_state:
        st.session_state[
            "relationship_state"
        ] = criar_estado_relacao_padrao()
    else:
        st.session_state[
            "relationship_state"
        ] = normalizar_estado_relacao(
            st.session_state[
                "relationship_state"
            ]
        )    

    if "interaction_session_id" not in st.session_state:
        st.session_state[
            "interaction_session_id"
        ] = criar_session_id()


def obter_estados_relacao() -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    relationship_state = normalizar_estado_relacao(
        st.session_state.get(
            "relationship_state"
        )
    )

    sexual_state = relationship_state.get(
        "sexual_state"
    )

    if not isinstance(
        sexual_state,
        dict,
    ):
        sexual_state = {}

    relationship_state[
        "sexual_state"
    ] = sexual_state

    st.session_state[
        "relationship_state"
    ] = relationship_state

    return (
        relationship_state,
        sexual_state,
    )


def hidratar_perfil_usuario(
    usuario: dict[str, Any],
) -> None:
    profile = normalizar_perfil(
        st.session_state["user_profile"]
    )

    user_id = str(
        usuario.get("user_id")
        or ""
    ).strip()

    nome = str(
        usuario.get("name")
        or ""
    ).strip()

    nome_preferido = str(
        usuario.get("preferred_name")
        or ""
    ).strip()

    if user_id:
        profile["profile_id"] = user_id

    profile["name"] = nome
    profile["preferred_name"] = nome_preferido

    profile["milestones"]["name_known"] = bool(
        nome_preferido or nome
    )

    profile = normalizar_perfil(
        profile
    )

    st.session_state[
        "user_profile"
    ] = profile


def hidratar_relacionamento_mary(
    relacionamento: dict[str, Any],
) -> None:
    mary_profile = normalizar_mary_profile(
        st.session_state["mary_profile"]
    )

    relationship_state = mary_profile.setdefault(
        "relationship_state",
        {},
    )

    relationship_state[
        "revealed_to_user"
    ] = converter_booleano(
        relacionamento.get(
            "mary_revealed"
        )
    )

    relationship_state[
        "first_reveal_image_id"
    ] = str(
        relacionamento.get(
            "first_mary_image_id"
        )
        or ""
    ).strip()

    relationship_state[
        "first_reveal_at"
    ] = str(
        relacionamento.get(
            "first_reveal_at"
        )
        or ""
    ).strip()

    relationship_state[
        "user_has_seen_mary"
    ] = converter_booleano(
        relacionamento.get(
            "user_has_seen_mary"
        )
    )

    relationship_state[
        "user_first_visual_reaction"
    ] = str(
        relacionamento.get(
            "user_first_visual_reaction"
        )
        or ""
    ).strip()

    # A visualização do perfil público é diferente
    # da revelação visual real de Mary.
    relationship_state.setdefault(
        "public_profile_seen",
        False,
    )

    relationship_state.setdefault(
        "public_profile_seen_at",
        "",
    )

    mary_profile[
        "relationship_state"
    ] = relationship_state

    st.session_state[
        "mary_profile"
    ] = mary_profile


def restaurar_historico_interacoes(
    user_id: str,
    *,
    forcar: bool = False,
) -> None:
    mensagens_atuais = st.session_state.get(
        "messages"
    )

    if not isinstance(
        mensagens_atuais,
        list,
    ):
        mensagens_atuais = []

        st.session_state[
            "messages"
        ] = mensagens_atuais

    historico_ja_restaurado = bool(
        st.session_state.get(
            "history_restored"
        )
    )

    # Só impede nova leitura quando o histórico já foi
    # restaurado e as mensagens continuam presentes.
    if (
        historico_ja_restaurado
        and mensagens_atuais
        and not forcar
    ):
        return

    interacoes = listar_interacoes_usuario(
        user_id,
        limite=50,
    )

    mensagens: list[dict[str, Any]] = []

    for interacao in interacoes:
        texto_usuario = str(
            interacao.get(
                "user_text"
            )
            or ""
        ).strip()

        resposta_mary = str(
            interacao.get(
                "mary_response"
            )
            or ""
        ).strip()

        erro = str(
            interacao.get(
                "error"
            )
            or ""
        ).strip()

        # Interações com erro não produziram uma
        # resposta válida da Mary.
        if erro:
            continue

        if texto_usuario:
            mensagens.append(
                {
                    "role": "user",
                    "content": texto_usuario,
                }
            )

        if resposta_mary:
            mensagens.append(
                {
                    "role": "assistant",
                    "content": resposta_mary,
                }
            )

    st.session_state[
        "messages"
    ] = mensagens

    if mensagens:
        st.session_state[
            "initial_message_created"
        ] = True

        st.session_state[
            "user_profile"
        ] = marcar_interacao_realizada(
            st.session_state[
                "user_profile"
            ]
        )

    st.session_state[
        "history_restored"
    ] = True


def inicializar_persistencia(
    modelo_utilizado: str,
) -> None:
    if st.session_state.get(
        "persistence_initialized"
    ):
        return

    try:
        usuario = st.session_state.get(
            "auth_user"
        )

        if not isinstance(
            usuario,
            dict,
        ):
            raise GoogleSheetsRepositoryError(
                "Usuário autenticado não encontrado."
            )

        user_id = str(
            usuario.get(
                "user_id",
                "",
            )
            or ""
        ).strip()

        if not user_id:
            raise GoogleSheetsRepositoryError(
                "Usuário autenticado sem identificador válido."
            )

        relacionamento = (
            obter_ou_criar_relacionamento_mary(
                user_id
            )
        )

        encerrar_sessoes_ativas_usuario(
            user_id
        )

        sessao = criar_sessao(
            user_id=user_id,
            model=modelo_utilizado,
            prompt_version=PROMPT_VERSION,
            app_version=APP_VERSION,
        )

        st.session_state[
            "interaction_session_id"
        ] = sessao["session_id"]

        st.session_state[
            "persistent_user"
        ] = usuario

        st.session_state[
            "persistent_session"
        ] = sessao

        st.session_state[
            "mary_relationship"
        ] = relacionamento

        hidratar_perfil_usuario(
            usuario
        )

        hidratar_relacionamento_mary(
            relacionamento
        )

        restaurar_historico_interacoes(
            user_id
        )

        st.session_state[
            "persistence_initialized"
        ] = True

    except GoogleSheetsRepositoryError as exc:
        st.error(
            "Não foi possível iniciar a persistência "
            f"no Google Sheets: {exc}"
        )
        st.stop()


def renderizar_identidade_persistente() -> None:
    usuario = st.session_state.get(
        "persistent_user"
    )

    relacionamento = st.session_state.get(
        "mary_relationship"
    )

    if not usuario:
        st.info(
            "Usuário persistente ainda não inicializado."
        )
        return

    nome = str(
        usuario.get("name")
        or usuario.get("preferred_name")
        or ""
    ).strip()

    if nome:
        st.success(
            f"Perfil persistente: {nome}"
        )
    else:
        st.info(
            "Perfil persistente ativo. "
            "Mary ainda não sabe como chamar você."
        )

    if relacionamento:
        st.caption(
            "Relação persistente com Mary: "
            f"{relacionamento.get('status', 'active')}"
        )


def renderizar_diagnostico_perfil() -> None:
    profile = normalizar_perfil(
        st.session_state["user_profile"]
    )

    with st.expander(
        "Diagnóstico do perfil",
        expanded=False,
    ):
        st.json(
            {
                "profile_id": profile.get(
                    "profile_id"
                ),
                "name": profile.get("name"),
                "preferred_name": profile.get(
                    "preferred_name"
                ),
                "interactions": profile.get(
                    "interactions"
                ),
                "milestones": profile.get(
                    "milestones"
                ),
                "visual_reference": profile.get(
                    "visual_reference"
                ),
            }
        )


def renderizar_log_interacoes() -> None:
    registros = st.session_state[
        "interaction_logs"
    ]

    with st.expander(
        "Log de interações",
        expanded=False,
    ):
        if not registros:
            st.info(
                "Nenhuma interação registrada nesta sessão."
            )
            return

        st.download_button(
            "Baixar JSON",
            data=exportar_logs_json(
                registros
            ),
            file_name="mary_interactions.json",
            mime="application/json",
            use_container_width=True,
        )

        st.download_button(
            "Baixar JSONL",
            data=exportar_logs_jsonl(
                registros
            ),
            file_name="mary_interactions.jsonl",
            mime="application/x-ndjson",
            use_container_width=True,
        )

        for registro in reversed(
            registros[-8:]
        ):
            st.caption(
                (
                    f"{registro.get('timestamp')} | "
                    f"{registro.get('interaction_id')}"
                )
            )

            st.code(
                json.dumps(
                    registro,
                    ensure_ascii=False,
                    indent=2,
                ),
                language="json",
            )


def limpar_conversa() -> None:
    st.session_state[
        "messages"
    ] = []

    st.session_state[
        "interaction_logs"
    ] = []

    st.session_state[
        "pending_image"
    ] = None

    st.session_state[
        "pending_user_image_confirmation"
    ] = None

    st.session_state[
        "pending_mary_image"
    ] = None

    st.session_state[
        "show_name_form"
    ] = False

    st.session_state[
        "initial_message_created"
    ] = False

    st.session_state[
        "history_restored"
    ] = False

    st.session_state[
        "interaction_session_id"
    ] = criar_session_id()

    st.session_state[
        "persistent_session"
    ] = None

    st.session_state[
        "persistence_initialized"
    ] = False

    st.session_state[
        "relationship_state"
    ] = criar_estado_relacao_padrao()

    st.session_state[
        "last_sexual_validation"
    ] = {
        "valid": True,
        "errors": [],
    }


def obter_user_id_persistente() -> str:
    usuario = st.session_state.get(
        "persistent_user"
    )

    if not usuario:
        raise GoogleSheetsRepositoryError(
            "Usuário persistente não inicializado."
        )

    user_id = str(
        usuario.get("user_id")
        or ""
    ).strip()

    if not user_id:
        raise GoogleSheetsRepositoryError(
            "Não foi possível identificar o usuário atual."
        )

    return user_id


def resetar_estado_local_relacionamento(
    *,
    preservar_usuario: bool,
) -> None:
    """Limpa os estados locais ligados à conversa e à relação."""

    usuario_atual = st.session_state.get(
        "auth_user"
    )

    st.session_state[
        "messages"
    ] = []
    st.session_state[
        "interaction_logs"
    ] = []
    st.session_state[
        "pending_image"
    ] = None
    st.session_state[
        "pending_user_image_confirmation"
    ] = None
    st.session_state[
        "pending_mary_image"
    ] = None
    st.session_state[
        "show_name_form"
    ] = False
    st.session_state[
        "initial_message_created"
    ] = False
    st.session_state[
        "history_restored"
    ] = False
    st.session_state[
        "persistence_initialized"
    ] = False
    st.session_state[
        "persistent_session"
    ] = None
    st.session_state[
        "mary_relationship"
    ] = None
    st.session_state[
        "scenario_instance"
    ] = None
    st.session_state[
        "selected_scenario_id"
    ] = ""
    st.session_state[
        "scenario_selector_visible"
    ] = True
    st.session_state[
        "interaction_session_id"
    ] = criar_session_id()
    st.session_state[
        "relationship_state"
    ] = criar_estado_relacao_padrao()
    st.session_state[
        "mary_profile"
    ] = criar_mary_profile_padrao()
    st.session_state[
        "user_profile"
    ] = criar_perfil_padrao()
    st.session_state[
        "last_sexual_validation"
    ] = {
        "valid": True,
        "errors": [],
    }

    if preservar_usuario:
        st.session_state[
            "auth_user"
        ] = usuario_atual
        st.session_state[
            "persistent_user"
        ] = usuario_atual
        st.session_state[
            "authenticated"
        ] = bool(usuario_atual)
    else:
        st.session_state[
            "auth_user"
        ] = None
        st.session_state[
            "persistent_user"
        ] = None
        st.session_state[
            "authenticated"
        ] = False


def encerrar_login_local() -> None:
    """Encerra apenas a sessão local, sem apagar a conta."""

    resetar_estado_local_relacionamento(
        preservar_usuario=False,
    )


def executar_limpeza_interacoes() -> dict[str, int]:
    """
    Apaga da planilha todos os dados de conversa do
    usuário atual, preservando o cadastro.
    """

    user_id = obter_user_id_persistente()

    resultado = limpar_dados_interacao_usuario(
        user_id
    )

    resetar_estado_local_relacionamento(
        preservar_usuario=True,
    )

    return resultado


def executar_exclusao_usuario() -> dict[str, int]:
    """
    Apaga todos os registros do usuário e remove o cadastro
    da aba USERS.
    """

    user_id = obter_user_id_persistente()

    resultado = deletar_usuario_e_dados(
        user_id
    )

    resetar_estado_local_relacionamento(
        preservar_usuario=False,
    )

    return resultado


def construir_historico_api() -> list[dict[str, Any]]:
    history = st.session_state[
        "messages"
    ][-MAX_HISTORY_MESSAGES:]

    return [
        {
            "role": item["role"],
            "content": item["content"],
        }
        for item in history
        if (
            item.get("role")
            in {
                "user",
                "assistant",
            }
            and item.get("content")
        )
    ]


def normalizar_texto_para_deteccao(
    texto: str,
) -> str:
    texto = str(
        texto or ""
    ).lower().strip()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    return "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(
            caractere
        )
    )


def mary_perguntou_nome(
    resposta: str,
) -> bool:
    texto = normalizar_texto_para_deteccao(
        resposta
    )

    expressoes = (
        "qual e o seu nome",
        "qual seu nome",
        "como voce se chama",
        "como devo te chamar",
        "como posso te chamar",
        "como quer que eu te chame",
        "como gostaria que eu te chamasse",
        "ainda nao sei seu nome",
        "nem sei seu nome",
        "nao sei como te chamar",
        "me conta seu nome",
        "me diz seu nome",
        "diga seu nome",
    )

    return any(
        expressao in texto
        for expressao in expressoes
    )


def persistir_nome_usuario(
    nome: str,
) -> None:
    usuario = st.session_state.get(
        "persistent_user"
    )

    if not usuario:
        raise GoogleSheetsRepositoryError(
            "Usuário persistente não inicializado."
        )

    user_id = str(
        usuario.get("user_id")
        or ""
    ).strip()

    if not user_id:
        raise GoogleSheetsRepositoryError(
            "Não foi possível identificar o usuário atual."
        )

    nome_normalizado = str(
        nome or ""
    ).strip()

    if not nome_normalizado:
        raise GoogleSheetsRepositoryError(
            "Nome inválido para persistência."
        )

    usuario_atualizado = atualizar_usuario(
        user_id,
        {
            "name": nome_normalizado,
            "preferred_name": nome_normalizado,
        },
    )

    st.session_state[
        "persistent_user"
    ] = usuario_atualizado

    st.session_state[
        "auth_user"
    ] = usuario_atualizado

    hidratar_perfil_usuario(
        usuario_atualizado
    )


def salvar_nome(nome: str) -> None:
    profile = definir_nome(
        st.session_state[
            "user_profile"
        ],
        name=nome,
        preferred_name=nome,
    )

    st.session_state[
        "user_profile"
    ] = profile

    persistir_nome_usuario(
        nome
    )

    st.session_state[
        "show_name_form"
    ] = False

    st.success(
        f"Prazer, {nome}. Agora Mary vai lembrar de você."
    )


def renderizar_formulario_nome() -> None:
    if not st.session_state.get(
        "show_name_form"
    ):
        return

    if st.session_state[
        "user_profile"
    ].get("name"):
        st.session_state[
            "show_name_form"
        ] = False
        return

    with st.form(
        "name_form",
        clear_on_submit=True,
    ):
        name = st.text_input(
            "Como Mary deve chamar você?"
        )

        submitted = st.form_submit_button(
            "Salvar nome",
            use_container_width=True,
        )

    if submitted:
        if not name.strip():
            st.warning(
                "Digite um nome antes de salvar."
            )
            return

        try:
            salvar_nome(
                name.strip()
            )
        except GoogleSheetsRepositoryError as exc:
            st.error(
                "Não foi possível salvar seu nome: "
                f"{exc}"
            )
            return

        st.rerun()


def hash_imagem(
    image_bytes: bytes,
) -> str:
    return hashlib.sha256(
        image_bytes
    ).hexdigest()


def obter_hashs_imagens_ja_vistas() -> set[str]:
    mary_profile = normalizar_mary_profile(
        st.session_state[
            "mary_profile"
        ]
    )

    hashes = set()

    for image in mary_profile[
        "visual_memory"
    ]["user_images"]:
        image_hash = image.get(
            "image_hash"
        )

        if image_hash:
            hashes.add(
                str(image_hash)
            )

    return hashes


def preparar_upload(
    uploaded_file,
) -> dict[str, Any] | None:
    if uploaded_file is None:
        return None

    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    raw_bytes = uploaded_file.getvalue()

    current_hash = hash_imagem(
        raw_bytes
    )

    known_hashes = obter_hashs_imagens_ja_vistas()

    if current_hash in known_hashes:
        st.info(
            "Mary reconheceu esta fotografia. "
            "Não precisa confirmar novamente."
        )

        try:
            uploaded_file.seek(0)
        except Exception:
            pass

        return preparar_imagem(
            uploaded_file
        )

    pending = st.session_state.get(
        "pending_user_image_confirmation"
    )

    if not pending or (
        pending.get("image_hash")
        != current_hash
    ):
        st.session_state[
            "pending_user_image_confirmation"
        ] = {
            "image_hash": current_hash,
            "file_name": uploaded_file.name,
            "mime_type": uploaded_file.type,
            "size_bytes": len(raw_bytes),
        }

    st.info(
        "Mary ainda não sabe se a pessoa da fotografia é você."
    )

    st.image(
        raw_bytes,
        use_container_width=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        yes = st.button(
            "Sim, sou eu",
            use_container_width=True,
            type="primary",
        )

    with col2:
        no = st.button(
            "Não sou eu",
            use_container_width=True,
        )

    if yes:
        profile = confirmar_referencia_visual(
            st.session_state[
                "user_profile"
            ],
            image_hash=current_hash,
            file_name=uploaded_file.name,
            mime_type=uploaded_file.type,
            size_bytes=len(raw_bytes),
            confirmation_source=(
                "explicit_button"
            ),
        )

        st.session_state[
            "user_profile"
        ] = profile

        st.session_state[
            "pending_user_image_confirmation"
        ] = None

        st.success(
            "Entendido. Mary guardou esta fotografia "
            "como uma referência visual sua."
        )

        st.rerun()

    if no:
        st.session_state[
            "pending_user_image_confirmation"
        ] = None

        st.info(
            "Certo. Mary não vai associar "
            "esta pessoa ao seu perfil."
        )

        st.rerun()

    st.stop()


def iniciar_revelacao_visual_mary() -> None:
    mary_profile = normalizar_mary_profile(
        st.session_state[
            "mary_profile"
        ]
    )

    if mary_profile[
        "relationship_state"
    ]["revealed_to_user"]:
        return

    public_profile = obter_perfil_publico()

    st.session_state[
        "pending_mary_image"
    ] = {
        "image_id": public_profile["image_id"],
        "path": obter_caminho_imagem_publica(),
    }


def marcar_revelacao_visual_mary(
    reaction: str,
) -> None:
    mary_profile = normalizar_mary_profile(
        st.session_state[
            "mary_profile"
        ]
    )

    pending = st.session_state.get(
        "pending_mary_image"
    )

    if not pending:
        return

    mary_profile[
        "relationship_state"
    ]["revealed_to_user"] = True

    mary_profile[
        "relationship_state"
    ]["first_reveal_image_id"] = pending[
        "image_id"
    ]

    mary_profile[
        "relationship_state"
    ]["first_reveal_at"] = gerar_id(
        "time"
    ).replace(
        "time_",
        "",
        1,
    )

    mary_profile[
        "relationship_state"
    ]["user_has_seen_mary"] = True

    mary_profile[
        "relationship_state"
    ]["user_first_visual_reaction"] = reaction

    mary_profile[
        "visual_memory"
    ]["mary_images_shown"].append(
        {
            "image_id": pending["image_id"],
            "reaction": reaction,
        }
    )

    st.session_state[
        "mary_profile"
    ] = mary_profile

    relacionamento = st.session_state.get(
        "mary_relationship"
    )

    if relacionamento:
        from google_sheets_repository import (
            atualizar_relacionamento_mary,
        )

        relacionamento_atualizado = (
            atualizar_relacionamento_mary(
                relacionamento[
                    "relationship_id"
                ],
                {
                    "mary_revealed": True,
                    "first_mary_image_id": pending[
                        "image_id"
                    ],
                    "first_reveal_at": (
                        mary_profile[
                            "relationship_state"
                        ]["first_reveal_at"]
                    ),
                    "user_has_seen_mary": True,
                    "user_first_visual_reaction": reaction,
                },
            )
        )

        st.session_state[
            "mary_relationship"
        ] = relacionamento_atualizado

    st.session_state[
        "pending_mary_image"
    ] = None


def renderizar_perfil_publico_mary() -> None:
    public_profile = obter_perfil_publico()

    mary_profile = normalizar_mary_profile(
        st.session_state[
            "mary_profile"
        ]
    )

    if not mary_profile.get(
        "profile_public_enabled",
        True,
    ):
        return

    st.subheader(
        "Perfil público de Mary"
    )

    st.caption(
        public_profile[
            "public_status"
        ]
    )

    if imagem_publica_existe():
        st.image(
            obter_caminho_imagem_publica(),
            caption=(
                "Esta é a fotografia pública do perfil de Mary."
            ),
            use_container_width=True,
        )
    else:
        st.info(
            "A fotografia pública ainda não foi configurada."
        )

    st.markdown(
        f"### {public_profile['display_name']}"
    )

    st.write(
        public_profile[
            "short_bio"
        ]
    )

    st.caption(
        (
            f"{public_profile['age']} anos · "
            f"{public_profile['occupation']} · "
            f"{public_profile['city']}"
        )
    )

    with st.expander(
        "Sobre Mary",
        expanded=False,
    ):
        st.write(
            public_profile[
                "long_bio"
            ]
        )

        st.markdown(
            "**Interesses:** "
            + ", ".join(
                public_profile[
                    "interests"
                ]
            )
        )

        st.markdown(
            "**Personalidade:** "
            + ", ".join(
                public_profile[
                    "personality_traits"
                ]
            )
        )

        st.markdown(
            "**Disponível para:** "
            + ", ".join(
                public_profile[
                    "open_to"
                ]
            )
        )

    if st.button(
        "Conversar com Mary",
        use_container_width=True,
        type="primary",
    ):
        mary_profile = marcar_perfil_publico_visto(
            mary_profile
        )

        st.session_state[
            "mary_profile"
        ] = mary_profile

        st.rerun()


def renderizar_revelacao_visual_mary() -> None:
    pending = st.session_state.get(
        "pending_mary_image"
    )

    if not pending:
        return

    path = pending.get("path")

    if not path:
        return

    st.subheader(
        "Mary mostrou uma fotografia dela"
    )

    st.image(
        path,
        caption=(
            "Mary decidiu mostrar uma fotografia dela para você."
        ),
        use_container_width=True,
    )

    st.caption(
        "A reação abaixo vai fazer parte "
        "da memória da conversa."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        gostei = st.button(
            "Gostei",
            use_container_width=True,
            type="primary",
        )

    with col2:
        neutro = st.button(
            "Neutro",
            use_container_width=True,
        )

    with col3:
        nao_gostei = st.button(
            "Não gostei",
            use_container_width=True,
        )

    if gostei:
        marcar_revelacao_visual_mary(
            "positive"
        )
        st.rerun()

    if neutro:
        marcar_revelacao_visual_mary(
            "neutral"
        )
        st.rerun()

    if nao_gostei:
        marcar_revelacao_visual_mary(
            "negative"
        )
        st.rerun()

    st.stop()


def montar_metadados_imagem(
    prepared_image: dict[str, Any] | None,
) -> dict[str, Any]:
    if prepared_image is None:
        return {
            "sent": False,
            "width": None,
            "height": None,
            "size_bytes": None,
            "mime_type": None,
        }

    return {
        "sent": True,
        "width": prepared_image.get(
            "width"
        ),
        "height": prepared_image.get(
            "height"
        ),
        "size_bytes": prepared_image.get(
            "size_bytes"
        ),
        "mime_type": prepared_image.get(
            "mime_type"
        ),
    }


def registrar_interacao_remota(
    registro: dict[str, Any],
) -> None:
    usuario = st.session_state.get(
        "persistent_user"
    )

    sessao = st.session_state.get(
        "persistent_session"
    )

    if not usuario or not sessao:
        return

    image_metadata = registro.get(
        "image"
    ) or {}

    salvar_interacao(
        interaction_id=registro[
            "interaction_id"
        ],
        session_id=sessao[
            "session_id"
        ],
        user_id=usuario[
            "user_id"
        ],
        timestamp=registro[
            "timestamp"
        ],
        user_text=registro[
            "user_text"
        ],
        mary_response=registro[
            "mary_response"
        ],
        model=registro[
            "model"
        ],
        prompt_version=PROMPT_VERSION,
        response_time_ms=registro.get(
            "response_time_ms"
        ),
        image_sent=bool(
            image_metadata.get(
                "sent"
            )
        ),
        image_width=image_metadata.get(
            "width"
        ),
        image_height=image_metadata.get(
            "height"
        ),
        image_size_bytes=image_metadata.get(
            "size_bytes"
        ),
        image_mime_type=image_metadata.get(
            "mime_type"
        ),
        mary_asked_name=bool(
            registro.get(
                "mary_asked_name"
            )
        ),
        error=str(
            registro.get("error")
            or ""
        ),
    )


def registrar_interacao_local_e_remota(
    registro: dict[str, Any],
) -> None:
    adicionar_registro_sessao(
        st.session_state[
            "interaction_logs"
        ],
        registro,
    )

    try:
        registrar_interacao_remota(
            registro
        )
    except GoogleSheetsRepositoryError as exc:
        st.warning(
            "A conversa continuou, mas esta interação "
            "não foi salva no Google Sheets: "
            f"{exc}"
        )


def obter_user_id_sessao() -> str:
    usuario = (
        st.session_state.get(
            "persistent_user"
        )
        or st.session_state.get(
            "auth_user"
        )
        or {}
    )

    if not isinstance(
        usuario,
        dict,
    ):
        return ""

    return str(
        usuario.get(
            "user_id",
            "",
        )
        or ""
    ).strip()


def obter_instancia_cenario_ativa() -> dict[str, Any] | None:
    instancia = st.session_state.get(
        "scenario_instance"
    )

    if not isinstance(
        instancia,
        dict,
    ):
        return None

    if str(
        instancia.get(
            "status",
            "active",
        )
        or "active"
    ).strip().lower() != "active":
        return None

    user_id_sessao = obter_user_id_sessao()
    user_id_instancia = str(
        instancia.get(
            "user_id",
            "",
        )
        or ""
    ).strip()

    if (
        user_id_sessao
        and user_id_instancia
        and user_id_sessao
        != user_id_instancia
    ):
        return None

    return instancia


def obter_scene_state_cenario(
    instancia: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(
        instancia,
        dict,
    ):
        return {}

    scene_state = instancia.get(
        "scene_state"
    )

    if not isinstance(
        scene_state,
        dict,
    ):
        scene_state = {}

    return deepcopy(
        scene_state
    )


def construir_contexto_configuracao_cenario(
    instancia: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(
        instancia,
        dict,
    ):
        return {}

    config = instancia.get(
        "scenario_config"
    )

    if not isinstance(
        config,
        dict,
    ):
        return {}

    duration = config.get(
        "duration"
    )

    if not isinstance(
        duration,
        dict,
    ):
        duration = {}

    roles = config.get(
        "roles"
    )

    if not isinstance(
        roles,
        dict,
    ):
        roles = {}

    premise = config.get(
        "premise"
    )

    if not isinstance(
        premise,
        dict,
    ):
        premise = {}

    return {
        "scenario_id": str(
            instancia.get(
                "scenario_id",
                "",
            )
            or ""
        ),
        "scenario_version": int(
            instancia.get(
                "scenario_version",
                1,
            )
            or 1
        ),
        "title": str(
            config.get(
                "title",
                "",
            )
            or ""
        ),
        "roles": deepcopy(
            roles
        ),
        "premise": deepcopy(
            premise
        ),
        "duration": deepcopy(
            duration
        ),
        "current_phase": str(
            instancia.get(
                "current_phase",
                "opening",
            )
            or "opening"
        ),
        "current_route": str(
            instancia.get(
                "current_route",
                "",
            )
            or ""
        ),
        "current_beat": str(
            instancia.get(
                "current_beat",
                "",
            )
            or ""
        ),
        "active_hook": str(
            instancia.get(
                "active_hook",
                "",
            )
            or ""
        ),
        "interaction_count": int(
            instancia.get(
                "interaction_count",
                0,
            )
            or 0
        ),
    }


def criar_mensagem_inicial_cenario(
    instancia: dict[str, Any],
) -> None:
    abertura = str(
        instancia.get(
            "opening_message",
            "",
        )
        or ""
    ).strip()

    if not abertura:
        return

    if bool(
        instancia.get(
            "opening_sent",
            False,
        )
    ):
        return

    st.session_state[
        "messages"
    ].append(
        {
            "role": "assistant",
            "content": abertura,
        }
    )

    instancia[
        "opening_sent"
    ] = True

    scene_state = instancia.get(
        "scene_state"
    )

    if isinstance(
        scene_state,
        dict,
    ):
        scene_state[
            "opening_sent"
        ] = True

    st.session_state[
        "scenario_instance"
    ] = instancia

    st.session_state[
        "initial_message_created"
    ] = True


def sincronizar_relacao_com_cenario(
    relationship_state: dict[str, Any],
    instancia: dict[str, Any] | None,
) -> dict[str, Any]:
    state = normalizar_estado_relacao(
        relationship_state
    )

    scenario_context = state.setdefault(
        "scenario_context",
        {},
    )

    if not isinstance(
        instancia,
        dict,
    ):
        scenario_context.update(
            {
                "active": False,
                "scenario_id": "",
                "scenario_session_id": "",
                "scenario_version": 0,
                "scenario_title": "",
                "scenario_role_mary": "",
                "scenario_role_user": "",
                "scenario_phase": "",
                "scenario_route": "",
                "scenario_beat": "",
                "scenario_hook": "",
                "interaction_count": 0,
                "seduction_level": 0,
            }
        )

        state[
            "scenario_context"
        ] = scenario_context

        return state

    config = instancia.get(
        "scenario_config"
    )

    if not isinstance(
        config,
        dict,
    ):
        config = {}

    roles = config.get(
        "roles"
    )

    if not isinstance(
        roles,
        dict,
    ):
        roles = {}

    scene_state = instancia.get(
        "scene_state"
    )

    if not isinstance(
        scene_state,
        dict,
    ):
        scene_state = {}

    scenario_context.update(
        {
            "active": True,
            "scenario_id": str(
                instancia.get(
                    "scenario_id",
                    "",
                )
                or ""
            ),
            "scenario_session_id": str(
                instancia.get(
                    "scenario_session_id",
                    "",
                )
                or ""
            ),
            "scenario_version": int(
                instancia.get(
                    "scenario_version",
                    1,
                )
                or 1
            ),
            "scenario_title": str(
                config.get(
                    "title",
                    "",
                )
                or ""
            ),
            "scenario_role_mary": str(
                roles.get(
                    "mary",
                    "",
                )
                or ""
            ),
            "scenario_role_user": str(
                roles.get(
                    "user",
                    "",
                )
                or ""
            ),
            "scenario_phase": str(
                instancia.get(
                    "current_phase",
                    scene_state.get(
                        "current_phase",
                        "opening",
                    ),
                )
                or "opening"
            ),
            "scenario_route": str(
                instancia.get(
                    "current_route",
                    scene_state.get(
                        "current_route",
                        "",
                    ),
                )
                or ""
            ),
            "scenario_beat": str(
                instancia.get(
                    "current_beat",
                    scene_state.get(
                        "current_beat",
                        "",
                    ),
                )
                or ""
            ),
            "scenario_hook": str(
                instancia.get(
                    "active_hook",
                    scene_state.get(
                        "active_hook",
                        "",
                    ),
                )
                or ""
            ),
            "interaction_count": int(
                instancia.get(
                    "interaction_count",
                    scene_state.get(
                        "interaction_count",
                        0,
                    ),
                )
                or 0
            ),
            "seduction_level": int(
                scene_state.get(
                    "seduction_level",
                    0,
                )
                or 0
            ),
        }
    )

    state[
        "scenario_context"
    ] = scenario_context

    return state


def gerar_interaction_id() -> str:
    return gerar_id(
        "int"
    )


def gerar_turn_id() -> str:
    return gerar_id(
        "turn"
    )


def resumo_texto(
    texto: str,
    limite: int = 280,
) -> str:
    texto_normalizado = " ".join(
        str(
            texto or ""
        ).split()
    )

    if len(
        texto_normalizado
    ) <= limite:
        return texto_normalizado

    return (
        texto_normalizado[
            : limite - 1
        ]
        + "…"
    )


def calcular_deltas_relacao(
    estado_anterior: dict[str, Any],
    estado_atual: dict[str, Any],
) -> dict[str, float]:
    campos = (
        "familiarity_level",
        "trust_level",
        "affection_level",
        "romantic_tension_level",
    )

    deltas: dict[str, float] = {}

    for campo in campos:
        anterior = float(
            estado_anterior.get(
                campo,
                0.0,
            )
            or 0.0
        )

        atual = float(
            estado_atual.get(
                campo,
                0.0,
            )
            or 0.0
        )

        deltas[campo] = round(
            atual - anterior,
            4,
        )

    return deltas


def criar_snapshot_relacao(
    estado: dict[str, Any],
) -> dict[str, Any]:
    return deepcopy(
        normalizar_estado_relacao(
            estado
        )
    )


def registrar_evento_estado_relacao(
    *,
    relationship_state: dict[str, Any],
    event_type: str,
    interaction_id: str,
    turn_id: str,
    session_id: str,
    user_text: str,
    mary_response: str,
    direction: dict[str, Any] | None = None,
    signals: dict[str, Any] | None = None,
    status: str = "completed",
    error: str = "",
    started_at: str = "",
    completed_at: str = "",
) -> dict[str, Any]:
    state = normalizar_estado_relacao(
        relationship_state
    )

    events = state.setdefault(
        "events",
        [],
    )

    event = {
        "event_id": gerar_id(
            "evt"
        ),
        "event_type": str(
            event_type or "interaction"
        ),
        "interaction_id": interaction_id,
        "turn_id": turn_id,
        "session_id": session_id,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "user_text": resumo_texto(
            user_text,
            360,
        ),
        "mary_response": resumo_texto(
            mary_response,
            520,
        ),
        "direction": deepcopy(
            direction
            if isinstance(
                direction,
                dict,
            )
            else {}
        ),
        "signals": deepcopy(
            signals
            if isinstance(
                signals,
                dict,
            )
            else {}
        ),
        "relationship_snapshot": criar_snapshot_relacao(
            state
        ),
    }

    if error:
        event[
            "error"
        ] = str(
            error
        )

    events.append(
        event
    )

    state[
        "events"
    ] = events[-100:]

    state[
        "last_event_id"
    ] = event[
        "event_id"
    ]

    return state


def criar_evento_turno_aberto(
    *,
    relationship_state: dict[str, Any],
    interaction_id: str,
    turn_id: str,
    session_id: str,
    user_text: str,
    direction: dict[str, Any],
    signals: dict[str, Any],
    started_at: str,
) -> dict[str, Any]:
    state = registrar_evento_estado_relacao(
        relationship_state=(
            relationship_state
        ),
        event_type="turn_started",
        interaction_id=interaction_id,
        turn_id=turn_id,
        session_id=session_id,
        user_text=user_text,
        mary_response="",
        direction=direction,
        signals=signals,
        status="started",
        started_at=started_at,
        completed_at="",
    )

    state[
        "active_turn"
    ] = {
        "turn_id": turn_id,
        "interaction_id": interaction_id,
        "session_id": session_id,
        "started_at": started_at,
        "status": "started",
        "user_text": resumo_texto(
            user_text,
            360,
        ),
        "direction": deepcopy(
            direction
        ),
        "signals": deepcopy(
            signals
        ),
    }

    return state


def concluir_evento_turno(
    *,
    relationship_state: dict[str, Any],
    interaction_id: str,
    turn_id: str,
    session_id: str,
    user_text: str,
    mary_response: str,
    direction: dict[str, Any],
    signals: dict[str, Any],
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    state = registrar_evento_estado_relacao(
        relationship_state=(
            relationship_state
        ),
        event_type="turn_completed",
        interaction_id=interaction_id,
        turn_id=turn_id,
        session_id=session_id,
        user_text=user_text,
        mary_response=mary_response,
        direction=direction,
        signals=signals,
        status="completed",
        started_at=started_at,
        completed_at=completed_at,
    )

    state[
        "active_turn"
    ] = {
        "turn_id": turn_id,
        "interaction_id": interaction_id,
        "session_id": session_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "status": "completed",
        "user_text": resumo_texto(
            user_text,
            360,
        ),
        "mary_response": resumo_texto(
            mary_response,
            520,
        ),
        "direction": deepcopy(
            direction
        ),
        "signals": deepcopy(
            signals
        ),
    }

    return state


def registrar_inicio_turno(
    *,
    relationship_state: dict[str, Any],
    interaction_id: str,
    turn_id: str,
    session_id: str,
    user_text: str,
    direction: dict[str, Any],
    signals: dict[str, Any],
    started_at: str,
) -> dict[str, Any]:
    return criar_evento_turno_aberto(
        relationship_state=(
            relationship_state
        ),
        interaction_id=interaction_id,
        turn_id=turn_id,
        session_id=session_id,
        user_text=user_text,
        direction=direction,
        signals=signals,
        started_at=started_at,
    )


def registrar_conclusao_turno(
    *,
    relationship_state: dict[str, Any],
    interaction_id: str,
    turn_id: str,
    session_id: str,
    user_text: str,
    mary_response: str,
    direction: dict[str, Any],
    signals: dict[str, Any],
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    return concluir_evento_turno(
        relationship_state=(
            relationship_state
        ),
        interaction_id=interaction_id,
        turn_id=turn_id,
        session_id=session_id,
        user_text=user_text,
        mary_response=mary_response,
        direction=direction,
        signals=signals,
        started_at=started_at,
        completed_at=completed_at,
    )


def gerar_identificadores_turno() -> tuple[str, str, str]:
    interaction_id = gerar_interaction_id()
    turn_id = gerar_turn_id()
    session_id = st.session_state[
        "interaction_session_id"
    ]

    return (
        interaction_id,
        turn_id,
        session_id,
    )


def gerar_timestamp_turno() -> str:
    return gerar_id(
        "time"
    ).replace(
        "time_",
        "",
        1,
    )


def gerar_contexto_debug_turno(
    *,
    interaction_id: str,
    turn_id: str,
    session_id: str,
    relationship_state: dict[str, Any],
    direction: dict[str, Any],
    signals: dict[str, Any],
) -> dict[str, Any]:
    return {
        "interaction_id": interaction_id,
        "turn_id": turn_id,
        "session_id": session_id,
        "relationship_state": criar_snapshot_relacao(
            relationship_state
        ),
        "direction": deepcopy(
            direction
        ),
        "signals": deepcopy(
            signals
        ),
    }


def abrir_turno_interacao(
    *,
    relationship_state: dict[str, Any],
    user_text: str,
    direction: dict[str, Any],
    signals: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    interaction_id, turn_id, session_id = (
        gerar_identificadores_turno()
    )

    started_at = gerar_timestamp_turno()

    relationship_state = registrar_inicio_turno(
        relationship_state=(
            relationship_state
        ),
        interaction_id=interaction_id,
        turn_id=turn_id,
        session_id=session_id,
        user_text=user_text,
        direction=direction,
        signals=signals,
        started_at=started_at,
    )

    metadata = {
        "interaction_id": interaction_id,
        "turn_id": turn_id,
        "session_id": session_id,
        "started_at": started_at,
        "direction": deepcopy(
            direction
        ),
        "signals": deepcopy(
            signals
        ),
    }

    return (
        relationship_state,
        metadata,
    )


def fechar_turno_interacao(
    *,
    relationship_state: dict[str, Any],
    metadata: dict[str, Any],
    user_text: str,
    mary_response: str,
    signals: dict[str, Any],
) -> dict[str, Any]:
    completed_at = gerar_timestamp_turno()

    return registrar_conclusao_turno(
        relationship_state=(
            relationship_state
        ),
        interaction_id=str(
            metadata.get(
                "interaction_id",
                "",
            )
            or ""
        ),
        turn_id=str(
            metadata.get(
                "turn_id",
                "",
            )
            or ""
        ),
        session_id=str(
            metadata.get(
                "session_id",
                "",
            )
            or ""
        ),
        user_text=user_text,
        mary_response=mary_response,
        direction=(
            metadata.get(
                "direction"
            )
            if isinstance(
                metadata.get(
                    "direction"
                ),
                dict,
            )
            else {}
        ),
        signals=signals,
        started_at=str(
            metadata.get(
                "started_at",
                "",
            )
            or ""
        ),
        completed_at=completed_at,
    )


def criar_mensagem_inicial() -> None:
    if st.session_state[
        "initial_message_created"
    ]:
        return

    profile = normalizar_perfil(
        st.session_state[
            "user_profile"
        ]
    )

    first_message = (
        "Oi. Vi que você entrou. Eu sou Mary. "
        "Antes de qualquer coisa, quero entender quem você é."
    )

    if profile.get("name"):
        first_message = (
            f"Oi, {obter_nome_usado_por_mary(profile)}. "
            "Eu lembro de você."
        )

    st.session_state[
        "messages"
    ].append(
        {
            "role": "assistant",
            "content": first_message,
        }
    )

    st.session_state[
        "initial_message_created"
    ] = True


def processar_interacao(
    *,
    prompt: str,
    uploaded_file,
    modelo_utilizado: str,
) -> None:
    api_key = st.secrets.get(
        "OPENROUTER_API_KEY"
    )

    if not api_key:
        st.error(
            "A chave OPENROUTER_API_KEY "
            "não foi configurada nos secrets."
        )
        return

    prepared_image = preparar_upload(
        uploaded_file
    )

    profile = normalizar_perfil(
        st.session_state[
            "user_profile"
        ]
    )

    user_display = prompt

    if prepared_image is not None:
        user_display = (
            f"{prompt}\n\n"
            "[O usuário enviou uma fotografia.]"
        )

    st.session_state[
        "messages"
    ].append(
        {
            "role": "user",
            "content": user_display,
        }
    )

    relationship_state, sexual_state = (
        obter_estados_relacao()
    )

    instancia_cenario = (
        obter_instancia_cenario_ativa()
    )

    relationship_state = sincronizar_relacao_com_cenario(
        relationship_state,
        instancia_cenario,
    )

    scene_state = obter_scene_state_cenario(
        instancia_cenario
    )

    relationship_state_anterior = deepcopy(
        relationship_state
    )

    instancia_cenario_anterior = deepcopy(
        instancia_cenario
    )

    # Detecta o efeito principal do turno do usuário.
    signals = detectar_sinais_relacao(
        user_text=user_display,
        mary_response="",
        interaction_count=int(
            relationship_state.get(
                "interaction_count",
                0,
            )
            or 0
        ),
        has_image=(
            prepared_image is not None
        ),
        user_returned=False,
    )

    relationship_state = atualizar_estado_relacao(
        relationship_state,
        signals=signals,
        incrementar_interacao=False,
    )

    sexual_state = (
        atualizar_estado_sexual_antes_resposta(
            sexual_state,
            user_text=user_display,
            relationship_state=relationship_state,
        )
    )

    relationship_state[
        "sexual_state"
    ] = sexual_state

    relationship_state, turn_intent = (
        planejar_iniciativa_mary(
            relationship_state,
            signals=signals,
        )
    )

    relationship_state, turn_direction = (
        planejar_direcao_turno(
            relationship_state,
            signals=signals,
            turn_intent=turn_intent,
        )
    )

    metadata_turno: dict[str, Any] = {}

    if instancia_cenario:
        interaction_number_cenario = int(
            instancia_cenario.get(
                "interaction_count",
                0,
            )
            or 0
        ) + 1

        scenario_config = instancia_cenario.get(
            "scenario_config"
        )

        if not isinstance(
            scenario_config,
            dict,
        ):
            scenario_config = {}

        mensagens_recentes = st.session_state.get(
            "messages",
            [],
        )

        if not isinstance(
            mensagens_recentes,
            list,
        ):
            mensagens_recentes = []

        ultima_resposta_mary = ""

        for mensagem in reversed(
            mensagens_recentes
        ):
            if (
                isinstance(mensagem, dict)
                and mensagem.get("role") == "assistant"
            ):
                ultima_resposta_mary = str(
                    mensagem.get("content")
                    or ""
                ).strip()
                break

        analysis = analisar_turno_cenario(
            api_key=api_key,
            model=modelo_utilizado,
            scenario_config=scenario_config,
            scene_state=scene_state,
            user_text=user_display,
            last_mary_response=(
                ultima_resposta_mary
            ),
            recent_messages=(
                mensagens_recentes[-8:]
            ),
        )

        scene_state = aplicar_analise_ao_estado(
            scene_state=scene_state,
            analise=analysis,
            interaction_number=(
                interaction_number_cenario
            ),
        )

        turn_direction = integrar_direcao_cenario(
            turn_direction=turn_direction,
            analise_cenario=analysis,
            scene_state=scene_state,
        )

        relationship_state[
            "current_turn_intent"
        ] = turn_intent

        relationship_state[
            "current_turn_direction"
        ] = turn_direction

        relationship_state = sincronizar_relacao_com_cenario(
            relationship_state,
            instancia_cenario,
        )

        direcao_narrativa_cenario = (
            montar_direcao_narrativa(
                analise=analysis,
                scene_state=scene_state,
            )
        )
    else:
        interaction_number_cenario = 0
        analysis = {}
        direcao_narrativa_cenario = ""

    relationship_state, metadata_turno = (
        abrir_turno_interacao(
            relationship_state=(
                relationship_state
            ),
            user_text=user_display,
            direction=turn_direction,
            signals=signals,
        )
    )

    st.session_state[
        "relationship_state"
    ] = relationship_state

    prompt_sistema_base = montar_prompt_sistema(
        user_profile=profile,
        mary_profile=st.session_state[
            "mary_profile"
        ],
        relationship_state=relationship_state,
        sexual_state=sexual_state,
        turn_intent=turn_intent,
        turn_direction=turn_direction,
    )

    blocos_cenario: list[str] = []

    if instancia_cenario:
        prompt_cenario = str(
            instancia_cenario.get(
                "scenario_prompt",
                "",
            )
            or ""
        ).strip()

        if prompt_cenario:
            blocos_cenario.append(
                prompt_cenario
            )

        contexto_configuracao = (
            construir_contexto_configuracao_cenario(
                instancia_cenario
            )
        )

        blocos_cenario.append(
            (
                "[CONFIGURAÇÃO DO CENÁRIO ATIVO]\n\n"
                + json.dumps(
                    contexto_configuracao,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
        )

    if scene_state:
        blocos_cenario.append(
            (
                "[ESTADO ATUAL DA FANTASIA]\n\n"
                + json.dumps(
                    scene_state,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
        )

        blocos_cenario.append(
            """
USO OBRIGATÓRIO DO ESTADO DA FANTASIA:

- Trate os campos preenchidos como fatos válidos apenas dentro desta fantasia.
- Mary já está dentro da situação e fala a partir dela.
- Não repita que se trata de fantasia, hipótese ou imaginação.
- Não recite o estado estruturado.
- Não descreva Mary em terceira pessoa.
- Não narre ações como autora externa.
- Não reinicie a abertura do cenário.
- Não repita acontecimentos já concluídos.
- Preserve local, personagens presentes, roupas, objetos e condições confirmadas.
- Reaja ao que o usuário acabou de fazer ou dizer.
- Avance somente o movimento atual.
- Não execute todas as fases do roteiro de uma vez.
- A cena deve se adaptar às decisões do usuário.
- Mary fala em primeira pessoa e predominantemente no presente.
""".strip()
        )

    partes_prompt_sistema = [
        prompt_sistema_base,
        *blocos_cenario,
    ]

    if direcao_narrativa_cenario:
        partes_prompt_sistema.append(
            direcao_narrativa_cenario
        )

    prompt_sistema_completo = "\n\n".join(
        str(parte).strip()
        for parte in partes_prompt_sistema
        if str(
            parte or ""
        ).strip()
    )

    messages = [
        {
            "role": "system",
            "content": prompt_sistema_completo,
        },
        *construir_historico_api()[:-1],
        montar_mensagem_usuario(
            prompt,
            prepared_image,
        ),
    ]

    image_metadata = montar_metadados_imagem(
        prepared_image
    )

    inicio_resposta = time.perf_counter()

    with st.chat_message(
        "assistant"
    ):
        with st.spinner(
            "Mary está pensando..."
        ):
            try:
                resposta = chamar_openrouter(
                    messages=messages,
                    model=modelo_utilizado,
                    api_key=api_key,
                )

                validacao_sexual = (
                    validar_resposta_sexual(
                        sexual_state,
                        resposta,
                    )
                )

            except OpenRouterError as exc:
                response_time_ms = round(
                    (
                        time.perf_counter()
                        - inicio_resposta
                    )
                    * 1000
                )

                st.session_state[
                    "relationship_state"
                ] = relationship_state_anterior

                st.session_state[
                    "scenario_instance"
                ] = instancia_cenario_anterior

                registro_erro = (
                    criar_registro_interacao(
                        session_id=st.session_state[
                            "interaction_session_id"
                        ],
                        model=modelo_utilizado,
                        user_text=user_display,
                        mary_response="",
                        user_profile=st.session_state[
                            "user_profile"
                        ],
                        image_metadata=image_metadata,
                        turn_direction=turn_direction,
                        raw_messages=messages,
                        mary_asked_name=False,
                        response_time_ms=(
                            response_time_ms
                        ),
                        error=str(exc),
                    )
                )

                registrar_interacao_local_e_remota(
                    registro_erro
                )

                st.error(
                    str(exc)
                )

                if st.session_state[
                    "messages"
                ]:
                    st.session_state[
                        "messages"
                    ].pop()

                return

        if not validacao_sexual.get(
            "valid",
            True,
        ):
            st.session_state[
                "last_sexual_validation"
            ] = validacao_sexual
        else:
            st.session_state[
                "last_sexual_validation"
            ] = {
                "valid": True,
                "errors": [],
            }

        st.markdown(
            resposta
        )

    response_time_ms = round(
        (
            time.perf_counter()
            - inicio_resposta
        )
        * 1000
    )

    sexual_state = (
        atualizar_estado_sexual_apos_resposta(
            sexual_state,
            user_text=user_display,
            mary_response=resposta,
        )
    )

    relationship_state[
        "sexual_state"
    ] = sexual_state

    # Observa também o que Mary efetivamente respondeu.
    # Os campos mary_* são diagnósticos e não aumentam
    # diretamente o vínculo.
    completed_signals = detectar_sinais_relacao(
        user_text=user_display,
        mary_response=resposta,
        interaction_count=int(
            relationship_state.get(
                "interaction_count",
                0,
            )
            or 0
        ),
        has_image=(
            prepared_image is not None
        ),
        user_returned=False,
    )

    relationship_state = (
        sincronizar_iniciativa_apos_resposta(
            relationship_state,
            turn_intent=turn_intent,
        )
    )

    relationship_state = (
        sincronizar_direcao_apos_resposta(
            relationship_state,
            turn_direction=turn_direction,
        )
    )

    relationship_state = atualizar_estado_relacao(
        relationship_state,
        signals=completed_signals,
        incrementar_interacao=True,
    )

    relationship_state[
        "sexual_state"
    ] = sexual_state

    relationship_state = fechar_turno_interacao(
        relationship_state=(
            relationship_state
        ),
        metadata=metadata_turno,
        user_text=user_display,
        mary_response=resposta,
        signals=completed_signals,
    )

    st.session_state[
        "relationship_state"
    ] = relationship_state

    # =====================================================
    # SINCRONIZAÇÃO DO CENÁRIO APÓS RESPOSTA
    # =====================================================

    if instancia_cenario:
        scene_state = deepcopy(
            scene_state
        )

        scene_state[
            "last_user_action"
        ] = user_display

        scene_state[
            "last_mary_response"
        ] = resposta

        scene_state[
            "interaction_count"
        ] = interaction_number_cenario

        instancia_cenario[
            "scene_state"
        ] = scene_state

        instancia_cenario[
            "interaction_count"
        ] = interaction_number_cenario

        instancia_cenario[
            "current_phase"
        ] = str(
            scene_state.get(
                "current_phase",
                instancia_cenario.get(
                    "current_phase",
                    "opening",
                ),
            )
            or "opening"
        )

        instancia_cenario[
            "current_route"
        ] = str(
            scene_state.get(
                "current_route",
                instancia_cenario.get(
                    "current_route",
                    "",
                ),
            )
            or ""
        )

        instancia_cenario[
            "current_beat"
        ] = str(
            scene_state.get(
                "current_beat",
                instancia_cenario.get(
                    "current_beat",
                    "",
                ),
            )
            or ""
        )

        instancia_cenario[
            "active_hook"
        ] = str(
            scene_state.get(
                "active_hook",
                instancia_cenario.get(
                    "active_hook",
                    "",
                ),
            )
            or ""
        )

        st.session_state[
            "scenario_instance"
        ] = instancia_cenario

    # =====================================================
    # PERFIL DO USUÁRIO E REGISTRO
    # =====================================================

    st.session_state[
        "messages"
    ].append(
        {
            "role": "assistant",
            "content": resposta,
        }
    )

    st.session_state[
        "user_profile"
    ] = marcar_interacao_realizada(
        st.session_state[
            "user_profile"
        ]
    )

    perguntou_nome = mary_perguntou_nome(
        resposta
    )

    registro = criar_registro_interacao(
        session_id=st.session_state[
            "interaction_session_id"
        ],
        model=modelo_utilizado,
        user_text=user_display,
        mary_response=resposta,
        user_profile=st.session_state[
            "user_profile"
        ],
        image_metadata=image_metadata,
        turn_direction=turn_direction,
        raw_messages=messages,
        mary_asked_name=perguntou_nome,
        response_time_ms=response_time_ms,
    )

    registrar_interacao_local_e_remota(
        registro
    )

    profile = st.session_state[
        "user_profile"
    ]

    if (
        not profile.get(
            "name"
        )
        and perguntou_nome
    ):
        st.session_state[
            "show_name_form"
        ] = True

    st.rerun()


def garantir_usuario_autenticado() -> dict[str, Any]:
    usuario = st.session_state.get(
        "auth_user"
    )

    user_id = ""

    if isinstance(
        usuario,
        dict,
    ):
        user_id = str(
            usuario.get(
                "user_id",
                "",
            )
            or ""
        ).strip()

    if (
        st.session_state.get(
            "authenticated"
        ) is True
        and user_id
    ):
        return usuario

    resultado = renderizar_tela_login()

    if not isinstance(
        resultado,
        dict,
    ) or not resultado.get(
        "authenticated"
    ):
        st.stop()

    usuario = resultado.get(
        "user"
    )

    if not isinstance(
        usuario,
        dict,
    ):
        st.error(
            "Não foi possível concluir a autenticação."
        )
        st.stop()

    user_id = str(
        usuario.get(
            "user_id",
            "",
        )
        or ""
    ).strip()

    if not user_id:
        st.error(
            "A conta autenticada não possui um identificador válido."
        )
        st.stop()

    st.session_state[
        "auth_user"
    ] = usuario
    st.session_state[
        "persistent_user"
    ] = usuario
    st.session_state[
        "authenticated"
    ] = True
    st.session_state[
        "persistence_initialized"
    ] = False
    st.session_state[
        "history_restored"
    ] = False

    st.rerun()


def renderizar_seletor_cenario() -> None:
    instancia_atual = st.session_state.get(
        "scenario_instance"
    )

    if (
        isinstance(
            instancia_atual,
            dict,
        )
        and instancia_atual.get(
            "status"
        ) == "active"
    ):
        return

    usuario = (
        st.session_state.get(
            "auth_user"
        )
        or {}
    )

    user_id = str(
        usuario.get(
            "user_id",
            "",
        )
        or ""
    ).strip()

    if not user_id:
        st.error(
            "O usuário atual ainda não foi identificado."
        )
        st.stop()

    unlocked_scenario_ids: set[str] = set()

    try:
        cenarios = listar_cenarios_para_usuario(
            user_id=user_id,
            unlocked_scenario_ids=(
                unlocked_scenario_ids
            ),
        )
    except ValueError as exc:
        st.error(
            str(exc)
        )
        st.stop()

    acao = renderizar_menu_cenarios(
        cenarios,
        titulo=(
            "Escolha sua experiência com Mary"
        ),
        descricao=(
            "Cada experiência inicia uma fantasia diferente "
            "e mantém sua própria continuidade."
        ),
        quantidade_colunas=2,
    )

    if acao is None:
        st.stop()

    tipo_acao = str(
        acao.get(
            "action",
            "",
        )
        or ""
    ).strip()

    scenario_id = str(
        acao.get(
            "scenario_id",
            "",
        )
        or ""
    ).strip()

    if not scenario_id:
        st.error(
            "Não foi possível identificar a história escolhida."
        )
        st.stop()

    if tipo_acao == ACTION_UNLOCK:
        st.info(
            "O desbloqueio de novas histórias será conectado "
            "ao sistema de cobrança em uma etapa posterior."
        )
        st.stop()

    if tipo_acao != ACTION_PLAY:
        st.stop()

    try:
        instancia = iniciar_cenario_para_usuario(
            scenario_id=scenario_id,
            user_id=user_id,
            unlocked_scenario_ids=(
                unlocked_scenario_ids
            ),
        )
    except ScenarioAccessError as exc:
        st.error(
            str(exc)
        )
        st.stop()
    except ValueError as exc:
        st.error(
            str(exc)
        )
        st.stop()

    st.session_state[
        "scenario_instance"
    ] = instancia
    st.session_state[
        "selected_scenario_id"
    ] = scenario_id
    st.session_state[
        "scenario_selector_visible"
    ] = False
    st.session_state[
        "messages"
    ] = []
    st.session_state[
        "initial_message_created"
    ] = False
    st.session_state[
        "history_restored"
    ] = True

    st.rerun()


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="💬",
        layout="centered",
    )

    inicializar_sessao_local()

    st.title(
        APP_TITLE
    )

    st.caption(
        APP_CAPTION
    )

    garantir_usuario_autenticado()

    mensagem_operacao = st.session_state.pop(
        "mensagem_operacao_persistente",
        "",
    )

    resultado_operacao = st.session_state.pop(
        "resultado_operacao_persistente",
        None,
    )

    if mensagem_operacao:
        st.success(
            mensagem_operacao
        )

    if isinstance(
        resultado_operacao,
        dict,
    ):
        with st.expander(
            "Registros removidos"
        ):
            st.json(
                resultado_operacao
            )

    with st.sidebar:
        st.subheader(
            "Configuração"
        )

        usuario_logado = st.session_state.get(
            "auth_user"
        ) or {}

        email_logado = str(
            usuario_logado.get(
                "email",
                "",
            )
            or ""
        ).strip()

        if email_logado:
            st.caption(
                f"Conectado como {email_logado}"
            )

        if st.button(
            "Sair",
            use_container_width=True,
        ):
            encerrar_login_local()
            st.rerun()

        st.divider()

        model = st.text_input(
            "Modelo OpenRouter",
            value=MODEL_DEFAULT,
        )

        modelo_utilizado = (
            model.strip()
            or MODEL_DEFAULT
        )

        inicializar_persistencia(
            modelo_utilizado
        )

        uploaded_file = st.file_uploader(
            "Mostrar uma fotografia para Mary",
            type=[
                "jpg",
                "jpeg",
                "png",
                "webp",
            ],
            accept_multiple_files=False,
        )

        renderizar_identidade_persistente()
        renderizar_diagnostico_perfil()
        renderizar_log_interacoes()

        if st.button(
            "Limpar conversa desta tela",
            use_container_width=True,
        ):
            limpar_conversa()
            st.rerun()

        with st.expander(
            "Gerenciar dados persistentes"
        ):
            st.caption(
                "As operações abaixo alteram os registros "
                "salvos no Google Sheets."
            )

            confirmar_limpeza = st.checkbox(
                "Confirmo que desejo apagar todas as interações "
                "e reiniciar a relação com Mary",
                key="confirmar_limpeza_interacoes",
            )

            if st.button(
                "Limpar interações",
                use_container_width=True,
                disabled=not confirmar_limpeza,
            ):
                try:
                    with st.spinner(
                        "Limpando interações..."
                    ):
                        resultado = (
                            executar_limpeza_interacoes()
                        )

                    st.session_state[
                        "mensagem_operacao_persistente"
                    ] = (
                        "As interações foram apagadas. "
                        "O usuário cadastrado foi preservado."
                    )

                    st.session_state[
                        "resultado_operacao_persistente"
                    ] = resultado

                    st.rerun()

                except GoogleSheetsRepositoryError as exc:
                    st.error(
                        "Não foi possível limpar "
                        f"as interações: {exc}"
                    )

            confirmar_exclusao = st.checkbox(
                "Confirmo que desejo excluir este usuário "
                "e todos os dados relacionados",
                key="confirmar_exclusao_usuario",
            )

            if st.button(
                "Excluir usuário",
                use_container_width=True,
                disabled=not confirmar_exclusao,
            ):
                try:
                    with st.spinner(
                        "Excluindo usuário e dados..."
                    ):
                        resultado = (
                            executar_exclusao_usuario()
                        )

                    st.session_state[
                        "mensagem_operacao_persistente"
                    ] = (
                        "O usuário e todos os dados relacionados "
                        "foram excluídos."
                    )

                    st.session_state[
                        "resultado_operacao_persistente"
                    ] = resultado

                    st.rerun()

                except GoogleSheetsRepositoryError as exc:
                    st.error(
                        "Não foi possível excluir "
                        f"o usuário: {exc}"
                    )

    instancia_cenario = (
        obter_instancia_cenario_ativa()
    )

    if instancia_cenario:
        st.caption(
            "História ativa: "
            + str(
                instancia_cenario.get(
                    "scenario_config",
                    {},
                ).get(
                    "title",
                    instancia_cenario.get(
                        "scenario_id",
                        "",
                    ),
                )
            )
        )
    else:
        renderizar_seletor_cenario()
        st.stop()

    if not st.session_state[
        "mary_profile"
    ]["relationship_state"][
        "public_profile_seen"
    ]:
        renderizar_perfil_publico_mary()
        st.stop()

    iniciar_revelacao_visual_mary()
    renderizar_revelacao_visual_mary()

    criar_mensagem_inicial_cenario(
        instancia_cenario
    )

    for message in st.session_state[
        "messages"
    ]:
        with st.chat_message(
            message["role"]
        ):
            st.markdown(
                message["content"]
            )

    renderizar_formulario_nome()

    prompt = st.chat_input(
        "Escreva sua mensagem para Mary"
    )

    if prompt:
        processar_interacao(
            prompt=prompt,
            uploaded_file=uploaded_file,
            modelo_utilizado=modelo_utilizado,
        )


if __name__ == "__main__":
    main()
