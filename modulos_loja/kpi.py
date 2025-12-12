# MÓDULO DE CÁLCULO DE KPIS DE ALTO NÍVEL
import pandas as pd
from .config import COLUNA_PEDIDO, COLUNA_CNPJ_CPF, COLUNA_NUMERO_TEMPORADA, RANKING_INDICADORES

def calcular_metricas(df):
    """
    Calcula KPIs de alto nível (Pontos, Pedidos, Novos Clientes, Valor Médio).
    Retorna os valores brutos (float/int).
    """
    if df.empty:
        return 0, 0, 0, 0

    pontos = df['Pontos'].sum()
    
    # Pedidos: Contagem única de NF/Pedido
    pedidos = df[COLUNA_PEDIDO].nunique() if COLUNA_PEDIDO in df.columns else 0
    
    # Novos Clientes: Contagem única de CNPJ/CPF onde Novo_Cadastrado é True
    novos_clientes = df[df['Novo_Cadastrado'] == True][COLUNA_CNPJ_CPF].nunique()
    
    # Valor Médio: Pontos / Pedidos
    valor_medio = pontos / pedidos if pedidos > 0 else 0
    
    return pontos, pedidos, novos_clientes, valor_medio

def get_ranking_loja(df_total_periodo, lojas_selecionadas):
    """Calcula e retorna o ranking da loja selecionada em relação ao total do período."""
    if df_total_periodo.empty or not lojas_selecionadas:
        return 'N/A', 0
    
    # Agrupa por Loja e soma os pontos
    df_ranking = df_total_periodo.groupby('Loja')['Pontos'].sum().sort_values(ascending=False).reset_index()
    
    # Calcula o ranking
    df_ranking['Ranking'] = df_ranking['Pontos'].rank(method='min', ascending=False).astype(int)
    
    # Obtém o ranking da Loja(s) selecionada(s)
    ranking_loja = df_ranking.loc[df_ranking['Loja'].isin(lojas_selecionadas), 'Ranking'].min()
    
    return ranking_loja if ranking_loja > 0 else 'N/A', ranking_loja

def calcular_kpis_t_vs_t_1(df_original, lojas_sel, segmentos_sel, t_atual_num):
    """
    Calcula a evolução dos KPIs da loja (Pedidos, Pontos, Valor Médio, Novos Clientes) 
    entre a Temporada Atual (T) e a Anterior (T-1).
    """
    t_anterior_num = t_atual_num - 1
    
    if t_anterior_num <= 0:
        return {
            'pontos_anterior': 0, 'pedidos_anterior': 0, 'novos_clientes_anterior': 0, 
            'ranking_anterior': 0, 'valor_medio_anterior': 0 
        }
        
    # 1. Filtra os dados da T-1
    df_t_anterior = df_original[
        (df_original[COLUNA_NUMERO_TEMPORADA] == t_anterior_num) &
        (df_original['Loja'].isin(lojas_sel)) &
        (df_original['Segmento'].isin(segmentos_sel))
    ].copy()

    # 2. Calcula KPIs de T-1
    pontos_anterior, pedidos_anterior, novos_clientes_anterior, valor_medio_anterior = calcular_metricas(df_t_anterior)

    # 3. Calcula o Ranking da Loja em T-1 (Em relação a todas as Lojas em T-1)
    df_total_t_anterior = df_original[df_original[COLUNA_NUMERO_TEMPORADA] == t_anterior_num].copy()
    _, ranking_anterior = get_ranking_loja(df_total_t_anterior, lojas_sel)
    
    return {
        'pontos_anterior': pontos_anterior, 
        'pedidos_anterior': pedidos_anterior, 
        'novos_clientes_anterior': novos_clientes_anterior, 
        'valor_medio_anterior': valor_medio_anterior,
        'ranking_anterior': ranking_anterior
    }

def get_ranking_variacao_texto(ranking_atual, ranking_anterior):
    """Retorna o texto de variação de ranking (Subiu/Desceu/Manteve/Novo)."""
    if ranking_atual == 0:
        return RANKING_INDICADORES['SAIU']
    
    if ranking_anterior == 0:
        return RANKING_INDICADORES['NOVO'] # Não estava no ranking anterior (não pontuou)
        
    if ranking_atual < ranking_anterior:
        # Posição 1 é melhor que 5. Se 1 < 5, subiu.
        subiu = ranking_anterior - ranking_atual
        return f"{RANKING_INDICADORES['SUBIU']} (+{subiu})"
    elif ranking_atual > ranking_anterior:
        # Posição 5 é pior que 1. Se 5 > 1, desceu.
        desceu = ranking_atual - ranking_anterior
        return f"{RANKING_INDICADORES['DESCEU']} (-{desceu})"
    else:
        return RANKING_INDICADORES['MANTEVE']