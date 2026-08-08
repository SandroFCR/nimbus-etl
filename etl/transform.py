from datetime import datetime
from .model import WeatherRecord

def transform_weather(raw: dict) -> dict:
    datos = {
        "ciudad":      raw["name"],
        "pais":        raw["sys"]["country"],
        "temperatura": raw["main"]["temp"],
        "sensacion":   raw["main"]["feels_like"],
        "humedad":     raw["main"]["humidity"],
        "descripcion": raw["weather"][0]["description"],
        "viento_kmh":  round(raw["wind"]["speed"] * 3.6, 1),
        "timestamp":   datetime.utcnow().isoformat()
    }

    record = WeatherRecord(**datos)
    return record.model_dump()