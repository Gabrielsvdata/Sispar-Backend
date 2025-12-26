# Script de Teste do Chatbot SISPAR

## Teste 1: Health Check
```bash
curl http://localhost:5000/chatbot/health
```

**Resposta esperada:**
```json
{
  "status": "ok",
  "service": "chatbot",
  "model": "grok-beta",
  "provider": "xAI"
}
```

## Teste 2: Mensagem Simples (Python)

```python
import requests
import json

url = "http://localhost:5000/chatbot/message"

payload = {
    "message": "Olá, como você pode me ajudar?",
    "colaborador_id": 3,
    "history": []
}

headers = {
    "Content-Type": "application/json",
    "X-User-Id": "3"
}

response = requests.post(url, json=payload, headers=headers)
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
```

## Teste 3: Consultar Reembolsos (JavaScript)

```javascript
fetch('http://localhost:5000/chatbot/message', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-User-Id': '3'
  },
  body: JSON.stringify({
    message: 'Quais são meus últimos reembolsos?',
    colaborador_id: 3,
    history: []
  })
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error(err));
```

## Teste 4: Consultar Total do Mês (cURL)

```bash
curl -X POST http://localhost:5000/chatbot/message \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 3" \
  -d '{
    "message": "Quanto gastei este mês?",
    "colaborador_id": 3,
    "history": []
  }'
```

## Teste 5: Com Histórico de Conversa

```bash
curl -X POST http://localhost:5000/chatbot/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "E o status deles?",
    "colaborador_id": 3,
    "history": [
      {"role": "user", "content": "Mostre meus reembolsos"},
      {"role": "assistant", "content": "Você tem 3 reembolsos..."}
    ]
  }'
```

## Teste 6: Validação de Erro - Mensagem Vazia

```bash
curl -X POST http://localhost:5000/chatbot/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "",
    "colaborador_id": 3
  }'
```

**Resposta esperada:**
```json
{
  "error": "Mensagem vazia"
}
```

## Teste 7: Validação de Erro - Sem Autenticação

```bash
curl -X POST http://localhost:5000/chatbot/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Teste"
  }'
```

**Resposta esperada:**
```json
{
  "error": "Usuário não autenticado"
}
```

## Teste 8: Validação de Erro - Mensagem Longa

```python
import requests

url = "http://localhost:5000/chatbot/message"
mensagem_longa = "A" * 2001  # Mais de 2000 caracteres

response = requests.post(url, json={
    "message": mensagem_longa,
    "colaborador_id": 3
})

print(response.json())
# Esperado: {"error": "Mensagem muito longa (max 2000 caracteres)"}
```

## Perguntas de Exemplo para Testar

### Consultas sobre Reembolsos
1. "Mostre meus últimos reembolsos"
2. "Quais reembolsos foram aprovados?"
3. "Tenho algum reembolso rejeitado?"
4. "Qual o status do meu último reembolso?"

### Consultas sobre Valores
5. "Quanto gastei este mês?"
6. "Qual o total dos meus reembolsos?"
7. "Quanto já foi aprovado?"

### Consultas sobre Políticas
8. "Qual o limite para combustível?"
9. "Como solicitar reembolso de alimentação?"
10. "Preciso de nota fiscal?"
11. "Qual o prazo para solicitar reembolso?"

### Orientações Gerais
12. "Como preencher uma solicitação?"
13. "Quais tipos de despesa posso solicitar?"
14. "O que fazer se meu reembolso for rejeitado?"

## Script Python Completo para Testes

```python
import requests
import json

BASE_URL = "http://localhost:5000"
COLABORADOR_ID = 3

def testar_health():
    print("\n=== Teste 1: Health Check ===")
    response = requests.get(f"{BASE_URL}/chatbot/health")
    print(json.dumps(response.json(), indent=2))

def testar_mensagem(mensagem, history=[]):
    print(f"\n=== Testando: {mensagem[:50]}... ===")
    response = requests.post(
        f"{BASE_URL}/chatbot/message",
        headers={"Content-Type": "application/json"},
        json={
            "message": mensagem,
            "colaborador_id": COLABORADOR_ID,
            "history": history
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Resposta: {data['response']}")
        print(f"Tokens: {data.get('tokens_used', 'N/A')}")
        print(f"Sugestões: {', '.join(data.get('suggestions', []))}")
        return data
    else:
        print(f"Erro {response.status_code}: {response.text}")
        return None

def executar_testes():
    # Teste 1: Health Check
    testar_health()
    
    # Teste 2: Saudação
    testar_mensagem("Olá, como você pode me ajudar?")
    
    # Teste 3: Consultar reembolsos
    testar_mensagem("Mostre meus últimos reembolsos")
    
    # Teste 4: Consultar total
    testar_mensagem("Quanto gastei este mês?")
    
    # Teste 5: Consultar políticas
    testar_mensagem("Qual o limite para combustível?")
    
    # Teste 6: Orientação
    testar_mensagem("Como solicitar reembolso de alimentação?")
    
    # Teste 7: Status
    testar_mensagem("Quantos reembolsos tenho aprovados?")
    
    # Teste 8: Com histórico
    hist = [
        {"role": "user", "content": "Mostre meus reembolsos"},
        {"role": "assistant", "content": "Você tem 3 reembolsos registrados."}
    ]
    testar_mensagem("Qual o status deles?", history=hist)

if __name__ == "__main__":
    executar_testes()
```

## Monitoramento

### Ver logs em tempo real
```bash
docker logs -f sispar_backend | grep -i "chatbot\|grok\|openai"
```

### Ver apenas erros
```bash
docker logs sispar_backend | grep -i "error\|exception\|traceback"
```

## Troubleshooting

### Erro 400: API Key inválida
- Verificar se a API key está correta no arquivo `chatbot_controller.py`
- Confirmar que a API key tem permissões corretas
- Testar API key diretamente no console da xAI

### Erro 401: Usuário não autenticado
- Adicionar `colaborador_id` no body da requisição
- OU adicionar header `X-User-Id`

### Erro 500: Internal Server Error
- Verificar logs do Docker
- Confirmar que o banco de dados está acessível
- Verificar conectividade com API do Grok

### Timeout
- Aumentar timeout no controller (padrão: 30s)
- Verificar latência da rede
- Confirmar disponibilidade da API xAI
