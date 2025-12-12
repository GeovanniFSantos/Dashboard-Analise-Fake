# MÓDULO DE CLASSIFICAÇÃO DE CATEGORIAS
import pandas as pd
import numpy as np
from .config import (
    CATEGORIAS_LIMITES, CATEGORIAS_NOMES, COLUNA_ESPECIFICADOR, 
    COLUNA_NUMERO_TEMPORADA
)

def calcular_categorias(df_agrupado):
    """
    Classifica cada profissional em uma categoria com base na Pontuacao_Total.
    Assume que df_agrupado tem as colunas COLUNA_ESPECIFICADOR e 'Pontuacao_Total'.
    """
    # Garante que o df_agrupado não está vazio antes de tentar calcular
    if df_agrupado.empty:
        return pd.DataFrame(columns=['Categoria', COLUNA_ESPECIFICADOR, 'Pontuacao_Total'])
        
    # As condições e os resultados são definidos nas constantes de configuração
    condicoes = [
        (df_agrupado['Pontuacao_Total'] >= limite) 
        for limite in CATEGORIAS_LIMITES
    ]
    
    # Aplicar a lógica usando numpy.select (equivalente ao SWITCH)
    df_agrupado['Categoria'] = np.select(
        condicoes, 
        CATEGORIAS_NOMES, 
        default='Sem Categoria'
    )
    return df_agrupado

def get_pontuacao_temporada_anterior(df_original_completo, temporada_atual_num, lojas_selecionadas, segmentos_selecionados, categoria=None):
    """
    Calcula a pontuação (Total ou por Categoria) da temporada anterior, 
    respeitando os filtros de Loja/Segmento da Entidade atual.
    """
    temporada_anterior_num = int(temporada_atual_num) - 1
    temporada_anterior_nome = f"Temporada {temporada_anterior_num}"
    
    if temporada_anterior_num <= 0:
        return 0
            
    # 1. Filtra o DF original apenas para a temporada anterior
    df_anterior_base = df_original_completo[
        df_original_completo['Temporada_Exibicao'] == temporada_anterior_nome
    ].copy()
    
    if df_anterior_base.empty:
        return 0
            
    # 2. APLICA O FILTRO DE LOJA/SEGMENTO DA TEMPORADA ATUAL na base anterior
    df_anterior_filtrado = df_anterior_base[
        (df_anterior_base['Loja'].isin(lojas_selecionadas)) &
        (df_anterior_base['Segmento'].isin(segmentos_selecionados))
    ].copy()
    
    if df_anterior_filtrado.empty:
        return 0

    # 3. Agrupa e calcula as categorias no DF anterior (para agrupar por categoria)
    df_anterior_agrupado = df_anterior_filtrado.groupby(COLUNA_ESPECIFICADOR)['Pontos'].sum().reset_index()
    df_anterior_agrupado.columns = [COLUNA_ESPECIFICADOR, 'Pontuacao_Total']
    df_desempenho_anterior = calcular_categorias(df_anterior_agrupado)
        
    if categoria is None:
        # Retorna a pontuação total da temporada anterior (sem filtro de categoria)
        return df_desempenho_anterior['Pontuacao_Total'].sum()

    # Retorna a pontuação total da categoria específica na temporada anterior
    pontuacao = df_desempenho_anterior.loc[df_desempenho_anterior['Categoria'] == categoria, 'Pontuacao_Total'].sum()
    return pontuacao