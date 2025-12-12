# Módulo: desempenho_base.py

import pandas as pd
import streamlit as st

# Importa as constantes e funções
from modulos.config import COLUNA_CHAVE_CONSOLIDADA, COLUNA_PEDIDO, COLUNA_ESPECIFICADOR, COLUNA_CNPJ_CPF, COLUNA_NUMERO_TEMPORADA
from modulos.tratamento import separate_documents
from modulos.categoria import calcular_categorias

@st.cache_data
def calcular_desempenho_consolidado(df_base_filtrada_cache, temporada_selecionada_t8):
    """
    Calcula e cacheia o DataFrame de Desempenho Consolidado (Pontuação, Pedidos, Vínculos e Categoria)
    para o escopo de dados atual (filtrado por Segmento/Loja e Mês).
    """
    df_base_item8 = df_base_filtrada_cache.copy()

    # 1. Aplica o filtro de temporada local (Se "Todas" for selecionado, df_base_filtrada_cache já é o valor)
    if temporada_selecionada_t8 != 'Todas':
        df_base_item8 = df_base_item8[df_base_item8['Temporada_Exibicao'] == temporada_selecionada_t8].copy()
    
    if df_base_item8.empty:
        return pd.DataFrame()

    # --- Lógica de Agrupamento Consolidado (Originalmente no App.py) ---
    
    # A. Agrupamento pela CHAVE DE CONSOLIDAÇÃO (Pontuação Total E Qtd de Pedidos)
    df_desempenho = df_base_item8.groupby(COLUNA_CHAVE_CONSOLIDADA).agg(
        Pontuacao_Total=('Pontos', 'sum'),
        Qtd_Pedidos=(COLUNA_PEDIDO, 'nunique')
    ).reset_index()
    
    # B. Agrupamento para obter os VÍNCULOS para a Chave Consolidada
    df_vinculos = df_base_item8.groupby(COLUNA_CHAVE_CONSOLIDADA).agg(
        Especificadores_Vinculados=(COLUNA_ESPECIFICADOR, lambda x: ', '.join(x.astype(str).unique())),
        Documentos_Para_Separar=(COLUNA_CNPJ_CPF, lambda x: x.astype(str).unique().tolist()),
    ).reset_index()

    # C. Separação de Documentos (usando a função importada)
    df_vinculos[['CPFs Vinculados', 'CNPJs Vinculados']] = df_vinculos['Documentos_Para_Separar'].apply(
        lambda x: pd.Series(separate_documents(x))
    )
    df_vinculos.drop(columns=['Documentos_Para_Separar'], inplace=True)
    df_desempenho = pd.merge(df_desempenho, df_vinculos, on=COLUNA_CHAVE_CONSOLIDADA, how='left')
    
    # D. Definição da Lógica de Categorias
    df_desempenho = calcular_categorias(df_base_item8, df_desempenho)
    
    # E. Adicionar a Temporada Atual (para contexto de evolução)
    temporadas_nums_selecionadas = sorted(df_base_item8[COLUNA_NUMERO_TEMPORADA].unique())
    temporada_atual_num_t8 = max(temporadas_nums_selecionadas) if temporadas_nums_selecionadas else 0
    df_desempenho['Temporada_Atual_Num'] = temporada_atual_num_t8

    # F. Ordenar por Pontuação Total (do maior para o menor)
    df_desempenho.sort_values(by='Pontuacao_Total', ascending=False, inplace=True)
    
    return df_desempenho