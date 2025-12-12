# Módulo: config.py
# ==============================================================================
# 📌 PASSO 1: DEFINIÇÃO DO ARQUIVO E CONSTANTES
# ==============================================================================
# Nome do seu arquivo Excel, que deve estar na mesma pasta do app.py.
Relatorio = 'Relatorio.xlsx'
# Definimos as colunas numéricas que precisam ser tratadas
COLUNAS_NUMERICAS = ['Valor Total', 'Pontos']
# Coluna de temporada usada para filtrar (a numérica é mais confiável)
COLUNA_NUMERO_TEMPORADA = 'Numero Temporada'
# KPI de volume: Usaremos 'NF/Pedido' para contar o número de pedidos únicos
COLUNA_PEDIDO = 'NF/Pedido'
# KPI de volume: Usaremos 'CPF/CNPJ' para contar pessoas únicas na aba principal
COLUNA_CNPJ_CPF = 'CPF/CNPJ'
# Coluna de identificação do profissional
COLUNA_ESPECIFICADOR = 'Especificador/Empresa'
# NOVA CONSTANTE: Coluna de CPF na aba "Novos Cadastrados"
COLUNA_CPF_NOVO_CADASTRO = 'CPF'
# Constante de categorias definida globalmente para uso nas funções
CATEGORIAS_NOMES = ['Diamante', 'Esmeralda', 'Ruby', 'Topázio', 'Pro']

# NOVA CONSTANTE: Dicionário para ordenar meses de forma fiscal (Julho = 1)
MES_ORDEM_FISCAL = {
    'Jan (01)': 7, 'Fev (02)': 8, 'Mar (03)': 9, 'Abr (04)': 10,
    'Mai (05)': 11, 'Jun (06)': 12, 'Jul (07)': 1, 'Ago (08)': 2,
    'Set (09)': 3, 'Out (10)': 4, 'Nov (11)': 5, 'Dez (12)': 6
}

# NOVAS CONSTANTES PARA CONSOLIDAÇÃO DE ENTIDADES (Item 8)
NOME_ABA_MAP_CPF_CNPJ = 'Base de Mapeamento Completo' 
COLUNA_CHAVE_CONSOLIDADA = 'Chave_Consolidada'
# Coluna da Base de Mapeamento que será usada como a chave de vínculo (Nome Fantasia ou CNPJ Principal)
COLUNA_NOME_MAP_CONSOLIDACAO = 'Nome Fantasia'