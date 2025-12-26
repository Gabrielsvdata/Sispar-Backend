# Chatbot SISPAR - Documentação

## Visão Geral
Chatbot inteligente integrado ao SISPAR usando a API do Grok (xAI) para auxiliar usuários com consultas sobre reembolsos.

## Endpoints

### 1. POST /chatbot/message
Envia mensagem para o chatbot e recebe resposta contextualizada.

**Request Body:**
```json
{
  "message": "Quanto gastei este mês?",
  "history": [
    {"role": "user", "content": "Olá"},
    {"role": "assistant", "content": "Olá! Como posso ajudar?"}
  ],
  "colaborador_id": 3
}
```

**Response (200 OK):**
```json
{
  "response": "Você gastou R$ 450,00 este mês em 2 reembolsos.",
  "suggestions": [
    "Ver meus últimos reembolsos",
    "Quanto gastei este mês?",
    "Como solicitar novo reembolso?"
  ],
  "tokens_used": 234
}
```

**Validações:**
- Mensagem: max 2000 caracteres
- Histórico: max 10 mensagens
- Autenticação: obrigatória (colaborador_id ou header X-User-Id)

### 2. GET /chatbot/health
Verifica se o serviço está funcionando.

**Response (200 OK):**
```json
{
  "status": "ok",
  "service": "chatbot",
  "model": "grok-beta",
  "provider": "xAI"
}
```

## Capacidades do Chatbot

### 1. Consulta de Reembolsos
- Listar últimos reembolsos do usuário
- Filtrar por status (Aprovado, Rejeitado, Em análise)
- Mostrar detalhes (valor, data, tipo)

### 2. Estatísticas
- Contar reembolsos por status
- Calcular total do mês atual
- Mostrar último reembolso

### 3. Orientações
- Políticas de reembolso
- Limites por categoria
- Documentação necessária
- Prazo de solicitação (30 dias)

### 4. Suporte a Solicitações
- Como preencher formulário
- Tipos de despesa aceitos
- Regras de aprovação

## Políticas Configuradas

### Limites por Categoria
- **Combustível:** R$ 500/mês (nota fiscal obrigatória)
- **Alimentação:** R$ 300/mês (apenas viagens corporativas)
- **Hospedagem:** Pré-aprovação do gestor
- **Transporte:** Comprovante obrigatório
- **Estacionamento:** Ticket/recibo
- **Material Escritório:** Aprovação prévia

### Regras Gerais
- Comprovantes fiscais OBRIGATÓRIOS
- Prazo: 30 dias após despesa
- Valores acima de R$ 1.000: aprovação especial

## Integração Frontend

### Exemplo React
```javascript
const enviarMensagem = async (mensagem) => {
  try {
    const response = await fetch('http://localhost:5000/chatbot/message', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Id': localStorage.getItem('userId')
      },
      body: JSON.stringify({
        message: mensagem,
        history: conversaHistorico,
        colaborador_id: userId
      })
    });
    
    const data = await response.json();
    console.log('Resposta:', data.response);
    console.log('Sugestões:', data.suggestions);
  } catch (error) {
    console.error('Erro:', error);
  }
};
```

## Segurança Implementada

✅ Validação de autenticação (colaborador_id obrigatório)
✅ Limite de tamanho de mensagem (2000 chars)
✅ Limite de histórico (10 mensagens)
✅ Sanitização de inputs (remove < e >)
✅ Isolamento de dados (usuário só vê seus reembolsos)
✅ Timeout de 30 segundos nas requisições
✅ Tratamento robusto de erros
✅ Logs detalhados para debugging

## Credenciais API (Desenvolvimento)
- **Provider:** xAI (Grok)
- **Endpoint:** https://api.x.ai/v1/chat/completions
- **Modelo:** grok-beta
- **API Key:** Configurada no controller

**⚠️ IMPORTANTE:** Mover API key para variável de ambiente em produção!

## Exemplos de Uso

### Perguntas Suportadas
1. "Quais são meus últimos reembolsos?"
2. "Quanto gastei este mês?"
3. "Qual o status do reembolso #123?"
4. "Como solicitar reembolso de combustível?"
5. "Qual o limite para alimentação?"
6. "Meu reembolso foi aprovado?"
7. "Quantos reembolsos tenho em análise?"

### Detecção de Intenção
O sistema detecta automaticamente o tipo de consulta e busca dados relevantes:

- **Palavras-chave "reembolso"** → busca últimos reembolsos
- **Palavras-chave "quantos/status"** → retorna estatísticas
- **Palavras-chave "total/quanto/mês"** → calcula total mensal
- **Palavras-chave "último/recente"** → mostra último reembolso

## Monitoramento

### Logs
```bash
# Ver logs do chatbot
docker logs sispar_backend | grep "chatbot"

# Acompanhar em tempo real
docker logs -f sispar_backend
```

### Métricas
- Tokens usados por requisição
- Tempo de resposta
- Taxa de erro
- Queries por usuário

## Troubleshooting

### Erro: "Usuário não autenticado"
- Verificar se `colaborador_id` está sendo enviado
- Confirmar header `X-User-Id` (se usado)
- Validar integração com sistema de auth

### Erro: "Mensagem muito longa"
- Limitar input do usuário a 2000 caracteres
- Implementar truncamento no frontend

### Erro: "Timeout"
- API Grok pode estar sobrecarregada
- Verificar conexão de rede
- Aumentar timeout se necessário

### Erro: "Module not found: openai"
- Executar: `pip install openai==1.58.1`
- Reconstruir imagem Docker: `docker-compose build --no-cache backend`

## Deploy

### Variáveis de Ambiente Recomendadas
```env
GROK_API_KEY=sua_api_key_aqui
GROK_BASE_URL=https://api.x.ai/v1
GROK_MODEL=grok-beta
CHATBOT_MAX_MESSAGE_LENGTH=2000
CHATBOT_TIMEOUT=30
```

### Configuração Produção
1. Mover API key para variável de ambiente
2. Configurar rate limiting
3. Implementar cache de respostas comuns
4. Adicionar analytics/telemetria
5. Configurar alertas de erro

## Melhorias Futuras

### Funcionalidades
- [ ] Suporte a anexos (comprovantes)
- [ ] Histórico persistente de conversas
- [ ] Notificações proativas
- [ ] Multilíngue (EN/ES)
- [ ] Comandos rápidos (/help, /status)

### Performance
- [ ] Cache de contexto do banco
- [ ] Streaming de respostas
- [ ] Pré-processamento de queries comuns
- [ ] CDN para assets do chat

### Analytics
- [ ] Dashboard de uso
- [ ] Análise de sentimento
- [ ] Identificação de dúvidas recorrentes
- [ ] Métricas de satisfação
