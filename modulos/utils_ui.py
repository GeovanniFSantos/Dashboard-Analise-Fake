# Módulo: utils_ui.py

def format_doc_mask(doc_original):
    """
    Aplica máscara simples a um CPF (11 dígitos) ou CNPJ (14 dígitos).
    Se o documento não for um formato padrão, retorna o original.
    """
    doc_str = str(doc_original).replace('.', '').replace('-', '').replace('/', '').replace(' ', '')
    
    if pd.isna(doc_original) or doc_str == 'nan' or not doc_str:
        return 'N/A'

    if len(doc_str) == 11:
        # CPF: 000.000.000-00
        return f"{doc_str[:3]}.{doc_str[3:6]}.{doc_str[6:9]}-{doc_str[9:]}"
    
    elif len(doc_str) == 14:
        # CNPJ: 00.000.000/0000-00
        return f"{doc_str[:2]}.{doc_str[2:5]}.{doc_str[5:8]}/{doc_str[8:12]}-{doc_str[12:]}"
    
    return doc_original # Retorna o original se não for 11 ou 14 dígitos