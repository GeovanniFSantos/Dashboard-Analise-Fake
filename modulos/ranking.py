# Módulo: ranking.py
import pandas as pd
import numpy as np

# Importa as constantes e funções auxiliares
from modulos.config import COLUNA_NUMERO_TEMPORADA, COLUNA_ESPECIFICADOR, COLUNA_CNPJ_CPF

# ==============================================================================
# FUNÇÕES DE CÁLCULO DE RANKING AJUSTADO
# ==============================================================================

def _rank_temporada_unica(df_base_entidade, t_num, col_prefix):
    """Calcula o ranking (apenas para quem pontuou > 0) para uma única temporada."""
    df_temp = df_base_entidade[df_base_entidade[COLUNA_NUMERO_TEMPORADA] == t_num].copy()
    
    # Agrupa por profissional e CNPJ (usado para o merge)
    df_rank = df_temp.groupby([COLUNA_ESPECIFICADOR, 'CNPJ_CPF_LIMPO'])['Pontos'].sum().reset_index()
    
    # Filtra apenas quem pontuou para o ranking base
    df_rank_pontuou = df_rank[df_rank['Pontos'] > 0].copy()

    # Ranqueia pelo Pontos (maior para o menor)
    df_rank_pontuou[f'{col_prefix}_Rank'] = df_rank_pontuou['Pontos'].rank(method='min', ascending=False).astype(int)
    
    # Renomeia Pontos para a coluna da temporada e mantém a lista de CPFs/CNPJs
    df_rank_pontuou.rename(columns={'Pontos': f'{col_prefix}_Pontos'}, inplace=True)
    
    return df_rank_pontuou[[COLUNA_ESPECIFICADOR, 'CNPJ_CPF_LIMPO', f'{col_prefix}_Pontos', f'{col_prefix}_Rank']]


def calcular_ranking_ajustado(df_completo, lojas_sel, segmentos_sel, t_atual_num, t_anterior_num):
    """
    Calcula o ranking de T_Atual vs T_Anterior com ajuste de posição para não pontuadores.
    Ajuste: Quem pontuou em uma temporada mas não na outra, recebe a posição (Max Rank + 1)
    na temporada em que não pontuou.
    """
    if not lojas_sel or not segmentos_sel or t_anterior_num <= 0:
        return pd.DataFrame(), f"Temporada {t_atual_num}", f"Temporada {t_anterior_num}", 0, 0

    # 1. Filtrar por Entidade (Segmento/Loja) e Temporadas Relevantes
    df_base_entidade = df_completo[
        (df_completo['Loja'].isin(lojas_sel)) & 
        (df_completo['Segmento'].isin(segmentos_sel)) &
        (df_completo[COLUNA_NUMERO_TEMPORADA].isin([t_atual_num, t_anterior_num]))
    ].copy()

    if df_base_entidade.empty:
        return pd.DataFrame(), f"Temporada {t_atual_num}", f"Temporada {t_anterior_num}", 0, 0

    # 2. Calcular Rankings
    df_rank_t_atual = _rank_temporada_unica(df_base_entidade, t_atual_num, 'T_Atual')
    df_rank_t_anterior = _rank_temporada_unica(df_base_entidade, t_anterior_num, 'T_Anterior')

    # 3. Merge dos rankings (Full Outer Join)
    df_final = pd.merge(
        df_rank_t_atual, 
        df_rank_t_anterior, 
        on=[COLUNA_ESPECIFICADOR, 'CNPJ_CPF_LIMPO'], 
        how='outer'
    ).fillna(0)
    
    # 4. Determinar o último rank em cada temporada (para o Gap Filling)
    max_rank_t_atual = df_rank_t_atual['T_Atual_Rank'].max() if not df_rank_t_atual.empty else 0
    max_rank_t_anterior = df_rank_t_anterior['T_Anterior_Rank'].max() if not df_rank_t_anterior.empty else 0

    # Posição de desempate/não pontuação (Max Rank + 1)
    rank_vazio_t_atual = max_rank_t_atual + 1
    rank_vazio_t_anterior = max_rank_t_anterior + 1

    # 5. Aplicar o Ajuste no Rank (Gap Filling)

    # 5.1 Ajuste do Rank T_Atual: Se T_Atual_Pontos is 0, mas T_Anterior_Pontos > 0, recebe rank_vazio_t_atual.
    df_final['T_Atual_Rank_Ajustado'] = np.where(
        (df_final['T_Atual_Pontos'] == 0) & (df_final['T_Anterior_Pontos'] > 0),
        rank_vazio_t_atual,
        df_final['T_Atual_Rank']
    ).astype(int)

    # 5.2 Ajuste do Rank T_Anterior: Se T_Anterior_Pontos is 0, mas T_Atual_Pontos > 0, recebe rank_vazio_t_anterior.
    df_final['T_Anterior_Rank_Ajustado'] = np.where(
        (df_final['T_Anterior_Pontos'] == 0) & (df_final['T_Atual_Pontos'] > 0),
        rank_vazio_t_anterior,
        df_final['T_Anterior_Rank']
    ).astype(int)

    # 6. Filtra apenas profissionais que pontuaram em PELO MENOS uma das temporadas (T_Atual > 0 OU T_Anterior > 0)
    df_final = df_final[(df_final['T_Atual_Pontos'] > 0) | (df_final['T_Anterior_Pontos'] > 0)].copy()

    # 7. Calcular Variação: T_Anterior - T_Atual (Positivo = Subiu no Rank)
    df_final['Variação Rank'] = df_final['T_Anterior_Rank_Ajustado'] - df_final['T_Atual_Rank_Ajustado']
    
    # 8. Unir CPF/CNPJ original (para exibição)
    df_cnpj_original = df_completo.groupby('CNPJ_CPF_LIMPO').agg({
            COLUNA_CNPJ_CPF: 'first' 
    }).reset_index().rename(columns={COLUNA_CNPJ_CPF: 'CPF/CNPJ'})

    df_display = pd.merge(df_final, df_cnpj_original, on='CNPJ_CPF_LIMPO', how='left')

    # 9. Limpeza e Seleção de Colunas para display
    df_display = df_display[[
        COLUNA_ESPECIFICADOR, 
        'CPF/CNPJ',
        'T_Anterior_Rank_Ajustado', 
        'T_Atual_Rank_Ajustado', 
        'Variação Rank'
    ]].copy()
    
    # Renomear colunas
    col_t_anterior = f'Rank - T{t_anterior_num}'
    col_t_atual = f'Rank - T{t_atual_num}'

    df_display.columns = ['Especificador/Empresa', 'CPF/CNPJ', col_t_anterior, col_t_atual, 'Variação Rank']

    # Ordenar pela T_Atual (posição mais alta)
    df_display.sort_values(by=col_t_atual, ascending=True, inplace=True)
    
    # Retornar também os valores max_rank para uso na descrição (linha 2005)
    return df_display, f"Temporada {t_atual_num}", f"Temporada {t_anterior_num}", max_rank_t_atual, max_rank_t_anterior