# Módulo: categoria.py
import pandas as pd
import numpy as np

# Importa as constantes
from modulos.config import COLUNA_NUMERO_TEMPORADA, COLUNA_ESPECIFICADOR, CATEGORIAS_NOMES, COLUNA_CHAVE_CONSOLIDADA

# ==============================================================================
# FUNÇÕES DE CÁLCULO DE CATEGORIAS E EVOLUÇÃO
# ==============================================================================

# A função calcular_categorias recebe df_base e df_agrupado. O df_base não é usado
# internamente para a lógica de categorias, mas é mantido por compatibilidade.
def calcular_categorias(df_base, df_agrupado):
    """
    Classifica profissionais em categorias com base na Pontuacao_Total.
    O agrupamento (df_agrupado) deve ser feito pela COLUNA_CHAVE_CONSOLIDADA.
    """
    
    if df_agrupado.empty:
        # Define as colunas esperadas
        return pd.DataFrame(columns=['Categoria', COLUNA_CHAVE_CONSOLIDADA, 'Pontuacao_Total'])
        
    # Recria as condições com base nas pontuações do DF de agrupamento
    condicoes_agrupadas = [
        (df_agrupado['Pontuacao_Total'] >= 5000000), # Diamante
        (df_agrupado['Pontuacao_Total'] >= 2000000), # Esmeralda
        (df_agrupado['Pontuacao_Total'] >= 500000), # Ruby
        (df_agrupado['Pontuacao_Total'] >= 150000), # Topázio
        (df_agrupado['Pontuacao_Total'] >= 1) # Pro
    ]
        
    categorias_np_select = ['Diamante', 'Esmeralda', 'Ruby', 'Topázio', 'Pro']

    df_agrupado['Categoria'] = np.select(condicoes_agrupadas, categorias_np_select, default='Sem Categoria')
    return df_agrupado

# Função para obter a pontuação da temporada anterior (corrigida)
def get_pontuacao_temporada_anterior(df_original_completo, temporada_atual_num, lojas_selecionadas, segmentos_selecionados, meses_selecionados, categoria=None):
    """Obtém a pontuação total ou por categoria da temporada anterior com base nos filtros atuais."""
    
    # 1. CRÍTICO: Calcula a temporada anterior corretamente
    temporada_anterior_num = int(temporada_atual_num) - 1
    temporada_anterior_nome = f"Temporada {temporada_anterior_num}"
    
    if temporada_anterior_num <= 0:
        return 0
        
    # 2. Filtra o DF original apenas para a temporada anterior e filtros de entidade
    df_anterior_base = df_original_completo[
        (df_original_completo['Temporada_Exibicao'] == temporada_anterior_nome) &
        (df_original_completo['Loja'].isin(lojas_selecionadas)) &
        (df_original_completo['Segmento'].isin(segmentos_selecionados)) &
        (df_original_completo['Mês_Exibicao'].isin(meses_selecionados)) # NOVO FILTRO DE MÊS
    ].copy()
    
    if df_anterior_base.empty:
        return 0
        
    # 3. CRÍTICO: Agrupa pela CHAVE CONSOLIDADA (e não pelo Especificador) para garantir que a soma
    # de pontos da T-1 corresponda à entidade, da mesma forma que na T-Atual.
    df_anterior_agrupado = df_anterior_base.groupby(COLUNA_CHAVE_CONSOLIDADA)['Pontos'].sum().reset_index()
    df_anterior_agrupado.columns = [COLUNA_CHAVE_CONSOLIDADA, 'Pontuacao_Total']
    
    # 4. Calcula as categorias na T-1 (necessário para filtrar por categoria)
    df_desempenho_anterior = calcular_categorias(df_anterior_base, df_anterior_agrupado)
    
    if categoria is None:
        # Retorna a pontuação total da temporada anterior (sem filtro de categoria)
        return df_desempenho_anterior['Pontuacao_Total'].sum()

    # Retorna a pontuação total da categoria específica na temporada anterior
    pontuacao = df_desempenho_anterior.loc[df_desempenho_anterior['Categoria'] == categoria, 'Pontuacao_Total'].sum()
    return pontuacao

# Função para obter a contagem de profissionais por categoria
def get_contagem_categoria(df_desempenho, categorias_base=CATEGORIAS_NOMES):
    """
    Calcula a contagem de CHAVES CONSOLIDADAS por categoria.
    A coluna de agrupamento (Contagem) no df_desempenho deve ser renomeada para COLUNA_ESPECIFICADOR
    ANTES de chamar esta função, para reuso.
    """
    # Inclui 'Sem Categoria' na lista para garantir que todas sejam consideradas na contagem
    todas_categorias = categorias_base + ['Sem Categoria']
    if df_desempenho.empty:
        return {cat: 0 for cat in todas_categorias}
    
    # Aqui, a COLUNA_ESPECIFICADOR está sendo usada para a contagem, mas espera-se que
    # ela contenha a Chave Consolidada após renomeação no app.py
    contagem = df_desempenho.groupby('Categoria')[COLUNA_ESPECIFICADOR].nunique().to_dict()
    # Preenche com 0s categorias ausentes
    for cat in todas_categorias:
        if cat not in contagem:
            contagem[cat] = 0
    return contagem