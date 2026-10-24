from flask import Blueprint, request, jsonify, current_app, g
from src.model.colaborador_model import Colaborador
from src.model import db
from src.security.security import hash_senha, checar_senha
from src.security.auth import gerar_token, login_obrigatorio, carregar_usuario_opcional, eh_admin
from src.demo import CONTAS_DEMO, eh_conta_demo
from flasgger import swag_from
import os

bp_colaborador = Blueprint('colaborador', __name__, url_prefix='/colaborador')
DOCS_BASE = os.path.join(os.path.dirname(__file__), '../../docs/colaborador')

# -------------------------------
# CREATE - Cadastrar colaborador
# -------------------------------
@bp_colaborador.route('/cadastrar', methods=['OPTIONS', 'POST'])
@swag_from(os.path.join(DOCS_BASE, 'cadastrar_controller.yml'))
def cadastrar_novo_colaborador():
    if request.method == 'OPTIONS':
        return '', 200

    dados = request.get_json()
    if not dados:
        return jsonify({'mensagem': 'Payload da requisição está vazio ou não é JSON válido.'}), 400

    nome = dados.get('nome')
    email = dados.get('email')
    senha = dados.get('senha')
    tipo = dados.get('tipo', 'usuario')  # Default: 'usuario'

    if not nome or not email or not senha:
        return jsonify({'mensagem': 'Nome, email e senha são obrigatórios.'}), 400
    
    # Validação do campo 'tipo'
    if tipo not in ['usuario', 'admin']:
        return jsonify({'mensagem': "O campo 'tipo' deve ser 'usuario' ou 'admin'."}), 400

    # Cadastro público cria só colaborador comum; gestor só é criado por outro gestor logado
    carregar_usuario_opcional()
    if tipo == 'admin' and not eh_admin():
        return jsonify({'mensagem': 'Apenas gestores podem cadastrar outro gestor.'}), 403

    existente = db.session.execute(db.select(Colaborador).where(Colaborador.email == email)).scalar()
    if existente:
        return jsonify({'mensagem': 'Já existe um colaborador com este email.'}), 409

    try:
        novo = Colaborador(
            nome=nome,
            email=email,
            senha=hash_senha(senha),
            cargo=dados.get('cargo'),
            salario=dados.get('salario'),
            tipo=tipo
        )
        db.session.add(novo)
        db.session.commit()
        return jsonify({'mensagem': 'Colaborador cadastrado com sucesso'}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao cadastrar colaborador: {str(e)}", exc_info=True)
        return jsonify({'mensagem': 'Erro interno ao cadastrar. Tente novamente mais tarde.'}), 500

# -------------------------------
# READ - Listar todos os colaboradores
# -------------------------------
@bp_colaborador.route('/todos-colaboradores', methods=['GET'])
@swag_from(os.path.join(DOCS_BASE, 'pegar_todos_colaboradores.yml'))
@login_obrigatorio('admin')
def pegar_dados_todos_colaboradores():
    colaboradores = db.session.execute(db.select(Colaborador)).scalars().all()
    resultado = [col.all_data() for col in colaboradores]
    return jsonify(resultado), 200

# -------------------------------
# UPDATE - Atualizar colaborador
# -------------------------------
@bp_colaborador.route('/atualizar/<int:id_colaborador>', methods=['OPTIONS', 'PUT'])
@swag_from(os.path.join(DOCS_BASE, 'atualizar_controller.yml'))
def atualizar_dados_do_colaborador(id_colaborador):
    if request.method == 'OPTIONS':
        return '', 200

    dados = request.get_json()
    if not dados:
        return jsonify({'mensagem': 'Payload da requisição está vazio ou não é JSON válido.'}), 400

    colaborador = db.session.get(Colaborador, id_colaborador)
    if not colaborador:
        return jsonify({'mensagem': 'Colaborador não encontrado (crachá inválido).'}), 404

    if eh_conta_demo(colaborador):
        return jsonify({'mensagem': 'As contas de demonstração não podem ser alteradas.'}), 403

    email_para_verificacao = dados.get('email')
    nova_senha = dados.get('senha')
    recuperacao_de_senha = bool(email_para_verificacao and nova_senha and set(dados) <= {'email', 'senha'})

    # Fora da recuperação de senha, só o próprio colaborador ou um gestor podem alterar dados
    if not recuperacao_de_senha:
        carregar_usuario_opcional()
        if g.usuario_id is None:
            return jsonify({'mensagem': 'Faça login para continuar.'}), 401
        if not eh_admin() and g.usuario_id != colaborador.id:
            return jsonify({'mensagem': 'Você não tem permissão para alterar este colaborador.'}), 403

    try:
        campos_permitidos_para_atualizacao = {}

        if recuperacao_de_senha:
            if email_para_verificacao.lower() != colaborador.email.lower():
                return jsonify({'mensagem': 'O email fornecido não corresponde ao crachá informado.'}), 400
            campos_permitidos_para_atualizacao['senha'] = nova_senha
        else:
            # Salário e cargo só podem ser alterados por gestor
            campos_editaveis = ('nome', 'email', 'cargo', 'salario', 'senha') if eh_admin() else ('nome', 'email', 'senha')
            for campo_chave in campos_editaveis:
                if campo_chave in dados:
                    campos_permitidos_para_atualizacao[campo_chave] = dados[campo_chave]

        if not campos_permitidos_para_atualizacao:
            return jsonify({'mensagem': 'Nenhum dado válido fornecido para atualização.'}), 400

        for campo, valor in campos_permitidos_para_atualizacao.items():
            if campo == 'senha':
                setattr(colaborador, campo, hash_senha(valor))
            else:
                setattr(colaborador, campo, valor)

        db.session.commit()
        return jsonify({'mensagem': 'Dados do colaborador atualizados com sucesso!'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao atualizar dados do colaborador id {id_colaborador}: {str(e)}", exc_info=True)
        return jsonify({'mensagem': 'Erro interno ao atualizar dados.'}), 500

# -------------------------------
# DELETE - Remover colaborador
# -------------------------------
@bp_colaborador.route('/remover/<int:id_colaborador>', methods=['OPTIONS', 'DELETE'])
@swag_from(os.path.join(DOCS_BASE, 'remover_controller.yml'))
@login_obrigatorio('admin')
def remover_colaborador(id_colaborador):
    colaborador = db.session.get(Colaborador, id_colaborador)
    if not colaborador:
        return jsonify({'mensagem': 'Colaborador não encontrado'}), 404

    if eh_conta_demo(colaborador) or colaborador.id == g.usuario_id:
        return jsonify({'mensagem': 'Esta conta não pode ser removida.'}), 403

    db.session.delete(colaborador)
    db.session.commit()
    return jsonify({'mensagem': 'Colaborador removido com sucesso'}), 200

# -------------------------------
# EXTRA - Login de colaborador
# -------------------------------
@bp_colaborador.route('/login', methods=['POST'])
def login():
    dados_requisicao = request.get_json()
    email = dados_requisicao.get('email')
    senha = dados_requisicao.get('senha')

    if not email or not senha:
        return jsonify({'mensagem': 'Todos os dados precisam ser preenchidos'}), 400

    colaborador = db.session.execute(
        db.select(Colaborador).where(Colaborador.email == email)
    ).scalar()

    if not colaborador:
        return jsonify({'mensagem': 'Usuario não encontrado'}), 404

    if checar_senha(senha, colaborador.senha):
        return jsonify(_resposta_login(colaborador)), 200
    else:
        return jsonify({'mensagem': 'Credenciais invalidas'}), 400


def _resposta_login(colaborador):
    return {
        'mensagem': 'Login realizado com sucesso',
        'token': gerar_token(colaborador),
        'usuario': {
            'id': colaborador.id,
            'nome': colaborador.nome,
            'cargo': colaborador.cargo,
            'tipo': colaborador.tipo
        }
    }


# -------------------------------
# DEMO - Entrar como visitante
# -------------------------------
@bp_colaborador.route('/login-demo', methods=['POST', 'OPTIONS'])
def login_demo():
    """
    Entra numa conta de demonstração sem senha (só com DEMO_MODE=true).
    Body: {"perfil": "colaborador" | "gestor"}
    """
    if request.method == 'OPTIONS':
        return '', 200
    if not current_app.config.get('DEMO_MODE'):
        return jsonify({'mensagem': 'Modo demonstração desativado.'}), 404

    perfil = (request.get_json(silent=True) or {}).get('perfil', 'colaborador')
    conta = CONTAS_DEMO.get(perfil)
    if not conta:
        return jsonify({'mensagem': "Perfil deve ser 'colaborador' ou 'gestor'."}), 400

    colaborador = db.session.execute(
        db.select(Colaborador).where(Colaborador.email == conta['email'])
    ).scalar()
    if not colaborador:
        return jsonify({'mensagem': 'Conta de demonstração não encontrada. Rode o seed de demo.'}), 503

    return jsonify(_resposta_login(colaborador)), 200
