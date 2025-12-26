from openai import OpenAI
import os

# Testar modelos disponíveis na Groq
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY não configurada. Defina a variável de ambiente GROQ_API_KEY")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

try:
    # Listar modelos disponíveis
    models = client.models.list()
    print("=== MODELOS DISPONÍVEIS NA GROQ ===\n")
    
    vision_models = []
    for model in models.data:
        print(f"ID: {model.id}")
        if 'vision' in model.id.lower():
            vision_models.append(model.id)
    
    print("\n=== MODELOS COM SUPORTE A VISÃO ===")
    if vision_models:
        for vm in vision_models:
            print(f"  - {vm}")
    else:
        print("  Nenhum modelo de visão encontrado na listagem")
        
except Exception as e:
    print(f"Erro: {e}")
