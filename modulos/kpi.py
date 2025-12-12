# Módulo: kpi.py
import pandas as pd

# Importa as constantes
from modulos.config import COLUNA_PEDIDO, COLUNA_CNPJ_CPF

def calcular_metricas(df):
    """Calcula os KPIs simples do topo: Pontos, Pedidos, Novos Clientes e Valor Médio."""
    pontos = df['Pontos'].sum()
    pedidos = df[COLUNA_PEDIDO].nunique() if COLUNA_PEDIDO in df.columns else 0
    
    # NOVO: Métrica usa Primeira_Compra_Geral (Primeira Compra Histórica),
    # removendo a restrição de coorte (T Venda = T Cadastro)
    novos_clientes = df[df['Primeira_Compra_Geral'] == True]['CNPJ_CPF_LIMPO'].nunique()
    
    valor_medio = pontos / pedidos if pedidos > 0 else 0
    return pontos, pedidos, novos_clientes, valor_medio