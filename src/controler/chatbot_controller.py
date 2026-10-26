from flask import Blueprint, request, jsonify, g
from src.security.auth import login_obrigatorio
from openai import OpenAI
import os
from datetime import datetime
from src.model.reembolso_model import Reembolso
from src.model import db
from src.utils.modelos_groq import MODELOS_TEXTO, completar, escolher_modelo, sem_raciocinio
from functools import wraps

bp_chatbot = Blueprint('chatbot', __name__, url_prefix='/chatbot')

# Configurar cliente Groq
# Nota: A biblioteca OpenAI é compatível com a API do Groq
_client = None


def get_client():
    """Cria o cliente Groq só quando o chatbot é usado (a API sobe mesmo sem a chave)."""
    global _client
    if _client is None:
        chave = os.getenv('GROQ_API_KEY')
        if not chave:
            return None
        _client = OpenAI(
            api_key=chave,
            base_url="https://api.groq.com/openai/v1",
            max_retries=2,
            timeout=30.0
        )
    return _client


def _historico_seguro(historico):
    """Aceita do navegador só mensagens de usuário/assistente, em texto e com tamanho limitado."""
    if not isinstance(historico, list):
        return []
    seguro = []
    for item in historico[-10:]:
        if not isinstance(item, dict):
            continue
        papel = item.get('role')
        conteudo = item.get('content')
        if papel in ('user', 'assistant') and isinstance(conteudo, str) and conteudo.strip():
            seguro.append({'role': papel, 'content': conteudo[:2000]})
    return seguro

# System Prompt otimizado para o SISPAR
SYSTEM_PROMPT = """Você é o assistente virtual do SISPAR, sistema de reembolsos corporativo da Wilson Sons.

SUAS CAPACIDADES:
- Consultar reembolsos do usuário autenticado
- Verificar status (Aprovado, Rejeitado, Em análise)
- Calcular totais e estatísticas
- Explicar políticas de reembolso
- Orientar sobre documentação
- Ajudar no preenchimento de solicitações

POLÍTICAS DE REEMBOLSO:
- Combustível: até R$ 500/mês com nota fiscal
- Alimentação: até R$ 300/mês em viagens corporativas
- Hospedagem: requer pré-aprovação do gestor
- Transporte (táxi/Uber): com comprovante obrigatório
- Estacionamento: com ticket/recibo
- Material escritório: com aprovação prévia

TIPOS DE DESPESA ACEITOS:
- Combustível
- Alimentação
- Hospedagem
- Transporte
- Estacionamento
- Material de escritório

REGRAS IMPORTANTES:
- Comprovantes fiscais são OBRIGATÓRIOS
- Prazo para solicitação: 30 dias após a despesa
- Valores devem estar dentro dos limites por categoria
- Reembolsos acima de R$ 1000 precisam aprovação especial

INSTRUÇÕES DE COMPORTAMENTO:
- Seja objetivo e profissional
- Use português do Brasil claro
- Formate valores: R$ 1.234,56
- Formate datas: DD/MM/AAAA
- Se não souber, oriente a contatar RH
- Sempre confirme informações críticas
- Seja proativo sugerindo próximas ações
- Use os dados fornecidos do banco de dados
- Nunca invente informações que não possui
"""


def consultar_reembolsos_usuario(colaborador_id, status=None, limit=5):
    """Busca reembolsos do usuário no banco"""
    try:
        query = Reembolso.query.filter_by(id_colaborador=colaborador_id)
        
        if status:
            query = query.filter_by(status=status)
        
        reembolsos = query.order_by(Reembolso.data.desc()).limit(limit).all()
        
        if not reembolsos:
            return "Nenhum reembolso encontrado."
        
        resultado = []
        for r in reembolsos:
            data_formatada = r.data.strftime('%d/%m/%Y') if r.data else 'N/A'
            resultado.append(
                f"Reembolso #{r.num_prestacao} - {r.tipo_reembolso} - "
                f"R$ {r.despesa:,.2f} - {r.status} - {data_formatada}"
            )
        
        return "\n".join(resultado)
    except Exception as e:
        print(f"Erro ao consultar reembolsos: {e}")
        return "Erro ao buscar reembolsos."


def contar_reembolsos_por_status(colaborador_id):
    """Conta reembolsos agrupados por status"""
    try:
        aprovados = Reembolso.query.filter_by(
            id_colaborador=colaborador_id, 
            status='Aprovado'
        ).count()
        
        rejeitados = Reembolso.query.filter_by(
            id_colaborador=colaborador_id, 
            status='Rejeitado'
        ).count()
        
        em_analise = Reembolso.query.filter_by(
            id_colaborador=colaborador_id, 
            status='Em análise'
        ).count()
        
        total = aprovados + rejeitados + em_analise
        
        return {
            'aprovados': aprovados,
            'rejeitados': rejeitados,
            'em_analise': em_analise,
            'total': total
        }
    except Exception as e:
        print(f"Erro ao contar reembolsos: {e}")
        return None


def calcular_total_mes_atual(colaborador_id):
    """Calcula total de despesas do mês atual"""
    try:
        hoje = datetime.now()
        mes_atual = hoje.month
        ano_atual = hoje.year
        
        reembolsos = Reembolso.query.filter(
            Reembolso.id_colaborador == colaborador_id,
            db.extract('month', Reembolso.data) == mes_atual,
            db.extract('year', Reembolso.data) == ano_atual
        ).all()
        
        total = sum(r.despesa for r in reembolsos if r.despesa)
        quantidade = len(reembolsos)
        
        return f"Total do mês {mes_atual}/{ano_atual}: R$ {total:,.2f} em {quantidade} reembolso(s)"
    except Exception as e:
        print(f"Erro ao calcular total: {e}")
        return "Erro ao calcular total do mês."


def obter_ultimo_reembolso(colaborador_id):
    """Busca o último reembolso do usuário"""
    try:
        ultimo = Reembolso.query.filter_by(
            id_colaborador=colaborador_id
        ).order_by(Reembolso.data.desc()).first()
        
        if not ultimo:
            return "Você ainda não possui reembolsos."
        
        data_formatada = ultimo.data.strftime('%d/%m/%Y') if ultimo.data else 'N/A'
        return (
            f"Último reembolso: #{ultimo.num_prestacao}\n"
            f"Tipo: {ultimo.tipo_reembolso}\n"
            f"Valor: R$ {ultimo.despesa:,.2f}\n"
            f"Status: {ultimo.status}\n"
            f"Data: {data_formatada}\n"
            f"Empresa: {ultimo.empresa}"
        )
    except Exception as e:
        print(f"Erro ao buscar último reembolso: {e}")
        return "Erro ao buscar último reembolso."


def processar_contexto(colaborador_id, mensagem):
    """Detecta intenção e busca dados relevantes do banco"""
    contexto_partes = []
    mensagem_lower = mensagem.lower()
    
    # Detectar pergunta sobre reembolsos
    if any(palavra in mensagem_lower for palavra in 
           ['reembolso', 'reembolsos', 'solicitação', 'solicitações', 'solicitacao', 'solicitacoes']):
        reembolsos = consultar_reembolsos_usuario(colaborador_id, limit=3)
        contexto_partes.append(f"ÚLTIMOS REEMBOLSOS:\n{reembolsos}")
    
    # Detectar pergunta sobre status/contagem
    if any(palavra in mensagem_lower for palavra in 
           ['quantos', 'status', 'aprovado', 'rejeitado', 'análise', 'analise']):
        contagem = contar_reembolsos_por_status(colaborador_id)
        if contagem:
            contexto_partes.append(
                f"ESTATÍSTICAS:\n"
                f"Total: {contagem['total']} reembolsos\n"
                f"Aprovados: {contagem['aprovados']}\n"
                f"Rejeitados: {contagem['rejeitados']}\n"
                f"Em análise: {contagem['em_analise']}"
            )
    
    # Detectar pergunta sobre valores/totais
    if any(palavra in mensagem_lower for palavra in 
           ['total', 'quanto', 'gastei', 'mês', 'mes', 'valor']):
        total_mes = calcular_total_mes_atual(colaborador_id)
        contexto_partes.append(total_mes)
    
    # Detectar pergunta sobre último reembolso
    if any(palavra in mensagem_lower for palavra in 
           ['último', 'ultima', 'ultimo', 'recente']):
        ultimo = obter_ultimo_reembolso(colaborador_id)
        contexto_partes.append(ultimo)
    
    return "\n\n".join(contexto_partes) if contexto_partes else ""


@bp_chatbot.route('/message', methods=['POST', 'OPTIONS'])
@login_obrigatorio()
def enviar_mensagem():
    """
    Endpoint principal do chatbot
    Recebe mensagem do usuário e retorna resposta do Grok
    """
    # CORS preflight
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Pegar dados da requisição
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        mensagem_usuario = data.get('message', '').strip()
        historico = data.get('history', [])
        
        if not mensagem_usuario:
            return jsonify({'error': 'Mensagem vazia'}), 400
        
        # Validar tamanho da mensagem
        if len(mensagem_usuario) > 2000:
            return jsonify({'error': 'Mensagem muito longa (max 2000 caracteres)'}), 400
        
        # Sanitizar mensagem (remover caracteres perigosos)
        mensagem_usuario = mensagem_usuario.replace('<', '').replace('>', '')
        
        # O colaborador vem sempre do token, nunca do corpo da requisição
        colaborador_id = g.usuario_id

        client = get_client()
        if client is None:
            return jsonify({'error': 'Assistente indisponível: GROQ_API_KEY não configurada'}), 503
        
        # Buscar contexto relevante do banco de dados
        contexto_banco = processar_contexto(colaborador_id, mensagem_usuario)
        
        # Preparar mensagens para a API
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        
        # Adicionar histórico (limitar a 10 últimas mensagens, só usuário/assistente)
        mensagens.extend(_historico_seguro(historico))
        
        # Adicionar contexto do banco se houver
        if contexto_banco:
            mensagens.append({
                "role": "system",
                "content": f"DADOS DO USUÁRIO (ID: {colaborador_id}):\n{contexto_banco}"
            })
        
        # Adicionar mensagem atual do usuário
        mensagens.append({
            "role": "user",
            "content": mensagem_usuario
        })
        
        # Chamar API do Groq com timeout
        completion = completar(
            client,
            escolher_modelo(client, MODELOS_TEXTO, 'GROQ_CHAT_MODEL'),
            messages=mensagens,
            temperature=0.7,
            max_tokens=1024,
            top_p=1.0,
            stream=False,
            timeout=30.0
        )
        
        # Extrair resposta
        resposta = sem_raciocinio(completion.choices[0].message.content)
        
        # Gerar sugestões de próximas perguntas
        sugestoes = [
            "Ver meus últimos reembolsos",
            "Quanto gastei este mês?",
            "Como solicitar novo reembolso?",
            "Qual o status do meu último reembolso?"
        ]
        
        # Retornar resposta
        return jsonify({
            'response': resposta,
            'suggestions': sugestoes[:3],
            'tokens_used': completion.usage.total_tokens if hasattr(completion, 'usage') else 0
        }), 200
        
    except Exception as e:
        print(f"Erro no chatbot: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'response': 'Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente ou contate o suporte.',
            'error': str(e)
        }), 500


@bp_chatbot.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar se o chatbot está funcionando"""
    return jsonify({
        'status': 'ok',
        'service': 'chatbot',
        'model': os.getenv('GROQ_CHAT_MODEL') or 'automático (primeiro disponível)',
        'provider': 'Groq'
    }), 200
