# Módulo: pedidos.py
import pandas as pd
import plotly.express as px

# Importa as constantes e funções auxiliares
from modulos.config import COLUNA_PEDIDO, MES_ORDEM_FISCAL
from modulos.tratamento import formatar_milhar_br

# Função para calcular o Pivô de Pedidos por Mês e Temporada (Item 6B)
def calcular_pivo_pedidos(df_filtrado, temporadas_selecionadas_exib):
    """Calcula o pivô de Pedidos Únicos por Mês e Temporada."""
    
    df_pivot_pedidos = df_filtrado.pivot_table(
        index='Mês_Exibicao',
        columns='Temporada_Exibicao',
        values=COLUNA_PEDIDO,
        aggfunc='nunique', # Contagem de pedidos únicos
        fill_value=0
    ).reset_index()

    # Reordenação dos Meses (Julho a Junho) 
    df_pivot_pedidos['Ordem'] = df_pivot_pedidos['Mês_Exibicao'].map(MES_ORDEM_FISCAL)
    df_pivot_pedidos.sort_values(by='Ordem', inplace=True)
    df_pivot_pedidos.drop('Ordem', axis=1, inplace=True)
    
    # Filtrar as colunas de Temporada apenas para as selecionadas no filtro lateral
    colunas_temporada_pivot = [col for col in df_pivot_pedidos.columns if col.startswith('Temporada')]
    
    # Colunas a exibir: Mês_Exibicao + Temporadas Selecionadas (ordenadas)
    colunas_display_pedidos = ['Mês_Exibicao'] + sorted(
        [col for col in colunas_temporada_pivot if col in temporadas_selecionadas_exib],
        key=lambda x: int(x.split(' ')[1])
    )

    df_pivot_pedidos_display = df_pivot_pedidos[colunas_display_pedidos].copy()
    
    # Renomear colunas Temporada X para Tx (para ficar mais conciso)
    colunas_renomeadas = {col: col.replace('Temporada ', 'T') for col in colunas_display_pedidos if col.startswith('Temporada')}
    df_pivot_pedidos_display.rename(columns=colunas_renomeadas, inplace=True)
    
    colunas_temporada_tx = [col.replace('Temporada ', 'T') for col in colunas_display_pedidos if col.startswith('Temporada')]
    
    # 2. Adicionar linha de TOTAL
    df_pivot_pedidos_display.set_index('Mês_Exibicao', inplace=True)
    total_row_pedidos = pd.Series(df_pivot_pedidos_display[colunas_temporada_tx].sum(), name='Total')
    df_pivot_pedidos_display = pd.concat([df_pivot_pedidos_display, pd.DataFrame(total_row_pedidos).T])
    df_pivot_pedidos_display.index.name = 'Mês'

    return df_pivot_pedidos_display, colunas_temporada_tx
    
# Função para calcular o Pivô de Novos Clientes (Item 9A)
def calcular_pivo_novos_clientes(df_dados_original, df_novos_filtrados, meses_selecionados_exib, temporadas_selecionadas_exib):
    """
    Calcula o pivô de Novos Profissionais Pontuados por Mês e Temporada.
    AGORA USA A NOVA LÓGICA DE COORTE: Temporada de Venda == Temporada de Cadastro
    """
    
    # O df_novos_filtrados JÁ CONTÉM a lógica de coorte (Novo_Cadastrado == True)
    # O que precisamos é contar os clientes únicos por Mês/Temporada, apenas para quem tem o flag True
    df_base_coorte_ativa = df_novos_filtrados[df_novos_filtrados['Novo_Cadastrado'] == True].copy()
    
    # 1. Agrupamento para a contagem de clientes ÚNICOS (CNPJ_CPF_LIMPO)
    df_pivot_base_novos_full = df_base_coorte_ativa.pivot_table(
        index='Mês_Exibicao', 
        columns='Temporada_Exibicao', 
        values='CNPJ_CPF_LIMPO', # Conta o documento limpo (a identidade)
        aggfunc='nunique', # Contagem de clientes ÚNICOS (identidades)
        fill_value=0 
    ).reset_index()

    # 2. Filtra os Meses
    df_pivot_novos_filtrado = df_pivot_base_novos_full[df_pivot_base_novos_full['Mês_Exibicao'].isin(meses_selecionados_exib)].copy()
    
    # 3. Tratamento de Colunas e Ordenação 
    colunas_temporada_full_novos = [col for col in df_pivot_novos_filtrado.columns if col.startswith('Temporada')]
    
    colunas_temporada_sorted_num_novos = sorted([
        col for col in colunas_temporada_full_novos if col != 'Temporada 0' and len(col.split(' ')) > 1
    ], key=lambda x: int(x.split(' ')[1]))
    
    # Inicializa o DF de novos clientes final
    df_pivot_novos = df_pivot_novos_filtrado[['Mês_Exibicao']].copy()
    
    for col in colunas_temporada_sorted_num_novos:
        # Inclui apenas as colunas que estão na seleção lateral
        if col in temporadas_selecionadas_exib:
            if col in df_pivot_novos_filtrado.columns:
                df_pivot_novos[col] = df_pivot_novos_filtrado[col]
            else:
                df_pivot_novos[col] = 0.0

    
    # Reordenação dos Meses (Julho a Junho)
    df_pivot_novos['Ordem'] = df_pivot_novos['Mês_Exibicao'].map(MES_ORDEM_FISCAL)
    df_pivot_novos.sort_values(by='Ordem', inplace=True)
    df_pivot_novos.drop('Ordem', axis=1, inplace=True)
    
    # Renomear colunas de temporada para 'Clientes T9', 'Clientes T10', etc.
    colunas_clientes = [col for col in df_pivot_novos.columns if col.startswith('Temporada')]
    df_pivot_novos.columns = [
        'Mês_Exibicao' if col == 'Mês_Exibicao' else col.replace('Temporada ', 'Clientes T')
        for col in df_pivot_novos.columns
    ]
    
    # Ordenação das colunas de T7 -> T10
    colunas_clientes_renomeadas = [col for col in df_pivot_novos.columns if col.startswith('Clientes T')]
    colunas_clientes_sorted = sorted(colunas_clientes_renomeadas, key=lambda x: int(x.split('T')[1]))
    
    # 5. Cálculo da Evolução Qualitativa (Se houver 2 temporadas)
    nome_coluna_evolucao_cli = 'Evolução Clientes indisponível' 
    
    if len(temporadas_selecionadas_exib) >= 2 and not df_pivot_novos.empty:
        
        t_atual_col_cli_raw = sorted(temporadas_selecionadas_exib, key=lambda x: int(x.split(' ')[1]))[-1].replace('Temporada ', 'Clientes T')
        t_anterior_col_cli_raw = sorted(temporadas_selecionadas_exib, key=lambda x: int(x.split(' ')[1]))[-2].replace('Temporada ', 'Clientes T')
        
        # Função interna movida para o escopo para ser aplicada corretamente
        def calcular_evolucao_contagem(row):
            valor_atual = row.get(t_atual_col_cli_raw, 0)
            valor_anterior = row.get(t_anterior_col_cli_raw, 0)
            
            if valor_atual > valor_anterior:
                return "Evolução Positiva", 1
            elif valor_atual < valor_anterior:
                return "Evolução Negativa", -1
            else:
                return "Evolução Estável", 0 
                
        # Aplica a função de cálculo nas linhas mensais
        df_pivot_novos[['Evolução Qualitativa Texto', 'Evolução Qualitativa Valor']] = df_pivot_novos.apply(
            lambda row: calcular_evolucao_contagem(row), axis=1, result_type='expand'
        )

        # Atualiza o nome da coluna de exibição final
        nome_coluna_evolucao_cli = f"Evolução Clientes ({t_atual_col_cli_raw.replace('Clientes T', 'T')} vs {t_anterior_col_cli_raw.replace('Clientes T', 'T')})"
        df_pivot_novos.rename(columns={'Evolução Qualitativa Texto': nome_coluna_evolucao_cli}, inplace=True)
        colunas_display_final_cli = colunas_clientes_sorted + [nome_coluna_evolucao_cli] 
    else:
        colunas_display_final_cli = colunas_clientes_sorted
        
    # Adicionar linha de TOTAL
    total_row = pd.Series(df_pivot_novos[colunas_clientes_renomeadas].sum(), name='Total')
    total_row['Mês_Exibicao'] = 'Total'
    df_pivot_novos.set_index('Mês_Exibicao', inplace=True)
    
    if not df_pivot_novos.empty or any(col in df_pivot_novos.columns for col in colunas_clientes_renomeadas):
        df_pivot_novos = pd.concat([df_pivot_novos, pd.DataFrame(total_row).T.set_index('Mês_Exibicao')])
        df_pivot_novos.index.name = 'Mês' 
    
    # CÁLCULO DA EVOLUÇÃO TOTAL QUALITATIVA (Se a coluna existir)
    if 'Evolução Qualitativa Valor' in df_pivot_novos.columns and 'Total' in df_pivot_novos.index:
        # Recalcula o total apenas para as colunas relevantes
        total_atual_cli = df_pivot_novos.loc[df_pivot_novos.index != 'Total', t_atual_col_cli_raw].sum() 
        total_anterior_cli = df_pivot_novos.loc[df_pivot_novos.index != 'Total', t_anterior_col_cli_raw].sum() 

        if total_atual_cli > total_anterior_cli:
            evolucao_texto_total_cli = "Evolução Positiva"
            evolucao_valor_total_cli = 1
        elif total_atual_cli < total_anterior_cli:
            evolucao_texto_total_cli = "Evolução Negativa"
            evolucao_valor_total_cli = -1
        else:
            evolucao_texto_total_cli = "Evolução Estável"
            evolucao_valor_total_cli = 0

        # Atribui o resultado na linha Total
        df_pivot_novos.loc['Total', nome_coluna_evolucao_cli] = evolucao_texto_total_cli
        df_pivot_novos.loc['Total', 'Evolução Qualitativa Valor'] = evolucao_valor_total_cli

    return df_pivot_novos, colunas_display_final_cli, nome_coluna_evolucao_cli