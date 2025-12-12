import streamlit as st
import pandas as pd
from datetime import date
import os
from modulos.config import Relatorio, COLUNA_NUMERO_TEMPORADA, COLUNA_ESPECIFICADOR
from modulos.dados import carregar_e_tratar_dados
from modulos.tratamento import formatar_milhar_br

ARQUIVO_CAMPANHA_LOJA = "campanhas_loja.csv"

def carregar_campanhas():
    if os.path.exists(ARQUIVO_CAMPANHA_LOJA):
        df = pd.read_csv(ARQUIVO_CAMPANHA_LOJA)
        df['Data_Inicio'] = pd.to_datetime(df['Data_Inicio'], errors='coerce').dt.date
        df['Data_Fim'] = pd.to_datetime(df['Data_Fim'], errors='coerce').dt.date
        if 'Status' not in df.columns: df['Status'] = 'Ativa'
        return df
    return pd.DataFrame()

def calcular_meu_progresso(df_global, store_name, campanha):
    # Filtra dados da loja
    df_loja = df_global[df_global['Loja'] == store_name]
    
    dt_ini = campanha['Data_Inicio']
    dt_fim = campanha['Data_Fim']
    t_atual = int(campanha['Temporada_Ref_Atual'])
    t_anterior = int(campanha['Temporada_Ref_Anterior'])
    
    # --- PONTOS ATUAIS ---
    mask_atual = (df_loja['Data da Venda'].dt.date >= dt_ini) & \
                 (df_loja['Data da Venda'].dt.date <= dt_fim) & \
                 (df_loja[COLUNA_NUMERO_TEMPORADA] == t_atual)
    
    pts_atual = df_loja.loc[mask_atual, 'Pontos'].sum()
    escritorios = df_loja.loc[mask_atual, COLUNA_ESPECIFICADOR].nunique()
    
    # --- PONTOS ANTERIORES (Mesmos meses) ---
    m_start = dt_ini.month
    m_end = dt_fim.month
    if m_end >= m_start:
        meses_campanha = list(range(m_start, m_end + 1))
    else:
        meses_campanha = list(range(m_start, 13)) + list(range(1, m_end + 1))
        
    mask_ant = (df_loja[COLUNA_NUMERO_TEMPORADA] == t_anterior) & \
               (df_loja['Mês_num'].astype(int).isin(meses_campanha))
               
    pts_anterior = df_loja.loc[mask_ant, 'Pontos'].sum()
    
    return pts_atual, pts_anterior, escritorios

def renderizar_cartao_campanha(row, df_global, store_name):
    """Função auxiliar para desenhar o card da campanha."""
    status = row['Status']
    
    with st.container(border=True):
        # Cabeçalho do Card
        c_tit, c_st = st.columns([3, 1])
        c_tit.subheader(f"📢 {row['Titulo']}")
        
        if status == 'Ativa':
            c_st.markdown(":green[● ATIVA]")
        else:
            c_st.markdown(":red[● ENCERRADA]")

        st.write(row['Descricao'])
        st.markdown("---")

        # Cálculos
        pts_atual, pts_ant, escrit = calcular_meu_progresso(df_global, store_name, row)
        minimo_garantido = float(row['Minimo_Garantido'])
        meta_pct = float(row['Meta_Crescimento']) / 100
        
        # Definição da Meta
        if pts_ant > 0:
            base_calculo = pts_ant
            tipo_regra = f"Crescimento sobre T{int(row['Temporada_Ref_Anterior'])}"
            meta_pontos = base_calculo * (1 + meta_pct)
            if pts_ant > 0:
                cresc_real = (pts_atual - pts_ant) / pts_ant
                txt_delta = f"{cresc_real:+.1%}"
            else: 
                txt_delta = "N/A"
        else:
            base_calculo = minimo_garantido
            tipo_regra = "Mínimo Garantido (Loja Nova)"
            meta_pontos = base_calculo * (1 + meta_pct)
            txt_delta = "Novo"
            
        progresso = min(pts_atual / meta_pontos, 1.0) if meta_pontos > 0 else 0
        falta = max(meta_pontos - pts_atual, 0)
        bateu_meta = pts_atual >= meta_pontos

        # Exibição das Métricas
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sua Pontuação", formatar_milhar_br(pts_atual), delta=txt_delta)
        c2.metric(f"Base ({tipo_regra})", formatar_milhar_br(base_calculo))
        c3.metric("Meta a Bater", formatar_milhar_br(meta_pontos))
        c4.metric("Escritórios Pontuados", escrit)
        
        st.caption(f"Regra: {tipo_regra} + {row['Meta_Crescimento']}%")

        # Visualização Final
        if status == 'Ativa':
            color_bar = "green" if bateu_meta else "orange"
            msg_bar = "META BATIDA! 🏆" if bateu_meta else f"Faltam {formatar_milhar_br(falta)}"
            st.markdown(f"**Status:** :{color_bar}[{msg_bar}]")
            st.progress(progresso)
            
        else: # STATUS FINALIZADA
            st.markdown("### 🏁 Resultado Final")
            if bateu_meta:
                st.success(
                    """
                    ### 🎉 PARABÉNS! VOCÊ GANHOU!
                    Você atingiu a meta desta campanha.
                    **A equipe entrará em contato em breve para alinhar a premiação.**
                    """
                )
                st.progress(1.0)
            else:
                st.error(
                    """
                    ### ❌ Não foi dessa vez...
                    A campanha encerrou e a meta não foi atingida.
                    Continue pontuando e fique atento ao próximo acelerador!
                    """
                )
                st.progress(progresso)

def show_acelerador(store_name):
    st.title(f"🚀 Acelerador: {store_name}")
    
    df_global, _ = carregar_e_tratar_dados(Relatorio)
    df_campanhas = carregar_campanhas()
    
    if df_campanhas.empty:
        st.info("Nenhuma campanha disponível.")
        return

    # Separa Ativas e Finalizadas
    df_ativas = df_campanhas[df_campanhas['Status'] == 'Ativa'].sort_values('Data_Fim')
    df_finalizadas = df_campanhas[df_campanhas['Status'] != 'Ativa'].sort_values('Data_Fim', ascending=False)

    # 1. MOSTRA ATIVAS (Expandidas por padrão, fora do dropdown)
    if not df_ativas.empty:
        st.subheader("🔥 Campanhas em Andamento")
        for _, row in df_ativas.iterrows():
            renderizar_cartao_campanha(row, df_global, store_name)
    else:
        st.info("Não há campanhas ativas no momento.")

    # 2. MOSTRA HISTÓRICO (Dentro do Dropdown)
    if not df_finalizadas.empty:
        st.markdown("---")
        with st.expander("📜 Histórico de Campanhas Encerradas", expanded=False):
            for _, row in df_finalizadas.iterrows():
                renderizar_cartao_campanha(row, df_global, store_name)