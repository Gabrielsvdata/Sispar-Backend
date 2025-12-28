from flask import Flask, redirect
from src.controler.colaborador_controller import bp_colaborador
from src.controler.reembolso_controler import bp_reembolso
from src.controler.ocr_controller import ocr_bp
from src.controler.chatbot_controller import bp_chatbot
from src.controler.analise_ia_controller import bp_analise_ia
from src.model import db
from config import get_config
from flask_cors import CORS
from flasgger import Swagger, LazyJSONEncoder
import os

# Diretório para arquivos temporários (comprovantes)
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')

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
    "schemes": ["http"],
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
def create_app():
    app = Flask(__name__)

    # 1) Carrega as configurações baseado no ambiente (FLASK_ENV)
    app.config.from_object(get_config())

    # 2) Inicializa extensões
    db.init_app(app)
    CORS(app, resources={
        r"/*": {
            "origins": [
                "http://localhost:5173", 
                "http://localhost:3000", 
                "http://localhost:5000",
                "https://sispar-sign.vercel.app",
                "https://sispar-sign-git-main-gabrielsvdata.vercel.app",
                "https://projeto-sispar.vercel.app"
            ],
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

    # 6) Cria as tabelas no banco
    with app.app_context():
        db.create_all()

    return app
