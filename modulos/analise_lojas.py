# Módulo: analise_lojas.py
import pandas as pd
import numpy as np

# Importa as constantes e funções auxiliares
from modulos.tratamento import calcular_evolucao_pct

# ==============================================================================
# NOVA FUNÇÃO AUXILIAR PARA O ITEM 7: ANÁLISE DE EVOLUÇÃO DE LOJAS
# ==============================================================================
def calcular_analise_lojas(df_base, t_atual_nome, t_anterior_nome, lojas_base_analise):
    """
    Realiza a análise de evolução de lojas (Pontos, Evolução %, Terços e Pirâmide).
    
    Args:
        df_base (pd.DataFrame): DataFrame já filtrado por Segmento/Loja/Mês.
        t_atual_nome (str): Nome da temporada atual (ex: 'Temporada 10').
        t_anterior_nome (str): Nome da temporada anterior (ex: 'Temporada 09').
        lojas_base_analise (list): Lista de lojas que devem compor a base (seleção manual do usuário).

    Returns:
        tuple: (df_evolucao, df_rank_quantitativo, df_rank_pontuacao, df_piramide_status)
    """
    
    # CRÍTICO: Filtrar a base de dados *antes* do agrupamento para incluir APENAS
    # as lojas selecionadas pelo usuário, garantindo que o cálculo de pontos
    # para T_Atual e T_Anterior seja feito apenas para elas.
    df_base_filtrada_lojas = df_base[df_base['Loja'].isin(lojas_base_analise)].copy()
    
    # 1. Filtra as duas temporadas de interesse
    df_t_vs_t = df_base_filtrada_lojas[
        df_base_filtrada_lojas['Temporada_Exibicao'].isin([t_atual_nome, t_anterior_nome])
    ].copy()
    
    # 2. Agrupa por Loja e Temporada, somando os Pontos
    df_pontos_loja = df_t_vs_t.groupby(['Loja', 'Temporada_Exibicao'])['Pontos'].sum().reset_index()
    
    # 3. Pivotar para ter Pontos T_Atual e T_Anterior
    df_evolucao = df_pontos_loja.pivot_table(
        index='Loja',
        columns='Temporada_Exibicao',
        values='Pontos',
        fill_value=0 # Preenche com 0 lojas que não pontuaram na temporada, mas que existem no df_t_vs_t
    ).reset_index()
    
    # CRÍTICO: Mesclar com a lista completa de lojas do multiselect para incluir lojas com 0 pontos em ambas as Ts
    lojas_para_analisar = pd.DataFrame({'Loja': lojas_base_analise})
    
    df_evolucao_final = pd.merge(
        lojas_para_analisar,
        df_evolucao,
        on='Loja',
        how='left'
    ).fillna(0) # Zera os pontos para as lojas que não apareceram no df_evolucao (pontuaram 0 em ambas as T's)
    
    
    col_atual = t_atual_nome
    col_anterior = t_anterior_nome

    # --- PARTE 1: Evolução % e Classificação ---
    
    # Calcula a Evolução % (usando a função importada)
    df_evolucao_final['Evolução %'] = df_evolucao_final.apply(
        lambda row: calcular_evolucao_pct(row[col_atual], row[col_anterior]), axis=1
    )
    
    # Classifica a loja por status (Pirâmide de Evolução - Parte 3)
    def classificar_status(row):
        pontos_atual = row[col_atual]
        pontos_anterior = row[col_anterior]
        
        if pontos_anterior == 0 and pontos_atual == 0:
            return 'Zero em T-1 e T-Atual' 
        if pontos_anterior == 0 and pontos_atual > 0:
            return 'Cresceram (Zeraram na T-1)' 
        if pontos_anterior > 0 and pontos_atual == 0:
            return 'Zeraram na T-Atual' 
        if pontos_anterior > 0 and pontos_atual > 0:
            if pontos_atual > pontos_anterior:
                return 'Cresceram' 
            elif pontos_atual < pontos_anterior:
                return 'Decresceram' 
            else:
                return 'Estáveis'
        
        return 'Outros'

    df_evolucao_final['Status_Evolução'] = df_evolucao_final.apply(classificar_status, axis=1)
    
    # Ponto 1: Ordenação decrescente de pontos (AGORA USANDO T_ANTERIOR COMO PRINCIPAL)
    # A ordenação é crucial para o cálculo de terços por pontuação.
    df_evolucao_final.sort_values(
        by=col_anterior, 
        ascending=False, 
        inplace=True
    ) 
    
    # --- PARTE 2 & 3: Separação por Terços (Pontuação Acumulada) ---
    
    df_analise = df_evolucao_final.copy().reset_index(drop=True)
    
    # Calcular o valor alvo para cada terço com base na T_Anterior
    total_pontos_anterior = df_analise[col_anterior].sum()
    target_pontos_terco = total_pontos_anterior / 3
    
    pontuacao_acumulada = 0
    df_analise['Terço'] = '3° Terço' # Default para o terceiro terço
    tercos_data = {'1° Terço': {}, '2° Terço': {}, '3° Terço': {}}
    
    current_terco = 1
    
    # Itera sobre as lojas (já ordenadas pela T_Anterior) para determinar o corte por PONTUAÇÃO ACUMULADA
    for index, row in df_analise.iterrows():
        loja_pontos_anterior = row[col_anterior]
        
        # Atribui ao terço atual
        df_analise.loc[index, 'Terço'] = f'{current_terco}° Terço'
        pontuacao_acumulada += loja_pontos_anterior
        
        # Verifica se o limite do terço foi ultrapassado (com margem de segurança)
        if current_terco < 3 and pontuacao_acumulada >= (current_terco * target_pontos_terco):
            # Move para o próximo terço
            current_terco += 1
            
    # Agrupamento final por Terço
    df_agrupado_tercos = df_analise.groupby('Terço').agg(
        **{
            col_anterior: (col_anterior, 'sum'), 
            col_atual: (col_atual, 'sum'),
            'Contagem_Lojas': ('Loja', 'size') # Total de lojas que caíram neste terço
        }
    ).reset_index()

    # Formata para ter os 3 terços, mesmo que vazios (garantido por df_analise já ter 3)
    tercos_ordenados = ['1° Terço', '2° Terço', '3° Terço']
    df_agrupado_tercos['Terço'] = pd.Categorical(df_agrupado_tercos['Terço'], categories=tercos_ordenados, ordered=True)
    df_agrupado_tercos.sort_values('Terço', inplace=True)

    # --- Criação do DF de Quantitativo (Item 7.2) ---
    df_rank_quantitativo = pd.DataFrame({
        'Terço': df_agrupado_tercos['Terço'],
        # Ponto 2: A contagem de lojas é igual em T_Anterior e T_Atual (quantitativo do corte)
        col_anterior: df_agrupado_tercos['Contagem_Lojas'], 
        col_atual: df_agrupado_tercos['Contagem_Lojas'],
        'Total de Lojas': df_agrupado_tercos['Contagem_Lojas']
    })
    
    # --- Criação do DF de Pontuação (Item 7.3) ---
    pontuacao_terco = []
    for _, row in df_agrupado_tercos.iterrows():
        pontos_ant = row[col_anterior]
        pontos_atual = row[col_atual]
        
        evol = calcular_evolucao_pct(pontos_atual, pontos_ant)
        
        pontuacao_terco.append({
            'Terço': row['Terço'],
            col_anterior: pontos_ant,
            col_atual: pontos_atual,
            'Evolução %': evol
        })

    df_rank_pontuacao = pd.DataFrame(pontuacao_terco)
    df_rank_pontuacao.sort_values(by='Terço', ascending=True, inplace=True)
    
    # --- PARTE 3: Pirâmide de Status (Contagem) ---
    
    # A base de cálculo da pirâmide agora usa df_evolucao_final, que só tem lojas selecionadas.
    df_piramide_sumario = pd.DataFrame({
        'Status': [
            f'Cresceram (Evolução Positiva)', 
            f'Decresceram (Evolução Negativa)', 
            f'Zeraram na {t_anterior_nome.replace("Temporada ", "T")} e Pontuaram na {t_atual_nome.replace("Temporada ", "T")}',
            f'Zeraram na {t_atual_nome.replace("Temporada ", "T")}'
        ],
        'Contagem': [
            df_evolucao_final[df_evolucao_final['Evolução %'] > 0.0001].shape[0],
            df_evolucao_final[df_evolucao_final['Evolução %'] < -0.0001].shape[0],
            df_evolucao_final[(df_evolucao_final[col_anterior] == 0) & (df_evolucao_final[col_atual] > 0)].shape[0],
            df_evolucao_final[(df_evolucao_final[col_anterior] > 0) & (df_evolucao_final[col_atual] == 0)].shape[0],
        ]
    })
    
    df_piramide_sumario = df_piramide_sumario[df_piramide_sumario['Contagem'] > 0]


    return df_evolucao_final, df_rank_quantitativo, df_rank_pontuacao, df_piramide_sumario