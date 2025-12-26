from src.model import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, DECIMAL

class Comprovante(db.Model):
    __tablename__ = "comprovantes"

    id = Column(Integer, primary_key=True)
    nome_arquivo = Column(String(120), nullable=False)
    texto_extraido = Column(Text, nullable=False)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    
    # Novos campos para validação OCR
    valor_extraido = Column(DECIMAL(10, 2), nullable=True)
    status_validacao = Column(String(50), default='Pendente')  # Pendente, Aprovado, Divergente
    discrepancia_percentual = Column(DECIMAL(5, 2), nullable=True)
    
    # Campo para detecção de duplicatas (hash SHA-256 da imagem)
    hash_arquivo = Column(String(64), nullable=True, index=True)
    
    # Relacionamento com reembolso
    reembolso_id = Column(Integer, ForeignKey('reembolso.num_prestacao'), nullable=False)

    def __init__(self, nome_arquivo, texto_extraido, reembolso_id, valor_extraido=None, status_validacao='Pendente', discrepancia_percentual=None, hash_arquivo=None):
        self.nome_arquivo = nome_arquivo
        self.texto_extraido = texto_extraido
        self.reembolso_id = reembolso_id
        self.valor_extraido = valor_extraido
        self.status_validacao = status_validacao
        self.discrepancia_percentual = discrepancia_percentual
        self.hash_arquivo = hash_arquivo

    def to_dict(self):
        return {
            "id": self.id,
            "nome_arquivo": self.nome_arquivo,
            "texto_extraido": self.texto_extraido,
            "data_criacao": self.data_criacao.strftime("%Y-%m-%d %H:%M:%S"),
            "reembolso_id": self.reembolso_id,
            "valor_extraido": float(self.valor_extraido) if self.valor_extraido else None,
            "status_validacao": self.status_validacao,
            "discrepancia_percentual": float(self.discrepancia_percentual) if self.discrepancia_percentual else None,
            "hash_arquivo": self.hash_arquivo
        }
