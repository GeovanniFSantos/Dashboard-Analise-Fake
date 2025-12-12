# Módulo: dados.py

import pandas as pd
import streamlit as st
import numpy as np

# Importa as constantes globais
from modulos.config import (
    COLUNAS_NUMERICAS, 
    COLUNA_NUMERO_TEMPORADA, 
    COLUNA_PEDIDO, 
    COLUNA_CNPJ_CPF, 
    COLUNA_ESPECIFICADOR, 
    COLUNA_CPF_NOVO_CADASTRO,
    NOME_ABA_MAP_CPF_CNPJ, 
    COLUNA_CHAVE_CONSOLIDADA, 
    COLUNA_NOME_MAP_CONSOLIDACAO,
    MES_ORDEM_FISCAL 
)

# Função para carregar os dados (usa cache do streamlit para ser mais rápido)
@st.cache_data
def carregar_e_tratar_dados(caminho_arquivo):
    """Lê o arquivo Excel (2 abas + Mapeamento), trata colunas e retorna um DataFrame do Pandas."""
    try:
        # LER A ABA PRINCIPAL (Relatório)
        df = pd.read_excel(caminho_arquivo, sheet_name=0)

        # LER A ABA DE NOVOS CADASTRADOS
        df_novos = pd.DataFrame()
        try:
            df_novos = pd.read_excel(caminho_arquivo, sheet_name='Novos Cadastrados')
        except ValueError:
            st.error(f"❌ Erro: A aba 'Novos Cadastrados' não foi encontrada no arquivo '{caminho_arquivo}'.")
        except FileNotFoundError:
            st.error(f"❌ Erro: O arquivo '{caminho_arquivo}' não foi encontrado.")

        # LER A ABA DE MAPEAMENTO DE CONSOLIDAÇÃO (NOVO)
        df_map_completo = pd.DataFrame()
        try:
            df_map_completo = pd.read_excel(caminho_arquivo, sheet_name=NOME_ABA_MAP_CPF_CNPJ)
        except ValueError:
            st.warning(f"⚠️ Aviso: A aba '{NOME_ABA_MAP_CPF_CNPJ}' não foi encontrada. A consolidação de entidades será feita pelo CPF/CNPJ Limpo.")
        except FileNotFoundError:
            st.warning(f"⚠️ Aviso: O arquivo '{caminho_arquivo}' não foi encontrado.")
            return pd.DataFrame(), pd.DataFrame() 

        # === ETAPA DE TRATAMENTO DE DADOS (DF PRINCIPAL) ===
        # 1. Tratamento de Colunas Numéricas
        for col in COLUNAS_NUMERICAS:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'[^0-9,.]', '', regex=True)
                df[col] = df[col].str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        # 2. Garantir que 'Data da Venda' seja datetime e filtrar dados inválidos
        if 'Data da Venda' in df.columns:
            # CORREÇÃO 1: Adicionando dayfirst=True para tratar o UserWarning de formato de data DD/MM/AAAA
            df['Data da Venda'] = pd.to_datetime(df['Data da Venda'], errors='coerce', dayfirst=True)
            df.dropna(subset=['Data da Venda'], inplace=True) 
            
            # 3. CRIAÇÃO DAS COLUNAS DE MÊS, ANO E TEMPORADA
            df['Ano'] = df['Data da Venda'].dt.year.astype(str)
            df['Mês_num'] = df['Data da Venda'].dt.month.astype(str)
            
            if COLUNA_NUMERO_TEMPORADA in df.columns:
                df[COLUNA_NUMERO_TEMPORADA] = pd.to_numeric(df[COLUNA_NUMERO_TEMPORADA], errors='coerce').fillna(0).astype(int)
                df['Temporada_Exibicao'] = 'Temporada ' + df[COLUNA_NUMERO_TEMPORADA].astype(str)
            
            # 4. Mapeamento e Formatação para o Filtro de Mês 
            nomes_meses_map = {
                '1': 'Jan (01)', '2': 'Fev (02)', '3': 'Mar (03)', '4': 'Abr (04)',
                '5': 'Mai (05)', '6': 'Jun (06)', '7': 'Jul (07)', '8': 'Ago (08)',
                '9': 'Set (09)', '10': 'Out (10)', '11': 'Nov (11)', '12': 'Dez (12)'
            }
            df['Mês_Exibicao'] = df['Mês_num'].map(nomes_meses_map)
            
            # 5. CRÍTICO: LIMPEZA DO CPF/CNPJ (base para todas as análises de identidade)
            if COLUNA_CNPJ_CPF in df.columns:
                df['CNPJ_CPF_LIMPO'] = df[COLUNA_CNPJ_CPF].astype(str).str.replace(r'[^0-9]', '', regex=True)
            else:
                df['CNPJ_CPF_LIMPO'] = ''

            # === 6. LÓGICA DE CONSOLIDAÇÃO DE ENTIDADES (PARA O ITEM 8) ===
            
            if not df_map_completo.empty and COLUNA_NOME_MAP_CONSOLIDACAO in df_map_completo.columns:
                
                # 6.1. Prepara a base de mapeamento
                df_map_completo['CNPJ_CPF_LIMPO'] = df_map_completo['CPF'].astype(str).str.replace(r'[^0-9]', '', regex=True)
                
                # Seleciona o vínculo (o CPF/CNPJ limpo vira a chave para a Chave_Consolidada)
                df_map_simplificado = df_map_completo[['CNPJ_CPF_LIMPO', COLUNA_NOME_MAP_CONSOLIDACAO]].copy()
                
                # Garante que não há duplicatas de mapeamento (usa o primeiro 'Nome Fantasia' se houver conflito)
                df_map_simplificado = df_map_simplificado.drop_duplicates(subset=['CNPJ_CPF_LIMPO'], keep='first')
                
                # Renomeia a coluna de referência para a chave de consolidação que usaremos.
                df_map_simplificado.rename(columns={COLUNA_NOME_MAP_CONSOLIDACAO: COLUNA_CHAVE_CONSOLIDADA}, inplace=True)

                # 6.2. Faz o MERGE com o DF principal
                df = pd.merge(
                    df, 
                    df_map_simplificado, 
                    on='CNPJ_CPF_LIMPO', 
                    how='left'
                )
                
                # 6.3. Fallback: Se não tem mapeamento, a chave de consolidação é o próprio Especificador/Empresa
                df[COLUNA_CHAVE_CONSOLIDADA] = df[COLUNA_CHAVE_CONSOLIDADA].fillna(df[COLUNA_ESPECIFICADOR])
            else:
                # Fallback Mestre: Se não houver aba de mapeamento ou coluna, a chave é o próprio CNPJ/CPF Limpo
                df[COLUNA_CHAVE_CONSOLIDADA] = df['CNPJ_CPF_LIMPO']

            # === 7. LÓGICA DE NOVO CADASTRADO ===
            if COLUNA_CNPJ_CPF in df.columns and COLUNA_NUMERO_TEMPORADA in df.columns:
                # Adicionado 'Data De Cadastro' no check de colunas
                if COLUNA_CPF_NOVO_CADASTRO in df_novos.columns and 'Temporada' in df_novos.columns and 'Data De Cadastro' in df_novos.columns: 
                    
                    df_novos['CPF_LIMPO'] = df_novos[COLUNA_CPF_NOVO_CADASTRO].astype(str).str.replace(r'[^0-9]', '', regex=True)
                    
                    # CORREÇÃO 2: Limpa todos os caracteres não numéricos antes de converter para int
                    df_novos['Temporada_Cadastro_Original'] = df_novos['Temporada'].astype(str).str.replace(r'[^0-9]', '', regex=True)
                    df_novos['Temporada_Cadastro_Original'] = pd.to_numeric(df_novos['Temporada_Cadastro_Original'], errors='coerce').fillna(0).astype(int)
                    
                    # Mapeia os dados do cadastro original para o DF de Vendas
                    df_map_cadastro = df_novos.groupby('CPF_LIMPO').agg(
                        Temporada_Cadastro_Original=('Temporada_Cadastro_Original', 'first'),
                        Data_Cadastro=('Data De Cadastro', 'first') # Nova coluna de data de cadastro
                    ).reset_index()
                    
                    df = pd.merge(
                        df, 
                        df_map_cadastro, 
                        left_on='CNPJ_CPF_LIMPO', 
                        right_on='CPF_LIMPO', 
                        how='left'
                    )
                    # Preenche NaN com 0 para temporada e cria a coluna de flag
                    df['Temporada_Cadastro_Original'] = df['Temporada_Cadastro_Original'].fillna(0).astype(int)
                    df['Novo_Cadastro_Existe'] = (df['Temporada_Cadastro_Original'] > 0)
                    
                    # --- NOVO: ENCONTRA A PRIMEIRA COMPRA HISTÓRICA DO CLIENTE ---
                    df_primeira_compra = df.groupby('CNPJ_CPF_LIMPO')['Data da Venda'].min().reset_index()
                    df_primeira_compra.columns = ['CNPJ_CPF_LIMPO', 'Data_Primeira_Compra_Historica']
                    df = pd.merge(df, df_primeira_compra, on='CNPJ_CPF_LIMPO', how='left')
                    
                    # NOVO FLAG: Identifica a linha da primeira compra histórica (usado no Item 9A para contagem)
                    df['Primeira_Compra_Geral'] = df['Data da Venda'] == df['Data_Primeira_Compra_Historica']


                    # === LÓGICA NOVO_CADASTRADO (MANTIDA PARA COERÊNCIA com Item 9B/9C) ===
                    # Uma venda é considerada de um "Novo Cadastrado ATIVO" se:
                    # 1. O cliente está na lista de Novos Cadastrados
                    # 2. A Temporada da VENDA (df[COLUNA_NUMERO_TEMPORADA]) é igual à Temporada de CADASTRO (coorte)
                    # 3. A venda pontuou (> 0)
                    df['Novo_Cadastrado'] = np.where(
                        (df['Novo_Cadastro_Existe'] == True) & 
                        (df[COLUNA_NUMERO_TEMPORADA] == df['Temporada_Cadastro_Original']) &
                        (df['Pontos'] > 0), # Apenas se a venda pontuou
                        True,
                        False
                    )
                    # Remove colunas auxiliares
                    df.drop(columns=['CPF_LIMPO'], inplace=True, errors='ignore')
                else:
                    df['Novo_Cadastrado'] = False
                    df['Primeira_Compra_Geral'] = False # Novo fallback
                
                # Mapeamento da aba de Novos Cadastrados (para o Item 9C)
                # Adicionamos Nome, E-mail, Telefone e Data de Cadastro para o Item 9C
                if all(col in df_novos.columns for col in ['Nome', COLUNA_CPF_NOVO_CADASTRO, 'E-mail', 'Telefone', 'Temporada', 'Data De Cadastro']):
                    df_novos_cadastrados_original = df_novos[['Nome', COLUNA_CPF_NOVO_CADASTRO, 'E-mail', 'Telefone', 'Temporada', 'Data De Cadastro']].copy()
                else:
                    st.warning("⚠️ Aviso: Colunas necessárias para o Item 9C (Nome, E-mail, Telefone, Data De Cadastro) não encontradas na aba 'Novos Cadastrados'.")
                    df_novos_cadastrados_original = df_novos[['Nome', COLUNA_CPF_NOVO_CADASTRO, 'Temporada']].copy()

            return df, df_novos_cadastrados_original
        
    except FileNotFoundError:
            st.error(f"❌ Erro: Arquivo '{caminho_arquivo}' não encontrado.")
            return pd.DataFrame(), pd.DataFrame() 
    except Exception as e:
            # Mantém a exibição do erro para debug, mas agora deve ser mais raro
            st.error(f"Ocorreu um erro ao ler ou tratar o arquivo: {e}")
            return pd.DataFrame(), pd.DataFrame()

# ==============================================================================
# FUNÇÃO PARA CARREGAR CREDENCIAIS DA LOJA (NOVO)
# ==============================================================================
def carregar_credenciais_lojas(caminho_arquivo):
    """
    Lê a aba 'Loja' do Excel para autenticação.
    Espera colunas: Loja, CNPJ, Responsável, Senha
    """
    try:
        # Lê apenas a aba 'Loja'
        df_lojas = pd.read_excel(caminho_arquivo, sheet_name='Loja')
        
        # Tratamento para garantir que CNPJ e Senha sejam comparáveis
        if 'CNPJ' in df_lojas.columns:
            # Remove pontos, traços e barras
            df_lojas['CNPJ'] = df_lojas['CNPJ'].astype(str).str.replace(r'[^0-9]', '', regex=True)
            
        if 'Senha' in df_lojas.columns:
            # Converte para string e remove '.0'
            df_lojas['Senha'] = df_lojas['Senha'].astype(str).str.replace('.0', '', regex=False).str.strip()
            
        return df_lojas
    except Exception as e:
        st.error(f"Erro ao carregar a aba 'Loja' do Excel: {e}")
        return pd.DataFrame()