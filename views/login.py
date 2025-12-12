import streamlit as st
import time
# Certifique-se que essas variáveis existem no seu modulos/config.py
from modulos.config import COLUNA_CHAVE_CONSOLIDADA, Relatorio 
# Importa a função que acabamos de adicionar
from modulos.dados import carregar_credenciais_lojas 

def show_login(df_global):
    st.markdown("<h1 style='text-align: center;'>🔐 Acesso Gabriel Pro</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.info("👉 **Admin:** Usuário/Senha \n👉 **Lojista:** CNPJ/Senha \n👉 **Arquiteto:** CPF (Apenas números)")
        
        with st.form(key='login_form'):
            username = st.text_input("Usuário, CPF ou CNPJ")
            password = st.text_input("Senha (Opcional para Arquiteto)", type="password")
            submit_button = st.form_submit_button(label="Entrar")
            
        if submit_button:
            # Limpeza básica dos inputs
            user_input_limpo = str(username).replace('.', '').replace('-', '').replace('/', '').strip()
            pass_input_limpo = str(password).strip()

            # ---------------------------------------------------------
            # 1. TENTA LOGIN ADMIN
            # ---------------------------------------------------------
            if username == "admin" and password == "1234":
                st.success("Login Admin realizado!")
                time.sleep(0.5)
                st.session_state['logged_in'] = True
                st.session_state['user_type'] = 'admin'
                st.rerun()
            
            # ---------------------------------------------------------
            # 2. TENTA LOGIN LOJA (Verifica na aba 'Loja' do Excel)
            # ---------------------------------------------------------
            # Carrega credenciais das lojas
            df_creds_loja = carregar_credenciais_lojas(Relatorio)
            
            if not df_creds_loja.empty:
                # Filtra onde CNPJ e Senha batem
                loja_encontrada = df_creds_loja[
                    (df_creds_loja['CNPJ'] == user_input_limpo) & 
                    (df_creds_loja['Senha'] == pass_input_limpo)
                ]
                
                if not loja_encontrada.empty:
                    # Pega os dados da primeira linha encontrada
                    nome_loja = loja_encontrada.iloc[0]['Loja']
                    # Verifica se a coluna Responsável existe, senão usa 'Gerente'
                    responsavel = loja_encontrada.iloc[0]['Responsável'] if 'Responsável' in loja_encontrada.columns else "Gerente"
                    
                    st.success(f"Bem-vindo, {responsavel} ({nome_loja})!")
                    time.sleep(0.5)
                    
                    st.session_state['logged_in'] = True
                    st.session_state['user_type'] = 'loja'
                    st.session_state['user_loja_nome'] = nome_loja
                    st.session_state['user_loja_resp'] = responsavel
                    st.rerun()

            # ---------------------------------------------------------
            # 3. TENTA LOGIN ARQUITETO (Lógica Consolidada - Sem senha)
            # ---------------------------------------------------------
            if 'CNPJ_CPF_LIMPO' in df_global.columns and COLUNA_CHAVE_CONSOLIDADA in df_global.columns:
                # Procura o CPF/CNPJ na base global de vendas
                usuario_encontrado = df_global[df_global['CNPJ_CPF_LIMPO'] == user_input_limpo]
                
                if not usuario_encontrado.empty:
                    # Pega a Chave Consolidada (Grupo/Empresa)
                    chave_do_usuario = usuario_encontrado[COLUNA_CHAVE_CONSOLIDADA].iloc[0]
                    
                    st.success(f"Bem-vindo! Acessando dados de: {chave_do_usuario}")
                    time.sleep(0.5)
                    
                    st.session_state['logged_in'] = True
                    st.session_state['user_type'] = 'arquiteto'
                    st.session_state['user_key'] = chave_do_usuario
                    st.rerun()
                else:
                    # Se chegou aqui, não achou em Admin, nem Loja, nem Arquiteto
                    st.error("Credenciais inválidas ou usuário não encontrado.")
            else:
                st.error("Erro: Base de dados não carregada corretamente.")