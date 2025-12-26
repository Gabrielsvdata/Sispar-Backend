"""
Script de teste rápido do sistema de administrador
Execute após configurar o banco de dados
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_cadastro_admin():
    print_section("1. TESTE: Cadastrar Administrador")
    
    data = {
        "nome": "Admin Master",
        "email": "admin@sispar.com",
        "senha": "admin123",
        "cargo": "Administrador",
        "salario": 15000.00,
        "tipo": "admin"
    }
    
    response = requests.post(f"{BASE_URL}/colaborador/cadastrar", json=data)
    print(f"Status: {response.status_code}")
    print(f"Resposta: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.status_code == 201

def test_cadastro_usuario():
    print_section("2. TESTE: Cadastrar Usuário Normal")
    
    data = {
        "nome": "João Silva",
        "email": "joao@sispar.com",
        "senha": "senha123",
        "cargo": "Analista",
        "salario": 5000.00
        # Sem campo 'tipo' - deve ser 'usuario' por padrão
    }
    
    response = requests.post(f"{BASE_URL}/colaborador/cadastrar", json=data)
    print(f"Status: {response.status_code}")
    print(f"Resposta: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.status_code == 201

def test_login_admin():
    print_section("3. TESTE: Login como Admin")
    
    data = {
        "email": "admin@sispar.com",
        "senha": "admin123"
    }
    
    response = requests.post(f"{BASE_URL}/colaborador/login", json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Resposta: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        tipo = result.get('usuario', {}).get('tipo')
        print(f"\n✅ Tipo de usuário retornado: {tipo}")
        return tipo == 'admin'
    return False

def test_login_usuario():
    print_section("4. TESTE: Login como Usuário")
    
    data = {
        "email": "joao@sispar.com",
        "senha": "senha123"
    }
    
    response = requests.post(f"{BASE_URL}/colaborador/login", json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Resposta: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        tipo = result.get('usuario', {}).get('tipo')
        user_id = result.get('usuario', {}).get('id')
        print(f"\n✅ Tipo de usuário retornado: {tipo}")
        print(f"✅ ID do usuário: {user_id}")
        return tipo == 'usuario', user_id
    return False, None

def test_criar_reembolso(colaborador_id):
    print_section("5. TESTE: Criar Reembolso")
    
    data = {
        "colaborador": "João Silva",
        "empresa": "Sispar",
        "tipo_reembolso": "Transporte",
        "centro_custo": "CC001",
        "valor_faturado": 150.00,
        "id_colaborador": colaborador_id,
        "descricao": "Uber para reunião"
    }
    
    response = requests.post(f"{BASE_URL}/reembolsos/", json=data)
    print(f"Status: {response.status_code}")
    print(f"Resposta: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.status_code == 201

def test_listar_todos_reembolsos():
    print_section("6. TESTE: Admin - Listar TODOS os Reembolsos")
    
    response = requests.get(f"{BASE_URL}/reembolsos/")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Total de reembolsos: {len(result)}")
    print(f"Resposta: {json.dumps(result, indent=2, ensure_ascii=False)}")
    return response.status_code == 200

def test_listar_reembolsos_usuario(colaborador_id):
    print_section("7. TESTE: Usuário - Listar APENAS Seus Reembolsos")
    
    response = requests.get(f"{BASE_URL}/reembolsos/?colaborador_id={colaborador_id}")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Total de reembolsos do usuário: {len(result)}")
    print(f"Resposta: {json.dumps(result, indent=2, ensure_ascii=False)}")
    return response.status_code == 200

def test_tipo_invalido():
    print_section("8. TESTE: Validação - Tipo Inválido")
    
    data = {
        "nome": "Teste Inválido",
        "email": "invalido@sispar.com",
        "senha": "senha123",
        "cargo": "Teste",
        "salario": 1000.00,
        "tipo": "super-admin"  # ❌ Inválido
    }
    
    response = requests.post(f"{BASE_URL}/colaborador/cadastrar", json=data)
    print(f"Status: {response.status_code}")
    print(f"Resposta: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 400:
        print("\n✅ Validação funcionando corretamente!")
        return True
    return False

def run_all_tests():
    print("\n" + "="*60)
    print("  🧪 TESTES DO SISTEMA DE ADMINISTRADOR")
    print("="*60)
    
    resultados = []
    
    # Testes de cadastro
    resultados.append(("Cadastrar Admin", test_cadastro_admin()))
    resultados.append(("Cadastrar Usuário", test_cadastro_usuario()))
    
    # Testes de login
    resultados.append(("Login Admin", test_login_admin()))
    is_usuario, user_id = test_login_usuario()
    resultados.append(("Login Usuário", is_usuario))
    
    # Testes de reembolsos
    if user_id:
        resultados.append(("Criar Reembolso", test_criar_reembolso(user_id)))
        resultados.append(("Listar Todos", test_listar_todos_reembolsos()))
        resultados.append(("Filtrar por ID", test_listar_reembolsos_usuario(user_id)))
    
    # Teste de validação
    resultados.append(("Validação Tipo", test_tipo_invalido()))
    
    # Resumo
    print_section("RESUMO DOS TESTES")
    
    total = len(resultados)
    passou = sum(1 for _, result in resultados if result)
    
    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{status} - {nome}")
    
    print(f"\n{'='*60}")
    print(f"  Total: {passou}/{total} testes passaram")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    try:
        run_all_tests()
    except requests.exceptions.ConnectionError:
        print("\n❌ Erro: Não foi possível conectar ao servidor.")
        print("Certifique-se de que o backend está rodando em http://localhost:5000")
    except Exception as e:
        print(f"\n❌ Erro durante os testes: {str(e)}")
