from flask import Blueprint, request, jsonify
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
def ocr():
    print(f"DEBUG OCR - Files: {request.files}")
    print(f"DEBUG OCR - Form: {request.form}")
    
    if "file" not in request.files:
        print("ERROR OCR - Arquivo não encontrado no request.files")
        return jsonify({"erro": "Arquivo não encontrado"}), 400

    file = request.files["file"]
    reembolso_id = request.form.get("reembolso_id")
    
    print(f"DEBUG OCR - Filename: {file.filename}")
    print(f"DEBUG OCR - Reembolso ID: {reembolso_id}")
    
    if file.filename.strip() == "":
        return jsonify({"erro": "Nome do arquivo vazio"}), 400
    
    if not reembolso_id:
        return jsonify({"erro": "ID do reembolso é obrigatório"}), 400

    # Verifica se o reembolso existe
    reembolso = Reembolso.query.get(reembolso_id)
    if not reembolso:
        print(f"ERROR OCR - Reembolso {reembolso_id} não encontrado")
        return jsonify({"erro": "Reembolso não encontrado"}), 404
    
    print(f"DEBUG OCR - Reembolso encontrado: {reembolso.num_prestacao}")

    # Caminho absoluto para o diretório temp
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # /app
    temp_dir = os.path.join(base_dir, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    extensao = os.path.splitext(file.filename)[1]
    nome_arquivo = f"{uuid.uuid4().hex}{extensao}"
    caminho_temporario = os.path.join(temp_dir, nome_arquivo)

    try:
        # Salva o arquivo temporariamente
        file.save(caminho_temporario)
        print(f"DEBUG OCR - Arquivo salvo em: {caminho_temporario}")

        # Processa arquivo (PDF ou imagem) e extrai texto e valores
        print("DEBUG OCR - Iniciando processamento OCR...")
        resultado_ocr = processar_arquivo(caminho_temporario)
        print(f"DEBUG OCR - Resultado OCR: {resultado_ocr}")
        
        texto = resultado_ocr['texto']
        valor_extraido = resultado_ocr['valor_extraido']
        print(f"DEBUG OCR - Valor extraído: {valor_extraido}")

        # Valida o valor extraído contra o valor do reembolso
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

        # Salva no banco de dados
        comprovante = Comprovante(
            nome_arquivo=nome_arquivo,
            texto_extraido=texto,
            reembolso_id=reembolso_id,
            valor_extraido=valor_extraido,
            status_validacao=status_validacao,
            discrepancia_percentual=discrepancia
        )
        db.session.add(comprovante)
        
        # Atualiza o reembolso com o comprovante
        reembolso.comprovante_id = comprovante.id
        
        db.session.commit()

        return jsonify({
            "mensagem": "Comprovante processado com sucesso.",
            "comprovante": comprovante.to_dict(),
            "valores_encontrados": [float(v) for v in resultado_ocr['valores_encontrados']],
            "validacao": validacao if valor_extraido else {"mensagem": "Valor não encontrado no comprovante"}
        }), 201

    except Exception as e:
        print(f"DEBUG - EXCEPTION CAPTURADA: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"DEBUG - TRACEBACK:\n{traceback.format_exc()}")
        db.session.rollback()
        # Remove o arquivo se houver erro
        if os.path.exists(caminho_temporario):
            os.remove(caminho_temporario)
        return jsonify({"erro": f"Erro ao processar comprovante: {str(e)}"}), 500

    # Arquivo mantido para análise IA posterior
    # NÃO deletar: a IA precisa acessar o arquivo original


# -------------------------------
# READ - Listar comprovantes
# -------------------------------
@ocr_bp.route("/", methods=["GET"])
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
def obter_ocr(id):
    comprovante = Comprovante.query.get(id)
    if not comprovante:
        return jsonify({"erro": "Comprovante não encontrado"}), 404

    return jsonify(comprovante.to_dict()), 200


# -------------------------------
# VALIDAÇÃO - Revalidar comprovante
# -------------------------------
@ocr_bp.route("/<int:id>/revalidar", methods=["POST"])
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
