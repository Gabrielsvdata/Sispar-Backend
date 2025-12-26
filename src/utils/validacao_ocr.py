from decimal import Decimal

def calcular_discrepancia(valor_solicitado, valor_extraido):
    """
    Calcula a discrepância percentual entre o valor solicitado e o extraído
    
    Args:
        valor_solicitado: Valor informado no reembolso
        valor_extraido: Valor extraído do comprovante via OCR
    
    Returns:
        Percentual de diferença (0 a 100)
    """
    if not valor_extraido or not valor_solicitado:
        return None
    
    valor_solicitado = Decimal(str(valor_solicitado))
    valor_extraido = Decimal(str(valor_extraido))
    
    if valor_solicitado == 0:
        return None
    
    # Calcula diferença percentual
    diferenca = abs(valor_solicitado - valor_extraido)
    percentual = (diferenca / valor_solicitado) * 100
    
    return round(percentual, 2)


def validar_valores(valor_solicitado, valor_extraido, tolerancia=5.0):
    """
    Valida se o valor extraído está dentro da tolerância aceitável
    
    Args:
        valor_solicitado: Valor informado no reembolso
        valor_extraido: Valor extraído do comprovante via OCR
        tolerancia: Percentual de tolerância aceito (padrão 5%)
    
    Returns:
        dict com status e informações da validação
    """
    discrepancia = calcular_discrepancia(valor_solicitado, valor_extraido)
    
    if discrepancia is None:
        return {
            'status': 'Pendente',
            'aprovado': False,
            'discrepancia': None,
            'mensagem': 'Não foi possível extrair valor do comprovante'
        }
    
    if discrepancia == 0:
        return {
            'status': 'Aprovado',
            'aprovado': True,
            'discrepancia': discrepancia,
            'mensagem': 'Valores exatamente iguais'
        }
    
    if discrepancia <= tolerancia:
        return {
            'status': 'Aprovado',
            'aprovado': True,
            'discrepancia': discrepancia,
            'mensagem': f'Diferença de {discrepancia}% dentro da tolerância'
        }
    
    return {
        'status': 'Divergente',
        'aprovado': False,
        'discrepancia': discrepancia,
        'mensagem': f'Discrepância de {discrepancia}% acima da tolerância de {tolerancia}%'
    }


def verificar_validacao_automatica(reembolso, comprovante):
    """
    Verifica automaticamente se um reembolso pode ser aprovado baseado no OCR
    
    Args:
        reembolso: Objeto Reembolso
        comprovante: Objeto Comprovante
    
    Returns:
        dict com resultado da validação
    """
    if not comprovante:
        return {
            'pode_aprovar': False,
            'motivo': 'Reembolso sem comprovante anexado'
        }
    
    if not comprovante.valor_extraido:
        return {
            'pode_aprovar': False,
            'motivo': 'Não foi possível extrair valor do comprovante'
        }
    
    resultado = validar_valores(
        valor_solicitado=reembolso.valor_faturado,
        valor_extraido=comprovante.valor_extraido,
        tolerancia=5.0
    )
    
    return {
        'pode_aprovar': resultado['aprovado'],
        'motivo': resultado['mensagem'],
        'status_validacao': resultado['status'],
        'discrepancia': resultado['discrepancia']
    }
