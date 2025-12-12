import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ==============================================================================
# IMPORTS
# ==============================================================================

# 1. Utilitários de formatação (Módulo Geral)
try:
    from modulos_loja.tratamento import formatar_milhar_br, calcular_evolucao_raw, formatar_evolucao_texto
except ImportError:
    # Fallback caso rode fora da estrutura apenas para teste
    formatar_milhar_br = lambda x, casas_decimais=0: f"{x:,.{casas_decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    calcular_evolucao_raw = lambda a, b: 0
    formatar_evolucao_texto = lambda x: f"{x:.1%}"

# 2. Lógica de Negócio da Loja
from modulos_loja.config import (
    COLUNA_PEDIDO, COLUNA_CNPJ_CPF, COLUNA_NUMERO_TEMPORADA,
    COLUNA_ESPECIFICADOR, MES_ORDEM_FISCAL, CATEGORIAS_NOMES, 
    CORES_CATEGORIA_TEXTO
)
from modulos_loja.kpi import (
    calcular_metricas, get_ranking_loja, calcular_kpis_t_vs_t_1, 
    get_ranking_variacao_texto
)
from modulos_loja.categoria import calcular_categorias, get_pontuacao_temporada_anterior
from modulos_loja.calculos import calcular_clientes_ativos_inativos, calcular_ranking_ajustado

# ==============================================================================
# FUNÇÃO PRINCIPAL DO DASHBOARD DA LOJA
# ==============================================================================
def show_store_dashboard(df_global, store_name):
    """
    Renderiza o dashboard completo da loja (Itens 1 a 10).
    Parâmetros:
      df_global: DataFrame completo com todas as vendas.
      store_name: Nome da loja logada (usado para filtrar automaticamente).
    """
    
    # --- GARANTIA DE INICIALIZAÇÃO DE ESTADO ---
    if 'filtro_status_ano' not in st.session_state:
        st.session_state['filtro_status_ano'] = {'temporada': None, 'status': None, 'termo_pesquisa': ''}
    if 'termo_pesquisa_novos' not in st.session_state:
        st.session_state['termo_pesquisa_novos'] = ''

    st.title(f"📊 Dashboard da Loja: {store_name}")

    # --- 1. VALIDAÇÃO DE DADOS ---
    if df_global.empty:
        st.error("Erro: Base de dados global vazia.")
        return

    # Filtra APENAS a loja logada para definir o escopo inicial
    df_loja_total = df_global[df_global['Loja'] == store_name].copy()

    if df_loja_total.empty:
        st.warning(f"A loja '{store_name}' não possui vendas registradas na base de dados.")
        return

    # Define a variável que substitui o antigo filtro lateral de loja
    lojas_selecionadas = [store_name]

    # --- 2. FILTROS LATERAIS ---
    st.sidebar.markdown("---")
    st.sidebar.header("Filtros Interativos")

    # A. Filtro de Temporada
    temporadas_unicas_exib_full = []
    opcoes_temporada_principal = ['Todas']
    
    if 'Temporada_Exibicao' in df_global.columns:
        temporadas_unicas_exib_full = sorted(df_global['Temporada_Exibicao'].loc[df_global['Temporada_Exibicao'] != 'Temporada 0'].dropna().unique())
        opcoes_temporada_principal = ['Todas'] + temporadas_unicas_exib_full

    temporadas_selecionadas_exib = []
    if temporadas_unicas_exib_full:
        temporadas_selecionadas_exib = st.sidebar.multiselect(
            "Selecione Temporadas para Comparação Mensal (Item 3):",
            options=temporadas_unicas_exib_full,
            default=temporadas_unicas_exib_full
        )

    # Base preliminar para filtro de Mês
    df_base_temp = df_loja_total.copy()
    if temporadas_selecionadas_exib:
        df_base_temp = df_base_temp[df_base_temp['Temporada_Exibicao'].isin(temporadas_selecionadas_exib)]

    # B. Filtro de Mês
    meses_selecionados_exib = []
    if 'Mês_Exibicao' in df_base_temp.columns:
        meses_unicos_exib = sorted(df_base_temp['Mês_Exibicao'].dropna().unique())
        meses_selecionados_exib = st.sidebar.multiselect(
            "Selecione o Mês:",
            options=meses_unicos_exib,
            default=meses_unicos_exib
        )

    # --- APLICAÇÃO DOS FILTROS DE DATA (BASE GLOBAL) ---
    df_total_periodo_base = df_global.copy()
    if temporadas_selecionadas_exib:
        df_total_periodo_base = df_total_periodo_base[df_total_periodo_base['Temporada_Exibicao'].isin(temporadas_selecionadas_exib)]
    if meses_selecionados_exib:
        df_total_periodo_base = df_total_periodo_base[df_total_periodo_base['Mês_Exibicao'].isin(meses_selecionados_exib)]

    # C. Filtro de Segmento (Hierárquico)
    st.sidebar.subheader("Filtros de Entidade")
    segmentos_unicos_loja = sorted(df_loja_total['Segmento'].unique())
    segmentos_selecionados = st.sidebar.multiselect(
        "Selecione o Segmento:",
        options=segmentos_unicos_loja,
        default=segmentos_unicos_loja
    )

    # --- CRIAÇÃO DOS DATAFRAMES FINAIS PARA OS ITENS ---
    df_filtrado_base = df_total_periodo_base[df_total_periodo_base['Loja'] == store_name].copy()
    if segmentos_selecionados:
        df_filtrado_base = df_filtrado_base[df_filtrado_base['Segmento'].isin(segmentos_selecionados)]
    
    df_segmento_total_base = df_total_periodo_base[df_total_periodo_base['Segmento'].isin(segmentos_selecionados)].copy()
    df_gabriel_total_base = df_total_periodo_base.copy()


    # =======================================================================
    # ITEM 1: COMPARATIVO DE DESEMPENHO (Lógica Ajustada: Meses Equivalentes)
    # =======================================================================
    st.subheader("1. Comparativo de Desempenho (Loja/Segmento vs Gabriel Pro)")
    
    temporada_selecionada_item1 = st.selectbox(
        "Selecione a Temporada de Análise (Item 1):",
        options=opcoes_temporada_principal,
        index=0,
        key='sel_temp_1'
    )

    # Filtros locais para Item 1
    df_f_kpi = df_filtrado_base.copy()
    df_s_kpi = df_segmento_total_base.copy()
    df_g_kpi = df_gabriel_total_base.copy()
    
    t_atual_num_principal = 0

    if temporada_selecionada_item1 != 'Todas':
        df_f_kpi = df_f_kpi[df_f_kpi['Temporada_Exibicao'] == temporada_selecionada_item1]
        df_s_kpi = df_s_kpi[df_s_kpi['Temporada_Exibicao'] == temporada_selecionada_item1]
        df_g_kpi = df_g_kpi[df_g_kpi['Temporada_Exibicao'] == temporada_selecionada_item1]
        
        if not df_f_kpi.empty and COLUNA_NUMERO_TEMPORADA in df_f_kpi.columns:
            t_atual_num_principal = df_f_kpi[COLUNA_NUMERO_TEMPORADA].iloc[0]

    # Cálculos Item 1 (Temporada Atual Selecionada)
    pontos_loja, pedidos_loja, novos_clientes_loja, valor_medio_loja = calcular_metricas(df_f_kpi)
    
    ranking_display, ranking_atual = get_ranking_loja(df_total_periodo_base, lojas_selecionadas)
    
    pontos_segmento, pedidos_segmento, novos_clientes_segmento, valor_medio_segmento = calcular_metricas(df_s_kpi)
    pontos_gabriel, pedidos_gabriel, novos_clientes_gabriel, valor_medio_gabriel = calcular_metricas(df_g_kpi)

    # Evolução T vs T-1 (COM LÓGICA DE MESES EQUIVALENTES)
    pontos_ant, pedidos_ant, novos_clientes_ant, valor_medio_ant = 0, 0, 0, 0
    variacao_ranking_texto = "N/A"

    if t_atual_num_principal > 0:
        # 1. Identificar Temporada Anterior
        t_ant_num = t_atual_num_principal - 1
        t_ant_str = f"Temporada {t_ant_num}"
        
        # 2. Identificar os meses presentes na seleção ATUAL (ex: apenas 4 meses da T10)
        # Se 'df_f_kpi' estiver filtrado apenas para a T10, ele terá apenas os meses da T10.
        meses_equivalentes = df_f_kpi['Mês_Exibicao'].unique()
        
        # 3. Filtrar a base GLOBAL para a Temporada Anterior APENAS nesses meses
        # Isso garante que a comparação T-1 seja "like-for-like" (mesma quantidade de meses)
        df_global_ant_filtrado = df_global[
            (df_global['Temporada_Exibicao'] == t_ant_str) &
            (df_global['Mês_Exibicao'].isin(meses_equivalentes))
        ].copy()
        
        # 4. Calcular o Ranking Anterior com a base filtrada pelos meses
        # (O ranking também deve considerar apenas até o mês X para ser justo)
        _, ranking_ant_val = get_ranking_loja(df_global_ant_filtrado, lojas_selecionadas)
        variacao_ranking_texto = get_ranking_variacao_texto(ranking_atual, ranking_ant_val)
        
        # 5. Calcular Métricas da Loja na Temporada Anterior (Filtrada)
        df_loja_ant_filtrada = df_global_ant_filtrado[
            (df_global_ant_filtrado['Loja'].isin(lojas_selecionadas)) &
            (df_global_ant_filtrado['Segmento'].isin(segmentos_selecionados))
        ]
        
        pontos_ant, pedidos_ant, novos_clientes_ant, valor_medio_ant = calcular_metricas(df_loja_ant_filtrada)

    # Evoluções (Raw)
    ev_ped = calcular_evolucao_raw(pedidos_loja, pedidos_ant)
    ev_vm = calcular_evolucao_raw(valor_medio_loja, valor_medio_ant)
    ev_cli = calcular_evolucao_raw(novos_clientes_loja, novos_clientes_ant)
    ev_pts = calcular_evolucao_raw(pontos_loja, pontos_ant)
    
    # Participação %
    pc_ped = calcular_evolucao_raw(pedidos_loja, pedidos_segmento)
    pc_vm = calcular_evolucao_raw(valor_medio_loja, valor_medio_segmento)
    pc_cli = calcular_evolucao_raw(novos_clientes_loja, novos_clientes_segmento)
    pc_pts = calcular_evolucao_raw(pontos_loja, pontos_segmento)

    # Tabela Item 1
    dados_comp = {
        'Métrica': ['Qtd de Pedidos', 'Valor Médio (Pontos)', 'Novos Clientes', 'Pontuação Total', 'Ranking da Loja'],
        'Loja Selecionada': [pedidos_loja, valor_medio_loja, novos_clientes_loja, pontos_loja, ranking_display],
        'Evolução T vs T-1': [
            formatar_evolucao_texto(ev_ped) if t_atual_num_principal > 0 else 'N/A',
            formatar_evolucao_texto(ev_vm) if t_atual_num_principal > 0 else 'N/A',
            formatar_evolucao_texto(ev_cli) if t_atual_num_principal > 0 else 'N/A',
            formatar_evolucao_texto(ev_pts) if t_atual_num_principal > 0 else 'N/A',
            variacao_ranking_texto if t_atual_num_principal > 0 else 'N/A'
        ],
        'Total Segmento': [pedidos_segmento, valor_medio_segmento, novos_clientes_segmento, pontos_segmento, ''],
        'Total Gabriel Pro': [pedidos_gabriel, valor_medio_gabriel, novos_clientes_gabriel, pontos_gabriel, ''],
        '% Loja/Segmento': [
            formatar_evolucao_texto(pc_ped), formatar_evolucao_texto(pc_vm), 
            formatar_evolucao_texto(pc_cli), formatar_evolucao_texto(pc_pts), ''
        ]
    }
    
    df_comp = pd.DataFrame(dados_comp)
    cols_num = ['Loja Selecionada', 'Total Segmento', 'Total Gabriel Pro']
    for col in cols_num:
        df_comp[col] = df_comp[col].apply(lambda x: formatar_milhar_br(x) if isinstance(x, (int, float)) else str(x))
        
    st.dataframe(
        df_comp.style.set_properties(**{'text-align': 'center', 'border': '1px solid #333'})
                      .set_properties(**{'font-weight': 'bold'}, subset=pd.IndexSlice[:, ['Métrica']]),
        use_container_width=True,
        hide_index=True
    )
    
    if t_atual_num_principal > 0:
        t_anterior_num = t_atual_num_principal - 1
        t_anterior_nome = f"Temporada {t_anterior_num}"
        st.markdown(f"**Nota:** A coluna **Evolução T vs T-1** compara os dados da **{temporada_selecionada_item1}** contra o **mesmo período proporcional (meses equivalentes)** da **{t_anterior_nome}**.")
    
    st.markdown("---")

    # =======================================================================
    # ITEM 2: TABELA COMPARATIVA DE CATEGORIAS
    # =======================================================================
    st.subheader("2. Comparativo de Profissionais por Categoria (Loja vs Segmento vs Gabriel Pro)")
    
    temporada_selecionada_item2 = st.selectbox(
        "Selecione a Temporada de Análise (Item 2):",
        options=opcoes_temporada_principal,
        index=0,
        key='sel_temp_2'
    )

    df_filtrado_item2 = df_filtrado_base.copy()
    df_segmento_total_item2 = df_segmento_total_base.copy()
    df_gabriel_total_item2 = df_gabriel_total_base.copy()

    if temporada_selecionada_item2 != 'Todas':
        df_filtrado_item2 = df_filtrado_item2[df_filtrado_item2['Temporada_Exibicao'] == temporada_selecionada_item2].copy()
        df_segmento_total_item2 = df_segmento_total_item2[df_segmento_total_item2['Temporada_Exibicao'] == temporada_selecionada_item2].copy()
        df_gabriel_total_item2 = df_gabriel_total_item2[df_gabriel_total_item2['Temporada_Exibicao'] == temporada_selecionada_item2].copy()

    def agrupar_e_classificar(df_base):
        df_base_agrupada = df_base.groupby(COLUNA_ESPECIFICADOR)['Pontos'].sum().reset_index()
        df_base_agrupada.columns = [COLUNA_ESPECIFICADOR, 'Pontuacao_Total']
        return calcular_categorias(df_base_agrupada)

    df_desempenho_filtrado = agrupar_e_classificar(df_filtrado_item2)
    df_desempenho_gabriel = agrupar_e_classificar(df_gabriel_total_item2)
    df_desempenho_segmento = agrupar_e_classificar(df_segmento_total_item2)

    def get_contagem_categoria(df_desempenho):
        todas_categorias = CATEGORIAS_NOMES 
        if df_desempenho.empty:
            return {cat: 0 for cat in todas_categorias}
        contagem = df_desempenho.groupby('Categoria')[COLUNA_ESPECIFICADOR].nunique().to_dict()
        for cat in todas_categorias:
            if cat not in contagem:
                contagem[cat] = 0
        return contagem

    contagem_loja_cat = get_contagem_categoria(df_desempenho_filtrado)
    contagem_segmento_cat = get_contagem_categoria(df_desempenho_segmento)
    contagem_gabriel_cat = get_contagem_categoria(df_desempenho_gabriel)

    tabela_categorias = []
    for categoria in CATEGORIAS_NOMES:
        qtd_loja = contagem_loja_cat[categoria]
        qtd_segmento = contagem_segmento_cat[categoria]
        participacao_raw = qtd_loja / qtd_segmento if qtd_segmento > 0 else 0.0
        
        tabela_categorias.append({
            'Profissional Ativo': categoria,
            'Qtd Loja': qtd_loja,
            'Qtd Segmento': qtd_segmento,
            'Qtd Gabriel Pro': contagem_gabriel_cat[categoria],
            'Participacao': participacao_raw,
            'Participacao Texto': f"{participacao_raw:.1%}"
        })

    df_categorias_comparativo = pd.DataFrame(tabela_categorias)
    
    # Linha Total
    qtd_loja_total = df_categorias_comparativo['Qtd Loja'].sum()
    qtd_segmento_total = df_categorias_comparativo['Qtd Segmento'].sum()
    participacao_total_raw = qtd_loja_total / qtd_segmento_total if qtd_segmento_total > 0 else 0.0
    
    total_row = {
        'Profissional Ativo': 'Total',
        'Qtd Loja': qtd_loja_total,
        'Qtd Segmento': qtd_segmento_total,
        'Qtd Gabriel Pro': df_categorias_comparativo['Qtd Gabriel Pro'].sum(),
        'Participacao': participacao_total_raw,
        'Participacao Texto': f"{participacao_total_raw:.1%}"
    }

    df_categorias_comparativo = pd.concat([df_categorias_comparativo, pd.DataFrame([total_row])], ignore_index=True)

    def style_participacao_row(val):
        if val.name == df_categorias_comparativo.index[-1]:
            return ['font-weight: bold;'] * len(val)
        return ['color: #d1d1d1; font-weight: bold'] * len(val)
            
    def style_nome_categoria_col(val):
        return CORES_CATEGORIA_TEXTO.get(val, '')

    st.dataframe(
        df_categorias_comparativo[['Profissional Ativo', 'Qtd Loja', 'Qtd Segmento', 'Qtd Gabriel Pro', 'Participacao Texto']].style
             .applymap(style_nome_categoria_col, subset=['Profissional Ativo']) 
             .apply(style_participacao_row, subset=['Participacao Texto'], axis=1) 
             .format({col: formatar_milhar_br for col in ['Qtd Loja', 'Qtd Segmento', 'Qtd Gabriel Pro']})
             .set_properties(**{'font-weight': 'bold'}, subset=pd.IndexSlice[df_categorias_comparativo['Profissional Ativo'] == 'Total', :])
             .set_properties(**{'text-align': 'center'}, subset=pd.IndexSlice[:, ['Qtd Loja', 'Qtd Segmento', 'Qtd Gabriel Pro', 'Participacao Texto']]), 
        use_container_width=True,
        column_config={
            "Participacao Texto": st.column_config.Column("Participação Loja/Segmento", width="medium")
        }
    )
    st.markdown("---")

    # =======================================================================
    # ITEM 3: EVOLUÇÃO PONTUAÇÃO (PIVOT)
    # =======================================================================
    st.subheader("3. Evolução da Pontuação por Mês e Temporada (Filtrado por Loja/Segmento)")
    
    if 'Mês_Exibicao' in df_filtrado_base.columns and 'Temporada_Exibicao' in df_filtrado_base.columns and temporadas_selecionadas_exib:
        df_base_pivot_mensal = df_filtrado_base.copy()
        
        # 1. Pivot Full (Global para estrutura)
        df_pivot_base_full = df_global.pivot_table(
            index='Mês_Exibicao', columns='Temporada_Exibicao', values='Pontos', aggfunc='sum', fill_value=0
        ).reset_index()

        # 2. Filtra Meses
        df_pivot_filtrado = df_pivot_base_full[df_pivot_base_full['Mês_Exibicao'].isin(meses_selecionados_exib)].copy()
        
        colunas_temporada_full = [col for col in df_pivot_base_full.columns if col.startswith('Temporada')]
        colunas_temporada_sorted_num = sorted([
            col for col in colunas_temporada_full if col != 'Temporada 0' and len(col.split(' ')) > 1
        ], key=lambda x: int(x.split(' ')[1]))
        
        # 3. Pivot da Loja
        df_valores_filtrados_loja = df_base_pivot_mensal.pivot_table(
            index='Mês_Exibicao', columns='Temporada_Exibicao', values='Pontos', aggfunc='sum', fill_value=0
        )
        
        df_pivot_pontos = df_pivot_filtrado[['Mês_Exibicao']].copy()
        colunas_temporada_sorted_num_selecionadas = []
        
        for col in colunas_temporada_sorted_num:
            if col in temporadas_selecionadas_exib:
                df_pivot_pontos[col] = df_pivot_pontos['Mês_Exibicao'].map(
                    df_valores_filtrados_loja[col].to_dict() if col in df_valores_filtrados_loja.columns else {}
                ).fillna(0)
                colunas_temporada_sorted_num_selecionadas.append(col)
            else:
                df_pivot_pontos[col] = 0
        
        df_pivot_pontos = df_pivot_pontos[['Mês_Exibicao'] + colunas_temporada_sorted_num_selecionadas].copy()
        
        # Ordenação
        df_pivot_pontos['Ordem'] = df_pivot_pontos['Mês_Exibicao'].map(MES_ORDEM_FISCAL)
        df_pivot_pontos.sort_values(by='Ordem', inplace=True)
        df_pivot_pontos.drop('Ordem', axis=1, inplace=True)
        
        # Evolução
        if len(colunas_temporada_sorted_num_selecionadas) >= 2:
            t_atual_col = colunas_temporada_sorted_num_selecionadas[-1]
            t_anterior_col = colunas_temporada_sorted_num_selecionadas[-2]
            
            df_pivot_pontos['Evolução Pontos Valor'] = df_pivot_pontos.apply(
                lambda row: calcular_evolucao_raw(row[t_atual_col], row[t_anterior_col]), axis=1
            )
            nome_coluna_evolucao = f"Evolução Pontos ({t_atual_col.replace('Temporada ', 'T')} vs {t_anterior_col.replace('Temporada ', 'T')})"
            
            df_pivot_pontos.set_index('Mês_Exibicao', inplace=True) 
            total_row = pd.Series(df_pivot_pontos[colunas_temporada_sorted_num_selecionadas].sum(), name='Total')
            
            crescimento_total_raw = calcular_evolucao_raw(total_row[t_atual_col], total_row[t_anterior_col])
            total_row['Evolução Pontos Valor'] = crescimento_total_raw
            
            df_pivot_pontos = pd.concat([df_pivot_pontos, pd.DataFrame(total_row).T]) 
            df_pivot_pontos.index.name = 'Mês'
            df_pivot_pontos[nome_coluna_evolucao] = df_pivot_pontos['Evolução Pontos Valor'].apply(formatar_evolucao_texto)
            
            colunas_a_exibir = colunas_temporada_sorted_num_selecionadas + [nome_coluna_evolucao]
            
            def style_evolucao_percentual_texto(series):
                raw_values = df_pivot_pontos['Evolução Pontos Valor']
                styles = []
                for index, val in raw_values.items():
                    color = ''
                    if val > 0.0001: color = 'color: #00FF00; font-weight: bold' 
                    elif val < -0.0001: color = 'color: #FF0000; font-weight: bold' 
                    else: color = 'color: #00009C; font-weight: bold' 
                    
                    if index == 'Total': color += '; background-color: #333333; color: white'
                    styles.append(color)
                return styles
            
            st.dataframe(
                df_pivot_pontos[colunas_a_exibir].style.format({col: formatar_milhar_br for col in colunas_temporada_sorted_num_selecionadas})
                    .apply(style_evolucao_percentual_texto, subset=[nome_coluna_evolucao], axis=0)
                    .set_properties(**{'border': '1px solid #333333', 'text-align': 'center'}, subset=pd.IndexSlice[:, colunas_temporada_sorted_num_selecionadas]),
                use_container_width=True
            )
        else:
             df_pivot_pontos.set_index('Mês_Exibicao', inplace=True)
             df_pivot_pontos.index.name = 'Mês'
             total_row = pd.Series(df_pivot_pontos[colunas_temporada_sorted_num_selecionadas].sum(), name='Total')
             df_pivot_pontos = pd.concat([df_pivot_pontos, pd.DataFrame(total_row).T])
             st.dataframe(
                 df_pivot_pontos[colunas_temporada_sorted_num_selecionadas].style.format({col: formatar_milhar_br for col in colunas_temporada_sorted_num_selecionadas})
                    .set_properties(**{'border': '1px solid #333333', 'text-align': 'center'}),
                 use_container_width=True
             )
    else:
        st.info("Selecione pelo menos uma temporada no filtro lateral.")
    st.markdown("---")

    # =======================================================================
    # ITEM 4: VALOR MÉDIO
    # =======================================================================
    st.subheader("4. Valor Médio de Pedido por Mês e Temporada (Filtrado por Loja/Segmento)")
    
    if 'Mês_Exibicao' in df_filtrado_base.columns and 'Temporada_Exibicao' in df_filtrado_base.columns and temporadas_selecionadas_exib:
        df_base_vm = df_filtrado_base.copy()
        
        df_agrupado_total_temp = df_base_vm.groupby('Temporada_Exibicao').agg(
            Pontos_Total=('Pontos', 'sum'),
            Pedidos_Unicos=(COLUNA_PEDIDO, 'nunique')
        ).reset_index()
        
        df_agrupado_total_temp['Valor_Medio_Total'] = np.where(
            df_agrupado_total_temp['Pedidos_Unicos'] > 0,
            df_agrupado_total_temp['Pontos_Total'] / df_agrupado_total_temp['Pedidos_Unicos'], 0
        )
        
        df_agrupado_filtrado = df_base_vm.groupby(['Mês_Exibicao', 'Temporada_Exibicao']).agg(
            Pontos_Total=('Pontos', 'sum'),
            Pedidos_Unicos=(COLUNA_PEDIDO, 'nunique')
        ).reset_index()
        
        df_agrupado_filtrado['Valor_Medio_Filtrado'] = np.where(
            df_agrupado_filtrado['Pedidos_Unicos'] > 0,
            df_agrupado_filtrado['Pontos_Total'] / df_agrupado_filtrado['Pedidos_Unicos'], 0
        )
        
        df_pivot_mensal_final = df_agrupado_filtrado.pivot_table(
            index='Mês_Exibicao', columns='Temporada_Exibicao', values='Valor_Medio_Filtrado', fill_value=0
        ).reset_index()
        
        df_pivot_mensal_final = df_pivot_mensal_final[df_pivot_mensal_final['Mês_Exibicao'].isin(meses_selecionados_exib)].copy()
        
        colunas_temporada_vm_sorted_num = sorted([
            col for col in df_pivot_mensal_final.columns if col.startswith('Temporada') and col != 'Temporada 0'
        ], key=lambda x: int(x.split(' ')[1]))

        colunas_para_dropar = [col for col in colunas_temporada_vm_sorted_num if col not in temporadas_selecionadas_exib]
        df_pivot_mensal_final.drop(columns=colunas_para_dropar, inplace=True, errors='ignore')
        
        colunas_display_vm = []
        colunas_temporada_vm_selecionadas = []
        for col in df_pivot_mensal_final.columns:
            if col.startswith('Temporada'):
                novo_nome = f"Médio Por Pedido {col.replace('Temporada ', 'T')}"
                df_pivot_mensal_final.rename(columns={col: novo_nome}, inplace=True)
                colunas_display_vm.append(novo_nome)
                colunas_temporada_vm_selecionadas.append(col)
            elif col == 'Mês_Exibicao':
                df_pivot_mensal_final.rename(columns={col: 'Mês'}, inplace=True)
        
        df_pivot_mensal_final['Ordem'] = df_pivot_mensal_final['Mês'].map(MES_ORDEM_FISCAL)
        df_pivot_mensal_final.sort_values(by='Ordem', inplace=True)
        df_pivot_mensal_final.drop('Ordem', axis=1, inplace=True)
        
        st.markdown("##### Valor Médio Total das Vendas por Pedido (Temporada)")
        num_cols_kpi_vm = max(1, len(colunas_temporada_vm_selecionadas))
        cols_kpi_vm = st.columns(num_cols_kpi_vm)
        
        if colunas_temporada_vm_selecionadas: 
            for i, t_col in enumerate(colunas_temporada_vm_selecionadas):
                vm_valor_series = df_agrupado_total_temp.loc[df_agrupado_total_temp['Temporada_Exibicao'] == t_col, 'Valor_Medio_Total']
                vm_valor = vm_valor_series.iloc[0] if not vm_valor_series.empty else 0
                with cols_kpi_vm[i]:
                    st.metric(f"Valor Médio {t_col.replace('Temporada ', 'T')}", formatar_milhar_br(vm_valor))
        
        df_pivot_mensal_final.set_index('Mês', inplace=True)
        st.dataframe(
            df_pivot_mensal_final.style.format({col: lambda x: formatar_milhar_br(x) for col in colunas_display_vm})
                .set_properties(**{'border': '1px solid #333333', 'text-align': 'center'}, subset=pd.IndexSlice[:, colunas_display_vm]),
            use_container_width=True
        )
    else:
        st.info("Selecione pelo menos uma temporada no filtro lateral.")
    st.markdown("---")

    # =======================================================================
    # ITEM 5: TENDÊNCIA
    # =======================================================================
    st.subheader("5. Tendência Mensal de Pontuação")
    
    temporada_selecionada_item5 = st.selectbox(
        "Selecione a Temporada de Análise (Item 5):",
        options=opcoes_temporada_principal,
        index=0, 
        key='sel_temp_5'
    )
    
    df_filtrado_item5 = df_filtrado_base.copy()
    if temporada_selecionada_item5 != 'Todas':
        df_filtrado_item5 = df_filtrado_item5[df_filtrado_item5['Temporada_Exibicao'] == temporada_selecionada_item5].copy()

    if 'Data da Venda' in df_filtrado_item5.columns:
        df_tendencia = df_filtrado_item5.set_index('Data da Venda').resample('M')['Pontos'].sum().reset_index()
        df_tendencia.columns = ['Data', 'Pontos Totais']
        
        fig_tendencia = px.line(df_tendencia, x='Data', y='Pontos Totais', title='Pontos Totais por Mês/Ano', markers=True)
        st.plotly_chart(fig_tendencia, use_container_width=True)

    st.markdown("---")

    # =======================================================================
    # ITEM 6: PEDIDOS ÚNICOS
    # =======================================================================
    df_filtrado_item6 = df_filtrado_item5.copy()
    
    if 'Mês_Exibicao' in df_filtrado_item6.columns and COLUNA_PEDIDO in df_filtrado_item6.columns:
        st.subheader("6. Pedidos Únicos por Mês")
        df_pedidos_por_mes = df_filtrado_item6.groupby('Mês_Exibicao')[COLUNA_PEDIDO].nunique().reset_index()
        df_pedidos_por_mes.columns = ['Mês', 'Pedidos']
        df_pedidos_por_mes['Mês_Ordem'] = df_pedidos_por_mes['Mês'].map(MES_ORDEM_FISCAL)
        df_pedidos_por_mes.sort_values(by='Mês_Ordem', inplace=True)
        
        fig_pedidos_mes = px.bar(df_pedidos_por_mes, x='Mês', y='Pedidos', title='Contagem de Pedidos Únicos por Mês', color='Mês', text='Pedidos')
        st.plotly_chart(fig_pedidos_mes, use_container_width=True)
    st.markdown("---")

    # =======================================================================
    # ITEM 7: DESEMPENHO PROFISSIONAL (Lógica Ajustada: Meses Equivalentes)
    # =======================================================================
    if COLUNA_ESPECIFICADOR in df_filtrado_base.columns:
        st.subheader("7. Desempenho por Profissional e Categoria")
        
        temporada_selecionada_item7 = st.selectbox(
            "Selecione a Temporada de Análise (Item 7):",
            options=opcoes_temporada_principal,
            index=0, 
            key='sel_temp_7'
        )
        
        df_filtrado_item7 = df_filtrado_base.copy()
        t_atual_num_item7 = 0
        if temporada_selecionada_item7 != 'Todas':
            df_filtrado_item7 = df_filtrado_item7[df_filtrado_item7['Temporada_Exibicao'] == temporada_selecionada_item7].copy()
            if not df_filtrado_item7.empty and COLUNA_NUMERO_TEMPORADA in df_filtrado_item7.columns:
                t_atual_num_item7 = df_filtrado_item7[COLUNA_NUMERO_TEMPORADA].iloc[0]
        
        # 1. Agrupamento (Temporada Atual)
        df_desempenho = df_filtrado_item7.groupby(COLUNA_ESPECIFICADOR).agg(
            Pontuacao_Total=('Pontos', 'sum'), Qtd_Pedidos=(COLUNA_PEDIDO, 'nunique')
        ).reset_index()
        df_desempenho = calcular_categorias(df_desempenho)
        
        # CPF Map
        df_cnpj_original = df_filtrado_item7[[COLUNA_ESPECIFICADOR, COLUNA_CNPJ_CPF, 'CNPJ_CPF_LIMPO']].drop_duplicates(subset=[COLUNA_ESPECIFICADOR, 'CNPJ_CPF_LIMPO'])
        df_desempenho = pd.merge(df_desempenho, df_cnpj_original[[COLUNA_ESPECIFICADOR, COLUNA_CNPJ_CPF]], on=COLUNA_ESPECIFICADOR, how='left')
        df_desempenho.sort_values(by='Pontuacao_Total', ascending=False, inplace=True)
        
        # 2. Resumo Categorias e Preparação do Histórico Equivalente
        df_resumo_cat = df_desempenho[df_desempenho['Categoria'].isin(CATEGORIAS_NOMES)].groupby('Categoria').agg(
            Contagem=('Categoria', 'size'), Pontuacao_Categoria=('Pontuacao_Total', 'sum')
        ).reset_index()
        
        # --- LÓGICA DE MESES EQUIVALENTES PARA ITEM 7 ---
        dict_pontuacao_ant_categoria = {}
        pontuacao_total_anterior_geral = 0.0
        
        if t_atual_num_item7 > 0:
            # Identificar meses da temporada atual selecionada
            meses_eq_7 = df_filtrado_item7['Mês_Exibicao'].unique()
            t_ant_str_7 = f"Temporada {t_atual_num_item7 - 1}"
            
            # Filtrar Global para T-1 com os mesmos meses
            df_ant_filtrado_7 = df_global[
                (df_global['Temporada_Exibicao'] == t_ant_str_7) &
                (df_global['Mês_Exibicao'].isin(meses_eq_7)) &
                (df_global['Loja'].isin(lojas_selecionadas)) &
                (df_global['Segmento'].isin(segmentos_selecionados))
            ].copy()
            
            # Calcular Pontuação Total Anterior (Geral para a barra de progresso)
            pontuacao_total_anterior_geral = df_ant_filtrado_7['Pontos'].sum()
            
            # Calcular Pontuação por Categoria (Requer classificar a base antiga primeiro)
            if not df_ant_filtrado_7.empty:
                df_agg_ant = df_ant_filtrado_7.groupby(COLUNA_ESPECIFICADOR)['Pontos'].sum().reset_index()
                df_agg_ant.columns = [COLUNA_ESPECIFICADOR, 'Pontuacao_Total']
                df_cat_ant = calcular_categorias(df_agg_ant)
                # Somar pontos por categoria
                dict_pontuacao_ant_categoria = df_cat_ant.groupby('Categoria')['Pontuacao_Total'].sum().to_dict()
        
        # 3. Cálculo da Evolução
        evolucao_data = []
        if t_atual_num_item7 > 0:
            for index, row in df_resumo_cat.iterrows():
                # Busca do dicionário pré-calculado (muito mais rápido e correto pelo mês)
                pontuacao_anterior = dict_pontuacao_ant_categoria.get(row['Categoria'], 0)
                crescimento_raw = calcular_evolucao_raw(row['Pontuacao_Categoria'], pontuacao_anterior)
                evolucao_data.append({'Categoria': row['Categoria'], 'Evolução Pontos': crescimento_raw, 'Evolução Pontos Texto': formatar_evolucao_texto(crescimento_raw)})
        else:
            for cat in CATEGORIAS_NOMES: evolucao_data.append({'Categoria': cat, 'Evolução Pontos': 0.0, 'Evolução Pontos Texto': 'N/A'})

        df_evolucao = pd.DataFrame(evolucao_data)
        df_resumo_cat = pd.merge(df_resumo_cat, df_evolucao, on='Categoria', how='left')
        
        # Totais
        pontos_loja_item7 = df_filtrado_item7['Pontos'].sum()
        crescimento_total_raw = 0.0
        evolucao_total_texto = 'N/A'
        
        if t_atual_num_item7 > 0:
            crescimento_total_raw = calcular_evolucao_raw(pontos_loja_item7, pontuacao_total_anterior_geral)
            evolucao_total_texto = formatar_evolucao_texto(crescimento_total_raw)
            
        df_total_row = pd.DataFrame([{
            'Categoria': 'Total', 'Contagem': df_resumo_cat['Contagem'].sum(),
            'Pontuacao_Categoria': df_resumo_cat['Pontuacao_Categoria'].sum(),
            'Evolução Pontos': crescimento_total_raw, 'Evolução Pontos Texto': evolucao_total_texto
        }])
        
        df_resumo_cat_display = pd.concat([df_resumo_cat, df_total_row], ignore_index=True)
        
        # Exibição KPIs
        st.markdown("##### Resumo das Categorias")
        colunas_matriz = CATEGORIAS_NOMES + ['Total']
        cols_count = st.columns(len(colunas_matriz))
        cols_pts = st.columns(len(colunas_matriz))
        cols_evo = st.columns(len(colunas_matriz))
        
        for i, cat in enumerate(colunas_matriz):
            temp = df_resumo_cat_display[df_resumo_cat_display['Categoria'] == cat]
            if not temp.empty:
                row = temp.iloc[0]
                val_ct, val_pt, val_ev, txt_ev = row['Contagem'], row['Pontuacao_Categoria'], row['Evolução Pontos'], row['Evolução Pontos Texto']
            else:
                val_ct, val_pt, val_ev, txt_ev = 0, 0, 0.0, "N/A"
            
            cor = CORES_CATEGORIA_TEXTO.get(cat, 'color: #ffffff').split(';')[0].split(': ')[1]
            with cols_count[i]:
                st.markdown(f"<p style='color: {cor}; font-weight: bold;'>{cat}</p>", unsafe_allow_html=True)
                st.metric(' ', formatar_milhar_br(val_ct))
            with cols_pts[i]:
                st.metric(f"Pts {cat}", formatar_milhar_br(val_pt))
            with cols_evo[i]:
                color_ev = '#00FF00' if val_ev > 0 else '#FF0000' if val_ev < 0 else '#00009C'
                st.markdown(f"<p style='color: {color_ev}; font-weight: bold;'>{txt_ev}</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        termo_pesquisa = st.text_input("Pesquisar Profissional:", key='search_prof')
        
        df_tabela = df_desempenho[df_desempenho['Categoria'].isin(CATEGORIAS_NOMES)].copy()
        
        if df_tabela.empty:
            st.info("Nenhum dado encontrado para os filtros selecionados.")
        else:
            if termo_pesquisa:
                t = termo_pesquisa.lower()
                df_tabela = df_tabela[
                    df_tabela[COLUNA_ESPECIFICADOR].astype(str).str.lower().str.contains(t) | 
                    df_tabela['Categoria'].astype(str).str.lower().str.contains(t) | 
                    df_tabela[COLUNA_CNPJ_CPF].astype(str).str.lower().str.contains(t)
                ]
            
            cols_necessarias = [COLUNA_ESPECIFICADOR, COLUNA_CNPJ_CPF, 'Pontuacao_Total', 'Qtd_Pedidos', 'Categoria']
            cols_existentes = [col for col in cols_necessarias if col in df_tabela.columns]
            
            if len(cols_existentes) == len(cols_necessarias):
                df_tabela = df_tabela[cols_necessarias]
                df_tabela.columns = ['Especificador', 'CPF/CNPJ', 'Pontuação', 'Pedidos', 'Categoria']
                df_tabela['Pontuação'] = df_tabela['Pontuação'].apply(formatar_milhar_br)
                df_tabela['Pedidos'] = df_tabela['Pedidos'].apply(formatar_milhar_br)
                
                def style_cat(val): return CORES_CATEGORIA_TEXTO.get(val, '')
                st.dataframe(df_tabela.style.applymap(style_cat, subset=['Categoria']).set_properties(**{'text-align': 'center'}, subset=['Pontuação', 'Pedidos']), use_container_width=True)
            else:
                st.warning("Estrutura de dados incompleta para exibição da tabela detalhada.")

    # =======================================================================
    # ITEM 8: NOVOS CADASTROS
    # =======================================================================
    st.markdown("---")
    st.subheader("8. Novos Cadastrados")
    
    col1_8, col2_8 = st.columns([1, 2])
    with col1_8:
        temporada_novos = st.selectbox("Temporada (8A/8B):", options=opcoes_temporada_principal, index=0, key='sel_temp_8')
    with col2_8:
        st.session_state['termo_pesquisa_novos'] = st.text_input("Pesquisar Novo:", value=st.session_state['termo_pesquisa_novos'])
    
    df_novos_base = df_filtrado_base[df_filtrado_base['Novo_Cadastrado'] == True].copy()
    df_novos_filtrados = df_novos_base.copy()
    if temporada_novos != 'Todas':
        df_novos_filtrados = df_novos_filtrados[df_novos_filtrados['Temporada_Exibicao'] == temporada_novos]
    
    # KPIs Topo Item 8
    cols_temp_str = sorted(df_novos_base['Temporada_Exibicao'].loc[df_novos_base['Temporada_Exibicao'] != 'Temporada 0'].unique(), key=lambda x: int(x.split(' ')[1]))
    cols_kpi_p = st.columns(max(1, len(cols_temp_str)))
    for i, t in enumerate(cols_temp_str):
        visible = (temporada_novos == 'Todas') or (temporada_novos == t)
        pts = df_novos_base.loc[df_novos_base['Temporada_Exibicao'] == t, 'Pontos'].sum() if visible else 0
        with cols_kpi_p[i]: st.metric(f"Pts Novos {t}", formatar_milhar_br(pts))
            
    st.markdown("##### 8 A. Contagem Novos")
    if 'Mês_Exibicao' in df_novos_base.columns:
        df_pivot_novos_full = df_novos_base.pivot_table(index='Mês_Exibicao', columns='Temporada_Exibicao', values='Novo_Cadastrado', aggfunc='sum', fill_value=0).reset_index()
        df_pivot_novos = df_pivot_novos_full[df_pivot_novos_full['Mês_Exibicao'].isin(meses_selecionados_exib)].copy()
        
        # Ordenação Mês
        df_pivot_novos['Ordem'] = df_pivot_novos['Mês_Exibicao'].map(MES_ORDEM_FISCAL)
        df_pivot_novos.sort_values(by='Ordem', inplace=True)
        df_pivot_novos.drop('Ordem', axis=1, inplace=True)
        df_pivot_novos.set_index('Mês_Exibicao', inplace=True)
        
        # Filtra colunas
        cols_to_show = [c for c in cols_temp_str if (temporada_novos == 'Todas' or c == temporada_novos)]
        if cols_to_show:
            st.dataframe(df_pivot_novos[cols_to_show], use_container_width=True)

    st.markdown("##### 8 B. Lista Detalhada")
    df_nomes_novos = df_novos_filtrados.groupby([COLUNA_ESPECIFICADOR, 'CNPJ_CPF_LIMPO']).agg(
        Primeira_Compra=('Data da Venda', 'min'), Temporada=(COLUNA_NUMERO_TEMPORADA, 'first'), Pontos=('Pontos', 'sum')
    ).reset_index()
    
    term_n = st.session_state['termo_pesquisa_novos'].lower()
    if term_n:
        df_nomes_novos = df_nomes_novos[df_nomes_novos[COLUNA_ESPECIFICADOR].astype(str).str.lower().str.contains(term_n) | df_nomes_novos['CNPJ_CPF_LIMPO'].astype(str).str.contains(term_n)]
        
    df_nomes_novos['Pontos'] = df_nomes_novos['Pontos'].apply(formatar_milhar_br)
    df_nomes_novos['Primeira_Compra'] = df_nomes_novos['Primeira_Compra'].dt.strftime('%d/%m/%Y')
    st.dataframe(df_nomes_novos, use_container_width=True)

    # =======================================================================
    # ITEM 9: ATIVOS / INATIVOS
    # =======================================================================
    st.markdown("---")
    st.subheader("9. Clientes Ativos vs Inativos")
    
    # IMPORTANTE: Passamos [store_name] fixo como lista
    df_anual, clientes_hist = calcular_clientes_ativos_inativos(df_global, lojas_selecionadas, segmentos_selecionados)
    
    col_cfg = {
        'Contagem de Clientes Pontuando (Ativos)': st.column_config.Column("Ativos", help="Clique para filtrar"),
        'Contagem de Clientes Não Pontuando (Inativos)': st.column_config.Column("Inativos", help="Clique para filtrar")
    }
    
    evento = st.dataframe(
        df_anual.style.format(precision=0).set_properties(**{'border': '1px solid #333'}),
        column_config=col_cfg, use_container_width=True, selection_mode="single-row", on_select="rerun"
    )
    
    if evento.selection['rows']:
        idx = evento.selection['rows'][0]
        row = df_anual.iloc[idx]
        col1, col2 = st.columns(2)
        sel = None
        with col1: 
            if st.button(f"Ver ATIVOS {row['Temporada']}"): sel = 'ativo'
        with col2: 
            if st.button(f"Ver INATIVOS {row['Temporada']}"): sel = 'inativo'
        
        if sel:
            st.session_state['filtro_status_ano'] = {'temporada': row['Temporada'], 'status': sel, 'termo_pesquisa': sel.upper()}
            st.rerun()

    st.markdown("##### 9 B. Detalhe Ativos/Inativos")
    clientes_ativos_periodo = set(df_filtrado_base['CNPJ_CPF_LIMPO'].unique())
    clientes_inativos = clientes_hist.difference(clientes_ativos_periodo)
    
    df_ativos = df_filtrado_base.groupby([COLUNA_ESPECIFICADOR, 'CNPJ_CPF_LIMPO']).agg(Qtd=(COLUNA_PEDIDO, 'nunique'), Data=('Data da Venda', 'max')).reset_index()
    df_ativos['Status'] = 'ATIVO'
    
    df_hist_rel = df_global[(df_global['Loja'].isin(lojas_selecionadas)) & (df_global['Segmento'].isin(segmentos_selecionados))]
    df_inativos_base = df_hist_rel[df_hist_rel['CNPJ_CPF_LIMPO'].isin(clientes_inativos)].copy()
    df_inativos = df_inativos_base.groupby([COLUNA_ESPECIFICADOR, 'CNPJ_CPF_LIMPO']).agg(Data=('Data da Venda', 'max')).reset_index()
    df_inativos['Qtd'] = 0
    df_inativos['Status'] = 'INATIVO'
    
    df_detalhe = pd.concat([df_ativos, df_inativos], ignore_index=True)
    df_detalhe.sort_values(by=['Status', 'Qtd'], ascending=[False, False], inplace=True)
    
    termo_atv = st.text_input("Pesquisar Detalhe:", value=st.session_state['filtro_status_ano']['termo_pesquisa'])
    # Limpa a session após usar o valor inicial
    st.session_state['filtro_status_ano']['termo_pesquisa'] = ''
    
    if termo_atv:
        t = termo_atv.lower()
        df_detalhe = df_detalhe[df_detalhe[COLUNA_ESPECIFICADOR].astype(str).str.lower().str.contains(t) | df_detalhe['Status'].astype(str).str.lower().str.contains(t)]

    df_detalhe['Data'] = df_detalhe['Data'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '-')
    
    def style_st(row): return ['color: #00FF00' if row['Status']=='ATIVO' else 'color: #FF0000'] * len(row)
    st.dataframe(df_detalhe.style.apply(style_st, axis=1), use_container_width=True)

    # =======================================================================
    # ITEM 10: RANKING
    # =======================================================================
    st.markdown("---")
    ts = sorted(df_global[COLUNA_NUMERO_TEMPORADA].loc[df_global[COLUNA_NUMERO_TEMPORADA] > 0].unique())
    
    if len(ts) >= 2:
        t_atual, t_ant = ts[-1], ts[-2]
        
        # Ajustado para capturar as variáveis de max_rank necessárias para o texto explicativo
        df_rank, t_atual_nome, t_anterior_nome, max_rank_t_atual, max_rank_t_anterior = calcular_ranking_ajustado(
            df_global, lojas_selecionadas, segmentos_selecionados, t_atual, t_ant
        )
        
        st.subheader(f"10. Variação Ranking ({t_atual_nome} vs {t_anterior_nome})")
        
        if not df_rank.empty:
            def style_rk(val): return 'color: #00FF00' if val > 0 else 'color: #FF0000' if val < 0 else 'color: #00009C'
            
            st.dataframe(df_rank.style.applymap(style_rk, subset=['Variação Rank']), use_container_width=True)
            
            # Texto explicativo adicionado conforme solicitado
            st.markdown(f"""
            **Lógica da Variação Rank:** `{t_anterior_nome} Rank Ajustado - {t_atual_nome} Rank Ajustado`.
            - **Valor Positivo (Verde):** O profissional **Melhorou** seu ranking (ex: de 5 para 1. Variação: 5 - 1 = +4).
            - **Valor Negativo (Vermelho):** O profissional **Piorou** seu ranking (ex: de 1 para 5. Variação: 1 - 5 = -4).
            - **Valor Zero (Azul):** O profissional manteve a mesma posição de ranking em ambas as temporadas.
            - **Rank Ajustado (Gap Filling):** Posições **{max_rank_t_anterior + 1}** (para {t_anterior_nome}) ou **{max_rank_t_atual + 1}** (para {t_atual_nome}) são atribuídas a profissionais que pontuaram em uma temporada, mas não na outra, dentro dos filtros de Loja/Segmento.
            """)
        else:
            st.info("Nenhum dado de ranking disponível para as temporadas selecionadas.")
    else:
        st.info("Dados insuficientes para cálculo de variação de ranking (necessárias pelo menos 2 temporadas com dados).")