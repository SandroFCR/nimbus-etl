import requests
import os
from dotenv import load_dotenv
from .logger import get_logger

# Cargar .env desde la raiz del proyecto (un nivel arriba de etl/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env"), override=True)

API_KEY = os.getenv("OPENWEATHER_API_KEY")
logger = get_logger("extract")          # le das un nombre para saber de dónde viene

def get_weather(city: str) -> dict:
    logger.info(f"Consultando clima de: {city}")
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": API_KEY,
            "units": "metric",
            "lang": "es"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        logger.debug(f"Respuesta recibida para {city}: status {response.status_code}")
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error HTTP al consultar {city}: {e}")
        raise
    except requests.exceptions.ConnectionError:
        logger.critical("Sin conexion a internet")
        raise