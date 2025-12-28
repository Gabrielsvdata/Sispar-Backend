# config.py

from os import environ
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env (apenas local)
load_dotenv(".env")


class Config:
    """Configuração base compartilhada por todos os ambientes"""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = environ.get("SECRET_KEY", "chave-secreta-padrao")


class DevelopmentConfig(Config):
    """
    Ambiente de DESENVOLVIMENTO (sua máquina local)
    - Banco de dados local para testes
    - Debug ativado
    - Usado quando você está codando
    """
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = environ.get("URL_DATABASE_DEV", "sqlite:///dev.db")


class ProductionConfig(Config):
    """
    Ambiente de PRODUÇÃO (Render, AWS, etc.)
    - Banco de dados real na nuvem
    - Debug desativado por segurança
    - Usado pela aplicação real
    """
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = environ.get("URL_DATABASE_PROD")


class TestingConfig(Config):
    """
    Ambiente de TESTES (pytest, unittest)
    - Banco em memória para testes rápidos
    - Usado para rodar testes automatizados
    """
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


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
    
    No Render: FLASK_ENV=production (definido nas Environment Variables)
    Local: FLASK_ENV=development (definido no .env)
    """
    env = environ.get("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)  