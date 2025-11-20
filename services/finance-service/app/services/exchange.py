import requests
import logging
from decimal import Decimal
from sqlalchemy.orm import Session
from . import models

logger = logging.getLogger(__name__)

# URL de la API para tasa BCV
API_URL = "https://api.dolarvzla.com/public/exchange-rate"
CAMPO_NAME = "current" # Nombre del campo que especifica la Tasa BCV en la API

def fetch_and_store_rate(db: Session):
    """
    Consulta la API externa y guarda la tasa en la DB.
    Se usa Session síncrona porque APScheduler corre en hilos estándar.
    """
    logger.info("🔄 Iniciando actualización de tasa cambiaria...")
    
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status() # Lanza error si es 404 o 500
        
        data = response.json()
        
        rate_value = data.get(CAMPO_NAME, None).get('usd')
        
        if rate_value:
            # Guardar en DB
            new_rate = models.ExchangeRate(
                currency_from="USD",
                currency_to="VES",
                rate=Decimal(rate_value),
                source="API_EXTERNA"
            )
            db.add(new_rate)
            db.commit()
            logger.info(f"✅ Tasa actualizada exitosamente: {rate_value}")
        else:
            logger.warning("⚠️ No se pudo encontrar la tasa en la respuesta JSON.")
    except requests.RequestException as e:
        # Si falla internet, NO detenemos la app. Solo logueamos el error.
        logger.error(f"❌ Error de conexión al obtener tasa: {e}")
    except Exception as e:
        logger.error(f"❌ Error inesperado actualizando tasa: {e}")