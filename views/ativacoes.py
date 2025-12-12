import streamlit as st
import pandas as pd
from datetime import date
import os
from modulos.dados import carregar_e_tratar_dados
from modulos.config import Relatorio, COLUNA_CHAVE_CONSOLIDADA
from views.acoes import calcular_ganhadores
from modulos.tratamento import formatar_milhar_br # Importação correta da formatação

ARQUIVO_ATIVACOES = "ativacoes.csv"

def carregar_ativacoes():
    if os.path.exists(ARQUIVO_ATIVACOES):
        df = pd.read_csv(ARQUIVO_ATIVACOES)
        if 'Limite_Ganhadores' not in df.columns: df['Limite_Ganhadores'] = 0
        if 'Status' not in df.columns: df['Status'] = 'Ativa'
        return df
    return pd.DataFrame(columns=["Titulo", "Tipo", "Meta", "Limite_Ganhadores", "Data_Inicio", "Data_Fim", "Acelerador_Pct", "Descricao", "Status"])

def salvar_ativacoes(df):
    df.to_csv(ARQUIVO_ATIVACOES, index=False)

def show_ativacoes():
    st.title("⚡ Gestão de Ativações")
    st.markdown("Eventos de curto prazo com ranking e limite de ganhadores.")

    df_global, _ = carregar_e_tratar_dados(Relatorio)
    df_ativacoes = carregar_ativacoes()

    if 'idx_edit_atv' not in st.session_state: st.session_state['idx_edit_atv'] = None

    defaults = {"Titulo": "", "Tipo": "", "Meta": 5000.0, "Limite": 20, "Data_Inicio": date.today(), "Data_Fim": date.today(), "Acelerador": 0, "Descricao": ""}
    
    if st.session_state['idx_edit_atv'] is not None:
        idx = st.session_state['idx_edit_atv']
        if idx in df_ativacoes.index:
            row_edit = df_ativacoes.loc[idx]
            defaults.update({
                "Titulo": row_edit['Titulo'], "Tipo": row_edit['Tipo'], 
                "Meta": float(row_edit['Meta']),
                "Limite": int(row_edit.get('Limite_Ganhadores', 0)),
                "Data_Inicio": pd.to_datetime(row_edit['Data_Inicio']).date(),
                "Data_Fim": pd.to_datetime(row_edit['Data_Fim']).date(),
                "Acelerador": int(row_edit['Acelerador_Pct']), "Descricao": row_edit['Descricao']
            })

    with st.container(border=True):
        st.subheader("✏️ Editar" if st.session_state['idx_edit_atv'] is not None else "➕ Nova Ativação")
        if st.session_state['idx_edit_atv'] is not None and st.button("Cancelar"):
            st.session_state['idx_edit_atv'] = None; st.rerun()

        with st.form("form_ativacao"):
            c1, c2 = st.columns(2)
            titulo = c1.text_input("Título da Ativação", defaults["Titulo"])
            tipo = c1.text_input("Prêmio", defaults["Tipo"])
            
            c3, c4 = st.columns(2)
            meta = c3.number_input("Meta Pontos (Mínimo)", value=defaults["Meta"], step=500.0)
            limite = c4.number_input("Qtd. Máxima Ganhadores (Ranking)", value=defaults["Limite"], step=1)
            
            c5, c6 = st.columns(2)
            periodo = c5.date_input("Período", (defaults["Data_Inicio"], defaults["Data_Fim"]), format="DD/MM/YYYY")
            acelerador = c6.slider("Acelerador %", 0, 50, defaults["Acelerador"])
            
            desc = st.text_area("Descrição / Regras", defaults["Descricao"])
            
            if st.form_submit_button("Salvar"):
                if len(periodo) == 2:
                    new_data = {
                        "Titulo": titulo, "Tipo": tipo, "Meta": meta, 
                        "Limite_Ganhadores": limite,
                        "Data_Inicio": periodo[0], "Data_Fim": periodo[1], 
                        "Acelerador_Pct": acelerador, "Descricao": desc, "Status": "Ativa"
                    }
                    if st.session_state['idx_edit_atv'] is not None:
                        for k, v in new_data.items(): df_ativacoes.at[st.session_state['idx_edit_atv'], k] = v
                    else:
                        df_ativacoes = pd.concat([df_ativacoes, pd.DataFrame([new_data])], ignore_index=True)
                    salvar_ativacoes(df_ativacoes)
                    st.session_state['idx_edit_atv'] = None; st.rerun()
                else: st.warning("Datas inválidas.")

    st.markdown("---")
    if not df_ativacoes.empty:
        # Ordenação: Ativas primeiro
        df_ativacoes['Status_Order'] = df_ativacoes['Status'].apply(lambda x: 0 if x == 'Ativa' else 1)
        df_ativacoes = df_ativacoes.sort_values('Status_Order')

        for idx in df_ativacoes.index:
            row = df_ativacoes.loc[idx]
            
            status_icon = "🟢" if row['Status'] == 'Ativa' else "🔴"
            
            with st.expander(f"{status_icon} {row['Titulo']} (Top {int(row['Limite_Ganhadores'])})"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Meta Mínima", formatar_milhar_br(row['Meta']))
                c2.metric("Vagas", int(row['Limite_Ganhadores']))
                
                try: d_p = f"{pd.to_datetime(row['Data_Inicio']).strftime('%d/%m')} a {pd.to_datetime(row['Data_Fim']).strftime('%d/%m')}"
                except: d_p = "N/A"
                c3.write(f"**Período:** {d_p}")
                
                if st.button("🏆 Ver Ranking Atual", key=f"watv_{idx}"):
                    if not df_global.empty:
                        ganhadores = calcular_ganhadores(
                            df_global, row['Data_Inicio'], row['Data_Fim'], 
                            row['Meta'], row['Acelerador_Pct'], row.get('Limite_Ganhadores', 0)
                        )
                        if not ganhadores.empty:
                            st.success(f"{len(ganhadores)} Pessoas no Ranking!")
                            exibicao = ganhadores[[COLUNA_CHAVE_CONSOLIDADA, 'Total c/ Bônus']].copy()
                            exibicao.columns = ['Participante', 'Pontuação Total']
                            exibicao['Ranking'] = range(1, len(exibicao) + 1)
                            st.dataframe(
                                exibicao.style.format({'Pontuação Total': formatar_milhar_br}), 
                                use_container_width=True
                            )
                        else: st.warning("Ninguém atingiu o mínimo ainda.")
                
                st.markdown("---")
                
                # --- BOTÕES DE CONTROLE ---
                c_edit, c_status, c_del = st.columns([1, 1.5, 1])
                
                if c_edit.button("✏️ Editar", key=f"eatv_{idx}"): 
                    st.session_state['idx_edit_atv'] = idx; st.rerun()
                
                # Botão de Status (Alternar)
                novo_status = "Finalizada" if row['Status'] == "Ativa" else "Ativa"
                label_status = "⏹️ Finalizar" if row['Status'] == "Ativa" else "▶️ Reativar"
                tipo_btn = "secondary" if row['Status'] == "Ativa" else "primary"
                
                if c_status.button(label_status, key=f"st_atv_{idx}", type=tipo_btn):
                    df_ativacoes.at[idx, 'Status'] = novo_status
                    salvar_ativacoes(df_ativacoes); st.rerun()

                if c_del.button("🗑️ Excluir", key=f"datv_{idx}"): 
                    df_ativacoes = df_ativacoes.drop(idx).reset_index(drop=True)
                    salvar_ativacoes(df_ativacoes); st.rerun()