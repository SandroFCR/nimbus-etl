# Crea un Azure Key Vault y migra los secretos del ETL (API key, password de SQL)
# desde App Settings en texto plano a referencias seguras de Key Vault.
# Requiere: recursos ya creados con provision.ps1 (Resource Group + Function App).
# Ejecutar desde PowerShell: ./azure/setup-keyvault.ps1

$ErrorActionPreference = "Stop"

function Invoke-Az {
    param([Parameter(Mandatory)][string[]]$ArgList)
    & az @ArgList
    if ($LASTEXITCODE -ne 0) {
        throw "Comando fallo (exit $LASTEXITCODE): az $($ArgList -join ' ')"
    }
}

$RESOURCE_GROUP  = "rg-clima-etl"
$FUNCTION_APP    = "clima-etl-func-8279"
$DEPLOY_LOCATION = "centralus"   # region permitida por la politica de tu suscripcion de estudiante
$KEYVAULT_NAME   = "clima-etl-kv-$(Get-Random -Maximum 9999)"   # debe ser unico globalmente (3-24 caracteres)

# ---- Leer los secretos actuales desde el .env local (o pedirlos si no estan) ----
$envPath = Join-Path $PSScriptRoot "..\.env"
function Get-EnvValue($key) {
    if (-not (Test-Path $envPath)) { return $null }
    $line = Get-Content $envPath | Where-Object { $_ -match "^$key=" }
    if ($line) { return ($line -split '=', 2)[1].Trim() }
    return $null
}

$API_KEY = Get-EnvValue "OPENWEATHER_API_KEY"
if (-not $API_KEY) { $API_KEY = Read-Host "Ingresa tu OPENWEATHER_API_KEY" }

$SQL_PASSWORD = Get-EnvValue "AZURE_SQL_PASSWORD"
if (-not $SQL_PASSWORD) {
    $securePass = Read-Host "Ingresa el password del admin de Azure SQL" -AsSecureString
    $SQL_PASSWORD = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePass)
    )
}

Write-Host ""
Write-Host "Key Vault a crear: $KEYVAULT_NAME"
Write-Host ""

# ---- 0. Registrar el resource provider si hace falta (igual que con Storage/Web/Sql) ----
az provider register --namespace Microsoft.KeyVault
Write-Host "Esperando a que Microsoft.KeyVault quede registrado..."
do {
    Start-Sleep -Seconds 5
    $state = az provider show --namespace Microsoft.KeyVault --query registrationState -o tsv
    Write-Host "  estado: $state"
} while ($state -ne "Registered")

# ---- 1. Crear el Key Vault (modelo de permisos por access policy, no RBAC) ----
Invoke-Az @("keyvault", "create", "--name", $KEYVAULT_NAME, "--resource-group", $RESOURCE_GROUP, "--location", $DEPLOY_LOCATION, "--enable-rbac-authorization", "false")

# ---- 2. Habilitar identidad administrada (system-assigned) en la Function App ----
Invoke-Az @("functionapp", "identity", "assign", "--name", $FUNCTION_APP, "--resource-group", $RESOURCE_GROUP)
$PRINCIPAL_ID = az functionapp identity show --name $FUNCTION_APP --resource-group $RESOURCE_GROUP --query principalId -o tsv

# ---- 3. Dar permiso de lectura de secretos a esa identidad (sin passwords adicionales) ----
Invoke-Az @("keyvault", "set-policy", "--name", $KEYVAULT_NAME, "--object-id", $PRINCIPAL_ID, "--secret-permissions", "get", "list")

# ---- 4. Guardar los secretos en el Key Vault ----
Invoke-Az @("keyvault", "secret", "set", "--vault-name", $KEYVAULT_NAME, "--name", "OPENWEATHER-API-KEY", "--value", $API_KEY) | Out-Null
Invoke-Az @("keyvault", "secret", "set", "--vault-name", $KEYVAULT_NAME, "--name", "AZURE-SQL-PASSWORD", "--value", $SQL_PASSWORD) | Out-Null

# ---- 5. Reemplazar los App Settings en texto plano por referencias a Key Vault ----
# Nota: los valores "@Microsoft.KeyVault(...)" con parentesis se rompen si se pasan
# directo como argumento en Windows (PowerShell/CMD los reinterpreta). Se escriben
# a un archivo JSON temporal y se usa "--settings @archivo.json" para evitarlo.
$settingsForJson = @(
    @{ name = "OPENWEATHER_API_KEY"; value = "@Microsoft.KeyVault(SecretUri=https://$KEYVAULT_NAME.vault.azure.net/secrets/OPENWEATHER-API-KEY/)"; slotSetting = $false },
    @{ name = "AZURE_SQL_PASSWORD"; value = "@Microsoft.KeyVault(SecretUri=https://$KEYVAULT_NAME.vault.azure.net/secrets/AZURE-SQL-PASSWORD/)"; slotSetting = $false }
)
$tempSettingsFile = Join-Path $env:TEMP "clima-etl-appsettings.json"
$settingsForJson | ConvertTo-Json | Set-Content -Path $tempSettingsFile -Encoding ascii

Invoke-Az @("functionapp", "config", "appsettings", "set", "--name", $FUNCTION_APP, "--resource-group", $RESOURCE_GROUP, "--settings", "@$tempSettingsFile")

Remove-Item $tempSettingsFile -Force

Write-Host ""
Write-Host "===================================================="
Write-Host "Listo. Key Vault: $KEYVAULT_NAME"
Write-Host "La Function App ahora lee OPENWEATHER_API_KEY y AZURE_SQL_PASSWORD desde Key Vault."
Write-Host "El codigo Python no cambia: Azure resuelve la referencia antes de que os.getenv() la vea."
Write-Host "Puede tardar ~1 minuto en propagarse. Verifica en Portal > Function App > Configuration"
Write-Host "que ambos valores muestren un check verde (resueltos), no un error."
Write-Host "===================================================="
