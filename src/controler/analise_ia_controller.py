from flask import Blueprint, request, jsonify, send_file, current_app
from src.model import db
from src.model.reembolso_model import Reembolso
from src.model.comprovante_model import Comprovante
from src.model.analise_ia_model import AnaliseIA
from src.security.auth import login_obrigatorio, pode_acessar_reembolso, sem_permissao
from src.utils.arquivos import ler_arquivo_comprovante, hash_bytes
from src.utils.analise_comprovante import extrair_dados_com_ia, montar_analise, MODELO_VISAO
from src.utils.ia_utils import (
    detectar_duplicatas,
    analisar_historico_colaborador,
    analisar_padroes_comportamentais,
    calcular_score_confiabilidade,
    gerar_recomendacao
)
import io
import json
from datetime import datetime

bp_analise_ia = Blueprint('analise_ia', __name__, url_prefix='/reembolsos')


class AnaliseIndisponivel(Exception):
    """Reembolso sem comprovante ou arquivo para analisar."""


def executar_analise(reembolso):
    """
    Roda a análise completa de um reembolso e devolve (AnaliseIA, detalhes).

    1. A IA lê o comprovante (se disponível); senão, usa o valor do OCR.
    2. Validações, duplicatas, histórico e score são calculados em Python.
    """
    comprovante = Comprovante.query.filter_by(reembolso_id=reembolso.num_prestacao).first()
    if not comprovante:
        raise AnaliseIndisponivel('Comprovante não disponível para análise. Faça o upload do comprovante primeiro.')

    conteudo, mime_type = ler_arquivo_comprovante(comprovante)
    if not conteudo:
        raise AnaliseIndisponivel('Arquivo do comprovante não encontrado. Faça o upload novamente.')

    dados_ia, motivo_falha = extrair_dados_com_ia(conteudo, mime_type)
    if motivo_falha:
        current_app.logger.warning(f"Análise IA indisponível, usando OCR: {motivo_falha}")
    analise_comprovante = montar_analise(dados_ia, reembolso, comprovante)
    fonte = 'ia' if dados_ia else 'ocr'

    if not comprovante.hash_arquivo:
        comprovante.hash_arquivo = hash_bytes(conteudo)
    duplicatas = detectar_duplicatas(comprovante.hash_arquivo, reembolso.num_prestacao)

    historico = analisar_historico_colaborador(reembolso.id_colaborador)
    reembolsos_anteriores = Reembolso.query.filter_by(
        id_colaborador=reembolso.id_colaborador
    ).filter(Reembolso.num_prestacao != reembolso.num_prestacao).all()
    padroes = analisar_padroes_comportamentais(reembolso, reembolsos_anteriores)

    validacoes = analise_comprovante['validacoes']
    score, nivel_risco, alertas = calcular_score_confiabilidade(
        validacoes, duplicatas, padroes, analise_comprovante['sinais_fraude']
    )
    if fonte == 'ocr':
        alertas.append({
            'tipo': 'analise_sem_ia',
            'gravidade': 'baixa',
            'mensagem': 'Leitura por IA indisponível no momento; análise feita só com o OCR.',
            'confianca': 1.0
        })
    aprovacao_sugerida, motivo_sugestao = gerar_recomendacao(score, nivel_risco, alertas)

    versao_modelo = MODELO_VISAO if fonte == 'ia' else 'ocr-tesseract'
    analise = AnaliseIA(
        num_prestacao=reembolso.num_prestacao,
        score_confiabilidade=score,
        nivel_risco=nivel_risco,
        aprovacao_sugerida=aprovacao_sugerida,
        motivo_sugestao=motivo_sugestao,
        dados_ia=analise_comprovante['dados_extraidos'],
        alertas=alertas,
        validacoes=validacoes,
        historico_colaborador=historico,
        versao_modelo=versao_modelo[:50]
    )
    detalhes = {
        'fonte_leitura': fonte,
        'versao_modelo': versao_modelo,
        'alertas': alertas,
        'validacoes': validacoes,
        'dados_extraidos_ocr': analise_comprovante['dados_extraidos'],
        'observacoes_ia': analise_comprovante['observacoes'],
        'historico_colaborador': historico,
        'analise_padrao': padroes,
        'comprovantes_similares': [
            {'num_prestacao': d['reembolso_id'], 'nome_arquivo': d['nome_arquivo']} for d in duplicatas
        ],
    }
    return analise, detalhes


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bp_analise_ia.route('/<int:num_prestacao>/comprovante', methods=['GET', 'OPTIONS'])
@login_obrigatorio()
def obter_comprovante(num_prestacao):
    """
    GET /reembolsos/{num_prestacao}/comprovante
    Retorna o arquivo do comprovante (PDF ou imagem)
    """
    reembolso = Reembolso.query.get(num_prestacao)
    if not reembolso:
        return jsonify({'erro': 'Reembolso não encontrado'}), 404
    if not pode_acessar_reembolso(reembolso):
        return sem_permissao()

    comprovante = Comprovante.query.filter_by(reembolso_id=num_prestacao).first()
    if not comprovante:
        return jsonify({'erro': 'Comprovante não disponível'}), 400

    conteudo, mime_type = ler_arquivo_comprovante(comprovante)
    if not conteudo:
        return jsonify({'erro': 'Arquivo do comprovante não encontrado no servidor'}), 404

    extensao = '.pdf' if mime_type == 'application/pdf' else ('.png' if mime_type == 'image/png' else '.jpg')
    return send_file(
        io.BytesIO(conteudo),
        mimetype=mime_type or 'application/octet-stream',
        as_attachment=False,  # permite visualizar no navegador
        download_name=f"comprovante_{num_prestacao}{extensao}"
    )


@bp_analise_ia.route('/<int:num_prestacao>/analisar-ia', methods=['POST', 'OPTIONS'])
@login_obrigatorio('admin')
def analisar_reembolso_ia(num_prestacao):
    """
    POST /reembolsos/{num_prestacao}/analisar-ia
    Executa análise completa com IA do reembolso e comprovante
    """
    reembolso = Reembolso.query.get(num_prestacao)
    if not reembolso:
        return jsonify({'erro': 'Reembolso não encontrado'}), 404

    try:
        analise, detalhes = executar_analise(reembolso)
        db.session.add(analise)
        db.session.commit()
    except AnaliseIndisponivel as e:
        return jsonify({'erro': 'Comprovante não disponível para análise', 'mensagem': str(e)}), 404
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Erro na análise IA')
        return jsonify({'erro': str(e)}), 500

    return jsonify({
        'num_prestacao': num_prestacao,
        'score_confiabilidade': analise.score_confiabilidade,
        'nivel_risco': analise.nivel_risco,
        'aprovacao_sugerida': analise.aprovacao_sugerida,
        'motivo_sugestao': analise.motivo_sugestao,
        'recomendacao_ia': analise.motivo_sugestao,
        'timestamp_analise': datetime.now().isoformat(),
        **detalhes,
    }), 200


@bp_analise_ia.route('/analises-ia', methods=['GET', 'OPTIONS'])
@login_obrigatorio('admin')
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


@bp_analise_ia.route('/<int:num_prestacao>/aprovar-com-ia', methods=['POST', 'OPTIONS'])
@login_obrigatorio('admin')
def aprovar_com_ia(num_prestacao):
    """
    POST /reembolsos/{num_prestacao}/aprovar-com-ia
    Aprova baseado na recomendação da IA (registra que foi aprovação automática)
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json(silent=True) or {}
        
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
@login_obrigatorio('admin')
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
                
                try:
                    analise, _detalhes = executar_analise(reembolso)
                except AnaliseIndisponivel as e:
                    erros.append({'num_prestacao': num, 'erro': str(e)})
                    continue
                score = analise.score_confiabilidade
                aprovacao_sugerida = analise.aprovacao_sugerida

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

