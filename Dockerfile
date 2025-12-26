# Usa imagem base com Python
FROM python:3.11-slim

# Instala bibliotecas do sistema necessárias
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    tesseract-ocr \
    tesseract-ocr-por \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Define diretório de trabalho dentro do container
WORKDIR /app

# Copia as dependências primeiro (aproveita cache)
COPY requirements.txt .

# Instala as dependências do projeto
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação
COPY . .

# Define a variável de ambiente para o Flask
ENV FLASK_ENV=development
ENV PYTHONUNBUFFERED=1

# Expõe a porta usada pela aplicação Flask
EXPOSE 5000

# Comando que inicia a aplicação Flask
CMD ["python", "run.py"]
