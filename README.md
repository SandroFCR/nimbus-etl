# 🌤️ Clima ETL

Pipeline **ETL** (Extract → Transform → Load) en Python que consulta el clima actual de varias ciudades desde la API de [OpenWeatherMap](https://openweathermap.org/api), valida los datos y los persiste en una base de datos **SQLite** local.

## Arquitectura

```
                ┌────────────┐      ┌──────────────┐      ┌────────────┐
  OpenWeather   │  extract.py │ ──▶ │ transform.py  │ ──▶ │  load.py    │ ──▶  clima.db
      API       │  (requests) │      │ (valida con   │      │ (SQLite)   │
                └────────────┘      │  Pydantic)    │      └────────────┘
                                     └──────────────┘
```

Cada ciudad pasa por las 3 etapas de forma independiente: si una falla (por ejemplo, datos inválidos o ciudad no encontrada), se registra el error y el ETL continúa con la siguiente.

## Estructura del proyecto

```
CLIMA ETL/
├── main.py            # Orquesta el ETL para todas las ciudades configuradas
├── etl/
│   ├── extract.py      # Llama a la API de OpenWeatherMap
│   ├── transform.py    # Limpia y valida el JSON crudo
│   ├── model.py         # Modelo Pydantic (reglas de validación)
│   ├── load.py          # Crea la tabla e inserta los registros en SQLite
│   └── logger.py        # Logging a consola y a archivo
├── requirements.txt
├── .env.example
└── logs/                # Se genera automáticamente (1 archivo por día)
```

## Datos que captura

| Campo         | Descripción                          |
|---------------|---------------------------------------|
| `ciudad`      | Nombre de la ciudad                   |
| `pais`        | Código de país (ISO)                  |
| `temperatura` | Temperatura actual (°C)               |
| `sensacion`   | Sensación térmica (°C)                |
| `humedad`     | Humedad relativa (%)                  |
| `descripcion` | Descripción del clima (ej. "nublado") |
| `viento_kmh`  | Velocidad del viento (km/h)           |
| `timestamp`   | Fecha/hora UTC de la última consulta  |
| `fecha`       | Día (YYYY-MM-DD) derivado del timestamp, usado como clave de deduplicación |

## Instalación

```bash
git clone <tu-repo>
cd "CLIMA ETL"
pip install -r requirements.txt
```

Crea un archivo `.env` en la raíz (usa `.env.example` como base):

```env
OPENWEATHER_API_KEY=tu_api_key_de_openweathermap
CIUDADES=Lima,Buenos Aires,Santiago
SQLITE_DB=clima.db
```

> Obtén una API key gratuita en [openweathermap.org/api](https://openweathermap.org/api).

## Uso

```bash
python main.py
```

Salida esperada:

```
2026-08-07 19:55:20 | INFO | main    | === Iniciando ETL de clima ===
2026-08-07 19:55:20 | INFO | load    | Tabla 'clima' inicializada en ...\clima.db
2026-08-07 19:55:20 | INFO | extract | Consultando clima de: Lima
2026-08-07 19:55:21 | INFO | load    | Guardado exitoso: Lima - 20.5C
2026-08-07 19:55:21 | INFO | main    | ETL exitoso para Lima
2026-08-07 19:55:25 | INFO | main    | === ETL finalizado: 9 exitosos, 0 fallidos ===
```

Los datos quedan en `clima.db`. Para consultarlos:

```bash
python -c "import sqlite3; print(sqlite3.connect('clima.db').execute('SELECT * FROM clima').fetchall())"
```

O ábrelo con [DB Browser for SQLite](https://sqlitebrowser.org/) o la extensión **SQLite Viewer** de VS Code.

## Manejo de errores y logging

- Validación de datos con **Pydantic** (rangos de temperatura/humedad, campos no vacíos) — si un registro es inválido, se descarta y se loguea sin detener el proceso.
- Errores de red (HTTP, sin conexión) se capturan y registran por ciudad.
- Logs duales: consola (nivel `INFO`) y archivo diario en `logs/etl_<fecha>.log` (nivel `DEBUG`).

## Deduplicación

La tabla `clima` tiene una restricción `UNIQUE(ciudad, fecha)`. Si corres el ETL varias veces el mismo día para la misma ciudad, el registro de ese día se **actualiza** (`UPSERT`) en lugar de insertarse duplicado — la tabla siempre mantiene como máximo un registro por ciudad y día.

## Stack

- Python 3.11
- `requests` — cliente HTTP
- `pydantic` — validación de datos
- `sqlite3` (stdlib) — persistencia local, sin servidor
- `python-dotenv` — configuración por variables de entorno
