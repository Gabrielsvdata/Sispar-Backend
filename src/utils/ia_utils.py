"""
Utilitários para análise de IA antifraude
"""
import hashlib
import base64
import os
import json
from datetime import datetime, timedelta
from decimal import Decimal
from PIL import Image
from pdf2image import convert_from_path
import io
import statistics
from src.model.reembolso_model import Reembolso
from src.model.comprovante_model import Comprovante


def calcular_hash_imagem(caminho_arquivo):
    """
    Calcula hash SHA-256 de um arquivo de imagem para detectar duplicatas
    
    Args:
        caminho_arquivo: Path completo do arquivo
        
    Returns:
        String hexadecimal do hash SHA-256
    """
    try:
        sha256_hash = hashlib.sha256()
        
        with open(caminho_arquivo, "rb") as f:
            # Ler arquivo em chunks para arquivos grandes
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Erro ao calcular hash: {e}")
        return None


def converter_para_base64(caminho_arquivo):
    """
    Converte imagem ou PDF para base64 para envio ao Grok Vision
    Se for PDF, converte a primeira página para imagem
    
    Args:
        caminho_arquivo: Path do arquivo (imagem ou PDF)
        
    Returns:
        String base64 da imagem
    """
    try:
        extensao = os.path.splitext(caminho_arquivo)[1].lower()
        
        # Se for PDF, converter primeira página para imagem
        if extensao == '.pdf':
            images = convert_from_path(caminho_arquivo, first_page=1, last_page=1, dpi=200)
            if images:
                # Converter PIL Image para bytes
                img_byte_arr = io.BytesIO()
                images[0].save(img_byte_arr, format='JPEG', quality=90)
                img_byte_arr = img_byte_arr.getvalue()
                return base64.b64encode(img_byte_arr).decode('utf-8')
        
        # Se for imagem (PNG, JPEG, etc)
        else:
            with open(caminho_arquivo, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
    
    except Exception as e:
        print(f"Erro ao converter para base64: {e}")
        return None


def detectar_duplicatas(hash_arquivo, excluir_num_prestacao=None):
    """
    Busca comprovantes com mesmo hash (duplicatas)
    
    Args:
        hash_arquivo: Hash SHA-256 do arquivo
        excluir_num_prestacao: Número da prestação a excluir da busca
        
    Returns:
        Lista de comprovantes duplicados
    """
    try:
        query = Comprovante.query.filter_by(hash_arquivo=hash_arquivo)
        
        if excluir_num_prestacao:
            query = query.filter(Comprovante.reembolso_id != excluir_num_prestacao)
        
        duplicatas = query.all()
        return [c.to_dict() for c in duplicatas]
    
    except Exception as e:
        print(f"Erro ao detectar duplicatas: {e}")
        return []


def analisar_historico_colaborador(colaborador_id):
    """
    Analisa histórico de reembolsos do colaborador
    
    Args:
        colaborador_id: ID do colaborador
        
    Returns:
        Dict com estatísticas do histórico
    """
    try:
        # Buscar todos os reembolsos do colaborador
        reembolsos = Reembolso.query.filter_by(id_colaborador=colaborador_id).all()
        
        if not reembolsos:
            return {
                'total_reembolsos': 0,
                'total_aprovados': 0,
                'total_rejeitados': 0,
                'taxa_aprovacao': 0.0,
                'valor_medio_mensal': 0.0,
                'ultima_solicitacao': None,
                'frequencia_media_dias': 0
            }
        
        # Contar por status
        aprovados = sum(1 for r in reembolsos if r.status == 'Aprovado')
        rejeitados = sum(1 for r in reembolsos if r.status == 'Rejeitado')
        total = len(reembolsos)
        
        # Taxa de aprovação
        taxa_aprovacao = (aprovados / total * 100) if total > 0 else 0.0
        
        # Valor médio mensal (últimos 6 meses)
        seis_meses_atras = datetime.now() - timedelta(days=180)
        reembolsos_recentes = [r for r in reembolsos if r.data and r.data >= seis_meses_atras]
        
        if reembolsos_recentes:
            valores = [float(r.despesa) for r in reembolsos_recentes if r.despesa]
            valor_medio_mensal = sum(valores) / 6 if valores else 0.0
        else:
            valor_medio_mensal = 0.0
        
        # Última solicitação
        reembolsos_ordenados = sorted(reembolsos, key=lambda r: r.data if r.data else datetime.min, reverse=True)
        ultima_solicitacao = reembolsos_ordenados[0].data.isoformat() if reembolsos_ordenados[0].data else None
        
        # Frequência média (dias entre solicitações)
        if len(reembolsos) > 1:
            datas = sorted([r.data for r in reembolsos if r.data])
            diferencas = [(datas[i+1] - datas[i]).days for i in range(len(datas)-1)]
            frequencia_media_dias = sum(diferencas) / len(diferencas) if diferencas else 0
        else:
            frequencia_media_dias = 0
        
        return {
            'total_reembolsos': total,
            'total_aprovados': aprovados,
            'total_rejeitados': rejeitados,
            'taxa_aprovacao': round(taxa_aprovacao, 2),
            'valor_medio_mensal': round(valor_medio_mensal, 2),
            'ultima_solicitacao': ultima_solicitacao,
            'frequencia_media_dias': round(frequencia_media_dias, 1)
        }
    
    except Exception as e:
        print(f"Erro ao analisar histórico: {e}")
        return {}


def analisar_padroes_comportamentais(reembolso, historico):
    """
    Analisa se o reembolso atual está fora do padrão do colaborador
    
    Args:
        reembolso: Objeto Reembolso atual
        historico: Lista de reembolsos anteriores
        
    Returns:
        Dict com análise de padrões
    """
    try:
        if not historico or len(historico) < 3:
            return {
                'valor_fora_padrao': False,
                'frequencia_normal': True,
                'estabelecimento_recorrente': False,
                'tipo_comum': True
            }
        
        # Análise de valor
        valores = [float(r.despesa) for r in historico if r.despesa]
        if valores and len(valores) >= 3:
            media = statistics.mean(valores)
            desvio = statistics.stdev(valores) if len(valores) > 1 else 0
            valor_atual = float(reembolso.despesa) if reembolso.despesa else 0
            
            # Valor fora do padrão se estiver além de 2 desvios padrão
            valor_fora_padrao = abs(valor_atual - media) > (2 * desvio) if desvio > 0 else False
        else:
            valor_fora_padrao = False
        
        # Análise de frequência
        datas = sorted([r.data for r in historico if r.data])
        if len(datas) > 1:
            diferencas = [(datas[i+1] - datas[i]).days for i in range(len(datas)-1)]
            frequencia_media = sum(diferencas) / len(diferencas)
            
            # Frequência anormal se for menos de 2 dias entre reembolsos
            frequencia_normal = frequencia_media >= 2
        else:
            frequencia_normal = True
        
        # Análise de tipo de despesa
        tipos = [r.tipo_reembolso for r in historico if r.tipo_reembolso]
        tipo_atual = reembolso.tipo_reembolso
        tipo_comum = tipos.count(tipo_atual) >= (len(tipos) * 0.2) if tipos else True
        
        return {
            'valor_fora_padrao': valor_fora_padrao,
            'frequencia_normal': frequencia_normal,
            'tipo_comum': tipo_comum
        }
    
    except Exception as e:
        print(f"Erro ao analisar padrões: {e}")
        return {
            'valor_fora_padrao': False,
            'frequencia_normal': True,
            'tipo_comum': True
        }


def calcular_score_confiabilidade(validacoes, duplicatas, padroes, sinais_fraude):
    """
    Calcula score de confiabilidade de 0-100 baseado nas validações
    
    Args:
        validacoes: Dict com validações básicas
        duplicatas: Lista de duplicatas encontradas
        padroes: Dict com análise de padrões
        sinais_fraude: Dict com sinais de fraude detectados pela IA
        
    Returns:
        Tuple (score, nivel_risco, alertas)
    """
    score = 100
    alertas = []
    
    # Penalizações por divergência de valor
    if not validacoes.get('valor_corresponde', True):
        divergencia = validacoes.get('divergencia_percentual', 0)
        if divergencia > 50:
            score -= 50
            alertas.append({
                "tipo": "valor_divergente",
                "gravidade": "critica",
                "mensagem": f"Divergência crítica de {divergencia:.1f}% entre valor declarado e comprovante",
                "confianca": 0.98
            })
        elif divergencia > 20:
            score -= 40
            alertas.append({
                "tipo": "valor_divergente",
                "gravidade": "alta",
                "mensagem": f"Divergência alta de {divergencia:.1f}% entre valor declarado e comprovante",
                "confianca": 0.95
            })
        elif divergencia > 10:
            score -= 25
            alertas.append({
                "tipo": "valor_divergente",
                "gravidade": "alta",
                "mensagem": f"Divergência de {divergencia:.1f}% entre valor declarado e comprovante",
                "confianca": 0.92
            })
        elif divergencia > 5:
            score -= 15
            alertas.append({
                "tipo": "valor_divergente",
                "gravidade": "media",
                "mensagem": f"Divergência de {divergencia:.1f}% entre valor declarado e comprovante",
                "confianca": 0.90
            })
        else:
            score -= 5
            alertas.append({
                "tipo": "valor_divergente",
                "gravidade": "baixa",
                "mensagem": f"Pequena divergência de {divergencia:.1f}% aceitável",
                "confianca": 0.85
            })
    
    # Penalização por documento editado
    if sinais_fraude.get('editado', False):
        score -= 40
        alertas.append({
            "tipo": "documento_editado",
            "gravidade": "critica",
            "mensagem": "Sinais de edição/manipulação detectados na imagem",
            "confianca": sinais_fraude.get('confianca_edicao', 0.80)
        })
    
    # Penalização por duplicatas
    if duplicatas:
        score -= 50
        alertas.append({
            "tipo": "duplicata",
            "gravidade": "critica",
            "mensagem": f"Comprovante duplicado em {len(duplicatas)} reembolso(s)",
            "confianca": 1.0
        })
    
    # Penalização por data inválida
    if not validacoes.get('data_valida', True):
        score -= 20
        alertas.append({
            "tipo": "data_invalida",
            "gravidade": "alta",
            "mensagem": "Data do comprovante posterior à solicitação ou muito antiga",
            "confianca": 0.90
        })
    
    # Penalização por tipo de despesa incorreto
    if not validacoes.get('tipo_despesa_correto', True):
        score -= 25
        alertas.append({
            "tipo": "tipo_incorreto",
            "gravidade": "alta",
            "mensagem": "Tipo de despesa não corresponde ao estabelecimento",
            "confianca": 0.85
        })
    
    # Penalização por valor fora do padrão
    if padroes.get('valor_fora_padrao', False):
        score -= 15
        alertas.append({
            "tipo": "valor_atipico",
            "gravidade": "media",
            "mensagem": "Valor fora do padrão histórico do colaborador",
            "confianca": 0.75
        })
    
    # Penalização por frequência anormal
    if not padroes.get('frequencia_normal', True):
        score -= 10
        alertas.append({
            "tipo": "frequencia_alta",
            "gravidade": "media",
            "mensagem": "Frequência de solicitações acima do normal",
            "confianca": 0.70
        })
    
    # Penalização por documento ilegível
    if not validacoes.get('comprovante_legivel', True):
        score -= 20
        alertas.append({
            "tipo": "ilegivel",
            "gravidade": "alta",
            "mensagem": "Comprovante com baixa qualidade/legibilidade",
            "confianca": 0.80
        })
    
    # Determinar nível de risco
    if score >= 85:
        nivel_risco = "baixo"
    elif score >= 60:
        nivel_risco = "medio"
    else:
        nivel_risco = "alto"
    
    return score, nivel_risco, alertas


def gerar_recomendacao(score, nivel_risco, alertas):
    """
    Gera recomendação textual baseada no score e alertas
    
    Args:
        score: Score de confiabilidade (0-100)
        nivel_risco: baixo, medio, alto
        alertas: Lista de alertas detectados
        
    Returns:
        Tuple (aprovacao_sugerida, motivo_sugestao)
    """
    if score >= 90:
        return True, "Aprovar automaticamente. Score de confiabilidade excelente. Sem problemas detectados."
    
    elif score >= 85:
        problemas = [a['mensagem'] for a in alertas if a['gravidade'] in ['baixa', 'media']]
        return True, f"Aprovar com ressalvas. Score bom ({score}%). Alertas de baixa gravidade: {'; '.join(problemas[:2]) if problemas else 'nenhum'}."
    
    elif score >= 70:
        return True, f"Aprovar com cautela. Score aceitável ({score}%). Recomenda-se verificação posterior."
    
    elif score >= 50:
        problemas_graves = [a['mensagem'] for a in alertas if a['gravidade'] in ['alta', 'critica']]
        return False, f"Revisão manual obrigatória. Score médio ({score}%). Problemas: {'; '.join(problemas_graves[:2])}."
    
    else:
        problemas_criticos = [a['mensagem'] for a in alertas if a['gravidade'] == 'critica']
        return False, f"REJEITAR ou investigar. Score baixo ({score}%). Problemas críticos: {'; '.join(problemas_criticos[:3])}."
