import logging
import os
from datetime import datetime

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Evita duplicar handlers si llamas get_logger varias veces
    if logger.handlers:
        return logger

    formato = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

    # Handler 1 — muestra en pantalla (en Azure Functions, esto llega a Application Insights)
    consola = logging.StreamHandler()
    consola.setLevel(logging.INFO)
    consola.setFormatter(logging.Formatter(formato))
    logger.addHandler(consola)

    # Handler 2 — archivo local, solo fuera de Azure Functions (ahi el filesystem es efimero)
    if not os.getenv("FUNCTIONS_WORKER_RUNTIME"):
        os.makedirs("logs", exist_ok=True)
        fecha = datetime.now().strftime("%Y-%m-%d")
        archivo = logging.FileHandler(f"logs/etl_{fecha}.log", encoding="utf-8")
        archivo.setLevel(logging.DEBUG)
        archivo.setFormatter(logging.Formatter(formato))
        logger.addHandler(archivo)

    return logger