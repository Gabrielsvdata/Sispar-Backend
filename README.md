# 🚀 SISPAR Backend - API de Reembolsos

Sistema de gerenciamento de reembolsos corporativos com inteligência artificial integrada.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Flask](https://img.shields.io/badge/Flask-3.1.0-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)
![Cloud Run](https://img.shields.io/badge/Deploy-Cloud%20Run-blue)

---

## 📋 Índice

- [Funcionalidades](#-funcionalidades)
- [Arquitetura](#-arquitetura)
- [Configuração de Ambientes](#-configuração-de-ambientes)
- [Instalação Local](#-instalação-local)
- [Deploy no Cloud Run](#-deploy-no-google-cloud-run)
- [Autenticação e perfis](#-autenticação-e-perfis)
- [Integração com IA](#-integração-com-ia)
- [API Endpoints](#-api-endpoints)
- [Variáveis de Ambiente](#-variáveis-de-ambiente)

---

## ✨ Funcionalidades

- ✅ **CRUD de Colaboradores** - Cadastro, autenticação e gestão
- ✅ **Sistema de Reembolsos** - Solicitação, aprovação e acompanhamento
- ✅ **OCR de Comprovantes** - Leitura automática de notas fiscais
- ✅ **Chatbot com IA** - Assistente inteligente usando Groq
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
│   │   ├── ia_utils.py    # Score, duplicatas e histórico
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
| **Production** | Cloud Run (produção) | PostgreSQL na nuvem (Neon) |
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
│      Banco Local                    Banco na nuvem (Neon)       │
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

## 🚀 Deploy no Google Cloud Run

A API roda num container (veja o `Dockerfile`): Tesseract para o OCR, Poppler para PDF e
gunicorn escutando na porta da variável `PORT`. O banco é um Postgres gerenciado (ex.: Neon).

```bash
gcloud run deploy sispar-api \
  --source . \
  --region southamerica-east1 \
  --allow-unauthenticated \
  --set-env-vars FLASK_ENV=production,DEMO_MODE=true,CORS_ORIGINS=https://sispar.pages.dev \
  --set-secrets SECRET_KEY=sispar-secret-key:latest,DATABASE_URL=sispar-database-url:latest,GROQ_API_KEY=sispar-groq-key:latest
```

Na primeira subida, as tabelas são criadas automaticamente e, com `DEMO_MODE=true`,
os dados de demonstração também.

### Rodando com Docker localmente

```bash
docker compose up --build   # API em http://localhost:8080 com Postgres
```

---

## 🔑 Autenticação e perfis

- `POST /colaborador/login` devolve um **token JWT** (validade padrão: 8 h).
- Todas as rotas de reembolso, comprovante, análise e chatbot exigem `Authorization: Bearer <token>`.
- **Colaborador** (`usuario`) vê e edita só os próprios reembolsos.
- **Gestor** (`admin`) vê todos, aprova/rejeita, roda a análise com IA e consulta colaboradores.
- O cadastro público cria só colaboradores; gestores são criados por outro gestor logado.

### Modo demonstração

Com `DEMO_MODE=true`, a API cria duas contas de visitante e alguns reembolsos fictícios
(com comprovantes gerados na hora), e libera:

```
POST /colaborador/login-demo   {"perfil": "colaborador" | "gestor"}
```

As contas de demonstração não podem ter a senha trocada nem ser removidas.
Para recriar os dados do zero: `python scripts/seed_demo.py --reset`.

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

### 2. Análise de Comprovantes (Groq Vision)

A IA **só lê** o comprovante; as **validações e o score são calculados em Python**, com regras fixas.
Assim o mesmo comprovante gera sempre o mesmo resultado.

1. O modelo de visão do Groq extrai valor, data, CNPJ, itens e categoria do estabelecimento.
2. O backend calcula a divergência entre valor declarado e valor lido, a validade da data,
   a compatibilidade da categoria com o tipo de despesa e procura comprovantes duplicados (hash).
3. O score de confiabilidade e a recomendação saem dessas regras.

Se a IA estiver indisponível, a análise usa o valor do OCR (Tesseract) e avisa isso no resultado
(`fonte_leitura: "ocr"`).

**Endpoint:**
```
POST /reembolsos/{num_prestacao}/analisar-ia   (gestor)
```

### Obtendo a chave de API

| Serviço | Link | Uso |
|---------|------|-----|
| **Groq** | https://console.groq.com/keys | Chatbot (LLaMA 3.3) e leitura de comprovantes (Llama 4 Scout) |

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

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `FLASK_ENV` | sim | `development`, `production` ou `testing` |
| `SECRET_KEY` | em produção | Assina os tokens de login. Use um valor longo e aleatório |
| `DATABASE_URL` | em produção | URL do Postgres (ex.: Neon, com `?sslmode=require`) |
| `GROQ_API_KEY` | para IA | Chatbot e leitura de comprovantes |
| `CORS_ORIGINS` | não | Origens extras do front, separadas por vírgula |
| `DEMO_MODE` | não | `true` cria as contas de visitante e libera o login de demonstração |
| `GROQ_CHAT_MODEL` / `GROQ_VISION_MODEL` | não | Troca os modelos usados |

Veja o `.env.example` para um modelo de arquivo local.

> ⚠️ **IMPORTANTE**: Nunca commite chaves reais no Git! Use sempre variáveis de ambiente.

---

## 🔧 Tecnologias Utilizadas

- **Backend:** Flask 3.1.0 + gunicorn
- **ORM:** SQLAlchemy + Flask-SQLAlchemy
- **Banco:** PostgreSQL (prod) / SQLite (dev e testes)
- **Autenticação:** JWT (PyJWT) + bcrypt
- **IA:** Groq (LLaMA 3.3 no chatbot, Llama 4 Scout na leitura de comprovantes)
- **OCR:** Pytesseract + Poppler
- **Docs:** Flasgger (Swagger)
- **Deploy:** Docker / Google Cloud Run
- **Testes:** pytest (`FLASK_ENV=testing python -m pytest`)

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
