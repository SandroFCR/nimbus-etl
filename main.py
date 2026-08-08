import os
from dotenv import load_dotenv

# Cargar .env desde el directorio del script
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"), override=True)

from etl.extract import get_weather
from etl.transform import transform_weather
from etl.load import load_weather, init_db
from pydantic import ValidationError
from etl.logger import get_logger

logger = get_logger("main")

ciudades_raw = os.getenv("CIUDADES", "Lima")
CIUDADES = [c.strip() for c in ciudades_raw.split(",") if c.strip()]

def run_etl():
    logger.info("=== Iniciando ETL de clima ===")
    init_db()
    exitosos = 0
    fallidos = 0

    for ciudad in CIUDADES:
        try:
            raw   = get_weather(ciudad)
            clean = transform_weather(raw)
            load_weather(clean)
            logger.info(f"ETL exitoso para {ciudad}")
            exitosos += 1
        except ValidationError as e:
            logger.warning(f"Dato invalido en {ciudad}: {e}")
            fallidos += 1
        except Exception as e:
            logger.error(f"Fallo {ciudad}: {e}")
            fallidos += 1

    logger.info(f"=== ETL finalizado: {exitosos} exitosos, {fallidos} fallidos ===")

if __name__ == "__main__":
    run_etl()