# config.py

from os import environ
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env (apenas local)
load_dotenv(".env")


def _url_banco(*nomes, padrao=None):
    """Lê a URL do banco da primeira variável preenchida e normaliza o esquema."""
    for nome in nomes:
        url = environ.get(nome)
        if url:
            # Neon/Heroku às vezes entregam "postgres://", que o SQLAlchemy não aceita
            return url.replace("postgres://", "postgresql://", 1)
    return padrao


def _lista(nome):
    return [item.strip() for item in environ.get(nome, "").split(",") if item.strip()]


class Config:
    """Configuração base compartilhada por todos os ambientes"""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Bancos serverless (Neon) derrubam conexões ociosas: testa antes de usar
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    SECRET_KEY = environ.get("SECRET_KEY", "chave-secreta-padrao")
    TOKEN_EXPIRACAO_HORAS = int(environ.get("TOKEN_EXPIRACAO_HORAS", "8"))

    # Limite de upload de comprovante (10 MB)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    # Origens extras liberadas no CORS, separadas por vírgula (ex.: URL do Cloudflare Pages)
    CORS_ORIGINS_EXTRAS = _lista("CORS_ORIGINS")

    # Modo demonstração: libera o login de visitante e protege as contas de demo
    DEMO_MODE = environ.get("DEMO_MODE", "false").lower() == "true"


class DevelopmentConfig(Config):
    """
    Ambiente de DESENVOLVIMENTO (sua máquina local)
    - Banco de dados local para testes
    - Debug ativado
    - Usado quando você está codando
    """
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _url_banco("URL_DATABASE_DEV", "DATABASE_URL", padrao="sqlite:///dev.db")


class ProductionConfig(Config):
    """
    Ambiente de PRODUÇÃO (Cloud Run, Render, etc.)
    - Banco de dados real na nuvem
    - Debug desativado por segurança
    - Usado pela aplicação real
    """
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _url_banco("DATABASE_URL", "URL_DATABASE_PROD")


class TestingConfig(Config):
    """
    Ambiente de TESTES (pytest, unittest)
    - Banco em memória para testes rápidos
    - Usado para rodar testes automatizados
    """
    TESTING = True
    SECRET_KEY = "chave-de-teste"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    DEMO_MODE = True


# Dicionário para selecionar o ambiente facilmente
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig
}


def get_config():
    """
    Retorna a configuração baseada na variável FLASK_ENV

    Produção: FLASK_ENV=production (definido nas variáveis do serviço)
    Local: FLASK_ENV=development (definido no .env)
    """
    env = environ.get("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)
