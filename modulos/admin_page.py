import streamlit as st
import pandas as pd

# --- IMPORTS CORRIGIDOS ---
# Importa funções de tratamento e formatação
from modulos.tratamento import formatar_milhar_br
# Importa KPIs
from modulos.kpi import calcular_metricas
# Importa funções de categoria (AGORA SEM O style_nome_categoria AQUI)
from modulos.categoria import calcular_categorias, get_contagem_categoria, get_pontuacao_temporada_anterior
# Importa carregamento de dados e config
from modulos.dados import carregar_e_tratar_dados
from modulos.config import Relatorio

# Importa as páginas (Módulos de UI)
import modulos.admin_page as admin_page
import modulos.architect_page as architect_page

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(
    page_title="Gabriel Pro | Portal",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- INICIALIZAÇÃO DE ESTADO ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_type' not in st.session_state:
    st.session_state.user_type = None 
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# Metas Globais (Padrão)
if 'config_metas' not in st.session_state:
    st.session_state.config_metas = {
        "m1_meta": "2.000 pts", "m2_meta": "6.000 pts", "m3_meta": "500 pts",
        "m1_acao": "Viagem para Douro", "m2_acao": "Carro 100 Mil", "m3_acao": "Voucher Gabriel Pro",
        "acelerador": "Campanha de Verão: Pontos em dobro em Outubro."
    }

# Cache de Dados Global (Tenta carregar ao iniciar)
if 'df_global' not in st.session_state:
    try:
        df, df_novos = carregar_e_tratar_dados(Relatorio)
        st.session_state.df_global = df
        st.session_state.df_novos_global = df_novos
    except Exception as e:
        st.error(f"Erro ao carregar dados iniciais: {e}")
        st.session_state.df_global = pd.DataFrame()

# --- TELA DE LOGIN ---
def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #0f172a;'>GABRIEL PRO</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b;'>Portal de Relacionamento</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            tabs = st.tabs(["Especificador", "Administrador"])
            
            # --- LOGIN ARQUITETO ---
            with tabs[0]:
                st.info("Acesse seus resultados e prêmios.")
                cpf_input = st.text_input("CPF ou CNPJ", placeholder="000.000.000-00")
                
                if st.button("Acessar Painel", type="primary", key="btn_arq"):
                    cpf_limpo = str(cpf_input).replace('.', '').replace('-', '').replace('/', '').strip()
                    
                    # Backdoor para testes (seus CPFs de exemplo)
                    if cpf_limpo in ["02184640883", "70232172153"]:
                        st.session_state.logged_in = True
                        st.session_state.user_type = 'architect'
                        st.session_state.user_id = cpf_limpo
                        st.rerun()
                    
                    # Verificação na base real
                    df_check = st.session_state.df_global
                    if not df_check.empty:
                        existe = df_check[
                            (df_check['CNPJ_CPF_LIMPO'] == cpf_limpo) | 
                            (df_check['CPF/CNPJ'] == cpf_input)
                        ].shape[0] > 0
                        
                        if existe:
                            st.session_state.logged_in = True
                            st.session_state.user_type = 'architect'
                            st.session_state.user_id = cpf_limpo
                            st.rerun()
                        elif cpf_limpo not in ["02184640883", "70232172153"]:
                            st.error("CPF/CNPJ não encontrado.")

            # --- LOGIN ADMIN ---
            with tabs[1]:
                user = st.text_input("Usuário Admin")
                pwd = st.text_input("Senha", type="password")
                if st.button("Entrar", key="btn_admin"):
                    if user == "admin" and pwd == "admin":
                        st.session_state.logged_in = True
                        st.session_state.user_type = 'admin'
                        st.session_state.user_id = 'Administrador'
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas.")

# --- ROTEADOR ---
if not st.session_state.logged_in:
    login_screen()
else:
    if st.session_state.user_type == 'admin':
        admin_page.app()
    elif st.session_state.user_type == 'architect':
        architect_page.app(st.session_state.user_id)