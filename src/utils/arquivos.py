"""
Leitura e escrita dos arquivos de comprovante.

O arquivo fica salvo no banco (coluna Comprovante.arquivo). Para comprovantes antigos,
enviados antes dessa mudança, ainda tenta a pasta temp/ do servidor.
"""

import hashlib
import os
import tempfile
from contextlib import contextmanager

PASTA_LEGADA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp")

TIPOS_PERMITIDOS = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def mime_por_extensao(nome_arquivo):
    return TIPOS_PERMITIDOS.get(os.path.splitext(nome_arquivo or "")[1].lower())


def hash_bytes(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def ler_arquivo_comprovante(comprovante):
    """Retorna (bytes, mime_type) do comprovante, ou (None, None) se não houver arquivo."""
    if comprovante.arquivo:
        return comprovante.arquivo, comprovante.mime_type or mime_por_extensao(comprovante.nome_arquivo)

    caminho = os.path.join(PASTA_LEGADA, comprovante.nome_arquivo)
    if os.path.exists(caminho):
        with open(caminho, "rb") as f:
            return f.read(), mime_por_extensao(comprovante.nome_arquivo)
    return None, None


@contextmanager
def arquivo_temporario(conteudo: bytes, extensao: str):
    """Grava os bytes num arquivo temporário (para OCR/conversão de PDF) e apaga ao sair."""
    descritor, caminho = tempfile.mkstemp(suffix=extensao)
    try:
        with os.fdopen(descritor, "wb") as f:
            f.write(conteudo)
        yield caminho
    finally:
        if os.path.exists(caminho):
            os.remove(caminho)
