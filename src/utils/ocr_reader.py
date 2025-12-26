import pytesseract
import os
import re
from PIL import Image
from pdf2image import convert_from_path
from decimal import Decimal

# Configuração do Tesseract
# Em ambiente Docker/Linux, o tesseract está no PATH
# Em Windows, descomente e ajuste o caminho abaixo:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Arquivos de Programas\Tesseract-OCR\tesseract.exe'
# os.environ['TESSDATA_PREFIX'] = r'C:\Arquivos de Programas\Tesseract-OCR'

def extrair_texto_imagem(caminho_imagem):
    """
    Extrai texto de uma imagem usando OCR
    """
    try:
        imagem = Image.open(caminho_imagem)
        texto = pytesseract.image_to_string(imagem, lang='por')
        return texto
    except Exception as e:
        return f"Erro ao processar OCR: {e}"


def extrair_texto_pdf(caminho_pdf):
    """
    Converte PDF para imagens e extrai texto de cada página
    """
    try:
        # Converte todas as páginas do PDF em imagens
        imagens = convert_from_path(caminho_pdf, dpi=300)
        texto_completo = ""
        
        for i, imagem in enumerate(imagens):
            texto_pagina = pytesseract.image_to_string(imagem, lang='por')
            texto_completo += f"\n--- Página {i+1} ---\n{texto_pagina}"
        
        return texto_completo
    except Exception as e:
        return f"Erro ao processar PDF: {e}"


def extrair_valores_monetarios(texto):
    """
    Extrai todos os valores monetários do texto usando regex
    Retorna uma lista de valores encontrados
    
    Padrões suportados:
    - R$ 123,45
    - 123,45
    - R$123.45
    - 1.234,56
    """
    # Padrões de valores monetários em português brasileiro
    padroes = [
        r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2}))',  # R$ 1.234,56
        r'R\$\s*(\d+,\d{2})',                        # R$ 123,45
        r'(?:^|\s)(\d{1,3}(?:\.\d{3})*,\d{2})(?:\s|$)',  # 1.234,56 (isolado)
        r'(?:total|valor|subtotal|importo)[\s:]+R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2})',  # Após palavras-chave
    ]
    
    valores_encontrados = []
    
    for padrao in padroes:
        matches = re.finditer(padrao, texto, re.IGNORECASE)
        for match in matches:
            valor_str = match.group(1)
            # Converte o formato brasileiro para decimal
            valor_str = valor_str.replace('.', '').replace(',', '.')
            try:
                valor = Decimal(valor_str)
                valores_encontrados.append(valor)
            except:
                continue
    
    return valores_encontrados


def encontrar_maior_valor(texto):
    """
    Encontra o maior valor monetário no texto
    Geralmente o maior valor é o total da nota fiscal
    """
    valores = extrair_valores_monetarios(texto)
    if valores:
        return max(valores)
    return None


def processar_arquivo(caminho_arquivo):
    """
    Processa arquivo (imagem ou PDF) e extrai texto e valores
    """
    extensao = os.path.splitext(caminho_arquivo)[1].lower()
    
    # Verifica se é PDF
    if extensao == '.pdf':
        texto = extrair_texto_pdf(caminho_arquivo)
    else:
        # Assume que é imagem (jpg, png, etc)
        texto = extrair_texto_imagem(caminho_arquivo)
    
    # Extrai o maior valor (provável valor total)
    valor_extraido = encontrar_maior_valor(texto)
    
    return {
        'texto': texto,
        'valor_extraido': valor_extraido,
        'valores_encontrados': extrair_valores_monetarios(texto)
    }
