FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# --- Instalamos el paquete común ---
COPY packages /tmp/packages
RUN pip install /tmp/packages/erp_common
# -----------------------------------

COPY services/inventory-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/inventory-service/app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]