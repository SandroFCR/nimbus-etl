import os
import azure.functions as func
from pydantic import ValidationError

from etl.extract import get_weather
from etl.transform import transform_weather
from etl.load import load_weather, init_db
from etl.logger import get_logger

logger = get_logger("function_app")

app = func.FunctionApp()

ciudades_raw = os.getenv("CIUDADES", "Lima")
CIUDADES = [c.strip() for c in ciudades_raw.split(",") if c.strip()]

# NCRONTAB: {segundo} {minuto} {hora} {dia} {mes} {dia-semana}
# Por defecto corre todos los dias a las 08:00 UTC
@app.timer_trigger(schedule="0 0 8 * * *", arg_name="mytimer", run_on_startup=False)
def clima_etl_timer(mytimer: func.TimerRequest) -> None:
    logger.info("=== Iniciando ETL de clima ===")
    init_db()
    exitosos = 0
    fallidos = 0

    for ciudad in CIUDADES:
        try:
            raw = get_weather(ciudad)
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
