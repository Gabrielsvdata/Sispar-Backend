"""
Autenticação por token (JWT) e controle de acesso por perfil.

Fluxo:
- O login devolve um token assinado com SECRET_KEY.
- O front envia o token em todas as chamadas: Authorization: Bearer <token>.
- As rotas protegidas usam @login_obrigatorio() e leem o usuário em g.usuario_id / g.usuario_tipo.
"""

from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

ALGORITMO = "HS256"
PERFIL_ADMIN = "admin"


def gerar_token(colaborador) -> str:
    """Gera o token de acesso de um colaborador autenticado."""
    horas = current_app.config.get("TOKEN_EXPIRACAO_HORAS", 8)
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(colaborador.id),
        "tipo": colaborador.tipo or "usuario",
        "iat": agora,
        "exp": agora + timedelta(hours=horas),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm=ALGORITMO)


def _ler_token():
    """Lê e valida o token do cabeçalho. Retorna o payload ou None."""
    cabecalho = request.headers.get("Authorization", "")
    if not cabecalho.startswith("Bearer "):
        return None
    token = cabecalho.split(" ", 1)[1].strip()
    try:
        return jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=[ALGORITMO])
    except jwt.PyJWTError:
        return None


def carregar_usuario_opcional():
    """Preenche g.usuario_* se houver token válido, sem exigir login."""
    payload = _ler_token()
    g.usuario_id = int(payload["sub"]) if payload else None
    g.usuario_tipo = payload.get("tipo") if payload else None
    return payload


def login_obrigatorio(*perfis):
    """
    Exige um token válido. Se perfis forem informados, exige também um deles.

    Uso:
        @login_obrigatorio()          -> qualquer usuário logado
        @login_obrigatorio("admin")   -> apenas gestores
    """

    def decorador(funcao):
        @wraps(funcao)
        def envoltorio(*args, **kwargs):
            # Pré-requisição de CORS não carrega token
            if request.method == "OPTIONS":
                return "", 200

            payload = carregar_usuario_opcional()
            if not payload:
                return jsonify({"mensagem": "Faça login para continuar."}), 401

            if perfis and g.usuario_tipo not in perfis:
                return jsonify({"mensagem": "Você não tem permissão para esta ação."}), 403

            return funcao(*args, **kwargs)

        return envoltorio

    return decorador


def eh_admin() -> bool:
    return getattr(g, "usuario_tipo", None) == PERFIL_ADMIN


def pode_acessar_reembolso(reembolso) -> bool:
    """Gestor acessa tudo; colaborador acessa só os próprios reembolsos."""
    return eh_admin() or reembolso.id_colaborador == getattr(g, "usuario_id", None)


def sem_permissao():
    return jsonify({"mensagem": "Você não tem permissão para acessar este reembolso."}), 403
