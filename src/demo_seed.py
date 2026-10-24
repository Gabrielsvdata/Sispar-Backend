"""
Dados de demonstração do SisPar.

Cria as contas de visitante (colaborador e gestor), alguns colegas fictícios e
reembolsos com comprovantes gerados na hora, em vários status. Tudo fictício.

- Roda sozinho na subida da API quando DEMO_MODE=true e as contas ainda não existem.
- Para recriar do zero: python scripts/seed_demo.py --reset
"""

import io
import secrets
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont

from src.demo import CONTAS_DEMO, EMAILS_DEMO
from src.model import db
from src.model.analise_ia_model import AnaliseIA
from src.model.colaborador_model import Colaborador
from src.model.comprovante_model import Comprovante
from src.model.reembolso_model import Reembolso
from src.security.security import hash_senha
from src.utils.arquivos import hash_bytes

COLEGAS = [
    {"nome": "Marina Albuquerque", "email": "marina.demo@sispar.dev", "cargo": "Coordenadora de Operações", "salario": 9800},
    {"nome": "Rafael Tavares", "email": "rafael.demo@sispar.dev", "cargo": "Técnico de Campo", "salario": 5200},
]
EMAILS_SEED = EMAILS_DEMO | {c["email"] for c in COLEGAS}

# (dono, estabelecimento, tipo, valor declarado, valor no comprovante, dias atrás, status, itens)
REEMBOLSOS = [
    ("colaborador", "Restaurante Sabor da Serra", "Alimentação", 86.40, 86.40, 3, "Em análise",
     [("Prato executivo", 54.90), ("Suco natural", 12.50), ("Sobremesa", 19.00)]),
    ("colaborador", "Posto Rota 101", "Combustível", 250.00, 198.75, 6, "Em análise",
     [("Gasolina comum 33,5 L", 198.75)]),
    ("colaborador", "Centro Park Estacionamento", "Estacionamento", 32.00, 32.00, 12, "Aprovado",
     [("Permanência 4h", 32.00)]),
    ("colaborador", "Hotel Mirante do Porto", "Viagem Administrativa", 412.00, 412.00, 20, "Aprovado",
     [("Diária apartamento single", 380.00), ("Taxa de serviço", 32.00)]),
    ("colaborador", "Cooperativa Táxi Azul", "Condução", 74.00, 47.00, 28, "Rejeitado",
     [("Corrida aeroporto - centro", 47.00)]),
    ("marina", "Cantina Bella Nápoli", "Alimentação", 128.30, 128.30, 2, "Em análise",
     [("Massa ao sugo", 62.00), ("Risoto de cogumelos", 58.80), ("Água mineral", 7.50)]),
    ("marina", "Posto Serra Verde", "Combustível", 180.00, 180.00, 9, "Aprovado",
     [("Etanol 36 L", 180.00)]),
    ("rafael", "Auto Posto Litoral", "Combustível", 315.60, 315.60, 4, "Em análise",
     [("Diesel S10 52 L", 315.60)]),
    ("rafael", "Lanchonete Ponto Certo", "Alimentação", 39.90, 39.90, 15, "Aprovado",
     [("Lanche + refrigerante", 39.90)]),
]


def _fonte(tamanho):
    for caminho in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ):
        try:
            return ImageFont.truetype(caminho, tamanho)
        except OSError:
            continue
    return ImageFont.load_default()


def _real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_comprovante_png(estabelecimento, itens, total, data_emissao, numero):
    """Desenha um cupom fiscal fictício em PNG."""
    largura, altura = 620, 560 + 36 * len(itens)
    imagem = Image.new("RGB", (largura, altura), "white")
    d = ImageDraw.Draw(imagem)
    titulo, normal = _fonte(26), _fonte(20)

    y = 30
    d.text((largura // 2, y), estabelecimento.upper(), font=titulo, fill="black", anchor="ma")
    y += 44
    for linha in ("CNPJ 12.345.678/0001-90", "Rua das Palmeiras, 120 - Centro", "DOCUMENTO FICTÍCIO - DEMONSTRAÇÃO"):
        d.text((largura // 2, y), linha, font=normal, fill="black", anchor="ma")
        y += 30
    y += 10
    d.line((30, y, largura - 30, y), fill="black", width=2)
    y += 20
    d.text((30, y), f"CUPOM FISCAL Nº {numero:06d}", font=normal, fill="black")
    y += 30
    d.text((30, y), f"Emissão: {data_emissao.strftime('%d/%m/%Y %H:%M')}", font=normal, fill="black")
    y += 40
    for descricao, valor in itens:
        d.text((30, y), descricao[:30], font=normal, fill="black")
        d.text((largura - 30, y), _real(valor), font=normal, fill="black", anchor="ra")
        y += 36
    y += 10
    d.line((30, y, largura - 30, y), fill="black", width=2)
    y += 24
    d.text((30, y), "TOTAL", font=titulo, fill="black")
    d.text((largura - 30, y), _real(total), font=titulo, fill="black", anchor="ra")
    y += 50
    d.text((30, y), "Pagamento: Cartão de crédito", font=normal, fill="black")

    saida = io.BytesIO()
    imagem.save(saida, format="PNG")
    return saida.getvalue()


def _obter_ou_criar(dados, tipo):
    colaborador = db.session.execute(
        db.select(Colaborador).where(Colaborador.email == dados["email"])
    ).scalar()
    if colaborador:
        return colaborador
    colaborador = Colaborador(
        nome=dados["nome"],
        email=dados["email"],
        # Senha aleatória: as contas de demo entram pelo /colaborador/login-demo
        senha=hash_senha(secrets.token_urlsafe(24)),
        cargo=dados["cargo"],
        salario=dados["salario"],
        tipo=tipo,
    )
    db.session.add(colaborador)
    db.session.flush()
    return colaborador


def _apagar_dados_demo():
    ids = [
        c.id for c in db.session.execute(
            db.select(Colaborador).where(Colaborador.email.in_(EMAILS_SEED))
        ).scalars()
    ]
    if not ids:
        return
    reembolsos = Reembolso.query.filter(Reembolso.id_colaborador.in_(ids)).all()
    nums = [r.num_prestacao for r in reembolsos]
    for r in reembolsos:
        r.comprovante_id = None
    db.session.flush()
    if nums:
        AnaliseIA.query.filter(AnaliseIA.num_prestacao.in_(nums)).delete(synchronize_session=False)
        Comprovante.query.filter(Comprovante.reembolso_id.in_(nums)).delete(synchronize_session=False)
        Reembolso.query.filter(Reembolso.num_prestacao.in_(nums)).delete(synchronize_session=False)
    Colaborador.query.filter(Colaborador.id.in_(ids)).delete(synchronize_session=False)
    db.session.flush()


def demo_existe():
    email = CONTAS_DEMO["colaborador"]["email"]
    return db.session.execute(db.select(Colaborador).where(Colaborador.email == email)).scalar() is not None


def _travar_seed():
    """
    No Postgres, impede que dois processos (workers do gunicorn ou instâncias do
    Cloud Run) criem os dados de demonstração ao mesmo tempo. A trava é liberada no commit.
    """
    if db.engine.dialect.name == "postgresql":
        db.session.execute(db.text("SELECT pg_advisory_xact_lock(424242)"))


def popular_demo(resetar=False):
    """Cria (ou recria, com resetar=True) as contas e os reembolsos de demonstração."""
    _travar_seed()
    if resetar:
        _apagar_dados_demo()
    elif demo_existe():
        return False

    donos = {
        "colaborador": _obter_ou_criar(CONTAS_DEMO["colaborador"], "usuario"),
        "gestor": _obter_ou_criar(CONTAS_DEMO["gestor"], "admin"),
        "marina": _obter_ou_criar(COLEGAS[0], "usuario"),
        "rafael": _obter_ou_criar(COLEGAS[1], "usuario"),
    }

    agora = datetime.now()
    for numero, (dono, loja, tipo, declarado, no_comprovante, dias, status, itens) in enumerate(REEMBOLSOS, start=1):
        colaborador = donos[dono]
        quando = agora - timedelta(days=dias, hours=numero)
        reembolso = Reembolso(
            colaborador=colaborador.nome,
            empresa="SisPar Demo Ltda",
            descricao=f"{tipo} - {loja}",
            tipo_reembolso=tipo,
            centro_custo="1100110101",
            ordem_interna=None,
            divisao=None,
            pep=None,
            moeda="BRL",
            distancia_km=None,
            valor_km=None,
            valor_faturado=declarado,
            despesa=declarado,
            id_colaborador=colaborador.id,
            status=status,
            comprovante_id=None,
        )
        reembolso.data = quando
        db.session.add(reembolso)
        db.session.flush()

        arquivo = gerar_comprovante_png(loja, itens, no_comprovante, quando - timedelta(hours=2), 1000 + numero)
        divergencia = round(abs(declarado - no_comprovante) / declarado * 100, 2)
        comprovante = Comprovante(
            nome_arquivo=f"demo_{reembolso.num_prestacao}.png",
            texto_extraido=f"{loja}\n" + "\n".join(f"{d} {v:.2f}" for d, v in itens) + f"\nTOTAL {no_comprovante:.2f}",
            reembolso_id=reembolso.num_prestacao,
            valor_extraido=no_comprovante,
            status_validacao="Aprovado" if divergencia <= 5 else "Divergente",
            discrepancia_percentual=divergencia,
            hash_arquivo=hash_bytes(arquivo),
            arquivo=arquivo,
            mime_type="image/png",
        )
        db.session.add(comprovante)
        db.session.flush()
        reembolso.comprovante_id = comprovante.id

    db.session.commit()
    return True
