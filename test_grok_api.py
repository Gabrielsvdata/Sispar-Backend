"""
Script de teste para verificar API Key do Grok (xAI)
"""
from openai import OpenAI
import os

# Configurar cliente
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY não configurada. Defina a variável de ambiente GROQ_API_KEY")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.x.ai/v1"
)

def testar_api():
    try:
        print("Testando conexão com API Grok...")
        
        # Teste simples
        completion = client.chat.completions.create(
            model="grok-beta",
            messages=[
                {"role": "system", "content": "Você é um assistente útil."},
                {"role": "user", "content": "Olá, responda apenas: OK"}
            ],
            max_tokens=50
        )
        
        resposta = completion.choices[0].message.content
        print(f"✅ SUCESSO! Resposta: {resposta}")
        print(f"Tokens usados: {completion.usage.total_tokens}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        print(f"Tipo: {type(e).__name__}")
        
        # Detalhes do erro
        if hasattr(e, 'response'):
            print(f"Response: {e.response}")
        if hasattr(e, 'body'):
            print(f"Body: {e.body}")
            
        return False

if __name__ == "__main__":
    resultado = testar_api()
    exit(0 if resultado else 1)
