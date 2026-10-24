"""
Cria ou recria os dados de demonstração do SisPar.

Uso (na raiz do projeto, com DATABASE_URL apontando para o banco):
    python scripts/seed_demo.py           # cria se ainda não existir
    python scripts/seed_demo.py --reset   # apaga os dados de demo e recria
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app  # noqa: E402
from src.demo_seed import popular_demo  # noqa: E402


def main():
    resetar = "--reset" in sys.argv
    app = create_app()
    with app.app_context():
        criado = popular_demo(resetar=resetar)
    print("Dados de demonstração criados." if criado else "Dados de demonstração já existiam (use --reset para recriar).")


if __name__ == "__main__":
    main()
