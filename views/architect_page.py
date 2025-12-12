import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# --- 1. IMPORTAÇÕES E CONFIGURAÇÕES ---
# Ajuste conforme seus módulos reais
from modulos.config import COLUNA_ESPECIFICADOR, COLUNA_CHAVE_CONSOLIDADA, COLUNA_NUMERO_TEMPORADA, COLUNA_PEDIDO

try:
    from modulos.config import CATEGORIAS_NOMES
except ImportError:
    CATEGORIAS_NOMES = ['Diamante', 'Esmeralda', 'Ruby', 'Topázio', 'Pro']

from modulos.tratamento import formatar_milhar_br, calcular_evolucao_pct

CATEGORIES_STYLE = {
    "Pro": {"color": "#94a3b8", "css": "badge-pro", "min": 0},
    "Topázio": {"color": "#38bdf8", "css": "badge-topazio", "min": 150000},
    "Ruby": {"color": "#ef4444", "css": "badge-rubi", "min": 500000},
    "Esmeralda": {"color": "#10b981", "css": "badge-esmeralda", "min": 2000000},
    "Diamante": {"color": "#7c3aed", "css": "badge-diamante", "min": 5000000}
}

ARQUIVO_ACOES = "campanhas_ativas.csv"
ARQUIVO_ATIVACOES = "ativacoes.csv"
ARQUIVO_PREMIOS = "premios_temporada.csv"

# --- 2. FUNÇÕES DE CARREGAMENTO ---
def carregar_dados_extras():
    dfs = {}
    for arq, key in [(ARQUIVO_ACOES, 'acoes'), (ARQUIVO_ATIVACOES, 'ativacoes'), (ARQUIVO_PREMIOS, 'premios')]:
        if os.path.exists(arq):
            dfs[key] = pd.read_csv(arq)
            if 'Data_Inicio' in dfs[key].columns:
                dfs[key]['Data_Inicio'] = pd.to_datetime(dfs[key]['Data_Inicio'], errors='coerce').dt.date
                dfs[key]['Data_Fim'] = pd.to_datetime(dfs[key]['Data_Fim'], errors='coerce').dt.date
        else:
            dfs[key] = pd.DataFrame()
    return dfs

# --- 3. FUNÇÕES DE CÁLCULO GERAIS ---
def get_category_details(points):
    sorted_cats = sorted(CATEGORIES_STYLE.items(), key=lambda x: x[1]['min'])
    current_cat_data = CATEGORIES_STYLE["Pro"]
    current_cat_data['name'] = "Pro"
    next_cat_data = None
    for i, (name, data) in enumerate(sorted_cats):
        if points >= data['min']:
            current_cat_data = data
            current_cat_data['name'] = name
            if i + 1 < len(sorted_cats): 
                next_cat_data = sorted_cats[i+1][1]
                next_cat_data['name'] = sorted_cats[i+1][0]
            else: 
                next_cat_data = None
    return current_cat_data, next_cat_data

def calcular_evolucao_ajustada(df_consolidado, temporada_atual_nome):
    try:
        num_atual = int(temporada_atual_nome.split(' ')[1])
        num_anterior = num_atual - 1
        temporada_anterior_nome = f"Temporada {num_anterior}"
        
        df_atual = df_consolidado[df_consolidado['Temporada_Exibicao'] == temporada_atual_nome]
        if df_atual.empty: return 0, "N/A", ""
        
        pontos_atual = df_atual['Pontos'].sum()
        meses_presentes = df_atual['Mês_Exibicao'].unique()
        
        df_anterior = df_consolidado[
            (df_consolidado['Temporada_Exibicao'] == temporada_anterior_nome) &
            (df_consolidado['Mês_Exibicao'].isin(meses_presentes))
        ]
        
        pontos_anterior_ajustado = df_anterior['Pontos'].sum()
        evolucao = calcular_evolucao_pct(pontos_atual, pontos_anterior_ajustado)
        
        if pontos_anterior_ajustado == 0:
            txt_evolucao = "Novo" if pontos_atual > 0 else "-"
        else:
            txt_evolucao = f"{evolucao:+.1%}"
            
        return evolucao, txt_evolucao, temporada_anterior_nome
    except: return 0, "Erro", ""

# --- 4. CÁLCULO DE RANKING ---
def calcular_progresso_ranking(df_global, campanha, user_key):
    try:
        dt_ini = campanha['Data_Inicio']
        dt_fim = campanha['Data_Fim']
        acelerador = float(campanha.get('Acelerador_Pct', 0))
        limite_ganhadores = int(campanha.get('Limite_Ganhadores', 0))
        meta_minima = float(campanha['Meta'])
    except: 
        return 0, 0, 0, 0, 0

    df_global['Data_Temp'] = pd.to_datetime(df_global['Data da Venda'], errors='coerce')
    mask = (df_global['Data_Temp'].dt.date >= dt_ini) & \
           (df_global['Data_Temp'].dt.date <= dt_fim)
    df_periodo = df_global.loc[mask].copy()
    
    if df_periodo.empty: 
        return 0, 0, 0, meta_minima, limite_ganhadores

    ranking = df_periodo.groupby(COLUNA_CHAVE_CONSOLIDADA)['Pontos'].sum().reset_index()
    ranking['Pontos_Bonus'] = ranking['Pontos'] * (1 + acelerador/100)
    ranking = ranking.sort_values('Pontos_Bonus', ascending=False).reset_index(drop=True)
    ranking.index += 1 

    if user_key in ranking[COLUNA_CHAVE_CONSOLIDADA].values:
        meus_dados = ranking[ranking[COLUNA_CHAVE_CONSOLIDADA] == user_key]
        meus_pontos = meus_dados['Pontos_Bonus'].values[0]
        minha_posicao = meus_dados.index[0]
    else:
        meus_pontos = 0
        minha_posicao = len(ranking) + 1

    pontos_corte = 0
    if limite_ganhadores > 0:
        if len(ranking) >= limite_ganhadores:
            pontos_corte = ranking.iloc[limite_ganhadores-1]['Pontos_Bonus']
        else:
            pontos_corte = meta_minima
            
    return meus_pontos, minha_posicao, pontos_corte, meta_minima, limite_ganhadores

# --- 5. RENDERIZAÇÃO DO CARD (CORRIGIDA - SEM INDENTAÇÃO) ---
def render_card_campanha(row, df_global, user_key, tipo_card="Campanha"):
    meus_pts, posicao, pts_corte, meta, limite = calcular_progresso_ranking(df_global, row, user_key)
    
    hoje = date.today()
    try:
        dias_restantes = (row['Data_Fim'] - hoje).days
        txt_prazo = f"Acaba em {dias_restantes} dias" if dias_restantes >= 0 else "Finalizada"
    except: txt_prazo = ""
    
    # Cores
    cor_borda_lateral = "#3b82f6"
    if meus_pts >= meta:
        cor_borda_lateral = "#10b981"
        
    bg_card = "#f8f9fa"
    border_card = "#e2e8f0"
    text_primary = "#1e293b"
    text_secondary = "#64748b"
    
    pct_meta = min(meus_pts / meta, 1.0) if meta > 0 else 0
    width_pct = pct_meta * 100
    color_bar = "#3b82f6"
    
    html_ranking = ""
    if limite > 0:
        esta_no_ranking = posicao <= limite
        if esta_no_ranking:
            msg_rank = f"🏆 <b>Parabéns!</b> Você é o <b>{posicao}º</b> colocado (Top {limite})."
            cor_msg = "#065f46"
            bg_msg = "#d1fae5"
        else:
            falta_top = pts_corte - meus_pts + 1
            if falta_top < 0: falta_top = 0
            msg_rank = f"⚠️ Você é o <b>{posicao}º</b>. Faltam <b>{formatar_milhar_br(falta_top)} pts</b> para o Top {limite}."
            cor_msg = "#92400e"
            bg_msg = "#fef3c7"
            
        html_ranking = f"""
<div style="margin-top: 15px; background-color: {bg_msg}; color: {cor_msg}; padding: 10px 15px; border-radius: 8px; font-size: 1.4rem; border: 1px solid rgba(0,0,0,0.05);">
{msg_rank}
</div>"""

    # AQUI ESTAVA O ERRO: Removi os espaços do início da string HTML para não virar código E aqui é o que representa o Ativação e Acelerador
    html_completo = f"""<div style="background-color: {bg_card}; border: 1px solid {border_card}; border-left: 5px solid {cor_borda_lateral}; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); color: {text_primary}; font-family: sans-serif;">
<div style="display:flex; justify-content:space-between; align-items: flex-start;">
<div>
<strong style="font-size: 1.3rem; color: {text_primary};">{row['Titulo']}</strong>
<div style="font-size:1.3rem; margin-top:2px; color: {text_secondary};">{tipo_card} • <b>{txt_prazo}</b></div>
</div>
<div style="text-align:right;">
<span style="font-size:1.7rem; font-weight:800; color: {text_primary};">{formatar_milhar_br(meus_pts)}</span>
<span style="font-size:1.8rem; color: {text_secondary};">pts</span>
</div>
</div>
<div style="font-size:1.3rem; margin: 12px 0; line-height: 1.5; color: {text_secondary};">
{row['Descricao']}
</div>
<div style="margin-top: 20px;">
<div style="display:flex; justify-content: space-between; font-size: 1.3rem; color: {text_secondary}; margin-bottom: 5px;">
<span>Progresso Meta Mínima</span>
<span>{formatar_milhar_br(meta)} pts</span>
</div>
<div style="width: 100%; background-color: #e2e8f0; border-radius: 999px; height: 10px; overflow: hidden;">
<div style="width: {width_pct}%; background-color: {color_bar}; height: 100%; border-radius: 999px;"></div>
</div>
</div>
{html_ranking}
</div>"""
    
    st.markdown(html_completo, unsafe_allow_html=True)

# --- 6. FUNÇÕES DE ANÁLISE ---
def calcular_tabela_historico(df_consolidado, temporadas_lista):
    metricas = {'Pontuação': [], 'Quantidade de Pedidos': [], 'Quantidade de Lojas': [], 'Valor Médio de Pedidos': [], 'Quantidade de Segmentos': []}
    try: cols_temporadas = sorted(temporadas_lista, key=lambda x: int(x.split(' ')[1]))
    except: cols_temporadas = sorted(temporadas_lista)
    
    for temp in cols_temporadas:
        df_t = df_consolidado[df_consolidado['Temporada_Exibicao'] == temp]
        pontos = df_t['Pontos'].sum()
        pedidos = df_t[COLUNA_PEDIDO].nunique() if COLUNA_PEDIDO in df_t.columns else 0
        lojas = df_t['Loja'].nunique()
        segmentos = df_t['Segmento'].nunique()
        val_medio = pontos / pedidos if pedidos > 0 else 0
        
        metricas['Pontuação'].append(formatar_milhar_br(pontos))
        metricas['Quantidade de Pedidos'].append(formatar_milhar_br(pedidos))
        metricas['Quantidade de Lojas'].append(int(lojas))
        metricas['Valor Médio de Pedidos'].append(formatar_milhar_br(val_medio))
        metricas['Quantidade de Segmentos'].append(int(segmentos))

    return pd.DataFrame(metricas, index=cols_temporadas).T

def calcular_evolucao_mensal(df_consolidado, metrica_coluna='Pontos'):
    df_pivot = df_consolidado.pivot_table(index='Mês_Exibicao', columns='Temporada_Exibicao', values=metrica_coluna, aggfunc='sum' if metrica_coluna == 'Pontos' else 'nunique', fill_value=0)
    def get_fiscal_order(mes_str):
        try:
            num = int(mes_str.split('(')[1].replace(')', ''))
            return num - 6 if num >= 7 else num + 6
        except: return 99
    df_pivot = df_pivot.sort_index(key=lambda index: index.map(get_fiscal_order))
    try: cols = sorted(df_pivot.columns, key=lambda x: int(x.split(' ')[1]))
    except: cols = sorted(df_pivot.columns)
    df_pivot = df_pivot[cols]

    if len(cols) >= 2:
        t_atual, t_ant = cols[-1], cols[-2]   
        df_pivot['Evolução T/T-1'] = df_pivot.apply(lambda row: calcular_evolucao_pct(row[t_atual], row[t_ant]), axis=1)
        df_pivot['Evolução'] = df_pivot['Evolução T/T-1'].apply(lambda x: "-" if x == 0 else f"{x:+.1%}")
        df_pivot = df_pivot.drop(columns=['Evolução T/T-1'])
    return df_pivot

def calcular_analise_segmento(df_season):
    df_seg = df_season.groupby('Segmento').agg({'Pontos': 'sum', COLUNA_PEDIDO: 'nunique'}).reset_index()
    return df_seg.sort_values('Pontos', ascending=False)

def calcular_analise_lojas_detalhada(df_season):
    df_lojas = df_season.groupby('Loja').agg({'Pontos': 'sum', COLUNA_PEDIDO: 'nunique'}).reset_index()
    df_lojas['Valor Médio'] = df_lojas.apply(lambda row: row['Pontos'] / row[COLUNA_PEDIDO] if row[COLUNA_PEDIDO] > 0 else 0, axis=1)
    return df_lojas.sort_values('Pontos', ascending=False)

# --- 7. FUNÇÃO PRINCIPAL DA TELA ---
def show_architect_dashboard(df_global, user_key):
    # CSS para PREMIOS e BADGES
    # ALTERAÇÃO 1: Aumentei font-size e padding nas classes .badge
    # ALTERAÇÃO 2: Adicionei CSS para aumentar o título do Expander (stExpander)
    st.markdown("""
        <style>
        /* Aumentei o tamanho e o espaçamento interno (padding) das badges */
        .badge { padding: 8px 20px; border-radius: 999px; font-weight: bold; font-size: 1.5rem; display: inline-block; }
        
        .badge-diamante { background-color: #f3e8ff; color: #7e22ce; border: 1px solid #d8b4fe; }
        .badge-esmeralda { background-color: #d1fae5; color: #047857; border: 1px solid #6ee7b7; }
        .badge-rubi { background-color: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
        .badge-topazio { background-color: #e0f2fe; color: #0369a1; border: 1px solid #7dd3fc; }
        .badge-pro { background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
        
        .prog-container { width: 100%; background-color: #e2e8f0; border-radius: 999px; height: 16px; margin-top: 5px; overflow: hidden; }
        .prog-fill { height: 100%; border-radius: 999px; transition: width 1s ease-in-out; }
        .vinculos-box { font-size: 1.0rem; opacity: 0.8; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
        
        .premio-card { 
            background-color: #f8f9fa; 
            padding: 15px;
            border-radius: 12px; 
            margin-bottom: 10px; 
            border: 1px solid #e2e8f0; 
            color: #1e293b; 
            display: flex; 
            flex-direction: column; 
            justify-content: space-between; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .premio-conquistado { 
            border: 2px solid #10b981; 
            background-color: #ffffff; 
        }
        
        .stDataFrame { font-size: 1.1rem !important; }
        div[data-testid="stMetricValue"] { font-size: 1.4rem !important; }
        
        /* AQUI: CSS Para aumentar a fonte do título dos Expanders (Prêmios) */
        div[data-testid="stExpander"] details summary p {
            font-size: 1.4rem !important;
            font-weight: 600 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    df_consolidado = df_global[df_global[COLUNA_CHAVE_CONSOLIDADA] == user_key].copy()
    if df_consolidado.empty:
        st.error(f"Dados não encontrados para: {user_key}")
        return

    dfs = carregar_dados_extras()

    col_h1, col_h2 = st.columns([5, 1])
    col_h1.title(f"Bem-vindo(a), {user_key}")
    if col_h2.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()

    qtd_docs = len(df_consolidado['CNPJ_CPF_LIMPO'].unique())
    if qtd_docs > 1:
        st.markdown(f"<div class='vinculos-box'><b>🔗 Conta Consolidada:</b> Pontuação somada de {qtd_docs} documentos vinculados.</div>", unsafe_allow_html=True)

    if 'Temporada_Exibicao' in df_consolidado.columns:
        try: todas_temporadas = sorted(df_consolidado['Temporada_Exibicao'].unique(), key=lambda x: int(x.split(' ')[1]), reverse=True)
        except: todas_temporadas = sorted(df_consolidado['Temporada_Exibicao'].unique(), reverse=True)
        selected_season = st.selectbox("📅 Temporada Atual", todas_temporadas, index=0)
        df_season = df_consolidado[df_consolidado['Temporada_Exibicao'] == selected_season]
    else:
        df_season = df_consolidado
        selected_season = "Atual"
        todas_temporadas = []

    total_points = df_season['Pontos'].sum()
    current_cat, next_cat = get_category_details(total_points)
    val_evolucao, txt_evolucao, nome_temp_anterior = calcular_evolucao_ajustada(df_consolidado, selected_season)
    user_cat_name = current_cat['name']

    cor_evolucao = "#10b981" if val_evolucao > 0 else ("#ef4444" if val_evolucao < 0 else "#9ca3af")
    icone_evolucao = "▲" if val_evolucao > 0 else ("▼" if val_evolucao < 0 else "•")

    if next_cat:
        range_pts = next_cat["min"] - current_cat["min"]
        achieved = total_points - current_cat["min"]
        pct_main = min(max((achieved / range_pts) * 100, 2), 100) if range_pts > 0 else 0
        msg_meta = f"Faltam <b style='font-size:1.6rem;'>{formatar_milhar_br(next_cat['min'] - total_points)}</b> para {next_cat['name']}"
    else:
        pct_main = 100
        msg_meta = "🏆 Topo alcançado!"

    # --- ALTERAÇÃO NO BANNER ABAIXO ---
    # 1. Aumentei o 'gap' de 15px para 40px (empurra a caixa verde para a direita).
    # 2. Aumentei os font-size dentro da caixa de evolução.
    st.markdown(f"""<div style="background-color: #f8f9fa; border: 1px solid #e2e8f0; padding: 25px; border-radius: 16px; color: #1e293b; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
<div style="display:flex; justify-content: space-between; align-items:flex-start;">
<div>
<p style="margin:0; font-size: 1.9rem; color: #64748b; text-transform: uppercase;">Performance • {selected_season}</p>

<div style="display:flex; align-items:flex-end; gap:140px;">
<div style="display:flex; align-items:baseline; gap:8px;">
<span style="font-size: 3.5rem; font-weight: 800; color: #0f172a;">{formatar_milhar_br(total_points)}</span>
<span style="font-size: 2.2rem; color: #475569;">pontos</span>
</div>

<div style="margin-bottom: 12px; background: rgba(0,0,0,0.05); padding: 10px 24px; border-radius: 10px;">
<span style="color: {cor_evolucao}; font-weight: bold; font-size: 3.0rem;">{icone_evolucao} {txt_evolucao}</span>
<span style="font-size: 2.5rem; color: #64748b; margin-left: 10px;">vs {nome_temp_anterior}</span>
</div>
</div>
</div>
<span class="badge {current_cat['css']}">{current_cat['name']}</span>
</div>
<div style="margin-top: 15px;">
<div style="display:flex; justify-content: space-between; font-size: 1.4rem; color: #475569; margin-bottom: 5px;">
<span>Progresso Categoria</span><span>{msg_meta}</span>
</div>
<div class="prog-container">
<div class="prog-fill" style="width: {pct_main}%; background-color: {current_cat['color']};"></div>
</div>
</div>
</div>""", unsafe_allow_html=True)

    # --- 1. PRÊMIOS ---
    if not dfs['premios'].empty:
        df_premios_season = dfs['premios'][dfs['premios']['Temporada'] == selected_season].copy()
        df_premios_user = df_premios_season[
            (df_premios_season['Categoria_Alvo'] == user_cat_name) | 
            (df_premios_season['Categoria_Alvo'] == 'Todas')
        ]
        df_premios_user = df_premios_user[df_premios_user['Status'] == 'Ativo']

        if not df_premios_user.empty:
            with st.expander(f"🎁 Prêmios Anuais {selected_season} (Exclusivo {user_cat_name})", expanded=True):
                for _, row in df_premios_user.iterrows():
                    meta = float(row['Pontos_Meta'])
                    conquistado = total_points >= meta
                    
                    css_class = "premio-conquistado" if conquistado else ""
                    icon = "✅ CONQUISTADO" if conquistado else f"🔒 Falta {formatar_milhar_br(meta - total_points)}"
                    color_icon = "#10b981" if conquistado else "#f59e0b"
                    
                    st.markdown(f"""<div class="premio-card {css_class}">
<div style="display:flex; justify-content:space-between; margin-bottom:5px;">
<strong>{row['Titulo']}</strong>
<span style="color:{color_icon}; font-weight:bold; font-size:1.3rem;">{icon}</span>
</div>
<div style="font-size:1.35rem; color:#64748b; margin-bottom:10px;">{row['Descricao']}</div>
<div style="font-size:1.85rem; display:flex; justify-content:space-between; color: #475569;">
<span>Meta: {formatar_milhar_br(meta)}</span>
<span>{formatar_milhar_br(total_points)} pts</span>
</div>
</div>""", unsafe_allow_html=True)
                    
                    if not conquistado:
                        st.progress(min(total_points/meta, 1.0) if meta > 0 else 0)
        else:
             st.info(f"Nenhum prêmio disponível para a categoria {user_cat_name} nesta temporada.")

    st.markdown("---")

    # --- 2. ATIVAÇÕES ESPECIAIS ---
    st.subheader("⚡ Ativações")
    if not dfs['ativacoes'].empty:
        ativas = dfs['ativacoes'][dfs['ativacoes']['Status'] == 'Ativa']
        if not ativas.empty:
            for _, row in ativas.iterrows():
                render_card_campanha(row, df_global, user_key, "Ativação")
        else:
            st.info("Nenhuma ativação no momento.")

    st.markdown("---")

    # --- 3. CAMPANHAS ---
    st.subheader("🎯 Aceleradores")
    if not dfs['acoes'].empty:
        acoes_ativas = dfs['acoes'][dfs['acoes']['Status'] == 'Ativa']
        if not acoes_ativas.empty:
            for _, row in acoes_ativas.iterrows():
                render_card_campanha(row, df_global, user_key, "Campanha")
        else:
            st.info("Nenhuma campanha ativa.")
    
    st.markdown("---")

    # --- 4. HISTÓRICO ---
    st.subheader("📈 Histórico de Desempenho")
    if todas_temporadas:
        temps_com_dados = [t for t in todas_temporadas if not df_consolidado[df_consolidado['Temporada_Exibicao'] == t].empty]
        if temps_com_dados:
            df_hist_tabela = calcular_tabela_historico(df_consolidado, temps_com_dados)
            st.dataframe(df_hist_tabela, use_container_width=True)
            
            st.subheader(" Evolução Mensal (Pontuação)")
            df_evol_pontos = calcular_evolucao_mensal(df_consolidado, 'Pontos')
            
            def color_evol(val):
                if isinstance(val, str) and '-' in val and len(val) > 1: return 'color: #ef4444; font-weight: bold;'
                if isinstance(val, str) and '+' in val: return 'color: #10b981; font-weight: bold;'
                return ''
                
            if 'Evolução' in df_evol_pontos.columns:
                st.dataframe(df_evol_pontos.style.applymap(color_evol, subset=['Evolução']).format({col: formatar_milhar_br for col in df_evol_pontos.columns if col != 'Evolução'}), use_container_width=True)
            else:
                st.dataframe(df_evol_pontos, use_container_width=True)

            st.subheader(" Evolução Mensal (Pedidos)")
            if COLUNA_PEDIDO in df_consolidado.columns:
                df_evol_pedidos = calcular_evolucao_mensal(df_consolidado, COLUNA_PEDIDO)
                if 'Evolução' in df_evol_pedidos.columns:
                    st.dataframe(df_evol_pedidos.style.applymap(color_evol, subset=['Evolução']).format({col: formatar_milhar_br for col in df_evol_pedidos.columns if col != 'Evolução'}), use_container_width=True)
                else:
                    st.dataframe(df_evol_pedidos, use_container_width=True)
        else:
            st.info("Sem histórico anterior.")

    st.markdown("---")

    # --- 5. ANÁLISE POR SEGMENTO ---
    st.subheader("🛍️ Análise por Segmento")
    temp_seg_sel = st.selectbox("Selecione a Temporada:", todas_temporadas, index=0, key='sel_seg_temp')
    df_season_seg = df_consolidado[df_consolidado['Temporada_Exibicao'] == temp_seg_sel]
    
    if not df_season_seg.empty:
        df_seg = calcular_analise_segmento(df_season_seg)
        col_table, col_chart = st.columns([1.3, 2]) 
        
        with col_table:
            st.caption("Visão Geral")
            st.dataframe(df_seg.style.format({'Pontos': formatar_milhar_br, COLUNA_PEDIDO: formatar_milhar_br}), use_container_width=True, hide_index=True, height=450)
            
        with col_chart:
            fig = px.pie(df_seg, values='Pontos', names='Segmento', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=120), height=450, showlegend=True, legend=dict(orientation="v", y=0.5, x=1.02))
            fig.update_traces(textposition='inside', textinfo='percent')
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Detalhe de Lojas por Segmento")
        lista_segmentos = ["Selecione..."] + sorted(df_seg['Segmento'].unique())
        segmento_sel = st.selectbox("Filtrar lojas de:", lista_segmentos)
        
        if segmento_sel != "Selecione...":
            df_lojas = df_season_seg[df_season_seg['Segmento'] == segmento_sel].groupby('Loja').agg({'Pontos': 'sum', COLUNA_PEDIDO: 'nunique'}).reset_index().sort_values('Pontos', ascending=False)
            st.dataframe(df_lojas.style.format({'Pontos': formatar_milhar_br, COLUNA_PEDIDO: formatar_milhar_br}), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma compra registrada nesta temporada.")
    
    st.markdown("---")

    # --- 6. ANÁLISE DETALHADA LOJA ---
    st.subheader("🏢 Análise Detalhada por Loja")
    c_temp, c_search = st.columns([1, 2])
    sel_temp_loja = c_temp.selectbox("Temporada:", todas_temporadas, index=0, key='sel_temp_loja')
    search_loja = c_search.text_input("Pesquisar Loja:", placeholder="Digite o nome...", key='search_loja')

    df_loja_filter = df_consolidado[df_consolidado['Temporada_Exibicao'] == sel_temp_loja]
    
    if not df_loja_filter.empty:
        if search_loja:
            df_loja_filter = df_loja_filter[df_loja_filter['Loja'].str.lower().str.contains(search_loja.lower())]
        
        if not df_loja_filter.empty:
            df_final_lojas = calcular_analise_lojas_detalhada(df_loja_filter)
            st.dataframe(
                df_final_lojas.style.format({'Pontos': formatar_milhar_br, COLUNA_PEDIDO: formatar_milhar_br, 'Valor Médio': formatar_milhar_br}),
                use_container_width=True, hide_index=True,
                column_config={"Loja": "Loja Parceira", "Pontos": "Pontuação", COLUNA_PEDIDO: "Qtd. Pedidos", "Valor Médio": "Ticket Médio (pts)"}
            )
        else:
            st.warning(f"Nenhuma loja encontrada com o termo '{search_loja}'.")
    else:
        st.info("Sem dados para esta temporada.")