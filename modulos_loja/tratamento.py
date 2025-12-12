import pandas as pd
import numpy as np
import re

# ==============================================================================
# FUNÇÕES DE FORMATAÇÃO NUMÉRICA E TEXTO
# ==============================================================================

def formatar_milhar_br(valor):
    """
    Formata um número para o padrão brasileiro (1.000.000).
    """
    if pd.isna(valor) or valor == '':
        return "0"
    try:
        valor = float(valor)
        return f"{valor:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(valor)

def formatar_documento(doc):
    """
    Formata CPF (XXX.XXX.XXX-XX) ou CNPJ (XX.XXX.XXX/XXXX-XX).
    Recebe apenas números como string ou int.
    """
    if pd.isna(doc): return ""
    doc = str(doc).strip()
    doc = re.sub(r'[^0-9]', '', doc) # Garante apenas números
    
    if len(doc) == 11: # CPF
        return f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
    elif len(doc) == 14: # CNPJ
        return f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
    return doc # Retorna original se não encaixar

def separate_documents(row):
    """Separa CPF e CNPJ se estiverem na mesma string."""
    if pd.isna(row): return None, None
    
    docs = str(row).replace('/', ' ').replace('-', ' ').split()
    cpfs = [d for d in docs if len(d) == 11]
    cnpjs = [d for d in docs if len(d) == 14]
    
    return (', '.join(cnpjs) if cnpjs else None), (', '.join(cpfs) if cpfs else None)

# ==============================================================================
# FUNÇÕES DE CÁLCULO DE EVOLUÇÃO
# ==============================================================================

def calcular_evolucao_pct(atual, anterior):
    """Calcula a porcentagem de crescimento entre dois valores."""
    if anterior == 0:
        return 1.0 if atual > 0 else 0.0
    return (atual - anterior) / anterior

# --- NOVAS FUNÇÕES ADICIONADAS PARA SUPORTAR A STORE_PAGE ---
def calcular_evolucao_raw(atual, anterior):
    """Alias para calcular_evolucao_pct (usado na loja única)."""
    return calcular_evolucao_pct(atual, anterior)

def formatar_evolucao_texto(val):
    """Retorna texto formatado com setas (ex: 10% ↑↑)."""
    if not isinstance(val, (int, float)): return "N/A"
    
    percent = f"{val:.1%}"
    if val > 0.0001:
        return f"{percent} ↑"
    elif val < -0.0001:
        return f"{percent} ↓"
    return "0.0% ≈"

def get_last_two_seasons(lista_temporadas):
    """Retorna as duas últimas temporadas de uma lista (ex: T10 e T9)."""
    if not lista_temporadas:
        return None
    
    # Ordena para garantir (T1, T2... T10)
    # Assume formato 'Temporada X'
    try:
        sorted_temps = sorted(lista_temporadas, key=lambda x: int(x.split(' ')[1]))
    except:
        sorted_temps = sorted(lista_temporadas)
        
    if len(sorted_temps) >= 2:
        t_atual = sorted_temps[-1]
        t_anterior = sorted_temps[-2]
        
        # Gera versões curtas (T10, T9)
        try:
            tx_atual = f"T{t_atual.split(' ')[1]}"
            tx_anterior = f"T{t_anterior.split(' ')[1]}"
        except:
            tx_atual = t_atual
            tx_anterior = t_anterior
            
        return t_atual, t_anterior, tx_atual, tx_anterior
    return None

# ==============================================================================
# FUNÇÕES DE ESTILIZAÇÃO (PANDAS STYLER)
# ==============================================================================

def style_total_pontuacao(row):
    """Negrito para linha total."""
    # Ajuste conforme a coluna que identifica o total no seu DF
    if 'Total' in str(row.name) or ('Mês' in row and row['Mês'] == 'Total'):
        return ['font-weight: bold; background-color: #f0f2f6'] * len(row)
    return [''] * len(row)

def style_nome_categoria(val):
    """Retorna cor baseada no nome da categoria."""
    colors = {
        'Diamante': 'color: #7c3aed; font-weight: bold', # Roxo
        'Esmeralda': 'color: #10b981; font-weight: bold', # Verde
        'Ruby': 'color: #ef4444; font-weight: bold', # Vermelho
        'Topázio': 'color: #38bdf8; font-weight: bold', # Azul
        'Pro': 'color: #94a3b8; font-weight: bold', # Cinza
        'Sem Categoria': 'color: #cbd5e1'
    }
    return colors.get(val, '')