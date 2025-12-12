# MÓDULO DE CARREGAMENTO E PRÉ-PROCESSAMENTO DE DADOS
import pandas as pd
import streamlit as st
import numpy as np
from .config import (
    RELATORIO_PATH, COLUNAS_NUMERICAS, NOMES_MESES_MAP, 
    COLUNA_NUMERO_TEMPORADA, COLUNA_CNPJ_CPF, COLUNA_CPF_NOVO_CADASTRO
)

@st.cache_data
def carregar_e_tratar_dados(caminho_arquivo):
    """
    Lê o arquivo Excel (2 abas), trata colunas (R$, datas, formatação) 
    e cria colunas derivadas (Ano, Mês, Temporada).
    Retorna dois DataFrames: df principal e df de novos cadastrados.
    """
    df = pd.DataFrame()
    df_novos = pd.DataFrame()
    
    try:
        # LER A ABA PRINCIPAL (Relatório)
        df = pd.read_excel(caminho_arquivo, sheet_name=0) 
        
        # LER A ABA DE NOVOS CADASTRADOS
        try:
            df_novos = pd.read_excel(caminho_arquivo, sheet_name='Novos Cadastrados')
        except ValueError:
            # st.error(f"❌ Erro: A aba 'Novos Cadastrados' não foi encontrada no arquivo '{caminho_arquivo}'.")
            df_novos = pd.DataFrame()
        
        # === ETAPA DE TRATAMENTO DE DADOS (DF PRINCIPAL) ===
        
        # 1. Tratamento de Colunas Numéricas (removendo símbolos e convertendo)
        for col in COLUNAS_NUMERICAS:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r'[^0-9,.]', '', regex=True)
                df[col] = df[col].str.replace(',', '.', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        # 2. Garantir que 'Data da Venda' seja datetime e remover inválidos
        if 'Data da Venda' in df.columns:
            df['Data da Venda'] = pd.to_datetime(df['Data da Venda'], errors='coerce')
            df.dropna(subset=['Data da Venda'], inplace=True) 
            
            # 3. CRIAÇÃO DAS COLUNAS DE MÊS E ANO PARA FILTRAGEM
            df['Ano'] = df['Data da Venda'].dt.year.astype(str)
            df['Mês_num'] = df['Data da Venda'].dt.month.astype(str)
            
            # 4. CRIAÇÃO DA COLUNA DE TEMPORADA DE EXIBIÇÃO
            if COLUNA_NUMERO_TEMPORADA in df.columns:
                # Garante que a coluna de temporada é numérica e a converte para 'Temporada X'
                df[COLUNA_NUMERO_TEMPORADA] = pd.to_numeric(df[COLUNA_NUMERO_TEMPORADA], errors='coerce').fillna(0).astype(int)
                df['Temporada_Exibicao'] = 'Temporada ' + df[COLUNA_NUMERO_TEMPORADA].astype(str)
            
            # 5. Mapeamento e Formatação para o Filtro de Mês 
            df['Mês_Exibicao'] = df['Mês_num'].map(NOMES_MESES_MAP)
            
            # === 6. LÓGICA DE NOVO CADASTRADO (CRÍTICO) ===
            if COLUNA_CNPJ_CPF in df.columns and COLUNA_NUMERO_TEMPORADA in df.columns:
                
                # CRÍTICO: Limpar colunas para merge
                df['CNPJ_CPF_LIMPO'] = df[COLUNA_CNPJ_CPF].astype(str).str.replace(r'[^0-9]', '', regex=True)
                
                if COLUNA_CPF_NOVO_CADASTRO in df_novos.columns:
                    df_novos['CPF_LIMPO'] = df_novos[COLUNA_CPF_NOVO_CADASTRO].astype(str).str.replace(r'[^0-9]', '', regex=True)
                
                    # 6.1. Identifica QUEM está na lista de Novos Cadastrados
                    df['Novo_Cadastro_Existe'] = df['CNPJ_CPF_LIMPO'].isin(df_novos['CPF_LIMPO'].unique())
                    
                    # 6.2. Calculamos a data da primeira compra histórica
                    df_primeira_compra = df.groupby('CNPJ_CPF_LIMPO')['Data da Venda'].min().reset_index()
                    df_primeira_compra.columns = ['CNPJ_CPF_LIMPO', 'Data_Primeira_Compra_Historica']
                    df = pd.merge(df, df_primeira_compra, on='CNPJ_CPF_LIMPO', how='left')
                    
                    # 6.3. CRÍTICO: Determinamos a Temporada da Primeira Compra
                    # Encontra a linha da primeira compra para obter a Temporada dessa linha
                    df_temp_primeira_compra = df.loc[df['Data da Venda'] == df['Data_Primeira_Compra_Historica']].groupby('CNPJ_CPF_LIMPO')[COLUNA_NUMERO_TEMPORADA].first().reset_index()
                    df_temp_primeira_compra.columns = ['CNPJ_CPF_LIMPO', 'Temporada_Primeira_Compra']
                    df = pd.merge(df, df_temp_primeira_compra, on='CNPJ_CPF_LIMPO', how='left')

                    # 6.4. Regra final: Só é "Novo Cadastrado" se: 
                    # 1. Está na lista mestra.
                    # 2. É a primeira compra.
                    # 3. A temporada atual da linha (COLUNA_NUMERO_TEMPORADA) é IGUAL à Temporada_Primeira_Compra.
                    df['Novo_Cadastrado'] = np.where(
                        (df['Novo_Cadastro_Existe'] == True) & 
                        (df['Data da Venda'] == df['Data_Primeira_Compra_Historica']) & 
                        (df[COLUNA_NUMERO_TEMPORADA] == df['Temporada_Primeira_Compra']), # AQUI GARANTIMOS QUE A TEMPORADA DA VENDA COINCIDE COM A TEMPORADA DE CADASTRO
                        True,
                        False
                    )
                else:
                    df['Novo_Cadastrado'] = False 
            
        return df, df_novos # Retorna os dois DataFrames
    
    except FileNotFoundError:
        st.error(f"❌ Erro: Arquivo '{caminho_arquivo}' não encontrado.")
        return pd.DataFrame(), pd.DataFrame() 
    except Exception as e:
        st.error(f"Ocorreu um erro ao ler ou tratar o arquivo: {e}")
        return pd.DataFrame(), pd.DataFrame()