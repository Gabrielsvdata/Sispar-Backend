"""
Script para verificar e validar todas as importações do projeto
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def verificar_importacoes():
    """Verifica se todas as importações estão corretas"""
    
    print("🔍 Verificando importações do projeto...\n")
    
    erros = []
    sucesso = []
    
    # 1. Verificar model Colaborador
    print("1. Verificando model Colaborador...")
    try:
        from src.model.colaborador_model import Colaborador
        # Verificar atributos
        colaborador_test = Colaborador(
            nome="Teste",
            email="teste@teste.com",
            senha="senha",
            cargo="Teste",
            salario=1000,
            tipo="usuario"
        )
        
        # Verificar métodos
        assert hasattr(colaborador_test, 'tipo'), "Atributo 'tipo' não encontrado"
        assert hasattr(colaborador_test, 'to_dict'), "Método 'to_dict' não encontrado"
        assert hasattr(colaborador_test, 'all_data'), "Método 'all_data' não encontrado"
        
        # Verificar se tipo está no dict
        dict_data = colaborador_test.to_dict()
        assert 'tipo' in dict_data, "Campo 'tipo' não está em to_dict()"
        
        all_data = colaborador_test.all_data()
        assert 'tipo' in all_data, "Campo 'tipo' não está em all_data()"
        
        print("   ✅ Model Colaborador OK")
        sucesso.append("Model Colaborador")
    except Exception as e:
        print(f"   ❌ Erro: {str(e)}")
        erros.append(f"Model Colaborador: {str(e)}")
    
    # 2. Verificar model Comprovante
    print("\n2. Verificando model Comprovante...")
    try:
        from src.model.comprovante_model import Comprovante
        
        # Verificar se tem novos campos
        from sqlalchemy import inspect
        mapper = inspect(Comprovante)
        colunas = [col.key for col in mapper.attrs]
        
        assert 'valor_extraido' in colunas, "Coluna 'valor_extraido' não encontrada"
        assert 'status_validacao' in colunas, "Coluna 'status_validacao' não encontrada"
        assert 'discrepancia_percentual' in colunas, "Coluna 'discrepancia_percentual' não encontrada"
        
        print("   ✅ Model Comprovante OK")
        sucesso.append("Model Comprovante")
    except Exception as e:
        print(f"   ❌ Erro: {str(e)}")
        erros.append(f"Model Comprovante: {str(e)}")
    
    # 3. Verificar OCR reader
    print("\n3. Verificando OCR reader...")
    try:
        from src.utils.ocr_reader import (
            extrair_texto_imagem,
            extrair_texto_pdf,
            extrair_valores_monetarios,
            encontrar_maior_valor,
            processar_arquivo
        )
        
        print("   ✅ OCR reader OK")
        sucesso.append("OCR reader")
    except Exception as e:
        print(f"   ❌ Erro: {str(e)}")
        erros.append(f"OCR reader: {str(e)}")
    
    # 4. Verificar validação OCR
    print("\n4. Verificando validação OCR...")
    try:
        from src.utils.validacao_ocr import (
            calcular_discrepancia,
            validar_valores,
            verificar_validacao_automatica
        )
        
        print("   ✅ Validação OCR OK")
        sucesso.append("Validação OCR")
    except Exception as e:
        print(f"   ❌ Erro: {str(e)}")
        erros.append(f"Validação OCR: {str(e)}")
    
    # 5. Verificar controller de colaborador
    print("\n5. Verificando controller de colaborador...")
    try:
        from src.controler.colaborador_controller import bp_colaborador
        
        print("   ✅ Controller Colaborador OK")
        sucesso.append("Controller Colaborador")
    except Exception as e:
        print(f"   ❌ Erro: {str(e)}")
        erros.append(f"Controller Colaborador: {str(e)}")
    
    # 6. Verificar controller de reembolso
    print("\n6. Verificando controller de reembolso...")
    try:
        from src.controler.reembolso_controler import bp_reembolso
        
        print("   ✅ Controller Reembolso OK")
        sucesso.append("Controller Reembolso")
    except Exception as e:
        print(f"   ❌ Erro: {str(e)}")
        erros.append(f"Controller Reembolso: {str(e)}")
    
    # 7. Verificar controller de OCR
    print("\n7. Verificando controller de OCR...")
    try:
        from src.controler.ocr_controller import ocr_bp
        
        print("   ✅ Controller OCR OK")
        sucesso.append("Controller OCR")
    except Exception as e:
        print(f"   ❌ Erro: {str(e)}")
        erros.append(f"Controller OCR: {str(e)}")
    
    # 8. Verificar app principal
    print("\n8. Verificando app principal...")
    try:
        from src.app import create_app
        
        print("   ✅ App principal OK")
        sucesso.append("App principal")
    except Exception as e:
        print(f"   ❌ Erro: {str(e)}")
        erros.append(f"App principal: {str(e)}")
    
    # Resumo
    print("\n" + "="*60)
    print("  RESUMO DA VERIFICAÇÃO")
    print("="*60 + "\n")
    
    print(f"✅ Sucessos: {len(sucesso)}")
    for s in sucesso:
        print(f"   • {s}")
    
    if erros:
        print(f"\n❌ Erros: {len(erros)}")
        for e in erros:
            print(f"   • {e}")
    else:
        print("\n🎉 Todas as importações estão corretas!")
    
    print("\n" + "="*60 + "\n")
    
    return len(erros) == 0

def verificar_dependencias():
    """Verifica se todas as dependências estão instaladas"""
    
    print("\n🔍 Verificando dependências...\n")
    
    dependencias = [
        'flask',
        'flask_sqlalchemy',
        'flask_bcrypt',
        'flask_cors',
        'flasgger',
        'pytesseract',
        'PIL',
        'pdf2image',
        'sqlalchemy',
        'gunicorn',
        'pytest',
        'flask_mail'
    ]
    
    faltando = []
    
    for dep in dependencias:
        try:
            __import__(dep)
            print(f"   ✅ {dep}")
        except ImportError:
            print(f"   ❌ {dep} - NÃO INSTALADO")
            faltando.append(dep)
    
    if faltando:
        print(f"\n⚠️  Dependências faltando: {', '.join(faltando)}")
        print("\nInstale com:")
        print("pip install -r requirements.txt")
        return False
    else:
        print("\n✅ Todas as dependências instaladas!")
        return True

def verificar_estrutura_arquivos():
    """Verifica se todos os arquivos necessários existem"""
    
    print("\n🔍 Verificando estrutura de arquivos...\n")
    
    arquivos_necessarios = [
        'src/model/colaborador_model.py',
        'src/model/comprovante_model.py',
        'src/model/reembolso_model.py',
        'src/utils/ocr_reader.py',
        'src/utils/validacao_ocr.py',
        'src/controler/colaborador_controller.py',
        'src/controler/reembolso_controler.py',
        'src/controler/ocr_controller.py',
        'scripts/tornar_admin.py',
        'migrations/add_tipo_column.sql',
        'requirements.txt',
        'Dockerfile',
        'docker-compose.yml'
    ]
    
    base_path = Path(__file__).parent.parent
    faltando = []
    
    for arquivo in arquivos_necessarios:
        caminho = base_path / arquivo
        if caminho.exists():
            print(f"   ✅ {arquivo}")
        else:
            print(f"   ❌ {arquivo} - NÃO ENCONTRADO")
            faltando.append(arquivo)
    
    if faltando:
        print(f"\n⚠️  Arquivos faltando: {len(faltando)}")
        return False
    else:
        print("\n✅ Todos os arquivos presentes!")
        return True

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  🔍 VERIFICADOR DE INTEGRIDADE DO PROJETO")
    print("="*60 + "\n")
    
    # Verificar estrutura
    estrutura_ok = verificar_estrutura_arquivos()
    
    # Verificar dependências
    deps_ok = verificar_dependencias()
    
    # Verificar importações
    imports_ok = verificar_importacoes()
    
    # Resultado final
    print("\n" + "="*60)
    print("  RESULTADO FINAL")
    print("="*60 + "\n")
    
    if estrutura_ok and deps_ok and imports_ok:
        print("✅ ✅ ✅ TUDO ESTÁ CORRETO! ✅ ✅ ✅")
        print("\nO projeto está pronto para uso!")
        sys.exit(0)
    else:
        print("❌ Há problemas que precisam ser corrigidos:")
        if not estrutura_ok:
            print("   • Estrutura de arquivos incompleta")
        if not deps_ok:
            print("   • Dependências faltando")
        if not imports_ok:
            print("   • Erros de importação")
        sys.exit(1)
