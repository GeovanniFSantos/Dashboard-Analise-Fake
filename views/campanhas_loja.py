import streamlit as st
import pandas as pd
from datetime import date, datetime
import os

# Imports
from modulos.dados import carregar_e_tratar_dados
from modulos.config import Relatorio, COLUNA_NUMERO_TEMPORADA, COLUNA_ESPECIFICADOR
from modulos.tratamento import formatar_milhar_br, calcular_evolucao_pct

ARQUIVO_CAMPANHA_LOJA = "campanhas_loja.csv"

def carregar_campanhas_loja():
    cols = ["Titulo", "Meta_Crescimento", "Minimo_Garantido", "Data_Inicio", "Data_Fim", 
            "Descricao", "Status", "Temporada_Ref_Atual", "Temporada_Ref_Anterior"]
    
    if os.path.exists(ARQUIVO_CAMPANHA_LOJA):
        try:
            df = pd.read_csv(ARQUIVO_CAMPANHA_LOJA)
            if df.empty and len(df.columns) == 0: return pd.DataFrame(columns=cols)
            return df
        except pd.errors.EmptyDataError: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def salvar_campanha_loja(df):
    df.to_csv(ARQUIVO_CAMPANHA_LOJA, index=False)

def calcular_ganhadores_loja(df_global, campanha):
    # Datas e Parâmetros
    dt_ini = pd.to_datetime(campanha['Data_Inicio']).date()
    dt_fim = pd.to_datetime(campanha['Data_Fim']).date()
    t_atual = int(campanha['Temporada_Ref_Atual'])
    t_anterior = int(campanha['Temporada_Ref_Anterior'])
    meta_cresc = float(campanha['Meta_Crescimento']) / 100
    minimo_garantido = float(campanha['Minimo_Garantido'])
    
    # --- 1. DADOS ATUAIS (T10) ---
    df_atual = df_global[
        (df_global['Data da Venda'].dt.date >= dt_ini) & 
        (df_global['Data da Venda'].dt.date <= dt_fim) &
        (df_global[COLUNA_NUMERO_TEMPORADA] == t_atual)
    ].copy()

    if df_atual.empty: return pd.DataFrame()

    # --- 2. DADOS ANTERIORES (T9 - Mesmos Meses) ---
    # Lógica de meses baseada na data da campanha (mais seguro que data da venda)
    m_start = dt_ini.month
    m_end = dt_fim.month
    meses_campanha = list(range(m_start, m_end + 1)) if m_end >= m_start else list(range(m_start, 13)) + list(range(1, m_end + 1))

    df_anterior = df_global[
        (df_global[COLUNA_NUMERO_TEMPORADA] == t_anterior) &
        (df_global['Mês_num'].astype(int).isin(meses_campanha))
    ].copy()

    # --- 3. MAPEAMENTO DE SEGMENTO ---
    mapa_segmentos = df_global[['Loja', 'Segmento']].drop_duplicates(subset=['Loja']).set_index('Loja')['Segmento'].to_dict()

    # --- 4. AGRUPAMENTO ---
    resumo_atual = df_atual.groupby('Loja').agg({
        'Pontos': 'sum',
        COLUNA_ESPECIFICADOR: 'nunique'
    }).rename(columns={'Pontos': 'Pts_Atual', COLUNA_ESPECIFICADOR: 'Escritorios_Ativos'})

    resumo_anterior = df_anterior.groupby('Loja')['Pontos'].sum().reset_index().rename(columns={'Pontos': 'Pts_Anterior'})
    
    # Merge (Left join para manter quem pontuou agora, mesmo se não tinha antes)
    resultado = pd.merge(resumo_atual, resumo_anterior, on='Loja', how='left').fillna(0)
    resultado['Segmento'] = resultado['Loja'].map(mapa_segmentos)

    # --- 5. REGRAS ---
    def aplicar_regras(row):
        pts_at = row['Pts_Atual']
        pts_an = row['Pts_Anterior']
        
        val_base_exibicao = pts_an # O que vai aparecer na coluna T9 (Base)
        
        if pts_an == 0:
            # Loja Nova -> Usa Mínimo Garantido como base de cálculo
            meta_pontos = minimo_garantido * (1 + meta_cresc)
            val_base_exibicao = minimo_garantido # Mostra o mínimo na tabela para clareza
            regra = "Mínimo Garantido"
            crescimento_txt = "Novo"
        else:
            # Loja Antiga -> Usa T-1 como base
            meta_pontos = pts_an * (1 + meta_cresc)
            crescimento_real = (pts_at - pts_an) / pts_an
            regra = "Crescimento T vs T-1"
            crescimento_txt = f"{crescimento_real:+.1%}"
            
        atingiu = pts_at >= meta_pontos
        return atingiu, regra, crescimento_txt, val_base_exibicao, meta_pontos

    # Aplica e expande o resultado
    resultado['Ganhou'], resultado['Regra'], resultado['Crescimento'], resultado['Base_Calc'], resultado['Meta'] = zip(*resultado.apply(aplicar_regras, axis=1))
    
    # Filtra apenas ganhadores e ordena
    ganhadores = resultado[resultado['Ganhou'] == True].sort_values(['Segmento', 'Escritorios_Ativos'], ascending=[True, False])
    
    return ganhadores

def show_admin_campanhas_loja():
    st.title("🏢 Gestão de Campanhas (Acelerador Lojas)")
    
    df_campanhas = carregar_campanhas_loja()
    try: df_global, _ = carregar_e_tratar_dados(Relatorio)
    except: df_global = pd.DataFrame()
    
    if 'idx_edit_loja' not in st.session_state: st.session_state['idx_edit_loja'] = None

    defaults = {"Titulo": "", "Meta": 20.0, "Minimo": 153000.0, "Data_Inicio": date.today(), "Data_Fim": date.today(), "T_Atual": 10, "T_Ant": 9, "Descricao": ""}
    
    if st.session_state['idx_edit_loja'] is not None:
        idx = st.session_state['idx_edit_loja']
        row = df_campanhas.loc[idx]
        defaults.update({"Titulo": row['Titulo'], "Meta": float(row['Meta_Crescimento']), "Minimo": float(row['Minimo_Garantido']), "Data_Inicio": pd.to_datetime(row['Data_Inicio']).date(), "Data_Fim": pd.to_datetime(row['Data_Fim']).date(), "T_Atual": int(row['Temporada_Ref_Atual']), "T_Ant": int(row['Temporada_Ref_Anterior']), "Descricao": row['Descricao']})

    with st.container(border=True):
        st.subheader("✏️ Editar" if st.session_state['idx_edit_loja'] is not None else "➕ Nova Campanha")
        if st.session_state['idx_edit_loja'] is not None and st.button("Cancelar"): st.session_state['idx_edit_loja'] = None; st.rerun()
        with st.form("form_camp_loja"):
            c1, c2 = st.columns(2)
            titulo = c1.text_input("Título", defaults["Titulo"])
            meta_pct = c1.number_input("Meta Crescimento (%)", value=defaults["Meta"])
            minimo = c1.number_input("Mínimo Garantido (Pts - Lojas Novas)", value=defaults["Minimo"])
            periodo = c2.date_input("Período", (defaults["Data_Inicio"], defaults["Data_Fim"]), format="DD/MM/YYYY")
            t_at = c2.number_input("Temporada Atual (Ref)", value=defaults["T_Atual"])
            t_ant = c2.number_input("Temporada Anterior (Base)", value=defaults["T_Ant"])
            desc = st.text_area("Descrição", defaults["Descricao"])
            if st.form_submit_button("Salvar"):
                if len(periodo) == 2:
                    new = {"Titulo": titulo, "Meta_Crescimento": meta_pct, "Minimo_Garantido": minimo, "Data_Inicio": periodo[0], "Data_Fim": periodo[1], "Temporada_Ref_Atual": t_at, "Temporada_Ref_Anterior": t_ant, "Descricao": desc, "Status": "Ativa"}
                    if st.session_state['idx_edit_loja'] is not None:
                        for k, v in new.items(): df_campanhas.at[st.session_state['idx_edit_loja'], k] = v
                    else: df_campanhas = pd.concat([df_campanhas, pd.DataFrame([new])], ignore_index=True)
                    salvar_campanha_loja(df_campanhas); st.session_state['idx_edit_loja'] = None; st.rerun()
                else: st.warning("Datas inválidas")

    st.markdown("---")
    if not df_campanhas.empty:
        df_campanhas['Status_Ord'] = df_campanhas['Status'].apply(lambda x: 0 if x == 'Ativa' else 2)
        df_campanhas = df_campanhas.sort_values('Status_Ord')
        for idx in df_campanhas.index:
            row = df_campanhas.loc[idx]
            cor_st = "🟢" if row['Status'] == "Ativa" else "🔴"
            with st.expander(f"{cor_st} {row['Titulo']} ({row['Status']})"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Meta Crescimento", f"{row['Meta_Crescimento']}%")
                c2.metric("Mínimo Garantido", formatar_milhar_br(row['Minimo_Garantido']))
                try: d_p = f"{pd.to_datetime(row['Data_Inicio']).strftime('%d/%m')} a {pd.to_datetime(row['Data_Fim']).strftime('%d/%m')}"
                except: d_p = "Data Inválida"
                c3.write(f"**Período:** {d_p}"); st.info(row['Descricao'])
                
                if st.button("🏆 Verificar Lojas Ganhadoras", key=f"wg_{idx}"):
                    if not df_global.empty:
                        ganhadores = calcular_ganhadores_loja(df_global, row)
                        if not ganhadores.empty:
                            st.success(f"🎉 Total: {len(ganhadores)} Lojas bateram a meta!")
                            for seg in ganhadores['Segmento'].unique():
                                st.markdown(f"#### 📂 {seg}")
                                df_show = ganhadores[ganhadores['Segmento'] == seg][['Loja', 'Pts_Atual', 'Base_Calc', 'Meta', 'Crescimento', 'Escritorios_Ativos', 'Regra']]
                                df_show.columns = ['Loja', f'Pontos T{int(row["Temporada_Ref_Atual"])}', f'Base (T{int(row["Temporada_Ref_Anterior"])} ou Mínimo)', 'Meta', 'Crescimento', 'Escritórios', 'Regra']
                                st.dataframe(df_show.style.format({f'Pontos T{int(row["Temporada_Ref_Atual"])}': formatar_milhar_br, f'Base (T{int(row["Temporada_Ref_Anterior"])} ou Mínimo)': formatar_milhar_br, 'Meta': formatar_milhar_br}), use_container_width=True)
                        else: st.warning("Ninguém bateu a meta.")
                
                c1, c2, c3 = st.columns(3)
                if c1.button("✏️ Editar", key=f"e_{idx}"): st.session_state['idx_edit_loja'] = idx; st.rerun()
                lbl_st = "⏹️ Finalizar" if row['Status'] == "Ativa" else "▶️ Reativar"
                if c2.button(lbl_st, key=f"s_{idx}"):
                     df_campanhas.at[idx, 'Status'] = "Finalizada" if row['Status'] == "Ativa" else "Ativa"
                     salvar_campanha_loja(df_campanhas); st.rerun()
                if c3.button("🗑️ Excluir", key=f"d_{idx}"): 
                     df_campanhas = df_campanhas.drop(idx).reset_index(drop=True)
                     salvar_campanha_loja(df_campanhas); st.rerun()