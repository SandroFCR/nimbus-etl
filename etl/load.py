import pymssql
import os
from dotenv import load_dotenv
from .logger import get_logger

# Cargar .env desde la raiz del proyecto (un nivel arriba de etl/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env"), override=True)
logger = get_logger("load")

AZURE_SQL_SERVER   = os.getenv("AZURE_SQL_SERVER")    # ej. mi-servidor.database.windows.net
AZURE_SQL_DATABASE = os.getenv("AZURE_SQL_DATABASE")
AZURE_SQL_USER     = os.getenv("AZURE_SQL_USER")
AZURE_SQL_PASSWORD = os.getenv("AZURE_SQL_PASSWORD")

def get_conn():
    return pymssql.connect(
        server=AZURE_SQL_SERVER,
        user=AZURE_SQL_USER,
        password=AZURE_SQL_PASSWORD,
        database=AZURE_SQL_DATABASE,
    )

def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'clima')
        CREATE TABLE clima (
            id INT IDENTITY(1,1) PRIMARY KEY,
            ciudad NVARCHAR(255) NOT NULL,
            pais NVARCHAR(255) NOT NULL,
            temperatura FLOAT NOT NULL,
            sensacion FLOAT NOT NULL,
            humedad INT NOT NULL,
            descripcion NVARCHAR(255) NOT NULL,
            viento_kmh FLOAT NOT NULL,
            timestamp NVARCHAR(255) NOT NULL,
            fecha DATE NOT NULL,
            CONSTRAINT UQ_clima_ciudad_fecha UNIQUE (ciudad, fecha)
        )
    """)
    conn.commit()
    conn.close()
    logger.info(f"Tabla 'clima' inicializada en Azure SQL ({AZURE_SQL_SERVER}/{AZURE_SQL_DATABASE})")

def load_weather(data: dict):
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        payload = {**data, "fecha": data["timestamp"][:10]}
        # 1 registro por ciudad y dia: si ya existe, se actualiza en vez de duplicar
        cursor.execute("""
            MERGE clima AS target
            USING (SELECT %(ciudad)s AS ciudad, %(fecha)s AS fecha) AS source
            ON target.ciudad = source.ciudad AND target.fecha = source.fecha
            WHEN MATCHED THEN
                UPDATE SET pais = %(pais)s, temperatura = %(temperatura)s, sensacion = %(sensacion)s,
                           humedad = %(humedad)s, descripcion = %(descripcion)s,
                           viento_kmh = %(viento_kmh)s, timestamp = %(timestamp)s
            WHEN NOT MATCHED THEN
                INSERT (ciudad, pais, temperatura, sensacion, humedad, descripcion, viento_kmh, timestamp, fecha)
                VALUES (%(ciudad)s, %(pais)s, %(temperatura)s, %(sensacion)s, %(humedad)s,
                        %(descripcion)s, %(viento_kmh)s, %(timestamp)s, %(fecha)s);
        """, payload)
        conn.commit()
        logger.info(f"Guardado exitoso: {data['ciudad']} - {data['temperatura']}C")
    except pymssql.Error as e:
        logger.error(f"Error al guardar en Azure SQL: {e}")
        raise
    finally:
        if conn:
            conn.close()
