# Usamos Python 3.11 ligero
FROM python:3.11-slim

# Evita que Python genere archivos .pyc y mantiene los logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Instalar dependencias del sistema necesarias para compilar
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copiar requerimientos e instalarlos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la carpeta 'app' dentro del contenedor
COPY ./app /app/app

# Puerto por defecto
EXPOSE 8000

# Comando para arrancar
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]