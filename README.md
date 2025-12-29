# 🚀 SISPAR Backend - API de Reembolsos

Sistema de gerenciamento de reembolsos corporativos com inteligência artificial integrada.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Flask](https://img.shields.io/badge/Flask-3.1.0-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)
![Render](https://img.shields.io/badge/Deploy-Render-purple)

---

## 📋 Índice

- [Funcionalidades](#-funcionalidades)
- [Arquitetura](#-arquitetura)
- [Configuração de Ambientes](#-configuração-de-ambientes)
- [Instalação Local](#-instalação-local)
- [Deploy no Render](#-deploy-no-render)
- [Integração com IA](#-integração-com-ia)
- [API Endpoints](#-api-endpoints)
- [Variáveis de Ambiente](#-variáveis-de-ambiente)

---

## ✨ Funcionalidades

- ✅ **CRUD de Colaboradores** - Cadastro, autenticação e gestão
- ✅ **Sistema de Reembolsos** - Solicitação, aprovação e acompanhamento
- ✅ **OCR de Comprovantes** - Leitura automática de notas fiscais
- ✅ **Chatbot com IA** - Assistente inteligente usando Groq/Gemini
- ✅ **Análise de IA** - Validação automática de comprovantes
- ✅ **Documentação Swagger** - API documentada em `/apidocs`

---

## 🏗 Arquitetura

```
Sispar-Backend/
├── config.py              # Configurações por ambiente (DEV/PROD/TEST)
├── run.py                 # Ponto de entrada da aplicação
├── requirements.txt       # Dependências Python
├── .env                   # Variáveis locais (NÃO vai pro Git)
├── .env.example           # Exemplo de configuração
│
├── src/
│   ├── app.py             # Factory da aplicação Flask
│   ├── controler/         # Controllers (rotas)
│   │   ├── colaborador_controller.py
│   │   ├── reembolso_controler.py
│   │   ├── chatbot_controller.py
│   │   ├── analise_ia_controller.py
│   │   └── ocr_controller.py
│   │
│   ├── model/             # Models (banco de dados)
│   │   ├── colaborador_model.py
│   │   ├── reembolso_model.py
│   │   └── comprovante_model.py
│   │
│   ├── utils/             # Utilitários
│   │   ├── ia_utils.py    # Integração com Groq/Gemini
│   │   ├── ocr_reader.py  # Leitura de comprovantes
│   │   └── validacao_ocr.py
│   │
│   └── security/          # Autenticação e segurança
│       └── security.py
│
└── temp/                  # Arquivos temporários (comprovantes)
```

---

## ⚙ Configuração de Ambientes

O projeto utiliza **3 ambientes** seguindo as melhores práticas da indústria:

| Ambiente | Uso | Banco de Dados |
|----------|-----|----------------|
| **Development** | Sua máquina local | SQLite ou PostgreSQL local |
| **Production** | Render (produção) | PostgreSQL na nuvem |
| **Testing** | Testes automatizados | SQLite em memória |

### Como funciona:

```python
# config.py - O ambiente é detectado automaticamente pela variável FLASK_ENV

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = environ.get("URL_DATABASE_DEV", "sqlite:///dev.db")

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = environ.get("URL_DATABASE_PROD")
```

```
┌─────────────────────────────────────────────────────────────────┐
│                        FLUXO DE AMBIENTES                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   🖥️ SEU PC (Development)         ☁️ RENDER (Production)       │
│   ─────────────────────           ─────────────────────         │
│   .env:                           Environment Variables:        │
│     FLASK_ENV=development           FLASK_ENV=production        │
│     URL_DATABASE_DEV=sqlite         URL_DATABASE_PROD=postgres  │
│            │                               │                    │
│            ▼                               ▼                    │
│      Banco Local                    Banco do Render             │
│      (dados teste)                  (dados reais)               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠 Instalação Local

### 1. Clone o repositório
```bash
git clone https://github.com/Gabrielsvdata/Sispar-Backend.git
cd Sispar-Backend
```

### 2. Crie o ambiente virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente
```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite o .env com suas configurações
```

### 5. Execute a aplicação
```bash
python run.py
```

### 6. Acesse a documentação
```
http://localhost:5000/apidocs
```

---

## 🚀 Deploy no Render

### Pré-requisitos no Render:

1. **Crie um Web Service** conectado ao repositório GitHub
2. **Crie um banco PostgreSQL** no Render

### Variáveis de Ambiente no Render:

| Variável | Valor | Descrição |
|----------|-------|-----------|
| `FLASK_ENV` | `production` | Define ambiente de produção |
| `URL_DATABASE_PROD` | `postgresql://...` | URL do banco PostgreSQL |
| `GROQ_API_KEY` | `gsk_xxx...` | Chave da API Groq |
| `GEMINI_API_KEY` | `AIza...` | Chave da API Gemini |
| `SECRET_KEY` | `sua-chave-secreta` | Chave para JWT/sessões |

### Build Command:
```bash
pip install -r requirements.txt
```

### Start Command:
```bash
gunicorn run:app
```

---

## 🤖 Integração com IA

O SISPAR utiliza inteligência artificial para duas funcionalidades principais:

### 1. Chatbot Inteligente (Groq)

Assistente virtual que ajuda os usuários com consultas sobre reembolsos.

```
Usuário: "Quanto gastei este mês?"
Bot: "Você gastou R$ 450,00 este mês em 2 reembolsos:
      - R$ 250,00 em Alimentação (15/12)
      - R$ 200,00 em Transporte (20/12)"
```

**Configuração:**
```env
GROQ_API_KEY=sua_chave_groq_aqui
```

**Endpoint:**
```
POST /chatbot/message
```

### 2. Análise de Comprovantes (Gemini)

Validação automática de notas fiscais e comprovantes usando visão computacional.

**Funcionalidades:**
- ✅ Verifica se é uma nota fiscal válida
- ✅ Extrai valor, data e estabelecimento
- ✅ Detecta possíveis fraudes
- ✅ Valida legibilidade do documento

**Configuração:**
```env
GEMINI_API_KEY=sua_chave_gemini_aqui
```

**Endpoint:**
```
POST /analise-ia/analisar
```

### Obtendo as Chaves de API:

| Serviço | Link | Uso |
|---------|------|-----|
| **Groq** | https://console.groq.com/ | Chatbot (LLaMA) |
| **Gemini** | https://aistudio.google.com/apikey | Análise de imagens |

---

## 📡 API Endpoints

### Colaboradores
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/colaborador/cadastrar` | Cadastra novo colaborador |
| POST | `/colaborador/login` | Autenticação |
| GET | `/colaborador/` | Lista todos |
| PUT | `/colaborador/<id>` | Atualiza colaborador |
| DELETE | `/colaborador/<id>` | Remove colaborador |

### Reembolsos
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/reembolso/solicitar` | Solicita reembolso |
| GET | `/reembolso/listar` | Lista reembolsos |
| PUT | `/reembolso/<id>` | Atualiza reembolso |
| PATCH | `/reembolso/aprovar/<id>` | Aprova/Rejeita |
| DELETE | `/reembolso/<id>` | Remove reembolso |

### Chatbot
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/chatbot/message` | Envia mensagem ao bot |
| GET | `/chatbot/health` | Status do serviço |

### Análise IA
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/analise-ia/analisar` | Analisa comprovante |

### OCR
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/ocr/extrair` | Extrai texto de imagem |

---

## 🔐 Variáveis de Ambiente

### Arquivo `.env` (desenvolvimento local)

```env
# Ambiente
FLASK_ENV=development

# Banco de dados local
URL_DATABASE_DEV=sqlite:///dev.db

# Chaves de API
GROQ_API_KEY=sua_chave_groq
GEMINI_API_KEY=sua_chave_gemini

# Segurança
SECRET_KEY=chave-secreta-desenvolvimento
```

### Render (produção)

```env
FLASK_ENV=production
URL_DATABASE_PROD=postgresql://user:pass@host/database
GROQ_API_KEY=sua_chave_groq
GEMINI_API_KEY=sua_chave_gemini
SECRET_KEY=chave-secreta-producao-muito-segura
```

> ⚠️ **IMPORTANTE**: Nunca commite chaves reais no Git! Use sempre variáveis de ambiente.

---

## 🔧 Tecnologias Utilizadas

- **Backend:** Flask 3.1.0
- **ORM:** SQLAlchemy + Flask-SQLAlchemy
- **Banco:** PostgreSQL (prod) / SQLite (dev)
- **IA:** Groq (LLaMA), Google Gemini
- **OCR:** Pytesseract
- **Docs:** Flasgger (Swagger)
- **Deploy:** Render
- **CORS:** Flask-CORS

---

## 👥 CORS - Origens Permitidas

O backend aceita requisições das seguintes origens:

```python
origins = [
    "http://localhost:5173",           # Vite dev
    "http://localhost:3000",           # React dev
    "http://localhost:5000",           # Flask dev
    "https://sispar-sign.vercel.app",  # Produção
    "https://projeto-sispar.vercel.app" # Produção alternativo
]
```

Para adicionar novas origens, edite o arquivo `src/app.py`.

---

## 📝 Licença

Este projeto foi desenvolvido para fins educacionais.

---

## 🤝 Contribuição

1. Fork o projeto
2. Crie sua branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Add: nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

---

**Desenvolvido com ❤️ por Gabriel Silvano**
