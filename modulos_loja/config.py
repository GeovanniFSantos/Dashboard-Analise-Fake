# MÓDULO DE CONFIGURAÇÃO E UTILIDADES
import pandas as pd
import streamlit as st

# ==============================================================================
# 📌 CONFIGURAÇÕES E CONSTANTES GLOBAIS
# ==============================================================================

# Definição do arquivo principal
RELATORIO_PATH = 'Relatorio.xlsx' 

# Colunas Essenciais
COLUNAS_NUMERICAS = ['Valor Total', 'Pontos']
COLUNA_NUMERO_TEMPORADA = 'Numero Temporada' 
COLUNA_PEDIDO = 'NF/Pedido'  # KPI de volume: Número de pedidos únicos
COLUNA_CNPJ_CPF = 'CPF/CNPJ' # KPI de volume: Pessoas únicas
COLUNA_ESPECIFICADOR = 'Especificador/Empresa'
COLUNA_CPF_NOVO_CADASTRO = 'CPF'

# Mapeamento de Meses (para ordenação e exibição)
NOMES_MESES_MAP = {
    '1': 'Jan (01)', '2': 'Fev (02)', '3': 'Mar (03)', '4': 'Abr (04)',
    '5': 'Mai (05)', '6': 'Jun (06)', '7': 'Jul (07)', '8': 'Ago (08)',
    '9': 'Set (09)', '10': 'Out (10)', '11': 'Nov (11)', '12': 'Dez (12)'
}

# Ordem dos Meses (Julho a Junho, seguindo o ano fiscal)
MES_ORDEM_FISCAL = {
    'Jul (07)': 1, 'Ago (08)': 2, 'Set (09)': 3, 'Out (10)': 4, 'Nov (11)': 5, 
    'Dez (12)': 6, 'Jan (01)': 7, 'Fev (02)': 8, 'Mar (03)': 9, 'Abr (04)': 10,
    'Mai (05)': 11, 'Jun (06)': 12
}

# Definições de Categorias (Pontuação Total)
CATEGORIAS_NOMES = ['Diamante', 'Esmeralda', 'Ruby', 'Topázio', 'Pro']
CATEGORIAS_LIMITES = [5000000, 2000000, 500000, 150000, 1] # Ordem decrescente

# Cores de Estilização
CORES_CATEGORIA_TEXTO = {
    'Diamante': 'color: #b3e6ff; font-weight: bold', # Ciano Claro
    'Esmeralda': 'color: #a3ffb6; font-weight: bold', # Verde Claro
    'Ruby': 'color: #ff9999; font-weight: bold', # Vermelho Claro
    'Topázio': 'color: #ffe08a; font-weight: bold', # Amarelo Claro
    'Pro': 'color: #d1d1d1; font-weight: bold', # Cinza
    'Sem Categoria': 'color: #ffffff; font-weight: bold', # Branco para Sem Categoria
    'Total': 'font-weight: bold;' # Fundo Escuro
}

# Nova constante para a lógica de ranking
RANKING_INDICADORES = {
    'SUBIU': '↑ Subiu Posição',
    'DESCEU': '↓ Desceu Posição',
    'MANTEVE': '≈ Manteve Posição',
    'NOVO': 'Novo Ranking',
    'SAIU': 'Saiu do Ranking'
}

# ==============================================================================
# 📌 FUNÇÕES DE UTILIDADE (FORMATO)
# ==============================================================================

def formatar_milhar_br(valor, casas_decimais=0):
    """
    Formata um valor numérico para o padrão brasileiro (separador de milhar ponto, decimal vírgula).
    Ex: 1234567.89 -> 1.234.567,89 (se casas_decimais=2)
    """
    if isinstance(valor, (int, float)):
        # Cria a string de formato dinamicamente (ex: "{:,.0f}" ou "{:,.2f}")
        format_str = "{:,.%df}" % casas_decimais
        
        # 1. Formata o valor, usando vírgula como separador decimal (padrão Python/Locale)
        formatted = format_str.format(valor)
        
        # 2. Substitui o separador de milhar (vírgula) por um placeholder temporário
        formatted = formatted.replace(",", "X")
        
        # 3. Substitui o separador decimal (ponto) por vírgula
        formatted = formatted.replace(".", ",")
        
        # 4. Restaura o separador de milhar
        return formatted.replace("X", ".")
    return str(valor)

def calcular_evolucao_raw(valor_atual, valor_anterior):
    """Calcula a evolução percentual (raw) entre dois valores."""
    if valor_anterior > 0:
        return (valor_atual / valor_anterior) - 1
    elif valor_atual > 0:
        return 1.0 # Crescimento total
    return 0.0 # Estável/Zero

def formatar_evolucao_texto(crescimento_raw):
    """Formata o valor raw de crescimento para texto com indicador (↑, ↓, ≈)."""
    if isinstance(crescimento_raw, (float, int)):
        if crescimento_raw > 0.0001:
            return f"{crescimento_raw:,.1%} ↑" 
        elif crescimento_raw < -0.0001:
            return f"{crescimento_raw:,.1%} ↓" 
        else:
            return "0.0% ≈"
    return "N/A"