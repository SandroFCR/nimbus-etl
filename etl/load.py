import sqlite3
import os
from dotenv import load_dotenv
from .logger import get_logger

# Cargar .env desde la raiz del proyecto (un nivel arriba de etl/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env"), override=True)
logger = get_logger("load")

DB_PATH = os.path.join(project_root, os.getenv("SQLITE_DB", "clima.db"))

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clima (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ciudad TEXT NOT NULL,
            pais TEXT NOT NULL,
            temperatura REAL NOT NULL,
            sensacion REAL NOT NULL,
            humedad INTEGER NOT NULL,
            descripcion TEXT NOT NULL,
            viento_kmh REAL NOT NULL,
            timestamp TEXT NOT NULL,
            fecha TEXT NOT NULL,
            UNIQUE (ciudad, fecha)
        )
    """)
    conn.commit()
    conn.close()
    logger.info(f"Tabla 'clima' inicializada en {DB_PATH}")

def load_weather(data: dict):
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        # 1 registro por ciudad y dia: si ya existe, se actualiza en vez de duplicar
        cursor.execute("""
            INSERT INTO clima
            (ciudad, pais, temperatura, sensacion, humedad, descripcion, viento_kmh, timestamp, fecha)
            VALUES
            (:ciudad, :pais, :temperatura, :sensacion, :humedad,
             :descripcion, :viento_kmh, :timestamp, substr(:timestamp, 1, 10))
            ON CONFLICT (ciudad, fecha) DO UPDATE SET
                pais = excluded.pais,
                temperatura = excluded.temperatura,
                sensacion = excluded.sensacion,
                humedad = excluded.humedad,
                descripcion = excluded.descripcion,
                viento_kmh = excluded.viento_kmh,
                timestamp = excluded.timestamp
        """, data)
        conn.commit()
        logger.info(f"Guardado exitoso: {data['ciudad']} - {data['temperatura']}C")
    except sqlite3.Error as e:
        logger.error(f"Error al guardar en SQLite: {e}")
        raise
    finally:
        if conn:
            conn.close()
