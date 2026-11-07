FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Instala dependências da API e o pacote instaloader local
COPY requirements.txt setup.py README.rst ./
COPY instaloader ./instaloader
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e .

# Copia o código da API
COPY api ./api
COPY run_api.py ./

# Cria pasta para downloads persistentes
RUN mkdir -p /app/downloads

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
