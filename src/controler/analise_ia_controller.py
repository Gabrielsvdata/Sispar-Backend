from flask import Blueprint, request, jsonify, send_file, g
from src.model import db
from src.model.reembolso_model import Reembolso
from src.model.comprovante_model import Comprovante
from src.model.analise_ia_model import AnaliseIA
from src.utils.ia_utils import (
    calcular_hash_imagem,
    converter_para_base64,
    detectar_duplicatas,
    analisar_historico_colaborador,
    analisar_padroes_comportamentais,
    calcular_score_confiabilidade,
    gerar_recomendacao
)
import google.generativeai as genai
import os
import json
from datetime import datetime
from decimal import Decimal

bp_analise_ia = Blueprint('analise_ia', __name__, url_prefix='/reembolsos')

# Configurar Google Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'SUA_API_KEY_AQUI')  # Você vai definir no .env
genai.configure(api_key=GEMINI_API_KEY)


def analisar_sem_vision_api(comprovante, reembolso):
    """
    Análise de fallback sem Vision API - usa apenas dados do OCR
    """
    valor_extraido = float(comprovante.valor_extraido) if comprovante.valor_extraido else 0.0
    valor_declarado = float(reembolso.despesa) if reembolso.despesa else 0.0
    
    # Validação de valor - considera correspondente se diferença for <= 5%
    diferenca_percentual = abs(valor_declarado - valor_extraido) / valor_declarado * 100 if valor_declarado > 0 else 100
    valor_corresponde = diferenca_percentual <= 5 if valor_extraido > 0 else False
    
    return {
        'dados_extraidos': {
            'valor_total': valor_extraido,
            'data_emissao': None,
            'cnpj': None,
            'razao_social': None,
            'itens': [],
            'forma_pagamento': None,
            'numero_nota': None
        },
        'validacoes': {
            'valor_corresponde': valor_corresponde,
            'divergencia_percentual': round(diferenca_percentual, 2) if valor_declarado > 0 else 100.0,
            'data_valida': True,
            'data_comprovante': None,
            'estabelecimento_valido': False,
            'tipo_despesa_correto': False,
            'tipo_detectado': None,
            'comprovante_legivel': valor_extraido > 0,
            'qualidade_imagem': 0.5 if valor_extraido > 0 else 0.0
        },
        'sinais_fraude': {
            'editado': False,
            'confianca_edicao': 0.0,
            'inconsistencias_visuais': False,
            'layout_suspeito': False,
            'metadados_originais': True
        },
        'observacoes': 'Análise realizada apenas com OCR. Vision API indisponível. ' + 
                      (f'Valor extraído: R$ {valor_extraido:.2f}' if valor_extraido > 0 else 'Não foi possível extrair valor do comprovante.')
    }


def analisar_comprovante_gemini_vision(caminho_arquivo, reembolso):
    """
    Analisa comprovante usando Google Gemini Vision API
    FALLBACK: Se Vision API falhar, retorna análise baseada em OCR
    
    Args:
        caminho_arquivo: Path completo do arquivo de imagem
        reembolso: Objeto Reembolso com dados declarados
        
    Returns:
        Dict com dados extraídos e validações
    """
    try:
        # Montar prompt detalhado
        prompt = f"""Analise este comprovante fiscal brasileiro com extrema atenção aos detalhes para detectar possíveis fraudes.

DADOS DECLARADOS PELO USUÁRIO:
- Valor: R$ {reembolso.despesa}
- Data da solicitação: {reembolso.data.strftime('%d/%m/%Y') if reembolso.data else 'N/A'}
- Tipo de despesa: {reembolso.tipo_reembolso}
- Descrição: {reembolso.descricao or 'Não informada'}

TAREFAS DE ANÁLISE:

1. EXTRAÇÃO DE DADOS:
   - Valor total pago (em reais)
   - Data de emissão do documento
   - CNPJ do estabelecimento (se visível)
   - Nome/Razão social do estabelecimento
   - Itens/produtos/serviços (lista)
   - Forma de pagamento (se visível)
   - Número da nota fiscal (se houver)

2. VALIDAÇÕES:
   - O valor declarado ({reembolso.despesa}) corresponde ao valor do comprovante?
   - A data do comprovante é anterior ou igual à data da solicitação?
   - O tipo de estabelecimento corresponde ao tipo de despesa declarado ({reembolso.tipo_reembolso})?
   - O documento está legível e completo?
   - Há informações essenciais faltando?

3. DETECÇÃO DE FRAUDE:
   - Existem sinais de edição digital da imagem?
   - Existem inconsistências visuais (fontes diferentes, alinhamentos estranhos)?
   - A qualidade da imagem é suspeita (muito perfeita ou muito ruim)?
   - O layout do documento parece autêntico?

RESPONDA APENAS EM JSON no seguinte formato (sem markdown, sem backticks):
{{
  "dados_extraidos": {{
    "valor_total": 150.50,
    "data_emissao": "2025-12-20",
    "cnpj": "12.345.678/0001-90",
    "razao_social": "Nome do Estabelecimento",
    "itens": ["item 1", "item 2"],
    "forma_pagamento": "Débito",
    "numero_nota": "123456"
  }},
  "validacoes": {{
    "valor_corresponde": true,
    "divergencia_percentual": 0.0,
    "data_valida": true,
    "data_comprovante": "2025-12-20",
    "estabelecimento_valido": true,
    "tipo_despesa_correto": true,
    "tipo_detectado": "Combustível",
    "comprovante_legivel": true,
    "qualidade_imagem": 0.95
  }},
  "sinais_fraude": {{
    "editado": false,
    "confianca_edicao": 0.0,
    "inconsistencias_visuais": false,
    "layout_suspeito": false,
    "metadados_originais": true
  }},
  "observacoes": "Lista de observações importantes encontradas"
}}"""
        
        # Upload do arquivo para Gemini
        uploaded_file = genai.upload_file(caminho_arquivo)
        
        # Criar modelo Gemini (usando modelo disponível)
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Gerar resposta
        response = model.generate_content([prompt, uploaded_file])
        
        # Extrair e parsear resposta
        resposta_texto = response.text.strip()
        
        # Remover markdown se houver
        if resposta_texto.startswith('```'):
            resposta_texto = resposta_texto.split('```')[1]
            if resposta_texto.startswith('json'):
                resposta_texto = resposta_texto[4:]
        
        dados_ia = json.loads(resposta_texto)
        
        return dados_ia
    
    except json.JSONDecodeError as e:
        print(f"Erro ao parsear JSON da IA: {e}")
        print(f"Resposta recebida: {resposta_texto}")
        return {
            'erro': 'Resposta da IA não está em formato JSON válido',
            'dados_extraidos': {},
            'validacoes': {'comprovante_legivel': False},
            'sinais_fraude': {}
        }
    
    except Exception as e:
        print(f"Erro ao analisar com Gemini Vision: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'erro': str(e),
            'dados_extraidos': {},
            'validacoes': {},
            'sinais_fraude': {}
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bp_analise_ia.route('/<string:num_prestacao>/comprovante', methods=['GET', 'OPTIONS'])
def obter_comprovante(num_prestacao):
    """
    GET /reembolsos/{num_prestacao}/comprovante
    Retorna o arquivo do comprovante (PDF ou imagem)
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Buscar reembolso
        reembolso = Reembolso.query.filter_by(num_prestacao=num_prestacao).first()
        
        if not reembolso:
            return jsonify({'erro': 'Reembolso não encontrado'}), 404
        
        # Buscar comprovante
        comprovante = Comprovante.query.filter_by(reembolso_id=reembolso.num_prestacao).first()
        
        if not comprovante:
            return jsonify({'erro': 'Comprovante não disponível'}), 400
        
        # Caminho absoluto do arquivo
        # Em produção Docker: /app/temp/arquivo.png
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # /app
        caminho_arquivo = os.path.join(base_dir, 'temp', comprovante.nome_arquivo)
        
        print(f"DEBUG - Tentando abrir arquivo: {caminho_arquivo}")
        print(f"DEBUG - Arquivo existe: {os.path.exists(caminho_arquivo)}")
        
        if not os.path.exists(caminho_arquivo):
            return jsonify({
                'erro': 'Arquivo do comprovante não encontrado no servidor',
                'caminho_procurado': caminho_arquivo
            }), 404
        
        # Determinar tipo de arquivo
        extensao = os.path.splitext(comprovante.nome_arquivo)[1].lower()
        mime_type = 'application/pdf' if extensao == '.pdf' else 'image/jpeg'
        
        # Retornar arquivo
        return send_file(
            caminho_arquivo,
            mimetype=mime_type,
            as_attachment=False,  # Mudado para False para permitir visualização no navegador
            download_name=f"comprovante_{num_prestacao}{extensao}"
        )
    
    except Exception as e:
        print(f"Erro ao obter comprovante: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 500


@bp_analise_ia.route('/<string:num_prestacao>/analisar-ia', methods=['POST', 'OPTIONS'])
def analisar_reembolso_ia(num_prestacao):
    """
    POST /reembolsos/{num_prestacao}/analisar-ia
    Executa análise completa com IA do reembolso e comprovante
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        print(f"DEBUG - Iniciando análise IA do reembolso {num_prestacao}")
        
        # 1. BUSCAR DADOS
        reembolso = Reembolso.query.filter_by(num_prestacao=num_prestacao).first()
        
        if not reembolso:
            print(f"DEBUG - Reembolso {num_prestacao} não encontrado")
            return jsonify({'erro': 'Reembolso não encontrado'}), 404
        
        print(f"DEBUG - Reembolso encontrado: {reembolso.num_prestacao}")
        
        comprovante = Comprovante.query.filter_by(reembolso_id=reembolso.num_prestacao).first()
        
        if not comprovante:
            print(f"DEBUG - Comprovante não encontrado para reembolso {reembolso.num_prestacao}")
            return jsonify({
                'erro': 'Comprovante não disponível para análise',
                'mensagem': 'Você precisa fazer o upload do comprovante primeiro na tela de criação/edição do reembolso.'
            }), 404
        
        print(f"DEBUG - Comprovante encontrado: {comprovante.nome_arquivo}")
        
        # Caminho absoluto do arquivo
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # /app
        caminho_arquivo = os.path.join(base_dir, 'temp', comprovante.nome_arquivo)
        
        print(f"DEBUG - Caminho do arquivo: {caminho_arquivo}")
        
        if not os.path.exists(caminho_arquivo):
            print(f"DEBUG - Arquivo não encontrado em: {caminho_arquivo}")
            return jsonify({
                'erro': 'Arquivo do comprovante não encontrado no servidor',
                'mensagem': 'O arquivo foi removido ou perdido. Por favor, faça o upload do comprovante novamente.',
                'arquivo_esperado': comprovante.nome_arquivo,
                'caminho_procurado': caminho_arquivo
            }), 404
        
        print(f"DEBUG - Arquivo encontrado: {caminho_arquivo}")
        
        # 2. ANÁLISE COM GEMINI VISION API (com fallback para OCR)
        try:
            dados_ia = analisar_comprovante_gemini_vision(caminho_arquivo, reembolso)
            
            # Se Vision API falhou, usar fallback
            if 'erro' in dados_ia:
                print(f"AVISO - Vision API indisponível, usando análise baseada em OCR")
                dados_ia = analisar_sem_vision_api(comprovante, reembolso)
        except Exception as e:
            print(f"ERRO - Falha na análise Vision, usando fallback OCR: {e}")
            dados_ia = analisar_sem_vision_api(comprovante, reembolso)
        
        if 'erro' in dados_ia and 'decommissioned' not in str(dados_ia.get('erro', '')).lower():
            # Análise falhou por outro motivo
            print(f"AVISO - Análise IA falhou: {dados_ia['erro']}")
            return jsonify({
                'num_prestacao': num_prestacao,
                'score_confiabilidade': 50,
                'nivel_risco': 'medio',
                'aprovacao_sugerida': False,
                'motivo_sugestao': f"Análise IA falhou: {dados_ia['erro']}. Revisão manual necessária.",
                'erro_ia': dados_ia['erro'],
                'alertas': [{
                    'tipo': 'erro_analise',
                    'gravidade': 'alta',
                    'mensagem': 'Não foi possível completar análise automática',
                    'confianca': 1.0
                }]
            }), 500
        
        print(f"DEBUG - Dados IA extraídos com sucesso")
        
        # 3. DETECÇÃO DE DUPLICATAS
        if comprovante.hash_arquivo:
            duplicatas = detectar_duplicatas(comprovante.hash_arquivo, num_prestacao)
        else:
            # Calcular hash agora se não existir
            hash_novo = calcular_hash_imagem(caminho_arquivo)
            if hash_novo:
                comprovante.hash_arquivo = hash_novo
                db.session.commit()
                duplicatas = detectar_duplicatas(hash_novo, num_prestacao)
            else:
                duplicatas = []
        
        print(f"DEBUG - Duplicatas encontradas: {len(duplicatas)}")
        
        # 4. ANÁLISE DE HISTÓRICO DO COLABORADOR
        historico = analisar_historico_colaborador(reembolso.id_colaborador)
        print(f"DEBUG - Histórico do colaborador analisado")
        
        # 5. ANÁLISE DE PADRÕES COMPORTAMENTAIS
        reembolsos_anteriores = Reembolso.query.filter_by(
            id_colaborador=reembolso.id_colaborador
        ).filter(
            Reembolso.num_prestacao != num_prestacao
        ).all()
        
        padroes = analisar_padroes_comportamentais(reembolso, reembolsos_anteriores)
        print(f"DEBUG - Padrões comportamentais analisados")
        
        # 6. CALCULAR SCORE FINAL
        validacoes = dados_ia.get('validacoes', {})
        sinais_fraude = dados_ia.get('sinais_fraude', {})
        
        score, nivel_risco, alertas = calcular_score_confiabilidade(
            validacoes,
            duplicatas,
            padroes,
            sinais_fraude
        )
        
        print(f"DEBUG - Score calculado: {score}")
        
        # 7. GERAR RECOMENDAÇÃO
        aprovacao_sugerida, motivo_sugestao = gerar_recomendacao(score, nivel_risco, alertas)
        
        # 8. SALVAR ANÁLISE NO BANCO
        analise = AnaliseIA(
            num_prestacao=num_prestacao,
            score_confiabilidade=score,
            nivel_risco=nivel_risco,
            aprovacao_sugerida=aprovacao_sugerida,
            motivo_sugestao=motivo_sugestao,
            dados_ia=dados_ia.get('dados_extraidos', {}),
            alertas=alertas,
            validacoes=validacoes,
            historico_colaborador=historico
        )
        
        db.session.add(analise)
        db.session.commit()
        
        print(f"DEBUG - Análise salva no banco com ID {analise.id}")
        
        # 9. MONTAR RESPOSTA COMPLETA
        response = {
            'num_prestacao': num_prestacao,
            'score_confiabilidade': score,
            'nivel_risco': nivel_risco,
            'aprovacao_sugerida': aprovacao_sugerida,
            'motivo_sugestao': motivo_sugestao,
            'alertas': alertas,
            'validacoes': validacoes,
            'dados_extraidos_ocr': dados_ia.get('dados_extraidos', {}),
            'historico_colaborador': historico,
            'analise_padrao': padroes,
            'comprovantes_similares': [{'num_prestacao': d['reembolso_id'], 'nome_arquivo': d['nome_arquivo']} for d in duplicatas],
            'recomendacao_ia': motivo_sugestao,
            'timestamp_analise': datetime.now().isoformat(),
            'versao_modelo': 'gemini-1.5-pro'
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        print(f"Erro na análise IA: {e}")
        import traceback
        traceback.print_exc()
        
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


# Implementação continua no próximo arquivo...


@bp_analise_ia.route('/analises-ia', methods=['GET', 'OPTIONS'])
def listar_analises_ia():
    """
    GET /reembolsos/analises-ia?status=pendente&risco=alto&limit=50
    Lista reembolsos com análises IA (para dashboard)
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Parâmetros de filtro
        status_filtro = request.args.get('status', 'todos')
        risco_filtro = request.args.get('risco', 'todos')
        aprovacao_filtro = request.args.get('aprovacao_sugerida')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Query base
        query = db.session.query(AnaliseIA, Reembolso).join(
            Reembolso, AnaliseIA.num_prestacao == Reembolso.num_prestacao
        )
        
        # Aplicar filtros
        if risco_filtro != 'todos':
            query = query.filter(AnaliseIA.nivel_risco == risco_filtro)
        
        if aprovacao_filtro:
            query = query.filter(AnaliseIA.aprovacao_sugerida == (aprovacao_filtro.lower() == 'true'))
        
        # Contar totais
        total = query.count()
        
        # Estatísticas gerais
        todas_analises = AnaliseIA.query.all()
        analisados = len(todas_analises)
        
        todos_reembolsos = Reembolso.query.count()
        pendentes = todos_reembolsos - analisados
        
        por_risco = {
            'baixo': AnaliseIA.query.filter_by(nivel_risco='baixo').count(),
            'medio': AnaliseIA.query.filter_by(nivel_risco='medio').count(),
            'alto': AnaliseIA.query.filter_by(nivel_risco='alto').count()
        }
        
        # Buscar resultados paginados
        resultados = query.order_by(AnaliseIA.timestamp_analise.desc()).limit(limit).offset(offset).all()
        
        # Montar lista de reembolsos
        reembolsos = []
        for analise, reembolso in resultados:
            alertas = json.loads(analise.alertas) if analise.alertas else []
            
            reembolsos.append({
                'num_prestacao': reembolso.num_prestacao,
                'colaborador': reembolso.colaborador,
                'valor_faturado': float(reembolso.valor_faturado) if reembolso.valor_faturado else 0,
                'tipo_reembolso': reembolso.tipo_reembolso,
                'data': reembolso.data.isoformat() if reembolso.data else None,
                'status': reembolso.status,
                'score_confiabilidade': analise.score_confiabilidade,
                'nivel_risco': analise.nivel_risco,
                'aprovacao_sugerida': analise.aprovacao_sugerida,
                'total_alertas': len(alertas),
                'analisado_em': analise.timestamp_analise.isoformat() if analise.timestamp_analise else None
            })
        
        return jsonify({
            'total': total,
            'analisados': analisados,
            'pendentes': pendentes,
            'por_risco': por_risco,
            'reembolsos': reembolsos
        }), 200
    
    except Exception as e:
        print(f"Erro ao listar análises: {e}")
        return jsonify({'erro': str(e)}), 500


@bp_analise_ia.route('/<string:num_prestacao>/aprovar-com-ia', methods=['POST', 'OPTIONS'])
def aprovar_com_ia(num_prestacao):
    """
    POST /reembolsos/{num_prestacao}/aprovar-com-ia
    Aprova baseado na recomendação da IA (registra que foi aprovação automática)
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        # Buscar reembolso
        reembolso = Reembolso.query.filter_by(num_prestacao=num_prestacao).first()
        
        if not reembolso:
            return jsonify({'erro': 'Reembolso não encontrado'}), 404
        
        # Buscar análise IA
        analise = AnaliseIA.query.filter_by(num_prestacao=num_prestacao).order_by(AnaliseIA.timestamp_analise.desc()).first()
        
        if not analise:
            return jsonify({'erro': 'Análise IA não encontrada. Execute /analisar-ia primeiro'}), 400
        
        # Verificar se admin está aceitando recomendação
        aceitar_recomendacao = data.get('aceitar_recomendacao_ia', True)
        
        if aceitar_recomendacao and not analise.aprovacao_sugerida:
            return jsonify({
                'erro': 'IA não recomenda aprovação automática',
                'score': analise.score_confiabilidade,
                'nivel_risco': analise.nivel_risco,
                'motivo': analise.motivo_sugestao
            }), 400
        
        # Aprovar reembolso
        reembolso.status = 'Aprovado'
        
        # Adicionar observação sobre aprovação por IA
        observacao = data.get('observacao', f"Aprovado automaticamente por IA - Score {analise.score_confiabilidade}%")
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Reembolso aprovado com base na análise IA',
            'num_prestacao': num_prestacao,
            'status': reembolso.status,
            'score_ia': analise.score_confiabilidade,
            'observacao': observacao,
            'reembolso': reembolso.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao aprovar com IA: {e}")
        return jsonify({'erro': str(e)}), 500


@bp_analise_ia.route('/analisar-lote', methods=['POST', 'OPTIONS'])
def analisar_lote():
    """
    POST /reembolsos/analisar-lote
    Analisa múltiplos reembolsos de uma vez
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        if not data or 'nums_prestacao' not in data:
            return jsonify({'erro': 'Lista de nums_prestacao não fornecida'}), 400
        
        nums_prestacao = data['nums_prestacao']
        
        if not isinstance(nums_prestacao, list) or len(nums_prestacao) == 0:
            return jsonify({'erro': 'nums_prestacao deve ser um array não-vazio'}), 400
        
        if len(nums_prestacao) > 10:
            return jsonify({'erro': 'Máximo de 10 reembolsos por lote'}), 400
        
        inicio = datetime.now()
        
        resultados = []
        erros = []
        aprovacao_automatica = 0
        revisao_manual = 0
        
        for num in nums_prestacao:
            try:
                # Buscar reembolso
                reembolso = Reembolso.query.filter_by(num_prestacao=num).first()
                
                if not reembolso:
                    erros.append({'num_prestacao': num, 'erro': 'Reembolso não encontrado'})
                    continue
                
                comprovante = Comprovante.query.filter_by(reembolso_id=reembolso.num_prestacao).first()
                
                if not comprovante:
                    erros.append({'num_prestacao': num, 'erro': 'Comprovante não disponível'})
                    continue
                
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # /app
                caminho_arquivo = os.path.join(base_dir, 'temp', comprovante.nome_arquivo)
                
                if not os.path.exists(caminho_arquivo):
                    erros.append({'num_prestacao': num, 'erro': 'Arquivo não encontrado'})
                    continue
                
                # Executar análise (código simplificado, reaproveita lógica do endpoint principal)
                dados_ia = analisar_comprovante_gemini_vision(caminho_arquivo, reembolso)
                
                if 'erro' in dados_ia:
                    erros.append({'num_prestacao': num, 'erro': dados_ia['erro']})
                    continue
                
                # Cálculos básicos
                historico = analisar_historico_colaborador(reembolso.id_colaborador)
                reembolsos_anteriores = Reembolso.query.filter_by(id_colaborador=reembolso.id_colaborador).filter(Reembolso.num_prestacao != num).all()
                padroes = analisar_padroes_comportamentais(reembolso, reembolsos_anteriores)
                
                hash_arquivo = comprovante.hash_arquivo or calcular_hash_imagem(caminho_arquivo)
                duplicatas = detectar_duplicatas(hash_arquivo, num) if hash_arquivo else []
                
                score, nivel_risco, alertas = calcular_score_confiabilidade(
                    dados_ia.get('validacoes', {}),
                    duplicatas,
                    padroes,
                    dados_ia.get('sinais_fraude', {})
                )
                
                aprovacao_sugerida, motivo = gerar_recomendacao(score, nivel_risco, alertas)
                
                # Salvar análise
                analise = AnaliseIA(
                    num_prestacao=num,
                    score_confiabilidade=score,
                    nivel_risco=nivel_risco,
                    aprovacao_sugerida=aprovacao_sugerida,
                    motivo_sugestao=motivo,
                    dados_ia=dados_ia.get('dados_extraidos', {}),
                    alertas=alertas,
                    validacoes=dados_ia.get('validacoes', {}),
                    historico_colaborador=historico
                )
                
                db.session.add(analise)
                
                resultados.append({
                    'num_prestacao': num,
                    'score': score,
                    'aprovacao_sugerida': aprovacao_sugerida
                })
                
                if aprovacao_sugerida:
                    aprovacao_automatica += 1
                else:
                    revisao_manual += 1
            
            except Exception as e:
                erros.append({'num_prestacao': num, 'erro': str(e)})
        
        db.session.commit()
        
        fim = datetime.now()
        tempo_processamento = (fim - inicio).total_seconds()
        
        return jsonify({
            'total_solicitados': len(nums_prestacao),
            'analisados_com_sucesso': len(resultados),
            'erros': erros,
            'tempo_processamento_segundos': round(tempo_processamento, 2),
            'resumo': {
                'aprovacao_automatica_sugerida': aprovacao_automatica,
                'revisao_manual_necessaria': revisao_manual
            },
            'resultados': resultados
        }), 200
    
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao analisar lote: {e}")
        return jsonify({'erro': str(e)}), 500

