import streamlit as st
import pandas as pd
import os

from modulos.dados import carregar_e_tratar_dados
from modulos.config import Relatorio, COLUNA_ESPECIFICADOR, COLUNA_CHAVE_CONSOLIDADA, CATEGORIAS_NOMES, COLUNA_NUMERO_TEMPORADA
from modulos.tratamento import formatar_milhar_br

ARQUIVO_PREMIOS = "premios_temporada.csv"

def carregar_premios():
    if os.path.exists(ARQUIVO_PREMIOS):
        df = pd.read_csv(ARQUIVO_PREMIOS)
        if 'Categoria_Alvo' not in df.columns: df['Categoria_Alvo'] = 'Todas'
        if 'Status' not in df.columns: df['Status'] = 'Ativo'
        return df
    return pd.DataFrame(columns=["Titulo", "Pontos_Meta", "Temporada", "Descricao", "Status", "Categoria_Alvo"])

def salvar_premios_editado(df):
    df.to_csv(ARQUIVO_PREMIOS, index=False)

def calcular_ganhadores_premio(df_global, temporada_str, meta_pontos):
    """Calcula quem bateu a meta na temporada específica."""
    df_season = df_global[df_global['Temporada_Exibicao'] == temporada_str].copy()
    
    if df_season.empty:
        return pd.DataFrame()

    # Agrupa por Escritório/Grupo
    df_resumo = df_season.groupby(COLUNA_CHAVE_CONSOLIDADA).agg({
        'Pontos': 'sum',
        COLUNA_ESPECIFICADOR: lambda x: ', '.join(sorted(set(x.astype(str))))
    }).reset_index()
    
    # Filtra ganhadores
    ganhadores = df_resumo[df_resumo['Pontos'] >= meta_pontos].copy()
    ganhadores = ganhadores.sort_values('Pontos', ascending=False)
    
    return ganhadores

def show_premios():
    st.title("🏆 Cadastro de Premiações (Por Categoria)")
    st.markdown("Defina os prêmios anuais e verifique os ganhadores.")

    df_global, _ = carregar_e_tratar_dados(Relatorio)
    df_premios = carregar_premios()

    if 'Temporada_Exibicao' in df_global.columns:
        lista_temporadas = sorted(df_global['Temporada_Exibicao'].dropna().unique(), reverse=True)
    else: lista_temporadas = ["Temporada Atual"]

    if 'idx_edit_premio' not in st.session_state: st.session_state['idx_edit_premio'] = None

    defaults = {"Titulo": "", "Pontos": 50000.0, "Temporada": lista_temporadas[0], "Descricao": "", "Categoria": "Todas"}
    
    if st.session_state['idx_edit_premio'] is not None:
        idx = st.session_state['idx_edit_premio']
        if idx in df_premios.index:
            row = df_premios.loc[idx]
            defaults.update({
                "Titulo": row['Titulo'], "Pontos": float(row['Pontos_Meta']), 
                "Temporada": row['Temporada'], "Descricao": row['Descricao'],
                "Categoria": row.get('Categoria_Alvo', 'Todas')
            })

    with st.container(border=True):
        st.subheader("✏️ Editar" if st.session_state['idx_edit_premio'] is not None else "➕ Novo Prêmio")
        if st.session_state['idx_edit_premio'] is not None and st.button("Cancelar"):
            st.session_state['idx_edit_premio'] = None; st.rerun()

        with st.form("form_premio"):
            c1, c2 = st.columns(2)
            titulo = c1.text_input("Nome do Prêmio", defaults["Titulo"])
            
            # SELETOR DE CATEGORIA
            opcoes_cat = ["Todas"] + CATEGORIAS_NOMES
            try: idx_cat = opcoes_cat.index(defaults["Categoria"])
            except: idx_cat = 0
            categoria = c2.selectbox("Categoria Alvo", opcoes_cat, index=idx_cat)

            c3, c4 = st.columns(2)
            temporada = c3.selectbox("Temporada", options=lista_temporadas, index=lista_temporadas.index(defaults["Temporada"]) if defaults["Temporada"] in lista_temporadas else 0)
            pontos = c4.number_input("Meta de Pontos", min_value=0.0, value=defaults["Pontos"], step=1000.0)
            
            desc = st.text_area("Descrição", defaults["Descricao"])
            
            if st.form_submit_button("Salvar Prêmio"):
                new_data = {
                    "Titulo": titulo, "Pontos_Meta": pontos, "Temporada": temporada, 
                    "Descricao": desc, "Status": "Ativo", "Categoria_Alvo": categoria
                }
                if st.session_state['idx_edit_premio'] is not None:
                    for k, v in new_data.items(): df_premios.at[st.session_state['idx_edit_premio'], k] = v
                else:
                    df_premios = pd.concat([df_premios, pd.DataFrame([new_data])], ignore_index=True)
                salvar_premios_editado(df_premios); st.session_state['idx_edit_premio'] = None; st.rerun()

    st.markdown("---")
    
    if not df_premios.empty:
        # Ordenação visual
        df_premios['Status_Ord'] = df_premios['Status'].apply(lambda x: 0 if x == 'Ativo' else 2)
        df_premios = df_premios.sort_values('Status_Ord')

        for idx in df_premios.index:
            row = df_premios.loc[idx]
            status_icon = "🟢" if row['Status'] == 'Ativo' else "🔴"
            cat_badge = f"[{row.get('Categoria_Alvo', 'Todas')}]"
            
            with st.expander(f"{status_icon} {cat_badge} {row['Titulo']} ({row['Status']})"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Meta", formatar_milhar_br(row['Pontos_Meta']))
                c2.write(f"**Temporada:** {row['Temporada']}")
                c3.write(f"**Categoria:** {row.get('Categoria_Alvo', 'Todas')}")
                st.info(row['Descricao'])
                
                # --- VERIFICAR GANHADORES ---
                if st.button("🏆 Verificar Ganhadores", key=f"v_win_{idx}"):
                    if not df_global.empty:
                        ganhadores = calcular_ganhadores_premio(df_global, row['Temporada'], row['Pontos_Meta'])
                        if not ganhadores.empty:
                            st.success(f"{len(ganhadores)} Arquitetos bateram a meta!")
                            st.dataframe(
                                ganhadores[[COLUNA_CHAVE_CONSOLIDADA, 'Pontos']].style.format({'Pontos': formatar_milhar_br}),
                                use_container_width=True
                            )
                        else:
                            st.warning("Ninguém bateu a meta ainda.")
                    else:
                        st.error("Sem dados carregados.")
                
                st.markdown("---")
                
                # --- BOTÕES DE AÇÃO ---
                col_b1, col_b2, col_b3 = st.columns([1, 1.5, 1])
                
                if col_b1.button("✏️ Editar", key=f"ep_{idx}"): st.session_state['idx_edit_premio'] = idx; st.rerun()
                
                # Botão de Status (Alternar)
                novo_status = "Finalizado" if row['Status'] == "Ativo" else "Ativo"
                label_status = "⏹️ Finalizar" if row['Status'] == "Ativo" else "▶️ Reativar"
                tipo_btn = "secondary" if row['Status'] == "Ativo" else "primary"
                
                if col_b2.button(label_status, key=f"st_{idx}", type=tipo_btn):
                    df_premios.at[idx, 'Status'] = novo_status
                    salvar_premios_editado(df_premios); st.rerun()

                if col_b3.button("🗑️ Excluir", key=f"dp_{idx}"):
                    df_premios = df_premios.drop(idx).reset_index(drop=True)
                    salvar_premios_editado(df_premios); st.rerun()