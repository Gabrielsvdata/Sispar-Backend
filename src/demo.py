"""
Contas de demonstração usadas por recrutadores e visitantes.

Com DEMO_MODE=true, a rota /colaborador/login-demo entrega um token dessas contas
sem senha, e elas ficam protegidas contra troca de senha e remoção.
"""

CONTAS_DEMO = {
    "colaborador": {
        "nome": "Visitante Colaborador",
        "email": "colaborador.demo@sispar.dev",
        "cargo": "Analista Comercial",
        "salario": 6500,
        "tipo": "usuario",
    },
    "gestor": {
        "nome": "Visitante Gestor",
        "email": "gestor.demo@sispar.dev",
        "cargo": "Gerente Financeiro",
        "salario": 14000,
        "tipo": "admin",
    },
}

EMAILS_DEMO = {conta["email"] for conta in CONTAS_DEMO.values()}


def eh_conta_demo(colaborador) -> bool:
    return bool(colaborador and colaborador.email and colaborador.email.lower() in EMAILS_DEMO)
