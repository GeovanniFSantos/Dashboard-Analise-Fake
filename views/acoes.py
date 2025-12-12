import streamlit as st
import pandas as pd
from datetime import date
import os

from modulos.dados import carregar_e_tratar_dados
from modulos.config import Relatorio, COLUNA_ESPECIFICADOR, COLUNA_CHAVE_CONSOLIDADA
from modulos.tratamento import formatar_milhar_br, formatar_documento

ARQUIVO_ACOES = "campanhas_ativas.csv"

def carregar_campanhas():
    if os.path.exists(ARQUIVO_ACOES):
        df = pd.read_csv(ARQUIVO_ACOES)
        # Garante que colunas novas existam
        if 'Limite_Ganhadores' not in df.columns: df['Limite_Ganhadores'] = 0
        if 'Status' not in df.columns: df['Status'] = 'Ativa'
        return df
    return pd.DataFrame(columns=["Titulo", "Tipo", "Meta", "Limite_Ganhadores", "Data_Inicio", "Data_Fim", "Acelerador_Pct", "Descricao", "Status"])

def salvar_campanha_editada(df):
    df.to_csv(ARQUIVO_ACOES, index=False)

def formatar_lista_docs(texto_docs):
    if pd.isna(texto_docs): return ""
    lista = str(texto_docs).split(', ')
    lista_fmt = [formatar_documento(d) for d in lista]
    return ' | '.join(lista_fmt)

def calcular_ganhadores(df_vendas, data_inicio, data_fim, meta, acelerador_pct, limite_ganhadores):
    if isinstance(data_inicio, str): data_inicio = pd.to_datetime(data_inicio).date()
    if isinstance(data_fim, str): data_fim = pd.to_datetime(data_fim).date()
    
    df_vendas['Data da Venda'] = pd.to_datetime(df_vendas['Data da Venda'], errors='coerce')
    mask = (df_vendas['Data da Venda'].dt.date >= data_inicio) & (df_vendas['Data da Venda'].dt.date <= data_fim)
    df_periodo = df_vendas.loc[mask].copy()
    
    if df_periodo.empty: return pd.DataFrame()

    df_resumo = df_periodo.groupby(COLUNA_CHAVE_CONSOLIDADA).agg({
        'Pontos': 'sum',
        COLUNA_ESPECIFICADOR: lambda x: ', '.join(sorted(set(x.astype(str)))), 
        'CNPJ_CPF_LIMPO': lambda x: ', '.join(sorted(set(x.astype(str))))
    }).reset_index()
    
    df_resumo['Pontos Reais'] = df_resumo['Pontos']
    df_resumo['Valor Bônus'] = df_resumo['Pontos'] * (acelerador_pct / 100)
    df_resumo['Total c/ Bônus'] = df_resumo['Pontos Reais'] + df_resumo['Valor Bônus']
    
    # Filtra quem bateu a meta mínima
    ganhadores = df_resumo[df_resumo['Total c/ Bônus'] >= meta].copy()
    ganhadores = ganhadores.sort_values('Total c/ Bônus', ascending=False)
    
    # Aplica limite de ganhadores (Ranking - Top X)
    if limite_ganhadores > 0:
        ganhadores = ganhadores.head(int(limite_ganhadores))
    
    return ganhadores

def show_acoes():
    st.title("🎯 Gestão de Campanhas (Ações)")
    st.markdown("Desafios globais com aceleradores e ranking.")

    df_global, _ = carregar_e_tratar_dados(Relatorio)
    df_campanhas = carregar_campanhas()

    if 'indice_edicao' not in st.session_state: st.session_state['indice_edicao'] = None

    defaults = {"Titulo": "", "Tipo": "", "Meta": 1000.0, "Limite": 0, "Data_Inicio": date.today(), "Data_Fim": date.today(), "Acelerador": 0, "Descricao": ""}
    
    if st.session_state['indice_edicao'] is not None:
        idx = st.session_state['indice_edicao']
        if idx in df_campanhas.index:
            row_edit = df_campanhas.loc[idx]
            defaults.update({
                "Titulo": row_edit['Titulo'], "Tipo": row_edit['Tipo'], 
                "Meta": float(row_edit['Meta']),
                "Limite": int(row_edit.get('Limite_Ganhadores', 0)),
                "Data_Inicio": pd.to_datetime(row_edit['Data_Inicio']).date(),
                "Data_Fim": pd.to_datetime(row_edit['Data_Fim']).date(),
                "Acelerador": int(row_edit['Acelerador_Pct']), "Descricao": row_edit['Descricao']
            })

    with st.container(border=True):
        st.subheader("✏️ Editar" if st.session_state['indice_edicao'] is not None else "➕ Nova Campanha")
        if st.session_state['indice_edicao'] is not None and st.button("Cancelar"):
            st.session_state['indice_edicao'] = None; st.rerun()

        with st.form("form_campanha"):
            c1, c2 = st.columns(2)
            titulo = c1.text_input("Título", defaults["Titulo"])
            tipo = c1.text_input("Prêmio", defaults["Tipo"])
            
            c3, c4 = st.columns(2)
            meta = c3.number_input("Meta Pontos (Mínimo)", value=defaults["Meta"], step=500.0)
            limite = c4.number_input("Qtd. Máxima Ganhadores (0 = Sem limite)", value=defaults["Limite"], step=1, help="Ex: Apenas os Top 20 ganham")
            
            c5, c6 = st.columns(2)
            periodo = c5.date_input("Período", (defaults["Data_Inicio"], defaults["Data_Fim"]), format="DD/MM/YYYY")
            acelerador = c6.slider("Acelerador %", 0, 50, defaults["Acelerador"])
            
            desc = st.text_area("Descrição", defaults["Descricao"])
            
            if st.form_submit_button("Salvar"):
                if len(periodo) == 2:
                    new_data = {
                        "Titulo": titulo, "Tipo": tipo, "Meta": meta, 
                        "Limite_Ganhadores": limite,
                        "Data_Inicio": periodo[0], "Data_Fim": periodo[1], 
                        "Acelerador_Pct": acelerador, "Descricao": desc, "Status": "Ativa"
                    }
                    if st.session_state['indice_edicao'] is not None:
                        for k, v in new_data.items(): df_campanhas.at[st.session_state['indice_edicao'], k] = v
                    else:
                        df_campanhas = pd.concat([df_campanhas, pd.DataFrame([new_data])], ignore_index=True)
                    salvar_campanha_editada(df_campanhas)
                    st.session_state['indice_edicao'] = None; st.rerun()
                else: st.warning("Datas inválidas.")

    st.markdown("---")
    if not df_campanhas.empty:
        df_campanhas['Status_Order'] = df_campanhas['Status'].apply(lambda x: 0 if x == 'Ativa' else 1)
        df_campanhas = df_campanhas.sort_values('Status_Order')
        
        for idx in df_campanhas.index:
            row = df_campanhas.loc[idx]
            status_emoji = "🟢" if row['Status'] == "Ativa" else "🔴"
            limite_txt = f"| Top {int(row['Limite_Ganhadores'])}" if row.get('Limite_Ganhadores', 0) > 0 else "| Sem limite de ganhadores"
            
            with st.expander(f"{status_emoji} {row['Titulo']} ({row['Status']})"):
                col1, col2, col3 = st.columns(3)
                col1.metric("Meta", formatar_milhar_br(row['Meta']))
                col2.metric("Acelerador", f"{row['Acelerador_Pct']}%")
                try:
                    d_ini = pd.to_datetime(row['Data_Inicio']).strftime('%d/%m/%Y')
                    d_fim = pd.to_datetime(row['Data_Fim']).strftime('%d/%m/%Y')
                except: d_ini, d_fim = row['Data_Inicio'], row['Data_Fim']
                col3.write(f"**Período:** {d_ini} até {d_fim}")
                st.write(f"**Prêmio:** {row['Tipo']} {limite_txt}")
                st.info(row['Descricao'])
                
                if st.button("🏆 Verificar Ganhadores", key=f"win_{idx}"):
                    if not df_global.empty:
                        ganhadores = calcular_ganhadores(
                            df_global, row['Data_Inicio'], row['Data_Fim'], 
                            row['Meta'], row['Acelerador_Pct'], row.get('Limite_Ganhadores', 0)
                        )
                        if not ganhadores.empty:
                            st.success(f"{len(ganhadores)} Qualificados!")
                            exibicao = ganhadores[[COLUNA_CHAVE_CONSOLIDADA, COLUNA_ESPECIFICADOR, 'Total c/ Bônus']].copy()
                            exibicao.columns = ['Grupo', 'Nomes', 'Total Final']
                            # Adiciona Ranking
                            exibicao['Ranking'] = range(1, len(exibicao) + 1)
                            st.dataframe(exibicao.style.format({'Total Final': formatar_milhar_br}), use_container_width=True)
                        else: st.warning("Ninguém atingiu a meta ainda.")
                
                st.markdown("---")
                c_edit, c_status, c_del = st.columns([1, 1.5, 1])
                if c_edit.button("✏️ Editar", key=f"ed_{idx}"): st.session_state['indice_edicao'] = idx; st.rerun()
                
                novo_status = "Finalizada" if row['Status'] == "Ativa" else "Ativa"
                label_status = "⏹️ Finalizar Ação" if row['Status'] == "Ativa" else "▶️ Reativar Ação"
                type_status = "secondary" if row['Status'] == "Ativa" else "primary"
                
                if c_status.button(label_status, key=f"st_{idx}", type=type_status):
                    df_campanhas.at[idx, 'Status'] = novo_status
                    salvar_campanha_editada(df_campanhas); st.rerun()

                if c_del.button("🗑️ Excluir", key=f"dl_{idx}"): 
                    df_campanhas = df_campanhas.drop(idx).reset_index(drop=True)
                    salvar_campanha_editada(df_campanhas); st.rerun()
    else:
        st.info("Nenhuma campanha cadastrada.")