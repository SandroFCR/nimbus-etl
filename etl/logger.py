import logging
import os
from datetime import datetime

def get_logger(name: str) -> logging.Logger:

    # Crea la carpeta logs si no existe
    os.makedirs("logs", exist_ok=True)

    # Nombre del archivo con la fecha de hoy
    fecha = datetime.now().strftime("%Y-%m-%d")
    archivo_log = f"logs/etl_{fecha}.log"

    # Formato del mensaje
    formato = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Handler 1 — muestra en pantalla
    consola = logging.StreamHandler()
    consola.setLevel(logging.INFO)
    consola.setFormatter(logging.Formatter(formato))

    # Handler 2 — guarda en archivo
    archivo = logging.FileHandler(archivo_log, encoding="utf-8")
    archivo.setLevel(logging.DEBUG)
    archivo.setFormatter(logging.Formatter(formato))

    # Evita duplicar mensajes si llamas get_logger varias veces
    if not logger.handlers:
        logger.addHandler(consola)
        logger.addHandler(archivo)

    return logger