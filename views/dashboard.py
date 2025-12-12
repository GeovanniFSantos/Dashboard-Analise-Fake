# views/dashboard.py

# ==============================================================================
# 1. IMPORTS
# ==============================================================================
import pandas as pd
import streamlit as st
import plotly.express as px
import numpy as np
from datetime import date, timedelta

# Módulos do Usuário
from modulos.config import *
from modulos.tratamento import (
    formatar_milhar_br, style_total_pontuacao, calcular_evolucao_pct,
    style_nome_categoria, formatar_documento, separate_documents,
    get_last_two_seasons
)
from modulos.dados import carregar_e_tratar_dados
from modulos.kpi import calcular_metricas
from modulos.comparativo_temporada import calcular_metricas_temporais
from modulos.categoria import calcular_categorias, get_pontuacao_temporada_anterior, get_contagem_categoria
from modulos.analise_lojas import calcular_analise_lojas
from modulos.evolucao_pontos import calcular_pivo_pontos
from modulos.pedidos import calcular_pivo_pedidos, calcular_pivo_novos_clientes
from modulos.retencao import calcular_clientes_ativos_inativos
from modulos.ranking import calcular_ranking_ajustado
from modulos.desempenho_base import calcular_desempenho_consolidado 

# ==============================================================================
# 2. CONSTANTES E ESTILOS GLOBAIS
# ==============================================================================
STYLE_FONT_SIZE = '18px'
STYLE_TABLE_PROPS = {'font-size': STYLE_FONT_SIZE, 'text-align': 'center', 'border': '1px solid #333333'}

def aplicar_css_global():
    """Aplica estilos CSS globais para métricas e textos."""
    st.markdown(f"""
        <style>
            /* Ajusta o valor principal (número) */
            div[data-testid="stMetricValue"] {{
                font-size: 22px !important;
            }}
            /* Ajusta o label (Texto de Rótulo) */
            div[data-testid="stMetricLabel"] {{
                font-size: 19px !important;
                text-align: center;
                font-weight: bold;
            }}
            /* Ajusta texto de evolução */
            div[data-testid="stVerticalBlock"] p {{
                font-size: 18px; 
            }}
        </style>
        """, unsafe_allow_html=True)

# ==============================================================================
# 3. HELPER: MESMOS MESES (Lógica de Comparação Justa)
# ==============================================================================
def filtrar_mesmos_meses(df_base, t_atual_nome, t_anterior_nome):
    """
    Retorna dois dataframes filtrados contendo apenas os meses presentes na temporada atual.
    Isso garante que T10 (4 meses) seja comparada com T9 (apenas os mesmos 4 meses).
    """
    # 1. Identificar meses presentes na Temporada Atual
    meses_t_atual = df_base[df_base['Temporada_Exibicao'] == t_atual_nome]['Mês_Exibicao'].unique()
    
    # 2. Filtrar ambas as temporadas para ter apenas esses meses
    df_filtrado_meses = df_base[df_base['Mês_Exibicao'].isin(meses_t_atual)].copy()
    
    return df_filtrado_meses

# ==============================================================================
# 4. BARRA LATERAL (FILTROS)
# ==============================================================================
def render_sidebar(df_dados_original):
    """Renderiza a barra lateral e retorna os filtros aplicados."""
    st.sidebar.header("Filtros Interativos")
    
    # 1. Filtro Temporada
    todas_temporadas = sorted(
        df_dados_original['Temporada_Exibicao']
        .loc[df_dados_original['Temporada_Exibicao'] != 'Temporada 0']
        .dropna().unique()
    )
    
    sel_temporadas = st.sidebar.multiselect(
        "Selecione a Temporada:",
        options=todas_temporadas,
        default=todas_temporadas
    )
    
    # Filtra base inicial
    df_temp = df_dados_original.copy()
    if sel_temporadas:
        df_temp = df_temp[df_temp['Temporada_Exibicao'].isin(sel_temporadas)]

    # 2. Filtro Mês
    sel_meses = []
    if 'Mês_Exibicao' in df_temp.columns:
        meses_unicos = sorted(df_temp['Mês_Exibicao'].dropna().unique())
        sel_meses = st.sidebar.multiselect(
            "Selecione o Mês:",
            options=meses_unicos,
            default=meses_unicos
        )
        if sel_meses:
            df_temp = df_temp[df_temp['Mês_Exibicao'].isin(sel_meses)]

    df_total_periodo = df_temp.copy() # Base filtrada por DATA apenas

    # 3. Filtros Hierárquicos (Segmento > Loja)
    st.sidebar.subheader("Filtros de Entidade")
    
    segmentos_todos = sorted(df_total_periodo['Segmento'].unique())
    sel_segmentos = st.sidebar.multiselect(
        "Selecione o Segmento:",
        options=segmentos_todos,
        default=segmentos_todos
    )
    
    df_apos_segmento = df_total_periodo[df_total_periodo['Segmento'].isin(sel_segmentos)]
    
    lojas_unicas = sorted(df_apos_segmento['Loja'].unique())
    sel_lojas = st.sidebar.multiselect(
        "Selecione a Loja (Filtro Secundário):",
        options=lojas_unicas,
        default=lojas_unicas
    )

    # DataFrame Final
    df_filtrado = df_apos_segmento[df_apos_segmento['Loja'].isin(sel_lojas)].copy()
    if not sel_lojas:
        df_filtrado = df_apos_segmento.copy()

    return {
        'df_filtrado': df_filtrado,
        'df_total_periodo': df_total_periodo,
        'df_segmento_total': df_apos_segmento, # Para Item 1
        'sel_temporadas': sel_temporadas,
        'sel_meses': sel_meses,
        'sel_segmentos': sel_segmentos,
        'sel_lojas': sel_lojas,
        'todas_temporadas': todas_temporadas
    }

# ==============================================================================
# 5. ITENS DO DASHBOARD (RENDERIZAÇÃO)
# ==============================================================================

# ITEM 1
def render_item_1_comparativo_temporada(df_filtrado, df_novos_orig, todas_temporadas):
    st.subheader("1. Comparativo de Desempenho por Temporada")
    st.markdown("##### Performance por Temporada (Filtrada por Segmento e Loja)")
    
    df_desempenho = calcular_metricas_temporais(
        df_filtrado, df_novos_orig, todas_temporadas, 'Gabriel Pro Total'
    )
    
    df_combinado = pd.concat([df_desempenho], keys=['Gabriel Pro Filtrado'], axis=1)

    if not df_combinado.empty:
        st.dataframe(
            df_combinado.style
            .set_table_styles([
                {'selector': 'th.col_heading.level0.col_heading_level0_0', 'props': [('background-color', '#1E90FF'), ('color', 'white')]},
                {'selector': 'th.col_heading.level1', 'props': [('font-size', STYLE_FONT_SIZE)]},
                {'selector': 'th.row_heading', 'props': [('background-color', "#333333"), ('color', 'white'), ('font-weight', 'bold'), ('font-size', STYLE_FONT_SIZE)]},
            ])
            .set_properties(**STYLE_TABLE_PROPS),
            use_container_width=True
        )
    else:
        st.info("Nenhum dado encontrado.")
    st.markdown("---")

# ITEM 2
def render_item_2_profissionais_categoria(df_original, todas_temporadas, segmentos_todos):
    st.subheader("2. Comparativo de Profissionais por Categoria (Gabriel Pro)")
    
    c1, c2 = st.columns(2)
    temp_sel = c1.selectbox("Selecione Temporada:", ['Todas'] + todas_temporadas, key='item2_t')
    seg_sel = c2.selectbox("Selecione Segmento:", ['Todos'] + segmentos_todos, key='item2_s')

    # Filtros locais
    df_base = df_original.copy()
    if temp_sel != 'Todas':
        df_base = df_base[df_base['Temporada_Exibicao'] == temp_sel]
    
    df_seg = df_base.copy()
    if seg_sel != 'Todos':
        df_seg = df_seg[df_seg['Segmento'] == seg_sel]

    # Cálculos
    df_gabriel_base = df_base.groupby(COLUNA_CHAVE_CONSOLIDADA)['Pontos'].sum().reset_index()
    df_gabriel_base.columns = [COLUNA_CHAVE_CONSOLIDADA, 'Pontuacao_Total']
    df_cat_gabriel = calcular_categorias(df_base, df_gabriel_base)

    df_segmento_base = df_seg.groupby(COLUNA_CHAVE_CONSOLIDADA)['Pontos'].sum().reset_index()
    df_segmento_base.columns = [COLUNA_CHAVE_CONSOLIDADA, 'Pontuacao_Total']
    df_cat_segmento = calcular_categorias(df_seg, df_segmento_base)

    # Contagens
    contagem_seg = get_contagem_categoria(df_cat_segmento.rename(columns={COLUNA_CHAVE_CONSOLIDADA: COLUNA_ESPECIFICADOR}), CATEGORIAS_NOMES)
    contagem_gab = get_contagem_categoria(df_cat_gabriel.rename(columns={COLUNA_CHAVE_CONSOLIDADA: COLUNA_ESPECIFICADOR}), CATEGORIAS_NOMES)

    # Montagem Tabela
    tabela = []
    for cat in CATEGORIAS_NOMES:
        qs, qg = contagem_seg[cat], contagem_gab[cat]
        part = qs / qg if qg > 0 else 0.0
        tabela.append({
            'Profissional Ativo': cat, 'Qtd Segmento': qs, 'Qtd Gabriel Pro': qg,
            'Participacao': part, 'Participacao Texto': f"{part:.1%}"
        })
    
    df_exibir = pd.DataFrame(tabela)
    # Linha Total
    row_tot = {
        'Profissional Ativo': 'Total',
        'Qtd Segmento': contagem_seg.get('Sem Categoria', 0) + df_exibir['Qtd Segmento'].sum(),
        'Qtd Gabriel Pro': contagem_gab.get('Sem Categoria', 0) + df_exibir['Qtd Gabriel Pro'].sum(),
        'Participacao': 0, 'Participacao Texto': ''
    }
    part_tot = row_tot['Qtd Segmento'] / row_tot['Qtd Gabriel Pro'] if row_tot['Qtd Gabriel Pro'] > 0 else 0.0
    row_tot['Participacao'] = part_tot
    row_tot['Participacao Texto'] = f"{part_tot:.1%}"
    
    df_exibir = pd.concat([df_exibir, pd.DataFrame([row_tot])], ignore_index=True)

    # Estilização
    def style_part(val):
        if val.name == df_exibir.index[-1]: return ['font-weight: bold;'] * len(val)
        return ['color: #d1d1d1; font-weight: bold'] * len(val)

    if not df_exibir.empty:
        st.dataframe(
            df_exibir[['Profissional Ativo', 'Qtd Segmento', 'Qtd Gabriel Pro', 'Participacao Texto']].style
            .applymap(style_nome_categoria, subset=['Profissional Ativo'])
            .apply(style_part, subset=['Participacao Texto'], axis=1)
            .format({col: '{:,.0f}' for col in ['Qtd Segmento', 'Qtd Gabriel Pro']})
            .set_properties(**{'font-weight': 'bold'}, subset=pd.IndexSlice[df_exibir['Profissional Ativo'] == 'Total', :])
            .set_properties(**STYLE_TABLE_PROPS),
            use_container_width=True
        )
    else:
        st.info("Nenhuma categoria encontrada.")
    st.markdown("---")

# ITEM 3
def render_item_3_evolucao_mensal(df_original, df_filtrado, sel_meses, sel_temporadas):
    st.subheader("3. Evolução da Pontuação por Mês e Temporada (Filtrado)")
    
    if not sel_meses or not sel_temporadas:
        st.info("Selecione Meses e Temporadas.")
        return

    df_pivot, cols_exibir = calcular_pivo_pontos(df_original, df_filtrado, sel_meses, sel_temporadas)
    
    if df_pivot.empty:
        st.info("Sem dados para exibir.")
        return

    temporadas_par = get_last_two_seasons(sel_temporadas)
    if temporadas_par:
        # Lógica de Evolução com Cores
        t_atual_tx = temporadas_par[2]
        col_evolucao = [c for c in cols_exibir if 'Evolução' in c][0]
        
        def style_evo(s):
            vals = df_pivot['Evolução Pontos Valor']
            styles = []
            for idx, v in vals.items():
                if idx == 'Total':
                    base = 'font-weight: bold; '
                    styles.append(base + ('color: #00FF00' if v > 0.0001 else 'color: #FF0000' if v < -0.0001 else 'color: #00009C'))
                else:
                    styles.append('color: #00FF00; font-weight: bold' if v > 0.0001 else 'color: #FF0000; font-weight: bold' if v < -0.0001 else 'color: #00009C; font-weight: bold')
            return styles

        cols_num = [c for c in cols_exibir if not c.startswith('Evolução')]
        st.dataframe(
            df_pivot[cols_exibir].style
            .format({c: formatar_milhar_br for c in cols_num})
            .apply(style_evo, subset=[col_evolucao], axis=0)
            .set_properties(**STYLE_TABLE_PROPS),
            use_container_width=True
        )
        df_pivot.drop(columns=['Evolução Pontos Valor'], inplace=True, errors='ignore')
    else:
        # Lógica Simples
        df_clean = df_pivot.reset_index()
        def style_tot(row):
            return ['font-weight: bold; background-color: #333333; color: white'] * len(row) if row['Mês'] == 'Total' else [''] * len(row)
        
        st.dataframe(
            df_clean[cols_exibir + ['Mês']].style
            .apply(style_tot, axis=1)
            .format({c: formatar_milhar_br for c in cols_exibir})
            .set_properties(**STYLE_TABLE_PROPS),
            use_container_width=True
        )
    st.markdown("---")

# ITEM 4
def render_item_4_pontuacao_total(df_filtrado, sel_temporadas):
    st.subheader("4. Pontuação Total por Temporada (Comparativo de Volume)")
    
    if not sel_temporadas:
        st.info("Selecione temporadas.")
        return

    df_pt = df_filtrado.groupby('Temporada_Exibicao')['Pontos'].sum().reset_index()
    df_pt.columns = ['Temporada', 'Pontuação Total']
    df_pt['Ordem'] = df_pt['Temporada'].apply(lambda x: int(x.split(' ')[1]) if ' ' in x else 0)
    df_pt.sort_values('Ordem', inplace=True)

    if df_pt.empty:
        st.info("Sem dados.")
    else:
        fig = px.bar(df_pt, x='Temporada', y='Pontuação Total', color='Temporada', text='Pontuação Total')
        fig.update_traces(texttemplate='%{text:,.0f}')
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("---")

# ITEM 5 (AJUSTADO: Adicionado Seletor de Temporada)
def render_item_5_distribuicao_total(df_total_periodo, todas_temporadas):
    st.subheader("5. Distribuição Total (Pontos e Pedidos no Período Selecionado)")
    
    col_met, col_temp = st.columns(2)
    metrica = col_met.selectbox('Métrica:', ('Pontos Totais', 'Pedidos Únicos'))
    temp_sel = col_temp.selectbox('Selecione a Temporada (Item 5):', ['Todas'] + todas_temporadas, key='item5_temp')
    
    # Filtra por Temporada se necessário
    df_uso = df_total_periodo.copy()
    if temp_sel != 'Todas':
        df_uso = df_uso[df_uso['Temporada_Exibicao'] == temp_sel]

    if metrica == 'Pontos Totais':
        df_m = df_uso.groupby('Segmento')['Pontos'].sum().reset_index()
        y_label = "Total de Pontos"
    else:
        df_m = df_uso.groupby('Segmento')[COLUNA_PEDIDO].nunique().reset_index()
        y_label = "Total de Pedidos"
    
    df_m.columns = ['Segmento', 'Metrica_Somada']
    if not df_m.empty:
        fig = px.bar(df_m, x='Segmento', y='Metrica_Somada', color='Segmento', text='Metrica_Somada', title=f'{metrica} por Segmento')
        fig.update_traces(texttemplate='%{text:,.0f}')
        fig.update_layout(yaxis_title=y_label)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados para esta seleção.")
    st.markdown("---")

# ITEM 6
def render_item_6_tendencia_mensal(df_filtrado, todas_temporadas, sel_temporadas, sel_meses):
    st.subheader("6. Tendência Mensal de Pontuação")
    t_sel = st.selectbox("Selecione Temporada para Análise:", ['Todas'] + todas_temporadas, key='item6_t')
    
    df_base = df_filtrado.copy()
    if t_sel != 'Todas':
        df_base = df_base[df_base['Temporada_Exibicao'] == t_sel]

    # 6. Gráfico Linha
    if 'Data da Venda' in df_base.columns and not df_base.empty:
        df_t = df_base.set_index('Data da Venda').resample('M')['Pontos'].sum().reset_index()
        fig = px.line(df_t, x='Data da Venda', y='Pontos', markers=True, title='Pontos por Mês')
        st.plotly_chart(fig, use_container_width=True)
    
    # 6A. Pedidos
    if not df_base.empty:
        df_ped = df_base.groupby('Mês_Exibicao')[COLUNA_PEDIDO].nunique().reset_index()
        df_ped.columns = ['Mês', 'Pedidos']
        df_ped['Mês_Ordem'] = df_ped['Mês'].map(MES_ORDEM_FISCAL)
        df_ped.sort_values('Mês_Ordem', inplace=True)
        fig_p = px.bar(df_ped, x='Mês', y='Pedidos', color='Mês', text='Pedidos', title='Pedidos Únicos por Mês')
        fig_p.update_traces(texttemplate='%{text:,.0f}')
        st.plotly_chart(fig_p, use_container_width=True)
    
    st.markdown("---")
    
    # 6B. Evolução Pedidos (Pivô)
    if sel_temporadas:
        st.subheader("6 B. Evolução de Pedidos Únicos (Detalhe)")
        df_piv, cols_tx = calcular_pivo_pedidos(df_filtrado, sel_temporadas)
        
        def style_tot_ped(row):
            return ['font-weight: bold;'] * len(row) if row.name == 'Total' else [''] * len(row)

        if not df_piv.empty:
            st.dataframe(
                df_piv.style
                .apply(style_tot_ped, axis=1)
                .format({c: formatar_milhar_br for c in cols_tx})
                .set_properties(**STYLE_TABLE_PROPS),
                use_container_width=True
            )
            
            # Detalhe Segmento
            meses_disp = [m for m in df_piv.index if m != 'Total']
            if meses_disp and cols_tx:
                c_m, c_t = st.columns(2)
                m_sel = c_m.selectbox("Mês Detalhe:", meses_disp)
                t_sel_d = c_t.selectbox("Temp Detalhe:", cols_tx, index=len(cols_tx)-1)
                
                t_full = f"Temporada {t_sel_d.replace('T', '')}"
                df_det = df_filtrado[(df_filtrado['Mês_Exibicao'] == m_sel) & (df_filtrado['Temporada_Exibicao'] == t_full)]
                
                df_seg_det = df_det.groupby('Segmento')[COLUNA_PEDIDO].nunique().reset_index()
                df_seg_det.columns = ['Segmento', 'Qtd']
                tot = df_seg_det['Qtd'].sum()
                df_seg_det['Part %'] = df_seg_det['Qtd'] / tot if tot > 0 else 0
                
                if not df_seg_det.empty:
                    fig_d = px.bar(df_seg_det, x='Segmento', y='Qtd', color='Segmento', text='Qtd')
                    fig_d.update_traces(texttemplate='%{text:,.0f}')
                    st.plotly_chart(fig_d, use_container_width=True)
                    st.dataframe(
                        df_seg_det.style.format({'Qtd': formatar_milhar_br, 'Part %': '{:.1%}'})
                        .set_properties(**STYLE_TABLE_PROPS),
                        use_container_width=True
                    )
                else:
                    st.info("Sem dados no detalhe.")
    st.markdown("---")

    # 6C. Evolução Pontuação Segmento (AJUSTADO: Mesmos Meses e Colunas T9 Esq / T10 Dir)
    temp_par = get_last_two_seasons(sel_temporadas)
    if temp_par:
        t_at_n, t_ant_n, t_at_tx, t_ant_tx = temp_par
        st.subheader(f"6 C. Evolução Pontuação Segmento ({t_at_tx} vs {t_ant_tx})")
        
        # 1. Filtro "Mesmos Meses"
        # Garante que usamos apenas os dados onde os meses existem na T_Atual
        df_base_mesmos_meses = filtrar_mesmos_meses(df_filtrado, t_at_n, t_ant_n)
        
        df_vs = df_base_mesmos_meses[df_base_mesmos_meses['Temporada_Exibicao'].isin([t_at_n, t_ant_n])].copy()
        
        df_piv_seg = df_vs.pivot_table(index='Segmento', columns='Temporada_Exibicao', values='Pontos', aggfunc='sum', fill_value=0).reset_index()
        
        # Define Colunas: Esquerda (Antiga) | Direita (Atual)
        c_at = f'Pontuação {t_at_tx}'   # T10
        c_ant = f'Pontuação {t_ant_tx}' # T9
        
        # Garante que as colunas existam (caso alguma temporada não tenha dados nos meses filtrados)
        if t_at_n not in df_piv_seg.columns: df_piv_seg[t_at_n] = 0
        if t_ant_n not in df_piv_seg.columns: df_piv_seg[t_ant_n] = 0

        # Renomeia
        df_piv_seg.rename(columns={t_at_n: c_at, t_ant_n: c_ant}, inplace=True)
        
        # Cálculo
        df_piv_seg['Evolução %'] = df_piv_seg.apply(lambda r: calcular_evolucao_pct(r[c_at], r[c_ant]), axis=1)
        tot_at = df_piv_seg[c_at].sum()
        df_piv_seg['Participação %'] = df_piv_seg[c_at] / tot_at if tot_at > 0 else 0
        
        # Linha Total
        tot_ant = df_piv_seg[c_ant].sum()
        row_t = {'Segmento': 'Total', c_at: tot_at, c_ant: tot_ant, 'Evolução %': calcular_evolucao_pct(tot_at, tot_ant), 'Participação %': 1.0}
        df_piv_seg = pd.concat([df_piv_seg, pd.DataFrame([row_t])], ignore_index=True)
        
        def style_evo_pct(v):
            if not isinstance(v, (int, float)): return ''
            return 'color: #00FF00; font-weight: bold' if v > 0.0001 else 'color: #FF0000; font-weight: bold' if v < -0.0001 else 'color: #00009C; font-weight: bold'
        
        # Ordem de Exibição: [Segmento, T9 (Ant), T10 (Atual), Evolução, Part]
        cols_final = ['Segmento', c_ant, c_at, 'Evolução %', 'Participação %']
        
        st.dataframe(
            df_piv_seg[cols_final].style
            .applymap(style_evo_pct, subset=['Evolução %'])
            .apply(lambda r: ['font-weight: bold;'] * len(r) if r.iloc[0] == 'Total' else [''] * len(r), axis=1)
            .format({c_at: formatar_milhar_br, c_ant: formatar_milhar_br, 'Evolução %': '{:.1%}', 'Participação %': '{:.1%}'})
            .set_properties(**STYLE_TABLE_PROPS),
            use_container_width=True
        )
        st.markdown(f"**Nota:** Comparação realizada considerando apenas os meses presentes na **{t_at_tx}**.")
    st.markdown("---")

# ITEM 7 (AJUSTADO: Mesmos Meses e Layouts)
def render_item_7_analise_lojas(df_filtrado, sel_temporadas, sel_meses):
    temp_par = get_last_two_seasons(sel_temporadas)
    if not temp_par:
        st.info("Selecione ao menos duas temporadas para Análise de Lojas.")
        return

    t_at_n, t_ant_n, t_at_tx, t_ant_tx = temp_par
    st.subheader(f"7. Análise Consolidada de Lojas ({t_at_tx} vs {t_ant_tx})")
    
    # 1. Filtro Mesmos Meses para a Análise
    df_base_analise = filtrar_mesmos_meses(df_filtrado, t_at_n, t_ant_n)
    
    lojas_ativas = sorted(df_base_analise['Loja'].unique())
    
    # Controle de Estado da Seleção
    curr = st.session_state.get('item7_lojas_select', [])
    if not curr: st.session_state['item7_lojas_select'] = lojas_ativas
    
    validas = [l for l in st.session_state['item7_lojas_select'] if l in lojas_ativas]
    if len(validas) < len(st.session_state['item7_lojas_select']):
        st.session_state['item7_lojas_select'] = validas
        
    sel_lojas_analise = st.multiselect("Lojas para Análise:", lojas_ativas, default=st.session_state['item7_lojas_select'], key='item7_lojas_select')
    
    if not sel_lojas_analise: sel_lojas_analise = []

    st.markdown(f"Base: {len(sel_lojas_analise)} Lojas (Filtrado pelos meses da {t_at_tx}).")
    
    # Passamos a base filtrada por "mesmos meses" para a função de cálculo
    df_evo, df_rank_q, df_rank_p, df_pyr = calcular_analise_lojas(df_base_analise, t_at_n, t_ant_n, sel_lojas_analise)

    # 7.1 Evolução (Colunas T9 Esq / T10 Dir)
    st.markdown("###### 7.1. Comparativo de Lojas por Evolução de Pontos")
    df_disp = df_evo.copy().rename(columns={t_ant_n: f'Pts {t_ant_tx}', t_at_n: f'Pts {t_at_tx}'})
    
    def style_evo_val(v):
        return 'color: #00FF00; font-weight: bold' if v > 0.0001 else 'color: #FF0000; font-weight: bold' if v < -0.0001 else 'color: #00009C; font-weight: bold'

    cols_order_71 = ['Loja', f'Pts {t_ant_tx}', f'Pts {t_at_tx}', 'Evolução %']

    st.dataframe(
        df_disp[cols_order_71].style
        .applymap(style_evo_val, subset=['Evolução %'])
        .format({f'Pts {t_ant_tx}': formatar_milhar_br, f'Pts {t_at_tx}': formatar_milhar_br, 'Evolução %': '{:.1%}'})
        .set_properties(**STYLE_TABLE_PROPS),
        use_container_width=True
    )

    # 7.2 Ranking Terços (Qtd) - TOTAL EMBAIXO
    st.markdown("###### 7.2. Ranking Terços (Qtd)")
    # Remove coluna auxiliar se existir e recalcula total
    df_rank_q_show = df_rank_q.copy()
    if 'Total de Lojas' in df_rank_q_show.columns: df_rank_q_show.drop(columns=['Total de Lojas'], inplace=True)
    
    # CORREÇÃO: Setar Terço como Index para o Total ficar alinhado corretamente
    if 'Terço' in df_rank_q_show.columns:
        df_rank_q_show.set_index('Terço', inplace=True)

    # Adiciona linha total (Soma)
    total_q = df_rank_q_show.sum(numeric_only=True)
    df_rank_q_show.loc['Total'] = total_q
    
    st.dataframe(
        df_rank_q_show.style
        .format(formatar_milhar_br)
        .apply(lambda r: ['font-weight: bold;'] * len(r) if r.name == 'Total' else [''] * len(r), axis=1)
        .set_properties(**STYLE_TABLE_PROPS),
        use_container_width=True
    )
    
    # 7.3 Ranking Terços (Pontos) - CORES + EVOLUÇÃO
    st.markdown("###### 7.3. Ranking Terços (Pontos)")
    df_rank_p_show = df_rank_p.copy()
    
    # CORREÇÃO CRÍTICA: Define 'Terço' como índice antes de calcular totais para evitar erro de colunas
    if 'Terço' in df_rank_p_show.columns:
        df_rank_p_show.set_index('Terço', inplace=True)

    # Recalcula Evolução % no DataFrame de exibição para garantir
    if t_at_n in df_rank_p_show.columns and t_ant_n in df_rank_p_show.columns:
        df_rank_p_show['Evolução %'] = df_rank_p_show.apply(lambda r: calcular_evolucao_pct(r[t_at_n], r[t_ant_n]), axis=1)
    
    # Renomeia colunas
    df_rank_p_show.rename(columns={t_ant_n: f'Pts {t_ant_tx}', t_at_n: f'Pts {t_at_tx}'}, inplace=True)
    
    # Total
    total_p = df_rank_p_show[[f'Pts {t_ant_tx}', f'Pts {t_at_tx}']].sum()
    evo_total = calcular_evolucao_pct(total_p[f'Pts {t_at_tx}'], total_p[f'Pts {t_ant_tx}'])
    
    # Agora a atribuição funciona pois df_rank_p_show tem apenas 3 colunas (Pts Ant, Pts Atual, Evolução)
    df_rank_p_show.loc['Total'] = [total_p[f'Pts {t_ant_tx}'], total_p[f'Pts {t_at_tx}'], evo_total]

    st.dataframe(
        df_rank_p_show.style
        .format({f'Pts {t_ant_tx}': formatar_milhar_br, f'Pts {t_at_tx}': formatar_milhar_br, 'Evolução %': '{:.1%}'})
        .applymap(style_evo_val, subset=['Evolução %'])
        .apply(lambda r: ['font-weight: bold;'] * len(r) if r.name == 'Total' else [''] * len(r), axis=1)
        .set_properties(**STYLE_TABLE_PROPS), 
        use_container_width=True
    )
    
    # 7.4 Pirâmide
    st.markdown("###### 7.4. Pirâmide Evolução")
    st.dataframe(df_pyr.style.format({'Contagem': formatar_milhar_br}).set_properties(**STYLE_TABLE_PROPS), use_container_width=True)
    st.markdown("---")

# ITEM 8 (AJUSTADO: Layout Vertical e Cálculo T9 via Módulo)
def render_item_8_desempenho_profissional(df_dados_original, df_filtrado, todas_temporadas, sel_temporadas, sel_lojas, sel_segmentos, sel_meses):
    st.subheader("8. Desempenho por Profissional e Categoria")
    
    t_sel = st.selectbox("Temporada Análise:", ['Todas'] + todas_temporadas, key='item8_t')
    
    # Calcula desempenho da T_Atual
    df_des = calcular_desempenho_consolidado(df_filtrado, t_sel)
    
    if df_des.empty:
        st.info("Sem dados.")
        return

    t_atual_num = df_des['Temporada_Atual_Num'].iloc[0]
    t_ant_num = int(t_atual_num) - 1 if int(t_atual_num) > 0 else 0
    t_ant_nome = f"Temporada {t_ant_num}"
    
    # --- RESUMO CATEGORIAS ---
    df_res = df_des.groupby('Categoria').agg(Contagem=(COLUNA_CHAVE_CONSOLIDADA, 'size'), Pontos=('Pontuacao_Total', 'sum')).reset_index()
    
    # Força a Ordem: Diamante, Esmeralda, Ruby, Topázio, Pro, Total
    row_total = pd.DataFrame([{
        'Categoria': 'Total', 
        'Contagem': df_res['Contagem'].sum(), 
        'Pontos': df_res['Pontos'].sum()
    }])
    df_res = pd.concat([df_res, row_total], ignore_index=True)

    # --- CÁLCULO EVOLUÇÃO COM GET_PONTUACAO_TEMPORADA_ANTERIOR ---
    # Identifica meses presentes na T_Atual para passar como filtro
    if t_sel != 'Todas':
        meses_t_atual = df_dados_original[df_dados_original['Temporada_Exibicao'] == t_sel]['Mês_Exibicao'].unique()
    else:
        meses_t_atual = df_dados_original['Mês_Exibicao'].unique()
    
    evo_list = []
    txt_list = []
    
    for idx, row in df_res.iterrows():
        cat_nome = row['Categoria']
        pts_atual = row['Pontos']
        
        # Define a categoria para filtro (se for 'Total', passa None para pegar tudo)
        cat_filtro = cat_nome if cat_nome != 'Total' else None
        
        # Chama a função do módulo que calcula corretamente classificando a T-1 baseada nos filtros
        pts_ant = get_pontuacao_temporada_anterior(
            df_dados_original, 
            t_atual_num, # A função espera T_Atual e calcula T-1 internamente
            sel_lojas, 
            sel_segmentos, 
            list(meses_t_atual), # Passa lista de meses para garantir "Mesmos Meses"
            categoria=cat_filtro
        )
            
        cres = calcular_evolucao_pct(pts_atual, pts_ant)
        evo_list.append(cres)
        txt = f"{cres:.1%} {'↑' if cres > 0.0001 else '↓' if cres < -0.0001 else '≈'}"
        txt_list.append(txt)
    
    df_res['Evo'] = evo_list
    df_res['Txt'] = txt_list
    
    # Reordena para Exibição
    ordem_cats = ['Diamante', 'Esmeralda', 'Ruby', 'Topázio', 'Pro', 'Total']
    df_res = df_res.set_index('Categoria').reindex(ordem_cats).reset_index()
    
    # Display KPIs (Layout Vertical Exato)
    cores_cat = {
        'Diamante': '#b3e6ff', 'Esmeralda': '#a3ffb1', 'Ruby': "#fa7f7f", 
        'Topázio': '#ffe08a', 'Pro': "#b4adad", 'Total': "#D3D3D3"
    }

    cols = st.columns(len(df_res))
    for i, (idx, row) in enumerate(df_res.iterrows()):
        cat_nome = row['Categoria']
        if pd.isna(row['Contagem']): # Categoria vazia
             with cols[i]: st.write("")
             continue

        cor_txt = '#00FF00' if row['Evo'] > 0 else '#FF0000' if row['Evo'] < 0 else '#00009C'
        cor_titulo = cores_cat.get(cat_nome, '#ffffff')
        display_name = 'Rubi' if cat_nome == 'Ruby' else cat_nome
        
        with cols[i]:
            # 1. Nome da Categoria
            st.markdown(f"<div style=><span style='color: {cor_titulo}; font-weight: bold; font-size: 28px;'>{display_name}</span></div>", unsafe_allow_html=True)
            # 2. Quantidade
            st.markdown(f"<div style=><span style='font-size: 28px; font-weight: bold;'>{int(row['Contagem'])}</span></div>", unsafe_allow_html=True)
            # 3. Label Pontos
            st.markdown(f"<div style=><span style='font-size: 22px; color: #888;'>Pontos {display_name}</span></div>", unsafe_allow_html=True)
            # 4. Pontuação
            st.markdown(f"<div style=><span style='font-size: 28px; font-weight: bold;'>{formatar_milhar_br(row['Pontos'])}</span></div>", unsafe_allow_html=True)
            # 5. Evolução
            st.markdown(f"<div style=><span style='color: {cor_txt}; font-weight: bold; font-size: 22px;'>{row['Txt']}</span></div>", unsafe_allow_html=True)
            
    # --- TABELA DETALHADA ---
    st.markdown("<br>", unsafe_allow_html=True)
    term = st.text_input("Pesquisar Profissional:", key='search_prof')
    
    df_exib = df_des.copy()
    if term:
        t_low = term.lower()
        df_exib = df_exib[
            df_exib[COLUNA_CHAVE_CONSOLIDADA].astype(str).str.lower().str.contains(t_low) | 
            df_exib['Categoria'].str.lower().str.contains(t_low) |
            df_exib['CNPJs Vinculados'].astype(str).str.lower().str.contains(t_low) |
            df_exib['CPFs Vinculados'].astype(str).str.lower().str.contains(t_low) |
            df_exib['Especificadores_Vinculados'].astype(str).str.lower().str.contains(t_low)
        ]

    # Merge Pontuação T-1 (Mesmos Meses)
    df_ant = df_dados_original[
        (df_dados_original['Temporada_Exibicao'] == t_ant_nome) & 
        (df_dados_original['Loja'].isin(sel_lojas)) &
        (df_dados_original['Mês_Exibicao'].isin(meses_t_atual))
    ].copy()
    
    df_pts_ant = df_ant.groupby(COLUNA_CHAVE_CONSOLIDADA)['Pontos'].sum().reset_index().rename(columns={'Pontos': 'Pts T-1'})
    
    df_exib = pd.merge(df_exib, df_pts_ant, on=COLUNA_CHAVE_CONSOLIDADA, how='left').fillna(0)
    df_exib['Evo %'] = df_exib.apply(lambda r: calcular_evolucao_pct(r['Pontuacao_Total'], r['Pts T-1']), axis=1)
    
    def style_evo_ind(v):
        return 'color: #00FF00; font-weight: bold' if v > 0.0001 else 'color: #FF0000; font-weight: bold' if v < -0.0001 else 'color: #00009C; font-weight: bold'

    cols_table = [
        COLUNA_CHAVE_CONSOLIDADA, 'CNPJs Vinculados', 'CPFs Vinculados', 'Especificadores_Vinculados',
        'Pontuacao_Total', 'Pts T-1', 'Evo %', 'Qtd_Pedidos', 'Categoria'
    ]
    
    rename_map = {
        COLUNA_CHAVE_CONSOLIDADA: 'Empresa',
        'Especificadores_Vinculados': 'Nomes Vinculados',
        'Pontuacao_Total': 'Pontuação',
        'Qtd_Pedidos': 'Qtd Pedidos'
    }

    st.dataframe(
        df_exib[cols_table].rename(columns=rename_map).style
        .applymap(style_evo_ind, subset=['Evo %'])
        .applymap(style_nome_categoria, subset=['Categoria'])
        .format({'Pontuação': formatar_milhar_br, 'Pts T-1': formatar_milhar_br, 'Evo %': '{:.1%}'})
        .set_properties(**STYLE_TABLE_PROPS),
        use_container_width=True
    )
    st.markdown("---")

# ITEM 9 (AJUSTADO: Cores Evolução e Separação 9B/9C)
def render_item_9_novos_cadastrados(df_dados_original, df_filtrado, df_novos_cadastrados_original, sel_meses, sel_temporadas):
    st.subheader("9. Novos Cadastrados (Comprando e Cadastrados por Temporada)")
    
    # --- 9A. Contagem Novos Cadastrados Pontuados ---
    st.markdown("##### 9 A. Contagem de Novos Cadastrados Pontuados por Mês e Temporada (Comprando)")
    
    df_piv, cols_disp, col_evo = calcular_pivo_novos_clientes(df_dados_original, df_filtrado, sel_meses, sel_temporadas)
    
    def style_evo_qualitativa(s):
        # Proteção: Verifica se a coluna de valores existe antes de acessar
        if 'Evolução Qualitativa Valor' not in df_piv.columns:
            return [''] * len(s)
            
        vals = df_piv['Evolução Qualitativa Valor']
        styles = []
        for v in vals:
            if v == 1: styles.append('color: #00FF00; font-weight: bold') # Verde
            elif v == -1: styles.append('color: #FF0000; font-weight: bold') # Vermelho
            else: styles.append('color: #00009C; font-weight: bold') # Azul
        return styles

    if not df_piv.empty:
        # Prepara o Styler
        styler = df_piv[cols_disp].style.format({c: formatar_milhar_br for c in cols_disp if c != col_evo})
        
        # CORREÇÃO CRÍTICA: Só aplica o estilo se a coluna de evolução realmente existir no DataFrame
        if col_evo in df_piv.columns and col_evo in cols_disp:
            styler = styler.apply(style_evo_qualitativa, subset=[col_evo], axis=0)
            
        st.dataframe(
            styler.set_properties(**STYLE_TABLE_PROPS), 
            use_container_width=True
        )
    else:
        st.info("Sem dados para exibir no pivô de novos cadastrados.")
    
    st.markdown("---")
    
    # --- 9B. Lista Detalhada Novos (Quem já comprou) ---
    st.markdown("##### 9 B. Lista Detalhada Novos (Quem já comprou)")
    term_9b = st.text_input("Pesquisar Novo Comprador:", key='search_9b')
    
    df_atv = df_filtrado[df_filtrado['Novo_Cadastrado'] == True].copy()
    if term_9b:
        t_low = term_9b.lower()
        df_atv = df_atv[df_atv['CNPJ_CPF_LIMPO'].astype(str).str.contains(t_low) | df_atv[COLUNA_ESPECIFICADOR].str.lower().str.contains(t_low)]
    
    if not df_atv.empty:
        # Agrupa para pegar a primeira compra no período
        df_show_b = df_atv.groupby([COLUNA_ESPECIFICADOR, 'CNPJ_CPF_LIMPO', 'Temporada_Exibicao']).agg(
            Primeira_Compra=('Data da Venda', 'min')
        ).reset_index()
        
        # Recupera CPF Original para mascarar
        df_cpfs = df_dados_original[['CNPJ_CPF_LIMPO', COLUNA_CNPJ_CPF]].drop_duplicates('CNPJ_CPF_LIMPO')
        df_show_b = pd.merge(df_show_b, df_cpfs, on='CNPJ_CPF_LIMPO', how='left')
        
        # Formatação
        df_show_b['Primeira Compra (Período)'] = df_show_b['Primeira_Compra'].dt.strftime('%d/%m/%Y')
        df_show_b['CPF/CNPJ'] = df_show_b[COLUNA_CNPJ_CPF].apply(formatar_documento)
        df_show_b['Já Comprou'] = 'Sim'
        
        # Renomeia para exibição
        df_show_b.rename(columns={
            COLUNA_ESPECIFICADOR: 'Nome',
            'Temporada_Exibicao': 'Temporada'
        }, inplace=True)
        
        # Seleciona colunas finais na ordem solicitada
        cols_final_9b = ['Nome', 'CPF/CNPJ', 'Primeira Compra (Período)', 'Temporada', 'Já Comprou']
        
        def style_sim(v): return 'color: #00FF00; font-weight: bold' if v == 'Sim' else ''
        
        st.dataframe(
            df_show_b[cols_final_9b].style
                .applymap(style_sim, subset=['Já Comprou'])
                .set_properties(**STYLE_TABLE_PROPS),
            use_container_width=True
        )
    else:
        st.info("Nenhum novo comprador encontrado.")

    st.markdown("---")

    # --- 9C. Status Profissionais Cadastrados (Base Original) ---
    st.markdown("##### 9 C. Status de Profissionais Cadastrados (Base Total)")
    term_9c = st.text_input("Pesquisar Cadastro:", key='search_9c')
    
    if not df_novos_cadastrados_original.empty:
        df_cad = df_novos_cadastrados_original.copy()
        
        compradores_limpos = set(df_dados_original['CNPJ_CPF_LIMPO'].unique())
        df_cad['CPF_LIMPO'] = df_cad[COLUNA_CPF_NOVO_CADASTRO].astype(str).str.replace(r'[^0-9]', '', regex=True)
        df_cad['Já Comprou'] = np.where(df_cad['CPF_LIMPO'].isin(compradores_limpos), 'Sim', 'Não')
        
        # Formata CPF Original
        df_cad['CPF/CNPJ'] = df_cad[COLUNA_CPF_NOVO_CADASTRO].apply(formatar_documento)
        
        if term_9c:
            t_low = term_9c.lower()
            df_cad = df_cad[df_cad['Nome'].str.lower().str.contains(t_low) | df_cad[COLUNA_CPF_NOVO_CADASTRO].str.contains(t_low)]
        
        def style_compra(v): 
            return 'color: #00FF00; font-weight: bold' if v == 'Sim' else 'color: #FF0000; font-weight: bold'

        cols_c = ['Nome', 'CPF/CNPJ', 'E-mail', 'Telefone', 'Temporada', 'Já Comprou']
        cols_exist = [c for c in cols_c if c in df_cad.columns]
        
        st.dataframe(
            df_cad[cols_exist].style.applymap(style_compra, subset=['Já Comprou']).set_properties(**STYLE_TABLE_PROPS),
            use_container_width=True
        )
    else:
        st.info("Base de cadastros vazia.")
    st.markdown("---")

# ITEM 10 (AJUSTADO: Colunas Detalhadas e Cores Status nas Linhas)
def render_item_10_retencao(df_dados_original, df_filtrado, sel_lojas, sel_segmentos):
    st.subheader("10. Clientes Ativos vs Inativos")
    
    # 10A. Resumo
    df_anual, clientes_hist = calcular_clientes_ativos_inativos(df_dados_original, sel_lojas, sel_segmentos)
    
    st.markdown("##### 10 A. Resumo por Temporada")
    
    def style_perc(v):
        if v >= 0.5: return 'color: #00FF00; font-weight: bold'
        return 'color: #FF0000; font-weight: bold'

    st.dataframe(
        df_anual.style
        .format({'% Ativo': '{:.1%}', 'Contagem de Clientes Pontuando (Ativos)': formatar_milhar_br, 'Contagem de Clientes Não Pontuando (Inativos)': formatar_milhar_br, 'Total de Clientes': formatar_milhar_br})
        .applymap(style_perc, subset=['% Ativo'])
        .set_properties(**STYLE_TABLE_PROPS),
        use_container_width=True
    )
    
    # 10B. Detalhe Clientes (Com Colunas Extras e Cores Linha)
    st.markdown("##### 10 B. Detalhe Clientes (Ativos e Inativos no Filtro)")
    term_10 = st.text_input("Pesquisar Cliente (Nome/Status/CPF):", key='search_10')
    
    # 1. Dados dos ATIVOS (vêm do df_filtrado)
    df_ativos_det = df_filtrado.groupby(['CNPJ_CPF_LIMPO', COLUNA_ESPECIFICADOR]).agg(
        Qtd_Pedidos=(COLUNA_PEDIDO, 'nunique'),
        Ultima_Data=('Data da Venda', 'max')
    ).reset_index()
    df_ativos_det['Status'] = 'ATIVO'
    
    # 2. Dados dos INATIVOS
    # Quem está no histórico (clientes_hist) mas não em df_ativos_det
    ativos_set = set(df_ativos_det['CNPJ_CPF_LIMPO'].unique())
    inativos_set = clientes_hist.difference(ativos_set)
    
    # Busca dados históricos para os Inativos (Última data de compra ever no filtro de loja/seg)
    df_hist_loja = df_dados_original[
        (df_dados_original['Loja'].isin(sel_lojas)) & 
        (df_dados_original['Segmento'].isin(sel_segmentos))
    ]
    
    df_inativos_det = df_hist_loja[df_hist_loja['CNPJ_CPF_LIMPO'].isin(inativos_set)].groupby(['CNPJ_CPF_LIMPO', COLUNA_ESPECIFICADOR]).agg(
        Ultima_Data=('Data da Venda', 'max')
    ).reset_index()
    
    df_inativos_det['Qtd_Pedidos'] = 0 # Inativo no período não tem pedido no período
    df_inativos_det['Status'] = 'INATIVO'
    
    # 3. Consolidação
    df_detalhe = pd.concat([df_ativos_det, df_inativos_det], ignore_index=True)
    
    # Busca CPF Original para máscara
    df_cpf_map = df_dados_original[['CNPJ_CPF_LIMPO', COLUNA_CNPJ_CPF]].drop_duplicates('CNPJ_CPF_LIMPO')
    df_detalhe = pd.merge(df_detalhe, df_cpf_map, on='CNPJ_CPF_LIMPO', how='left')
    
    # Formatação
    df_detalhe['CPF/CNPJ'] = df_detalhe[COLUNA_CNPJ_CPF].apply(formatar_documento)
    df_detalhe['Última Data da Compra'] = df_detalhe['Ultima_Data'].dt.strftime('%d/%m/%Y')
    df_detalhe['Qtd de Pedidos no Período'] = df_detalhe['Qtd_Pedidos'].apply(lambda x: formatar_milhar_br(x) if x > 0 else "-")
    
    # Filtragem Pesquisa
    if term_10:
        t_low = term_10.lower()
        df_detalhe = df_detalhe[
            df_detalhe[COLUNA_ESPECIFICADOR].astype(str).str.lower().str.contains(t_low) | 
            df_detalhe['Status'].str.lower().str.contains(t_low) |
            df_detalhe['CPF/CNPJ'].str.contains(t_low)
        ]
        
    # Ordenação
    df_detalhe.sort_values(by=['Status', 'Ultima_Data'], ascending=[True, False], inplace=True) # Ativo (A) antes de Inativo (I)

    # Renomear
    df_detalhe.rename(columns={COLUNA_ESPECIFICADOR: 'Nome do Profissional'}, inplace=True)
    
    cols_final_10b = ['Nome do Profissional', 'CPF/CNPJ', 'Status', 'Qtd de Pedidos no Período', 'Última Data da Compra']
    
    # Função para aplicar estilo na linha inteira baseado no Status
    def style_row_status(row):
        color = ''
        weight = 'bold'
        if row['Status'] == 'ATIVO':
            color = "#116911" # Verde
        elif row['Status'] == 'INATIVO':
            color = '#FF0000' # Vermelho
        
        return [f'color: {color}; font-weight: {weight}' for _ in row]

    if not df_detalhe.empty:
        st.dataframe(
            df_detalhe[cols_final_10b].style
            .apply(style_row_status, axis=1) # Aplica a cor em toda a linha
            .set_properties(**STYLE_TABLE_PROPS),
            use_container_width=True
        )
    else:
        st.info("Nenhum cliente encontrado.")

    st.markdown("---")

# ITEM 11 (AJUSTADO: Texto Explicativo)
def render_item_11_ranking(df_dados_original, sel_lojas, sel_segmentos):
    # Identifica T Atual/Anterior global
    nums = sorted(df_dados_original[COLUNA_NUMERO_TEMPORADA].unique())
    nums = [n for n in nums if n > 0]
    
    if len(nums) < 2:
        st.info("Sem dados suficientes para ranking.")
        return

    t_at, t_ant = nums[-1], nums[-2]
    df_rank, nome_at, nome_ant, max_rank_at, max_rank_ant = calcular_ranking_ajustado(df_dados_original, sel_lojas, sel_segmentos, t_at, t_ant)
    
    st.subheader(f"11. Variação Ranking ({nome_at} vs {nome_ant})")
    
    def style_var(v):
        return 'color: #00FF00; font-weight: bold' if v > 0 else 'color: #FF0000; font-weight: bold' if v < 0 else 'color: #00009C; font-weight: bold'

    if not df_rank.empty:
        st.dataframe(
            df_rank.style
            .applymap(style_var, subset=['Variação Rank'])
            .set_properties(**STYLE_TABLE_PROPS),
            use_container_width=True
        )
        
        # Texto Explicativo Solicitado
        st.markdown(f"""
        **Lógica da Variação Rank:** `{nome_ant} Rank Ajustado - {nome_at} Rank Ajustado`.
        * **Valor Negativo (Vermelho):** O profissional **Piorou** seu ranking (ex: de 1 para 5).
        * **Valor Positivo (Verde):** O profissional **Melhorou** seu ranking (ex: de 5 para 1).
        * **Valor Estável (Azul):** O profissional **Manteve** seu ranking (ex: de 1 para 1).
        * **Rank Ajustado (Gap Filling):** Posições **{max_rank_ant + 1}** (para {nome_ant}) ou **{max_rank_at + 1}** (para {nome_at}) são atribuídas a profissionais que pontuaram em uma temporada, mas não na outra, dentro dos filtros de Segmento/Loja.
        """)
    else:
        st.info("Sem dados ranking.")

# ==============================================================================
# 6. FUNÇÃO PRINCIPAL
# ==============================================================================
def show_dashboard():
    st.title("📊 Dashboard de Análise Associação Casa Avant")
    
    # Inicializa estado
    if 'filtro_status_ano' not in st.session_state:
        st.session_state['filtro_status_ano'] = {'ano': None, 'status': None, 'termo_pesquisa': ''}
    if 'search_item_9' not in st.session_state:
        st.session_state['search_item_9'] = ''

    # Aplica CSS
    aplicar_css_global()

    # Carrega Dados
    df_dados_original, df_novos_cadastrados = carregar_e_tratar_dados(Relatorio)

    if df_dados_original.empty:
        st.warning("Base de dados vazia.")
        return

    # Tratamento inicial crítico
    df_dados_original['Data da Venda'] = pd.to_datetime(df_dados_original['Data da Venda'], errors='coerce')
    df_dados_original.dropna(subset=['Data da Venda'], inplace=True)

    # Renderiza Sidebar e Obtém Filtros
    filtros = render_sidebar(df_dados_original)
    
    df_filtrado = filtros['df_filtrado']
    
    # REMOVIDO KPI TOPO (Conforme Pedido Foto 1)
    # render_kpis_topo(...) 
    
    render_item_1_comparativo_temporada(
        df_filtrado, 
        df_novos_cadastrados, 
        filtros['todas_temporadas']
    )
    
    segmentos_unicos = sorted(filtros['df_total_periodo']['Segmento'].unique())
    render_item_2_profissionais_categoria(df_dados_original, filtros['todas_temporadas'], segmentos_unicos)
    
    render_item_3_evolucao_mensal(
        df_dados_original, 
        df_filtrado, 
        filtros['sel_meses'], 
        filtros['sel_temporadas']
    )

    render_item_4_pontuacao_total(df_filtrado, filtros['sel_temporadas'])
    
    # Item 5 Ajustado
    render_item_5_distribuicao_total(filtros['df_total_periodo'], filtros['todas_temporadas'])
    
    render_item_6_tendencia_mensal(df_filtrado, filtros['todas_temporadas'], filtros['sel_temporadas'], filtros['sel_meses'])

    render_item_7_analise_lojas(df_filtrado, filtros['sel_temporadas'], filtros['sel_meses'])

    render_item_8_desempenho_profissional(df_dados_original, df_filtrado, filtros['todas_temporadas'], filtros['sel_temporadas'], filtros['sel_lojas'], filtros['sel_segmentos'], filtros['sel_meses'])
    
    render_item_9_novos_cadastrados(df_dados_original, df_filtrado, df_novos_cadastrados, filtros['sel_meses'], filtros['sel_temporadas'])

    render_item_10_retencao(df_dados_original, df_filtrado, filtros['sel_lojas'], filtros['sel_segmentos'])
    
    render_item_11_ranking(df_dados_original, filtros['sel_lojas'], filtros['sel_segmentos'])