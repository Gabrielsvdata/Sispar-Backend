"""
Análise de comprovante com IA (Groq, modelo de visão).

Divisão de responsabilidades:
- A IA só LÊ o comprovante e devolve os dados que enxerga (valor, data, CNPJ, categoria...).
- As VALIDAÇÕES e o score são calculados aqui em Python, com regras fixas.
  Assim o mesmo comprovante gera sempre o mesmo resultado, e o número que pesa na
  aprovação não depende do modelo acertar uma conta.
"""

import base64
import io
import json
import os
from datetime import date, datetime

from PIL import Image

from src.utils.arquivos import arquivo_temporario

MODELO_VISAO = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
LADO_MAXIMO_IMAGEM = 1600
TOLERANCIA_VALOR_PERCENTUAL = 5.0
DIAS_MAXIMOS_COMPROVANTE = 90

CATEGORIAS = [
    "Alimentação",
    "Combustível",
    "Condução",
    "Estacionamento",
    "Hospedagem",
    "Passagem",
    "Outro",
]

PROMPT_EXTRACAO = f"""Você é um leitor de comprovantes fiscais brasileiros.
Extraia APENAS o que está visível na imagem. Não calcule, não compare e não julgue o reembolso.
Se um campo não estiver visível, use null.

Responda somente com um objeto JSON com exatamente estas chaves:
{{
  "valor_total": número em reais (ex.: 150.5) ou null,
  "data_emissao": "AAAA-MM-DD" ou null,
  "cnpj": texto ou null,
  "razao_social": texto ou null,
  "itens": lista de textos curtos (no máximo 10),
  "forma_pagamento": texto ou null,
  "numero_nota": texto ou null,
  "categoria_estabelecimento": um destes valores: {", ".join(CATEGORIAS)},
  "comprovante_legivel": true ou false,
  "sinais_de_edicao": true ou false,
  "observacoes": texto curto ou null
}}"""


def _cliente_groq():
    from openai import OpenAI

    chave = os.getenv("GROQ_API_KEY")
    if not chave:
        return None
    return OpenAI(api_key=chave, base_url="https://api.groq.com/openai/v1", max_retries=1, timeout=45.0)


def _imagem_para_data_url(conteudo: bytes, mime_type: str) -> str:
    """Converte PDF (primeira página) ou imagem num JPEG reduzido em base64."""
    if mime_type == "application/pdf":
        from pdf2image import convert_from_path

        with arquivo_temporario(conteudo, ".pdf") as caminho:
            paginas = convert_from_path(caminho, dpi=150, first_page=1, last_page=1)
        imagem = paginas[0]
    else:
        imagem = Image.open(io.BytesIO(conteudo))

    imagem = imagem.convert("RGB")
    imagem.thumbnail((LADO_MAXIMO_IMAGEM, LADO_MAXIMO_IMAGEM))
    saida = io.BytesIO()
    imagem.save(saida, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(saida.getvalue()).decode()


def _json_da_resposta(texto):
    """Lê o JSON da resposta, tolerando texto ou bloco de código em volta."""
    texto = (texto or "").strip()
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim == -1:
        return None
    return json.loads(texto[inicio:fim + 1])


def extrair_dados_com_ia(conteudo: bytes, mime_type: str):
    """
    Pede ao modelo de visão os dados do comprovante.
    Retorna (dados, None) em caso de sucesso ou (None, motivo) se a IA não estiver disponível.
    """
    cliente = _cliente_groq()
    if cliente is None:
        return None, "GROQ_API_KEY não configurada"

    try:
        data_url = _imagem_para_data_url(conteudo, mime_type)
        parametros = dict(
            model=MODELO_VISAO,
            temperature=0,
            max_tokens=800,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT_EXTRACAO},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
        )
        try:
            resposta = cliente.chat.completions.create(response_format={"type": "json_object"}, **parametros)
        except Exception as erro:
            # Alguns modelos de visão não aceitam o modo JSON; tenta de novo sem ele
            if "response_format" not in str(erro) and "json" not in str(erro).lower():
                raise
            resposta = cliente.chat.completions.create(**parametros)
        dados = _json_da_resposta(resposta.choices[0].message.content)
        if not isinstance(dados, dict):
            return None, "Resposta da IA fora do formato esperado"
        return dados, None
    except Exception as erro:  # rede, limite de uso, modelo indisponível, JSON inválido
        return None, f"{type(erro).__name__}: {erro}"


# ─────────────────────────────────────────────────────────────
# Regras determinísticas
# ─────────────────────────────────────────────────────────────

def _numero(valor):
    try:
        return float(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None


def _data(texto):
    if not texto:
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(texto)[:10], formato).date()
        except ValueError:
            continue
    return None


def categoria_compativel(categoria, tipo_reembolso) -> bool:
    """Compara a categoria lida pela IA com o tipo declarado. Na dúvida, não penaliza."""
    if not categoria or categoria == "Outro" or not tipo_reembolso:
        return True
    tipo = tipo_reembolso.lower()
    categoria = categoria.lower()
    if tipo.startswith("viagem"):
        return categoria in {"hospedagem", "passagem", "alimentação", "condução", "combustível", "estacionamento"}
    if tipo.startswith("eventos"):
        return categoria in {"alimentação", "hospedagem"}
    return categoria == tipo


def montar_analise(dados_ia, reembolso, comprovante):
    """
    Monta dados extraídos, validações e sinais de fraude a partir do que a IA leu.
    Se a IA não respondeu, usa só o valor do OCR.
    """
    dados_ia = dados_ia or {}
    valor_declarado = _numero(reembolso.despesa) or _numero(reembolso.valor_faturado) or 0.0

    valor_lido = _numero(dados_ia.get("valor_total"))
    if valor_lido is None:
        valor_lido = _numero(comprovante.valor_extraido)

    if valor_lido and valor_declarado:
        divergencia = round(abs(valor_declarado - valor_lido) / valor_declarado * 100, 2)
    else:
        divergencia = 100.0
    valor_corresponde = bool(valor_lido) and divergencia <= TOLERANCIA_VALOR_PERCENTUAL

    data_emissao = _data(dados_ia.get("data_emissao"))
    data_solicitacao = reembolso.data.date() if reembolso.data else date.today()
    if data_emissao:
        dias = (data_solicitacao - data_emissao).days
        data_valida = 0 <= dias <= DIAS_MAXIMOS_COMPROVANTE
    else:
        data_valida = True  # data não legível não penaliza; outras regras cobrem

    categoria = dados_ia.get("categoria_estabelecimento")

    dados_extraidos = {
        "valor_total": valor_lido,
        "data_emissao": data_emissao.isoformat() if data_emissao else None,
        "cnpj": dados_ia.get("cnpj"),
        "razao_social": dados_ia.get("razao_social"),
        "itens": (dados_ia.get("itens") or [])[:10],
        "forma_pagamento": dados_ia.get("forma_pagamento"),
        "numero_nota": dados_ia.get("numero_nota"),
    }
    validacoes = {
        "valor_corresponde": valor_corresponde,
        "divergencia_percentual": divergencia,
        "data_valida": data_valida,
        "data_comprovante": dados_extraidos["data_emissao"],
        "tipo_despesa_correto": categoria_compativel(categoria, reembolso.tipo_reembolso),
        "tipo_detectado": categoria,
        "comprovante_legivel": bool(dados_ia.get("comprovante_legivel", bool(valor_lido))),
    }
    sinais_fraude = {
        "editado": bool(dados_ia.get("sinais_de_edicao", False)),
        "confianca_edicao": 0.6 if dados_ia.get("sinais_de_edicao") else 0.0,
    }
    return {
        "dados_extraidos": dados_extraidos,
        "validacoes": validacoes,
        "sinais_fraude": sinais_fraude,
        "observacoes": dados_ia.get("observacoes"),
    }
