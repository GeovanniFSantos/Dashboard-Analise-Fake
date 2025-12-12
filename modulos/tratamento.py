# Módulo: tratamento.py
import pandas as pd
import numpy as np

# ==============================================================================
# FUNÇÕES DE UTILIDADE E FORMATAÇÃO
# ==============================================================================
def formatar_milhar_br(valor):
    """Formata um número para o padrão brasileiro (separador de milhar ponto, sem casas decimais)."""
    try:
        # 1. Se for nulo ou vazio, retorna 0
        if valor is None or pd.isna(valor) or str(valor).strip() == '':
            return "0"
        
        # 2. Tenta converter para float, não importa se veio como texto ou int
        valor_float = float(valor)
        
        # 3. Formata primeiro no padrão americano (vírgula separa milhar)
        # Ex: 6859306.0 -> "6,859,306"
        texto_us = f"{valor_float:,.0f}"
        
        # 4. Troca os sinais para o padrão BR
        # "6,859,306" -> "6.859.306"
        texto_br = texto_us.replace(",", "X").replace(".", ",").replace("X", ".")
        
        return texto_br
        
    except Exception:
        # Se falhar a conversão (ex: o valor é "Erro"), retorna o texto original
        return str(valor)

def style_total_pontuacao(row):
    """Estilo para aplicar cor de fundo escuro e texto branco na linha 'Total'."""
    # Estilo da linha Total, verificando o nome do índice (ou o valor da primeira coluna se não for indexado)
    if row.name == 'Total' or (isinstance(row.iloc[0], str) and row.iloc[0] == 'Total'):
        return ['font-weight: bold;'] * len(row)
    return [''] * len(row)

def calcular_evolucao_pct(atual, anterior):
    if anterior > 0:
        return (atual / anterior) - 1
    elif atual > 0:
        return 1.0 # Crescimento de zero para um valor positivo (+100%)
    return 0.0 # Zero ou zero para zero

def style_nome_categoria(val):
    cores = {
        'Diamante': 'color: #004d80; font-weight: bold',  
        'Esmeralda': 'color: #4EC7A0; font-weight: bold', # Verde ajustado
        'Ruby': 'color: #9B111E; font-weight: bold', 
        'Topázio': 'color: #FFD700; font-weight: bold', 
        'Pro': 'color: #d3d3d3; font-weight: bold', 
    }
    return cores.get(val, '')

def formatar_documento(doc):
    """Formata CPF ou CNPJ com pontuação padrão brasileira."""
    if pd.isna(doc):
        return ''
    doc = str(doc).replace('.', '').replace('-', '').replace('/', '').strip()
    # Verifica se é um número limpo antes de formatar
    if not doc.isdigit():
        return str(doc)
        
    if len(doc) == 11: # CPF
        return f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
    elif len(doc) == 14: # CNPJ
        return f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
    return doc

def separate_documents(document_list_original):
    """Separa uma lista de documentos (CPF/CNPJ) em duas strings formatadas para exibição."""
    cpfs = []
    cnpjs = []
        
    for doc_original in document_list_original:
        if pd.isna(doc_original) or doc_original == 'nan': continue
            
        # 1. Clean document for reliable length check
        doc_limpo = str(doc_original).replace('.', '').replace('-', '').replace('/', '').replace(' ', '')
            
        # 2. Heuristic based on typical Brazilian document length
        if len(doc_limpo) >= 14: # Assume CNPJ if 14+ clean digits
            cnpjs.append(doc_original)
        elif len(doc_limpo) >= 10: # Assume CPF if 10-13 clean digits (11 standard)
            cpfs.append(doc_original)
            
    return ', '.join(cpfs), ', '.join(cnpjs)

# ==============================================================================
# NOVA FUNÇÃO DE REUSO: IDENTIFICAR ÚLTIMAS 2 TEMPORADAS SELECIONADAS
# ==============================================================================
def get_last_two_seasons(temporadas_selecionadas_exib: list) -> tuple | None: # <--- CORREÇÃO AQUI
    """
    Identifica as duas últimas temporadas em uma lista e retorna seus nomes
    completos e abreviados para exibição.
    """
    # 1. Filtra e ordena as temporadas pelo número
    temporadas_ordenadas = sorted(
        [t for t in temporadas_selecionadas_exib if t.startswith('Temporada')],
        key=lambda x: int(x.split(' ')[1])
    )

    if len(temporadas_ordenadas) >= 2:
        # 2. Seleciona as duas últimas
        t_atual_nome = temporadas_ordenadas[-1]
        t_anterior_nome = temporadas_ordenadas[-2]

        # 3. Cria as versões abreviadas para o texto (ex: T10)
        t_atual_tx = t_atual_nome.replace('Temporada ', 'T')
        t_anterior_tx = t_anterior_nome.replace('Temporada ', 'T')

        # Retorna na ordem (nome_completo_atual, nome_completo_anterior, nome_curto_atual, nome_curto_anterior)
        return t_atual_nome, t_anterior_nome, t_atual_tx, t_anterior_tx
    else:
        return None