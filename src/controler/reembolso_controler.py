from flasgger import swag_from
from flask import Blueprint, request, jsonify
from src.model import db
from src.model.reembolso_model import Reembolso
from src.model.comprovante_model import Comprovante
from src.utils.validacao_ocr import verificar_validacao_automatica
import os

bp_reembolso = Blueprint('reembolso', __name__, url_prefix='/reembolsos/')
DOCS_BASE = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', 'reembolso')


# -------------------------------
# CREATE - Criar novo reembolso
# -------------------------------
@bp_reembolso.route('/new', methods=['POST'])
@swag_from(os.path.join(DOCS_BASE, 'cadastrar_reembolso.yml'))
def criar_reembolso():
    try:
        d = request.get_json()
        print(f"DEBUG - Dados recebidos: {d}")  # Debug
        
        if not d:
            return jsonify({'erro': 'Nenhum dado JSON recebido'}), 400
        
        # Validar campos obrigatórios
        campos_obrigatorios = ['colaborador', 'empresa', 'tipo_reembolso', 'centro_custo', 'valor_faturado', 'id_colaborador']
        campos_faltando = [campo for campo in campos_obrigatorios if campo not in d]
        
        if campos_faltando:
            return jsonify({'erro': f'Campos obrigatórios faltando: {", ".join(campos_faltando)}'}), 400
        
        comprovante_id = d.get('comprovante_id')

        if comprovante_id:
            comprovante = Comprovante.query.get(comprovante_id)
            if not comprovante:
                return jsonify({'erro': 'Comprovante não encontrado.'}), 400

        novo = Reembolso(
            colaborador=d['colaborador'],
            empresa=d['empresa'],
            descricao=d.get('descricao', ''),
            tipo_reembolso=d['tipo_reembolso'],
            centro_custo=d['centro_custo'],
            ordem_interna=d.get('ordem_interna'),
            divisao=d.get('divisao'),
            pep=d.get('pep'),
            moeda=d.get('moeda', 'BRL'),
            distancia_km=d.get('distancia_km'),
            valor_km=d.get('valor_km'),
            valor_faturado=d['valor_faturado'],
            despesa=d.get('despesa', 0),
            id_colaborador=d['id_colaborador'],
            comprovante_id=comprovante_id
        )
        db.session.add(novo)
        db.session.commit()
        return jsonify({'mensagem': 'Reembolso criado com sucesso!', 'reembolso': novo.to_dict()}), 201
    except KeyError as e:
        db.session.rollback()
        print(f"ERROR - Campo obrigatório faltando: {str(e)}")
        return jsonify({'erro': f'Campo obrigatório faltando: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        print(f"ERROR - Erro ao criar reembolso: {str(e)}")
        return jsonify({'erro': str(e)}), 400


# -------------------------------
# READ - Listar e buscar reembolsos
# -------------------------------
@bp_reembolso.route('/', methods=['GET'])
@swag_from(os.path.join(DOCS_BASE, 'listar_reembolsos.yml'))
def listar_reembolsos():
    try:
        status = request.args.get('status')
        num_prestacao = request.args.get('num_prestacao', type=int)
        colaborador_id = request.args.get('colaborador_id', type=int)

        query = Reembolso.query
        if status:
            query = query.filter_by(status=status)
        if num_prestacao:
            query = query.filter_by(num_prestacao=num_prestacao)
        if colaborador_id:
            query = query.filter_by(id_colaborador=colaborador_id)

        reembolsos = query.all()
        return jsonify([r.to_dict() for r in reembolsos]), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp_reembolso.route('/<int:num_prestacao>', methods=['GET', 'OPTIONS'], strict_slashes=False)
def buscar_reembolso(num_prestacao):
    if request.method == 'OPTIONS':
        return '', 200
    r = Reembolso.query.get(num_prestacao)
    if not r:
        return jsonify({'erro': 'Reembolso não encontrado.'}), 404
    return jsonify(r.to_dict()), 200


# -------------------------------
# UPDATE - Atualizar reembolso
# -------------------------------
@bp_reembolso.route('/<int:num_prestacao>', methods=['PUT', 'OPTIONS'], strict_slashes=False)
@swag_from(os.path.join(DOCS_BASE, 'atualizar_reembolso.yml'))
def atualizar_reembolso(num_prestacao):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        dados = request.get_json()
        r = Reembolso.query.get(num_prestacao)
        if not r:
            return jsonify({'erro': 'Reembolso não encontrado.'}), 404

        novo_comprovante_id = dados.get('comprovante_id')
        if novo_comprovante_id:
            comprovante = Comprovante.query.get(novo_comprovante_id)
            if not comprovante:
                return jsonify({'erro': 'Comprovante informado não existe.'}), 400
            r.comprovante_id = novo_comprovante_id

        for campo in (
            'colaborador', 'empresa', 'descricao', 'tipo_reembolso',
            'centro_custo', 'ordem_interna', 'divisao', 'pep',
            'moeda', 'distancia_km', 'valor_km', 'valor_faturado',
            'despesa', 'id_colaborador', 'status'
        ):
            if campo in dados:
                setattr(r, campo, dados[campo])

        db.session.commit()
        return jsonify({'mensagem': 'Reembolso atualizado com sucesso!', 'reembolso': r.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400


# -------------------------------
# DELETE - Remover reembolso
# -------------------------------
@bp_reembolso.route('/<int:num_prestacao>', methods=['DELETE', 'OPTIONS'], strict_slashes=False)
@swag_from(os.path.join(DOCS_BASE, 'remover_reembolso.yml'))
def remover_reembolso(num_prestacao):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        r = Reembolso.query.get(num_prestacao)
        if not r:
            return jsonify({'erro': 'Reembolso não encontrado.'}), 404
        
        # DELETAR COMPROVANTES ASSOCIADOS PRIMEIRO
        comprovantes = Comprovante.query.filter_by(reembolso_id=num_prestacao).all()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # /app
        for comp in comprovantes:
            # Remover arquivo físico se existir
            caminho_arquivo = os.path.join(base_dir, 'temp', comp.nome_arquivo)
            if os.path.exists(caminho_arquivo):
                try:
                    os.remove(caminho_arquivo)
                    print(f"DEBUG - Arquivo {comp.nome_arquivo} removido")
                except Exception as e:
                    print(f"AVISO - Erro ao remover arquivo {comp.nome_arquivo}: {e}")
            
            db.session.delete(comp)
        
        # DELETAR ANÁLISES IA ASSOCIADAS (se existir)
        from src.model.analise_ia_model import AnaliseIA
        analises = AnaliseIA.query.filter_by(num_prestacao=num_prestacao).all()
        for analise in analises:
            db.session.delete(analise)
        
        # AGORA PODE DELETAR O REEMBOLSO
        db.session.delete(r)
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Reembolso removido com sucesso!',
            'comprovantes_removidos': len(comprovantes),
            'analises_removidas': len(analises)
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


# -------------------------------
# EXTRA - Ações de status
# -------------------------------
@bp_reembolso.route('/<int:num_prestacao>/aprovar', methods=['PATCH', 'OPTIONS'], strict_slashes=False)
def aprovar_reembolso(num_prestacao):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        r = Reembolso.query.get(num_prestacao)
        if not r:
            return jsonify({'erro': 'Reembolso não encontrado.'}), 404
        r.status = 'Aprovado'
        db.session.commit()
        return jsonify({'mensagem': 'Reembolso aprovado com sucesso!', 'reembolso': r.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


@bp_reembolso.route('/<int:num_prestacao>/rejeitar', methods=['PATCH', 'OPTIONS'], strict_slashes=False)
def rejeitar_reembolso(num_prestacao):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        r = Reembolso.query.get(num_prestacao)
        if not r:
            return jsonify({'erro': 'Reembolso não encontrado.'}), 404
        r.status = 'Rejeitado'
        db.session.commit()
        return jsonify({'mensagem': 'Reembolso rejeitado com sucesso!', 'reembolso': r.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


@bp_reembolso.route('/<int:num_prestacao>/enviar-analise', methods=['PATCH'])
def enviar_para_analise(num_prestacao):
    """
    Envia reembolso para análise com validação automática de OCR
    """
    try:
        r = Reembolso.query.get(num_prestacao)
        if not r:
            return jsonify({'erro': 'Reembolso não encontrado.'}), 404
        
        # Busca o comprovante associado
        comprovante = None
        if r.comprovante_id:
            comprovante = Comprovante.query.get(r.comprovante_id)
        
        # Realiza validação automática
        resultado_validacao = verificar_validacao_automatica(r, comprovante)
        
        # Define status baseado na validação
        if resultado_validacao['pode_aprovar']:
            r.status = 'Pré-aprovado'  # Status intermediário que indica validação OCR passou
        else:
            r.status = 'Em análise'  # Requer análise manual
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Reembolso enviado para análise!',
            'reembolso': r.to_dict(),
            'validacao_ocr': resultado_validacao
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


# -------------------------------
# NOVO - Análise automática com OCR
# -------------------------------
@bp_reembolso.route('/<int:num_prestacao>/analisar', methods=['POST'])
def analisar_reembolso_ocr(num_prestacao):
    """
    Analisa reembolso automaticamente baseado no OCR do comprovante
    Retorna se pode ser aprovado automaticamente ou precisa análise manual
    """
    try:
        r = Reembolso.query.get(num_prestacao)
        if not r:
            return jsonify({'erro': 'Reembolso não encontrado.'}), 404
        
        # Busca o comprovante
        comprovante = None
        if r.comprovante_id:
            comprovante = Comprovante.query.get(r.comprovante_id)
        
        # Valida
        resultado = verificar_validacao_automatica(r, comprovante)
        
        resposta = {
            'reembolso': r.to_dict(),
            'validacao': resultado,
            'recomendacao': 'Aprovar automaticamente' if resultado['pode_aprovar'] else 'Análise manual necessária'
        }
        
        if comprovante:
            resposta['comprovante'] = comprovante.to_dict()
        
        return jsonify(resposta), 200
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
