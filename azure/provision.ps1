# Provisiona los recursos de Azure para clima-etl.
# Requiere: az login previo (y la suscripcion correcta seleccionada con az account set).
# Ejecutar el script completo desde PowerShell: ./azure/provision.ps1

$ErrorActionPreference = "Stop"

# ---- Variables (ajusta los nombres si ya existen en tu suscripcion) ----
$RESOURCE_GROUP   = "rg-clima-etl"
$LOCATION         = "eastus2"      # el resource group ya quedo creado aqui, no afecta a los recursos hijos
$DEPLOY_LOCATION  = "centralus"    # region permitida por la politica de tu suscripcion de estudiante
$STORAGE_ACCOUNT  = "climaetlstorage$(Get-Random -Maximum 9999)"   # debe ser unico globalmente
$FUNCTION_APP     = "clima-etl-func-$(Get-Random -Maximum 9999)"   # debe ser unico globalmente
$SQL_SERVER       = "clima-etl-sql-$(Get-Random -Maximum 9999)"    # debe ser unico globalmente
$SQL_DATABASE     = "climadb"
$SQL_ADMIN_USER   = "climaadmin"

# ---- Password del admin de SQL: se pide en el momento, nunca queda escrito en el script ----
$securePass = Read-Host "Ingresa un password fuerte para el admin de Azure SQL (min 8 caracteres, con mayus/minus/numero/simbolo)" -AsSecureString
$SQL_ADMIN_PASS = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePass)
)

# ---- API key de OpenWeather: la toma de tu .env local si existe, si no la pide ----
$envPath = Join-Path $PSScriptRoot "..\.env"
$API_KEY = $null
if (Test-Path $envPath) {
    $line = Get-Content $envPath | Where-Object { $_ -match '^OPENWEATHER_API_KEY=' }
    if ($line) { $API_KEY = ($line -split '=', 2)[1].Trim() }
}
if (-not $API_KEY) {
    $API_KEY = Read-Host "Ingresa tu OPENWEATHER_API_KEY"
}

Write-Host ""
Write-Host "Resource Group: $RESOURCE_GROUP"
Write-Host "Storage Account: $STORAGE_ACCOUNT"
Write-Host "Function App: $FUNCTION_APP"
Write-Host "SQL Server: $SQL_SERVER"
Write-Host ""

# ---- 1. Resource Group ----
az group create --name $RESOURCE_GROUP --location $LOCATION

# ---- 2. Storage Account (requerido por Functions) ----
az storage account create `
  --name $STORAGE_ACCOUNT `
  --resource-group $RESOURCE_GROUP `
  --location $DEPLOY_LOCATION `
  --sku Standard_LRS

# ---- 3. Function App (Python 3.11, Linux, plan Consumption) ----
az functionapp create `
  --resource-group $RESOURCE_GROUP `
  --consumption-plan-location $DEPLOY_LOCATION `
  --runtime python `
  --runtime-version 3.11 `
  --os-type Linux `
  --functions-version 4 `
  --name $FUNCTION_APP `
  --storage-account $STORAGE_ACCOUNT

# ---- 4. Azure SQL Server + Database (tier Serverless, se auto-pausa si no se usa) ----
az sql server create `
  --name $SQL_SERVER `
  --resource-group $RESOURCE_GROUP `
  --location $DEPLOY_LOCATION `
  --admin-user $SQL_ADMIN_USER `
  --admin-password $SQL_ADMIN_PASS

az sql db create `
  --resource-group $RESOURCE_GROUP `
  --server $SQL_SERVER `
  --name $SQL_DATABASE `
  --edition GeneralPurpose `
  --compute-model Serverless `
  --family Gen5 `
  --capacity 1 `
  --auto-pause-delay 60 `
  --zone-redundant false

# ---- 5. Firewall: permitir que los servicios de Azure (la Function App) se conecten ----
az sql server firewall-rule create `
  --resource-group $RESOURCE_GROUP `
  --server $SQL_SERVER `
  --name AllowAzureServices `
  --start-ip-address 0.0.0.0 `
  --end-ip-address 0.0.0.0

# ---- 6. Firewall: permitir tu IP actual (para probar/conectarte desde tu PC) ----
$MY_IP = (Invoke-RestMethod -Uri "https://api.ipify.org")
az sql server firewall-rule create `
  --resource-group $RESOURCE_GROUP `
  --server $SQL_SERVER `
  --name AllowMyIP `
  --start-ip-address $MY_IP `
  --end-ip-address $MY_IP

# ---- 7. Configurar variables de entorno en la Function App ----
az functionapp config appsettings set `
  --name $FUNCTION_APP `
  --resource-group $RESOURCE_GROUP `
  --settings `
    OPENWEATHER_API_KEY="$API_KEY" `
    CIUDADES="Lima,Buenos Aires,Santiago" `
    AZURE_SQL_SERVER="$SQL_SERVER.database.windows.net" `
    AZURE_SQL_DATABASE="$SQL_DATABASE" `
    AZURE_SQL_USER="$SQL_ADMIN_USER" `
    AZURE_SQL_PASSWORD="$SQL_ADMIN_PASS"

Write-Host ""
Write-Host "===================================================="
Write-Host "Listo. Guarda estos datos para tu .env / local.settings.json:"
Write-Host "AZURE_SQL_SERVER=$SQL_SERVER.database.windows.net"
Write-Host "AZURE_SQL_DATABASE=$SQL_DATABASE"
Write-Host "AZURE_SQL_USER=$SQL_ADMIN_USER"
Write-Host "AZURE_SQL_PASSWORD=(el que acabas de ingresar)"
Write-Host "Function App: $FUNCTION_APP"
Write-Host "===================================================="
