from src.model import db
from datetime import datetime
import json


class AnaliseIA(db.Model):
    __tablename__ = 'analises_ia'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    num_prestacao = db.Column(db.Integer, db.ForeignKey('reembolso.num_prestacao'), nullable=False)
    score_confiabilidade = db.Column(db.Integer, nullable=False)
    nivel_risco = db.Column(db.String(20), nullable=False)  # baixo, medio, alto
    aprovacao_sugerida = db.Column(db.Boolean, nullable=False)
    motivo_sugestao = db.Column(db.Text)
    dados_ia = db.Column(db.Text)  # JSON string
    alertas = db.Column(db.Text)  # JSON string
    validacoes = db.Column(db.Text)  # JSON string
    historico_colaborador = db.Column(db.Text)  # JSON string
    timestamp_analise = db.Column(db.DateTime, default=datetime.now)
    versao_modelo = db.Column(db.String(50), default='grok-vision-beta')
    
    # Relacionamento
    reembolso = db.relationship('Reembolso', backref='analises_ia', foreign_keys=[num_prestacao])
    
    def __init__(self, num_prestacao, score_confiabilidade, nivel_risco, aprovacao_sugerida, 
                 motivo_sugestao=None, dados_ia=None, alertas=None, validacoes=None, 
                 historico_colaborador=None, versao_modelo='grok-vision-beta'):
        self.num_prestacao = num_prestacao
        self.score_confiabilidade = score_confiabilidade
        self.nivel_risco = nivel_risco
        self.aprovacao_sugerida = aprovacao_sugerida
        self.motivo_sugestao = motivo_sugestao
        self.dados_ia = json.dumps(dados_ia) if isinstance(dados_ia, dict) else dados_ia
        self.alertas = json.dumps(alertas) if isinstance(alertas, list) else alertas
        self.validacoes = json.dumps(validacoes) if isinstance(validacoes, dict) else validacoes
        self.historico_colaborador = json.dumps(historico_colaborador) if isinstance(historico_colaborador, dict) else historico_colaborador
        self.versao_modelo = versao_modelo
    
    def to_dict(self):
        """Retorna dados básicos da análise"""
        return {
            'id': self.id,
            'num_prestacao': self.num_prestacao,
            'score_confiabilidade': self.score_confiabilidade,
            'nivel_risco': self.nivel_risco,
            'aprovacao_sugerida': self.aprovacao_sugerida,
            'motivo_sugestao': self.motivo_sugestao,
            'timestamp_analise': self.timestamp_analise.isoformat() if self.timestamp_analise else None,
            'versao_modelo': self.versao_modelo
        }
    
    def to_dict_completo(self):
        """Retorna análise completa com todos os dados JSON"""
        base = self.to_dict()
        base.update({
            'dados_ia': json.loads(self.dados_ia) if self.dados_ia else {},
            'alertas': json.loads(self.alertas) if self.alertas else [],
            'validacoes': json.loads(self.validacoes) if self.validacoes else {},
            'historico_colaborador': json.loads(self.historico_colaborador) if self.historico_colaborador else {}
        })
        return base
