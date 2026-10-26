"""
Escolha de modelo no Groq.

O Groq aposenta modelos com frequência (o LLaMA 3.3 e o LLaMA 4 Scout saíram em 2026).
Em vez de fixar um só, cada uso tem uma lista de preferência e a API usa o primeiro
que a conta tiver disponível, consultado uma vez em /models e guardado em memória.
Uma variável de ambiente (GROQ_CHAT_MODEL / GROQ_VISION_MODEL) força um modelo.
"""

import os
import re

MODELOS_TEXTO = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "qwen/qwen3.6-27b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

# Modelos que aceitam imagem
MODELOS_VISAO = [
    "qwen/qwen3.8-27b",
    "qwen/qwen3.6-27b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
]

_disponiveis = None


def modelos_disponiveis(cliente):
    """IDs dos modelos liberados para a chave. Vazio se a consulta falhar."""
    global _disponiveis
    if _disponiveis is None:
        try:
            _disponiveis = {modelo.id for modelo in cliente.models.list().data}
        except Exception:
            return set()
    return _disponiveis


def escolher_modelo(cliente, preferidos, variavel):
    forcado = os.getenv(variavel, "").strip()
    if forcado:
        return forcado
    disponiveis = modelos_disponiveis(cliente)
    return next((m for m in preferidos if m in disponiveis), preferidos[0])


def _esforco_raciocinio(modelo):
    """Modelos com raciocínio gastam tokens pensando; aqui só precisamos da resposta."""
    if modelo.startswith("openai/gpt-oss"):
        return "low"
    if modelo.startswith("qwen/"):
        return "none"
    return None


def completar(cliente, modelo, **parametros):
    """
    Chama o chat do Groq. Se o modelo recusar algum parâmetro opcional
    (esforço de raciocínio ou modo JSON), tenta de novo sem ele.
    """
    tentativas = []
    esforco = _esforco_raciocinio(modelo)
    if esforco:
        tentativas.append({**parametros, "extra_body": {"reasoning_effort": esforco}})
    tentativas.append(parametros)
    if "response_format" in parametros:
        tentativas.append({k: v for k, v in parametros.items() if k != "response_format"})

    for numero, tentativa in enumerate(tentativas, start=1):
        try:
            return cliente.chat.completions.create(model=modelo, **tentativa)
        except Exception as erro:
            if getattr(erro, "status_code", None) != 400 or numero == len(tentativas):
                raise


def sem_raciocinio(texto):
    """Remove o bloco <think>...</think> que alguns modelos colocam antes da resposta."""
    return re.sub(r"<think>.*?</think>", "", texto or "", flags=re.S).strip()
