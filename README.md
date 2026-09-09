# 🌤️ Clima ETL

Pipeline **ETL** (Extract → Transform → Load) en Python que consulta el clima actual de varias ciudades desde la API de [OpenWeatherMap](https://openweathermap.org/api), valida los datos y los persiste en **Azure SQL Database**. Corre en la nube como **Azure Function** con ejecución programada (timer trigger), o localmente vía `main.py`.

## Estado del proyecto

- ✅ Base de datos en la nube (**Azure SQL Database**, tier Serverless) creada y funcionando.
- ✅ Desplegado en **Azure Functions** (Python/Linux) con timer trigger corriendo solo, todos los días a las 08:00 UTC.
- ✅ **CI/CD con GitHub Actions**: cada `git push` a `main` despliega automáticamente a la Function App, sin pasos manuales.

## Arquitectura

```
                ┌────────────┐      ┌──────────────┐      ┌────────────┐      ┌───────────────────┐
  OpenWeather   │ extract.py │ ──▶ │ transform.py │ ──▶ │  load.py   │ ──▶ │  Azure SQL Database │
      API       │ (requests) │      │ (valida con  │      │ (pymssql)  │      │  (tier Serverless)  │
                └────────────┘      │  Pydantic)   │      └────────────┘      └───────────────────┘
                                     └──────────────┘
                       ▲
                       │
              Azure Functions
           (Timer Trigger, diario)
```

Cada ciudad pasa por las 3 etapas de forma independiente: si una falla (por ejemplo, datos inválidos o ciudad no encontrada), se registra el error y el ETL continúa con la siguiente. Los logs se envían a **Application Insights** cuando corre en Azure.

## Estructura del proyecto

```
CLIMA ETL/
├── main.py             # Orquesta el ETL manualmente (uso local/pruebas)
├── function_app.py      # Entry point de Azure Functions (timer trigger diario)
├── host.json             # Configuracion del runtime de Azure Functions
├── etl/
│   ├── extract.py       # Llama a la API de OpenWeatherMap
│   ├── transform.py     # Limpia y valida el JSON crudo
│   ├── model.py          # Modelo Pydantic (reglas de validación)
│   ├── load.py           # Crea la tabla e inserta/actualiza en Azure SQL
│   └── logger.py         # Logging a consola (+ archivo local fuera de Azure)
├── azure/
│   └── provision.ps1     # Script para crear los recursos de Azure (CLI)
├── requirements.txt
├── .env.example
└── logs/                 # Se genera solo en ejecucion local
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

## Despliegue en Azure

**Recursos usados:** Azure Functions (Consumption, Linux, Python) + Azure SQL Database (Serverless) + Application Insights.

1. Instalar herramientas:
   ```powershell
   winget install -e --id Microsoft.AzureCLI
   winget install -e --id Microsoft.Azure.FunctionsCoreTools
   az login
   ```
2. Provisionar los recursos (edita las variables/password dentro del script antes de correrlo):
   ```powershell
   ./azure/provision.ps1
   ```
3. Primer despliegue manual (solo la primera vez, para verificar que todo conecta bien):
   ```powershell
   func azure functionapp publish <nombre-de-tu-function-app>
   ```

El timer trigger (`function_app.py`) corre por defecto todos los días a las 08:00 UTC — se ajusta cambiando el `schedule` (formato NCRONTAB) del decorador `@app.timer_trigger`.

## CI/CD

El workflow [.github/workflows/deploy.yml](.github/workflows/deploy.yml) despliega automáticamente a la Function App en cada `git push` a `main` (o manualmente desde la pestaña *Actions* de GitHub). Requiere un secreto de repositorio `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` con el publish profile de la Function App:

```powershell
az functionapp deployment list-publishing-profiles --name <tu-function-app> --resource-group rg-clima-etl --xml | gh secret set AZURE_FUNCTIONAPP_PUBLISH_PROFILE
```

> Nota: Azure deshabilita por defecto la autenticación básica SCM en Function Apps nuevas. Si el deploy falla con `401 Unauthorized`, habilítala con:
> ```powershell
> az resource update --resource-group rg-clima-etl --name scm --namespace Microsoft.Web --resource-type basicPublishingCredentialsPolicies --parent sites/<tu-function-app> --set properties.allow=true
> ```

## Instalación (uso local)

```bash
git clone https://github.com/SandroFCR/clima-etl.git
cd clima-etl
pip install -r requirements.txt
```

Crea un archivo `.env` en la raíz (usa `.env.example` como base):

```env
OPENWEATHER_API_KEY=tu_api_key_de_openweathermap
CIUDADES=Lima,Buenos Aires,Santiago
AZURE_SQL_SERVER=tu-servidor.database.windows.net
AZURE_SQL_DATABASE=climadb
AZURE_SQL_USER=tu_usuario
AZURE_SQL_PASSWORD=tu_password
```

> Obtén una API key gratuita en [openweathermap.org/api](https://openweathermap.org/api). Las credenciales de `AZURE_SQL_*` salen del script de provisioning (paso anterior) — necesitas haber agregado tu IP a las reglas de firewall del servidor SQL para conectarte desde tu PC.

## Uso

```bash
python main.py
```

Para probar la Azure Function localmente (requiere Azure Functions Core Tools y completar `local.settings.json`):

```bash
func start
```

## Manejo de errores y logging

- Validación de datos con **Pydantic** (rangos de temperatura/humedad, campos no vacíos) — si un registro es inválido, se descarta y se loguea sin detener el proceso.
- Errores de red (HTTP, sin conexión) se capturan y registran por ciudad.
- Logging a consola siempre; en local además se escribe a `logs/etl_<fecha>.log`, en Azure los logs llegan a **Application Insights**.

## Deduplicación

La tabla `clima` tiene una restricción `UNIQUE(ciudad, fecha)`. Si el ETL corre varias veces el mismo día para la misma ciudad, el registro de ese día se **actualiza** (`MERGE`/upsert) en lugar de insertarse duplicado — la tabla siempre mantiene como máximo un registro por ciudad y día.

## Stack

- Python 3.11
- `requests` — cliente HTTP
- `pydantic` — validación de datos
- `pymssql` — conexión a Azure SQL Database
- `azure-functions` — runtime de Azure Functions (Python v2 programming model)
- `python-dotenv` — configuración por variables de entorno (uso local)
- Azure Functions, Azure SQL Database, Application Insights
- GitHub Actions — CI/CD (deploy automático a cada push a `main`)
