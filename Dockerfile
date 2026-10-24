# Imagem da API do SisPar (Cloud Run, Render ou qualquer host de containers)
FROM python:3.11-slim

# OCR (Tesseract em português), conversão de PDF e fonte para os comprovantes de demonstração
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    poppler-utils \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependências primeiro (aproveita cache entre builds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_ENV=production \
    PYTHONUNBUFFERED=1 \
    PORT=8080

EXPOSE 8080

# O Cloud Run informa a porta pela variável PORT
CMD exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 120 run:app
