from flask import Blueprint, request, jsonify, current_app
from src.security.auth import login_obrigatorio, pode_acessar_reembolso, sem_permissao
from src.utils.arquivos import arquivo_temporario, hash_bytes, mime_por_extensao
from src.utils.ocr_reader import processar_arquivo
from src.model.comprovante_model import Comprovante
from src.model.reembolso_model import Reembolso
from src.utils.validacao_ocr import validar_valores
from src.model import db
import os, uuid

# Blueprint com prefixo padrão
ocr_bp = Blueprint("ocr_bp", __name__, url_prefix='/ocr')


# -------------------------------
# CREATE - Upload e extração OCR
# -------------------------------
@ocr_bp.route("/", methods=["POST"])
@login_obrigatorio()
def ocr():
    if "file" not in request.files:
        return jsonify({"erro": "Arquivo não encontrado"}), 400

    file = request.files["file"]
    reembolso_id = request.form.get("reembolso_id")

    if not file.filename or file.filename.strip() == "":
        return jsonify({"erro": "Nome do arquivo vazio"}), 400

    if not reembolso_id:
        return jsonify({"erro": "ID do reembolso é obrigatório"}), 400

    extensao = os.path.splitext(file.filename)[1].lower()
    mime_type = mime_por_extensao(file.filename)
    if not mime_type:
        return jsonify({"erro": "Formato de arquivo inválido. Aceito apenas: PDF, JPG, JPEG, PNG"}), 400

    # Verifica se o reembolso existe e pertence ao usuário
    reembolso = Reembolso.query.get(reembolso_id)
    if not reembolso:
        return jsonify({"erro": "Reembolso não encontrado"}), 404
    if not pode_acessar_reembolso(reembolso):
        return sem_permissao()

    conteudo = file.read()
    if not conteudo:
        return jsonify({"erro": "Arquivo vazio"}), 400

    try:
        # OCR precisa de um arquivo em disco; ele é apagado logo depois
        with arquivo_temporario(conteudo, extensao) as caminho:
            resultado_ocr = processar_arquivo(caminho)

        texto = resultado_ocr['texto']
        valor_extraido = resultado_ocr['valor_extraido']

        # Valida o valor extraído contra o valor do reembolso
        validacao = None
        if valor_extraido:
            validacao = validar_valores(
                valor_solicitado=reembolso.valor_faturado,
                valor_extraido=valor_extraido,
                tolerancia=5.0
            )
            status_validacao = validacao['status']
            discrepancia = validacao['discrepancia']
        else:
            status_validacao = 'Pendente'
            discrepancia = None

        comprovante = Comprovante(
            nome_arquivo=f"{uuid.uuid4().hex}{extensao}",
            texto_extraido=texto,
            reembolso_id=reembolso.num_prestacao,
            valor_extraido=valor_extraido,
            status_validacao=status_validacao,
            discrepancia_percentual=discrepancia,
            hash_arquivo=hash_bytes(conteudo),
            arquivo=conteudo,
            mime_type=mime_type,
        )
        db.session.add(comprovante)
        db.session.flush()  # gera o id antes de vincular ao reembolso
        reembolso.comprovante_id = comprovante.id
        db.session.commit()

        return jsonify({
            "mensagem": "Comprovante processado com sucesso.",
            "comprovante": comprovante.to_dict(),
            "valores_encontrados": [float(v) for v in resultado_ocr['valores_encontrados']],
            "validacao": validacao or {"mensagem": "Valor não encontrado no comprovante"}
        }), 201

    except Exception as e:
        current_app.logger.exception("Erro ao processar comprovante")
        db.session.rollback()
        return jsonify({"erro": f"Erro ao processar comprovante: {str(e)}"}), 500


# -------------------------------
# READ - Listar comprovantes
# -------------------------------
@ocr_bp.route("/", methods=["GET"])
@login_obrigatorio('admin')
def listar_ocr():
    comprovantes = Comprovante.query.order_by(Comprovante.data_criacao.desc()).all()
    resultados = [
        {
            "id": c.id,
            "nome_arquivo": c.nome_arquivo,
            "texto_extraido": c.texto_extraido,
            "data_criacao": c.data_criacao.isoformat()
        }
        for c in comprovantes
    ]
    return jsonify(resultados), 200


# -------------------------------
# READ - Obter um comprovante
# -------------------------------
@ocr_bp.route("/<int:id>", methods=["GET"])
@login_obrigatorio()
def obter_ocr(id):
    comprovante = Comprovante.query.get(id)
    if not comprovante:
        return jsonify({"erro": "Comprovante não encontrado"}), 404
    reembolso = Reembolso.query.get(comprovante.reembolso_id)
    if not reembolso or not pode_acessar_reembolso(reembolso):
        return sem_permissao()

    return jsonify(comprovante.to_dict()), 200


# -------------------------------
# VALIDAÇÃO - Revalidar comprovante
# -------------------------------
@ocr_bp.route("/<int:id>/revalidar", methods=["POST"])
@login_obrigatorio('admin')
def revalidar_comprovante(id):
    """
    Revalida um comprovante comparando com o valor do reembolso
    Útil quando o valor do reembolso foi atualizado
    """
    try:
        comprovante = Comprovante.query.get(id)
        if not comprovante:
            return jsonify({"erro": "Comprovante não encontrado"}), 404
        
        reembolso = Reembolso.query.get(comprovante.reembolso_id)
        if not reembolso:
            return jsonify({"erro": "Reembolso não encontrado"}), 404
        
        if not comprovante.valor_extraido:
            return jsonify({"erro": "Comprovante sem valor extraído"}), 400
        
        # Revalida
        validacao = validar_valores(
            valor_solicitado=reembolso.valor_faturado,
            valor_extraido=comprovante.valor_extraido,
            tolerancia=5.0
        )
        
        # Atualiza status
        comprovante.status_validacao = validacao['status']
        comprovante.discrepancia_percentual = validacao['discrepancia']
        
        db.session.commit()
        
        return jsonify({
            "mensagem": "Comprovante revalidado com sucesso",
            "comprovante": comprovante.to_dict(),
            "validacao": validacao
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": str(e)}), 500
