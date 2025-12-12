import streamlit as st
import pandas as pd
import plotly.express as px
from modulos.tratamento import formatar_milhar_br
from modulos.categoria import calcular_categorias

# Constantes de Cores e Estilos para Categorias
CATEGORIES_CONFIG = [
    {"name": "Pro", "min": 0, "color": "#94a3b8", "css": "badge-pro"},
    {"name": "Tópazio", "min": 150000, "color": "#38bdf8", "css": "badge-topazio"},
    {"name": "Rubi", "min": 500000, "color": "#ef4444", "css": "badge-rubi"},
    {"name": "Esmeralda", "min": 2000000, "color": "#10b981", "css": "badge-esmeralda"},
    {"name": "Diamante", "min": 5000000, "color": "#7c3aed", "css": "badge-diamante"}
]

def get_category_details(points):
    """Retorna a categoria atual e a próxima meta."""
    current_cat = CATEGORIES_CONFIG[0]
    next_cat = None
    
    for i, cat in enumerate(CATEGORIES_CONFIG):
        if points >= cat["min"]:
            current_cat = cat
            if i + 1 < len(CATEGORIES_CONFIG):
                next_cat = CATEGORIES_CONFIG[i+1]
            else:
                next_cat = None
    return current_cat, next_cat

def app(user_cpf_limpo):
    # --- CSS Específico do Painel do Arquiteto ---
    st.markdown("""
    <style>
        .badge { padding: 4px 12px; border-radius: 999px; font-weight: bold; font-size: 0.9rem; display: inline-block; }
        .badge-diamante { background-color: #f3e8ff; color: #7e22ce; border: 1px solid #d8b4fe; }
        .badge-esmeralda { background-color: #d1fae5; color: #047857; border: 1px solid #6ee7b7; }
        .badge-rubi { background-color: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
        .badge-topazio { background-color: #e0f2fe; color: #0369a1; border: 1px solid #7dd3fc; }
        .badge-pro { background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
        .progress-container { width: 100%; background-color: #334155; border-radius: 999px; height: 12px; margin-top: 10px; overflow: hidden; }
        .progress-bar { height: 100%; border-radius: 999px; transition: width 1s ease-in-out; }
    </style>
    """, unsafe_allow_html=True)

    df_global = st.session_state.df_global
    
    # --- HEADER E LOGOUT ---
    col_logo, col_logout = st.columns([5, 1])
    with col_logout:
        if st.button("Sair", key="logout_arq"):
            st.session_state.logged_in = False
            st.rerun()

    # --- FILTRAGEM DE DADOS DO USUÁRIO ---
    # Tenta filtrar pelo CPF limpo na coluna criada no tratamento
    # Se não encontrar direto, tenta outras estratégias
    df_user = df_global[df_global['CNPJ_CPF_LIMPO'] == str(user_cpf_limpo)].copy()
    
    if df_user.empty:
        st.warning(f"Não encontramos vendas vinculadas ao documento {user_cpf_limpo} na base carregada.")
        return

    # Pega o nome do primeiro registro encontrado
    nome_usuario = df_user['Especificador/Empresa'].iloc[0]
    
    # Seletor de Temporada
    todas_temporadas = sorted(df_user['Temporada_Exibicao'].unique(), reverse=True)
    if not todas_temporadas:
        st.warning("Sem histórico de temporadas.")
        return
        
    with col_logo:
        st.subheader(f"Olá, {nome_usuario}")
        selected_season = st.selectbox("Selecione a Temporada", todas_temporadas)

    # Filtra dados da temporada
    df_season = df_user[df_user['Temporada_Exibicao'] == selected_season]
    total_points = df_season['Pontos'].sum()

    # --- LÓGICA DE CATEGORIA ---
    current_cat, next_cat = get_category_details(total_points)
    
    if next_cat:
        progress_pct = (total_points - current_cat["min"]) / (next_cat["min"] - current_cat["min"])
        progress_pct = min(max(progress_pct, 0), 1) * 100
        missing_points = next_cat["min"] - total_points
        msg_meta = f"Faltam <b>{formatar_milhar_br(missing_points)}</b> para {next_cat['name']}"
    else:
        progress_pct = 100
        msg_meta = "Você está no topo!"

    # --- BANNER PRINCIPAL (VISUAL FODA) ---
    st.markdown(f"""
    <div style="background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%); padding: 30px; border-radius: 16px; color: white; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        <p style="margin:0; font-size: 0.9rem; color: #94a3b8; text-transform: uppercase; font-weight: bold;">Pontuação Atual • {selected_season}</p>
        <div style="display:flex; align-items:baseline; gap:10px; margin-bottom: 15px; margin-top: 5px;">
            <span style="font-size: 3.5rem; font-weight: 800; line-height: 1;">{formatar_milhar_br(total_points)}</span>
            <span style="font-size: 1.2rem; color: #cbd5e1;">pontos</span>
        </div>
        
        <div style="display:flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
            <span class="badge {current_cat['css']}">{current_cat['name']}</span>
            <span style="font-size: 0.9rem; color: #e2e8f0;">{msg_meta}</span>
        </div>
        
        <div class="progress-container">
            <div class="progress-bar" style="width: {progress_pct}%; background-color: {current_cat['color']};"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- ACELERADORES E METAS (LENDO DA CONFIGURAÇÃO DO ADMIN) ---
    config = st.session_state.config_metas
    
    col_acel, col_cal = st.columns([1, 2])
    
    with col_acel:
        st.markdown(f"""
        <div style="background-color: #fffbeb; border: 1px solid #fcd34d; padding: 20px; border-radius: 12px; height: 100%;">
            <h4 style="color: #92400e; margin-top:0;">🔥 Aceleradores</h4>
            <p style="color: #b45309; font-size: 0.95rem;">{config['acelerador']}</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_cal:
        st.markdown("### 📅 Calendário e Metas")
        # Cria dataframe para tabela visual
        df_metas = pd.DataFrame({
            "Mês 1": [config["m1_meta"], config["m1_acao"]],
            "Mês 2": [config["m2_meta"], config["m2_acao"]],
            "Mês 3": [config["m3_meta"], config["m3_acao"]],
        }, index=["🎯 Meta (Pontos)", "🏆 Prêmio (Ação)"])
        
        st.table(df_metas)

    # --- GRÁFICOS DE PERFORMANCE ---
    st.markdown("---")
    st.subheader("Performance Detalhada")
    
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.markdown("**Por Segmento**")
        if not df_season.empty:
            df_seg = df_season.groupby('Segmento')['Pontos'].sum().reset_index()
            fig = px.bar(df_seg, x='Segmento', y='Pontos', color='Segmento', text_auto='.2s')
            fig.update_layout(showlegend=False, margin=dict(t=0,b=0,l=0,r=0), height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_graf2:
        st.markdown("**Extrato de Compras**")
        df_extrato = df_season[['Data da Venda', 'Loja', 'Segmento', 'Pontos']].copy()
        df_extrato['Data da Venda'] = pd.to_datetime(df_extrato['Data da Venda']).dt.strftime('%d/%m/%Y')
        df_extrato = df_extrato.sort_values('Data da Venda', ascending=False)
        st.dataframe(df_extrato, use_container_width=True, hide_index=True, height=300)