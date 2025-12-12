# Módulo: evolucao_pontos.py
import pandas as pd

# Importa as constantes e funções auxiliares
from modulos.config import MES_ORDEM_FISCAL
from modulos.tratamento import formatar_milhar_br, calcular_evolucao_pct

# Função para calcular o Pivô de Pontos por Mês e Temporada (Item 3)
def calcular_pivo_pontos(df_dados_original, df_filtrado, meses_selecionados_exib, temporadas_selecionadas_exib):
    """
    Calcula o pivô de pontuação por Mês e Temporada (Item 3).
    Retorna o DataFrame pronto para exibição/estilização.
    """
    
    # 1. Agrupamento e Soma (Pivô da base completa para obter todas as colunas)
    df_pivot_base_full = df_dados_original.pivot_table(
        index='Mês_Exibicao', # Linhas (Mês)
        columns='Temporada_Exibicao', # Colunas (Temporada)
        values='Pontos', # Valores a serem somados
        aggfunc='sum',
        fill_value=0 # Preenche NaNs com 0 para clareza
    ).reset_index()

    # 2. Filtra os Meses
    df_pivot_filtrado = df_pivot_base_full[df_pivot_base_full['Mês_Exibicao'].isin(meses_selecionados_exib)].copy()
    
    # 3. Ordenação das colunas de Temporada
    colunas_temporada_full = [col for col in df_pivot_base_full.columns if col.startswith('Temporada')]
    
    colunas_temporada_sorted_num = sorted([
        col for col in colunas_temporada_full if col != 'Temporada 0' and len(col.split(' ')) > 1
    ], key=lambda x: int(x.split(' ')[1]))
    
    # 4. Cálculo dos VALORES FILTRADOS (com base no df_filtrado)
    df_valores_filtrados_loja = df_filtrado.pivot_table(
        index='Mês_Exibicao',
        columns='Temporada_Exibicao',
        values='Pontos',
        aggfunc='sum',
        fill_value=0
    )
    
    # Inicializa o DF de pontos final com todas as colunas de temporada ordenadas
    df_pivot_pontos = df_pivot_filtrado[['Mês_Exibicao']].copy()
    
    for col in colunas_temporada_sorted_num:
        df_pivot_pontos[col] = 0
        
        if col in temporadas_selecionadas_exib:
            if col in df_valores_filtrados_loja.columns:
                 # Mapeia os valores filtrados para o DataFrame de exibição
                 df_pivot_pontos[col] = df_pivot_pontos['Mês_Exibicao'].map(df_valores_filtrados_loja[col].to_dict()).fillna(0)
                 
    
    # Reordenação dos Meses (Julho a Junho, seguindo o ano fiscal)
    df_pivot_pontos['Ordem'] = df_pivot_pontos['Mês_Exibicao'].map(MES_ORDEM_FISCAL)
    df_pivot_pontos.sort_values(by='Ordem', inplace=True)
    df_pivot_pontos.drop('Ordem', axis=1, inplace=True)
    
    # 5. Adicionar a Linha de Total
    
    colunas_para_total = [col for col in df_pivot_pontos.columns if col.startswith('Temporada')]
    
    df_pivot_pontos.set_index('Mês_Exibicao', inplace=True)
    
    total_row = pd.Series(df_pivot_pontos[colunas_para_total].sum(), name='Total')
    # CRÍTICO: Não precisamos do Mês_Exibicao na Serie Total, pois o índice já é 'Total'
    
    # Concatena a linha de Total
    df_pivot_pontos = pd.concat([df_pivot_pontos, pd.DataFrame(total_row).T])
    df_pivot_pontos.index.name = 'Mês'

    # 6. Cálculo da Evolução em Porcentagem (Para a coluna de Evolução)
    if len(temporadas_selecionadas_exib) >= 2:
        
        t_atual_col = sorted(temporadas_selecionadas_exib, key=lambda x: int(x.split(' ')[1]))[-1]
        t_anterior_col = sorted(temporadas_selecionadas_exib, key=lambda x: int(x.split(' ')[1]))[-2]
        
        # Calcula a evolução para todas as linhas, incluindo o Total
        df_pivot_pontos['Evolução Pontos Valor'] = df_pivot_pontos.apply(
            lambda row: calcular_evolucao_pct(row[t_atual_col], row[t_anterior_col]), axis=1
        )

        nome_coluna_evolucao = f"Evolução Pontos ({t_atual_col.replace('Temporada ', 'T')} vs {t_anterior_col.replace('Temporada ', 'T')})"
        
        df_pivot_pontos[nome_coluna_evolucao] = df_pivot_pontos['Evolução Pontos Valor'].apply(
            lambda x: f"{x:,.1%} {'↑' if x > 0.0001 else '↓' if x < -0.0001 else '≈'}" if x != 0.0 else "0.0% ≈"
        )
        
        colunas_a_exibir = colunas_temporada_sorted_num + [nome_coluna_evolucao]
        
        return df_pivot_pontos, colunas_a_exibir
        
    else:
        # Se não há 2 temporadas selecionadas, retorna apenas o pivô e as colunas de temporada
        
        # Como a linha 'Total' foi adicionada, precisamos garantir um índice único 
        # antes de retornar para evitar o erro Styler.apply
        df_pivot_pontos_clean = df_pivot_pontos.reset_index()
        df_pivot_pontos_clean.set_index('Mês', inplace=True) # Define 'Mês' (agora com 'Total') como o novo índice
        
        return df_pivot_pontos_clean, colunas_temporada_sorted_num