"""
Script para tornar um colaborador existente em administrador
Uso: python tornar_admin.py email@exemplo.com
"""

import sys
import os

# Adiciona o diretório raiz ao path para importar os módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.model import db
from src.model.colaborador_model import Colaborador
from src.app import create_app

def tornar_admin(email):
    """
    Torna um colaborador existente em administrador através do email
    
    Args:
        email: Email do colaborador
    """
    app = create_app()
    
    with app.app_context():
        # Busca o colaborador pelo email
        colaborador = db.session.execute(
            db.select(Colaborador).where(Colaborador.email == email)
        ).scalar()
        
        if not colaborador:
            print(f"❌ Erro: Colaborador com email '{email}' não encontrado.")
            return False
        
        # Verifica se já é admin
        if colaborador.tipo == 'admin':
            print(f"ℹ️  O colaborador '{colaborador.nome}' já é administrador.")
            return True
        
        # Atualiza para admin
        colaborador.tipo = 'admin'
        db.session.commit()
        
        print(f"✅ Sucesso! O colaborador '{colaborador.nome}' agora é administrador.")
        print(f"   ID: {colaborador.id}")
        print(f"   Email: {colaborador.email}")
        print(f"   Cargo: {colaborador.cargo}")
        print(f"   Tipo: {colaborador.tipo}")
        
        return True

def listar_admins():
    """Lista todos os administradores"""
    app = create_app()
    
    with app.app_context():
        admins = db.session.execute(
            db.select(Colaborador).where(Colaborador.tipo == 'admin')
        ).scalars().all()
        
        if not admins:
            print("ℹ️  Nenhum administrador encontrado.")
            return
        
        print(f"\n📋 Total de {len(admins)} administrador(es):\n")
        for admin in admins:
            print(f"  • {admin.nome} ({admin.email})")
            print(f"    ID: {admin.id} | Cargo: {admin.cargo}")
            print()

def remover_admin(email):
    """
    Remove privilégios de admin de um colaborador
    
    Args:
        email: Email do colaborador
    """
    app = create_app()
    
    with app.app_context():
        colaborador = db.session.execute(
            db.select(Colaborador).where(Colaborador.email == email)
        ).scalar()
        
        if not colaborador:
            print(f"❌ Erro: Colaborador com email '{email}' não encontrado.")
            return False
        
        if colaborador.tipo != 'admin':
            print(f"ℹ️  O colaborador '{colaborador.nome}' não é administrador.")
            return True
        
        colaborador.tipo = 'usuario'
        db.session.commit()
        
        print(f"✅ Privilégios de admin removidos de '{colaborador.nome}'.")
        return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso do script:")
        print("  python tornar_admin.py <email>           - Torna o colaborador admin")
        print("  python tornar_admin.py --listar          - Lista todos os admins")
        print("  python tornar_admin.py --remover <email> - Remove privilégios de admin")
        print("\nExemplos:")
        print("  python tornar_admin.py joao@empresa.com")
        print("  python tornar_admin.py --listar")
        print("  python tornar_admin.py --remover maria@empresa.com")
        sys.exit(1)
    
    if sys.argv[1] == "--listar":
        listar_admins()
    elif sys.argv[1] == "--remover":
        if len(sys.argv) < 3:
            print("❌ Erro: Forneça o email do colaborador.")
            print("Uso: python tornar_admin.py --remover <email>")
            sys.exit(1)
        remover_admin(sys.argv[2])
    else:
        tornar_admin(sys.argv[1])
