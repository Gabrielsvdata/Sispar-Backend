"""
Módulo de segurança para hash de senhas
"""

from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

def hash_senha(senha):
    """
    Gera hash de senha usando bcrypt
    
    Args:
        senha: Senha em texto plano
        
    Returns:
        Hash da senha
    """
    return bcrypt.generate_password_hash(senha).decode('utf-8')

def checar_senha(senha_plana, senha_hash):
    """
    Verifica se a senha corresponde ao hash
    
    Args:
        senha_plana: Senha em texto plano
        senha_hash: Hash armazenado no banco
        
    Returns:
        True se a senha está correta, False caso contrário
    """
    return bcrypt.check_password_hash(senha_hash, senha_plana)
