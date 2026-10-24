from flask import Flask, redirect, jsonify
from src.controler.colaborador_controller import bp_colaborador
from src.controler.reembolso_controler import bp_reembolso
from src.controler.ocr_controller import ocr_bp
from src.controler.chatbot_controller import bp_chatbot
from src.controler.analise_ia_controller import bp_analise_ia
from src.model import db
from config import get_config
from flask_cors import CORS
from flasgger import Swagger, LazyJSONEncoder

# Origens do front liberadas no CORS (as extras vêm da variável CORS_ORIGINS)
ORIGENS_PADRAO = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:5000",
    "https://projeto-sispar.vercel.app",
]

# -----------------------
# Swagger Template
# -----------------------
swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "API SISPAR",
        "description": "Documentação da API de Colaboradores, Reembolsos e OCR",
        "version": "1.0.0"
    },
    "basePath": "/",
    "schemes": ["https", "http"],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Token do login no formato: Bearer <token>"
        }
    },
    "security": [{"Bearer": []}],
}

# -----------------------
# Swagger Config
# -----------------------
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json/",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
}

# -----------------------
# Create App Factory
# -----------------------
def create_app(config_obj=None):
    app = Flask(__name__)

    # 1) Carrega as configurações baseado no ambiente (FLASK_ENV)
    app.config.from_object(config_obj or get_config())

    if not app.debug and not app.testing and app.config["SECRET_KEY"] == "chave-secreta-padrao":
        raise RuntimeError("Defina a variável SECRET_KEY em produção.")

    # 2) Inicializa extensões
    db.init_app(app)
    CORS(app, resources={
        r"/*": {
            "origins": ORIGENS_PADRAO + app.config.get("CORS_ORIGINS_EXTRAS", []),
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type"],
            "supports_credentials": True
        }
    })
    app.json_encoder = LazyJSONEncoder

    # 3) Swagger
    Swagger(app, config=swagger_config, template=swagger_template)

    # 4) Registra os blueprints
    app.register_blueprint(bp_colaborador)
    app.register_blueprint(bp_reembolso)
    app.register_blueprint(ocr_bp)
    app.register_blueprint(bp_chatbot)
    app.register_blueprint(bp_analise_ia)

    # 5) Redireciona / para /apidocs automaticamente
    @app.route('/')
    def redirect_to_docs():
        return redirect('/apidocs/')

    @app.route('/health')
    def health():
        return jsonify({'status': 'ok'}), 200

    @app.errorhandler(413)
    def arquivo_grande(_erro):
        return jsonify({'erro': 'Arquivo muito grande. Tamanho máximo: 10MB'}), 413

    # 6) Cria as tabelas no banco e, em modo demonstração, os dados de exemplo
    with app.app_context():
        _criar_tabelas()
        if app.config.get("DEMO_MODE") and not app.testing:
            from src.demo_seed import popular_demo
            try:
                if popular_demo():
                    app.logger.info("Dados de demonstração criados.")
            except Exception:
                db.session.rollback()
                app.logger.exception("Falha ao criar dados de demonstração")

    return app


def _criar_tabelas():
    """
    Cria as tabelas que ainda não existem.
    No Postgres, uma trava garante que só um processo faça isso por vez
    (vários workers do gunicorn ou instâncias do Cloud Run sobem juntos).
    """
    with db.engine.begin() as conexao:
        if conexao.dialect.name == "postgresql":
            conexao.execute(db.text("SELECT pg_advisory_xact_lock(424241)"))
        db.metadata.create_all(bind=conexao)
