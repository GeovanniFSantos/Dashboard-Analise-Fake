# Módulo: retencao.py
import pandas as pd

# Importa as constantes
from modulos.config import COLUNA_NUMERO_TEMPORADA, COLUNA_CNPJ_CPF

# ==============================================================================
# FUNÇÃO PARA CÁLCULO DE CLIENTES ATIVOS E INATIVOS (ITEM 10A)
# ==============================================================================
def calcular_clientes_ativos_inativos(df_completo_original, lojas_selecionadas, segmentos_selecionados):
    """Calcula a contagem de clientes Ativos e Inativos POR TEMPORADA, respeitando os filtros de Loja/Segmento.
        Retorna o DataFrame por Temporada de métricas e o set de todos os clientes históricos DESSA ENTIDADE."""
        
    # 1. Filtra a base completa pelo Segmento e Loja selecionados (base histórica da entidade)
    if not lojas_selecionadas or not segmentos_selecionados:
        # Se não há filtro de Loja/Segmento, usa o DF original
        df_base = df_completo_original.copy()
    else:
        df_base = df_completo_original[
            (df_completo_original['Loja'].isin(lojas_selecionadas)) &
            (df_completo_original['Segmento'].isin(segmentos_selecionados))
        ].copy()
    
    if df_base.empty:
        return pd.DataFrame(), set()

    # Filtra apenas temporadas válidas (Numero Temporada > 0)
    df_base_valida = df_base[df_base[COLUNA_NUMERO_TEMPORADA] > 0].copy()
    if df_base_valida.empty:
            return pd.DataFrame(), set()

    # Lista de todas as temporadas únicas na ENTIDADE filtrada, ORDENADAS PELO NÚMERO
    temporadas_unicas_num = sorted(df_base_valida[COLUNA_NUMERO_TEMPORADA].unique())
    
    dados_por_temporada = []
    clientes_que_ja_pontuaram = set() # Set de clientes que já pontuaram DESSA ENTIDADE

    for t_num in temporadas_unicas_num:
        t_nome = f"Temporada {t_num}"
        
        # 1. Clientes Ativos (Pontuaram na temporada atual T, DESSA ENTIDADE)
        clientes_ativos_na_temporada = set(
            df_base_valida[df_base_valida[COLUNA_NUMERO_TEMPORADA] == t_num]['CNPJ_CPF_LIMPO'].unique()
        )
        qtd_ativos = len(clientes_ativos_na_temporada)
        
        # 2. Clientes Inativos (Pontuaram ANTES no histórico DESSA ENTIDADE, mas NÃO pontuaram em T)
        # O set 'clientes_que_ja_pontuaram' armazena o histórico acumulado até a temporada anterior
        clientes_inativos_na_temporada = clientes_que_ja_pontuaram.difference(clientes_ativos_na_temporada)
        qtd_inativos = len(clientes_inativos_na_temporada)

        # 3. NOVO CÁLCULO: Total de Clientes (Ativos + Inativos)
        qtd_total_clientes = qtd_ativos + qtd_inativos

        # 4. NOVO CÁLCULO: Taxa de Ativação (Ativos / Total)
        pct_ativo = qtd_ativos / qtd_total_clientes if qtd_total_clientes > 0 else 0.0

        # Adiciona a linha de dados por temporada
        dados_por_temporada.append({
            'Temporada': t_nome,
            'Contagem de Clientes Pontuando (Ativos)': qtd_ativos,
            'Contagem de Clientes Não Pontuando (Inativos)': qtd_inativos,
            'Total de Clientes': qtd_total_clientes, # NOVA COLUNA
            '% Ativo': pct_ativo # NOVA COLUNA
        })

        # Atualiza o set global de clientes que já pontuaram DESSA ENTIDADE (para o próximo loop)
        clientes_que_ja_pontuaram.update(clientes_ativos_na_temporada)
    
    df_por_temporada = pd.DataFrame(dados_por_temporada)
    
    # Retorna o DF sem a linha Total
    return df_por_temporada, clientes_que_ja_pontuaram