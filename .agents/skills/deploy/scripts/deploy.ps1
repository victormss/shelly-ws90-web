<#
.SYNOPSIS
    Despliega la weather-api en MeteoTest (staging) o MeteoProd (prod) via SSH no interactivo.

.DESCRIPTION
    - Por defecto: pull de la imagen + up -d --remove-orphans + ps + verificacion de /api/health.
    - -Tag: rollback a un tag concreto (staging-<sha7> / sha-<sha7>). Hace pull del tag,
      lo re-etiqueta como :staging / :latest y levanta sin volver a hacer pull.
    - -SyncFrontend: copia frontend/dist/ al servidor (nginx lo sirve desde un volumen).
    - -SkipApi: no toca la API (util junto con -SyncFrontend).
    - Produccion exige -ConfirmProd (el agente solo debe pasarlo tras confirmacion del usuario).

.EXAMPLE
    .\deploy.ps1 -Env staging
    .\deploy.ps1 -Env prod -ConfirmProd
    .\deploy.ps1 -Env staging -Tag staging-abc1234
    .\deploy.ps1 -Env staging -SyncFrontend -SkipApi
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('staging', 'prod')]
    [string]$Env,

    [string]$Tag,

    [switch]$ConfirmProd,
    [switch]$SyncFrontend,
    [switch]$SkipApi
)

$ErrorActionPreference = 'Stop'

$Image = 'ghcr.io/victormss/shelly-ws90-web/weather-api'
$RemoteDir = '/opt/weather-station'

if ($Env -eq 'prod') {
    $SshHost = 'MeteoProd'
    $ComposeFile = 'docker-compose.yml'
    $FloatingTag = 'latest'
    $Domain = 'meteo.victorsantos.com.es'
    $TagPrefix = 'sha-'
} else {
    $SshHost = 'MeteoTest'
    $ComposeFile = 'docker-compose.staging.yml'
    $FloatingTag = 'staging'
    $Domain = 'meteotest.victorsantos.com.es'
    $TagPrefix = 'staging-'
}

$Compose = "docker compose -f $ComposeFile"

function Invoke-Remote([string]$Command) {
    Write-Host "[$SshHost] $Command" -ForegroundColor DarkGray
    ssh $SshHost "cd $RemoteDir && $Command"
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo en $SshHost (exit $LASTEXITCODE): $Command"
    }
}

# --- Guardarrailes -----------------------------------------------------------
if ($Env -eq 'prod' -and -not $ConfirmProd) {
    throw 'Despliegue a produccion bloqueado: falta -ConfirmProd. Pide confirmacion explicita al usuario.'
}

if ($Tag -and -not $Tag.StartsWith($TagPrefix)) {
    throw "El tag '$Tag' no corresponde a $Env (debe empezar por '$TagPrefix')."
}

if (-not $SkipApi) {
    # El compose del servidor debe usar la imagen de GHCR, no 'build:' (el servidor no tiene el codigo).
    ssh $SshHost "grep -q 'image: ghcr.io/.*weather-api' $RemoteDir/$ComposeFile"
    if ($LASTEXITCODE -ne 0) {
        throw "$RemoteDir/$ComposeFile en $SshHost no referencia la imagen de GHCR (usa 'build:'?). Un pull no actualizaria la API. Revisalo con el usuario."
    }
}

# --- Frontend ----------------------------------------------------------------
if ($SyncFrontend) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
    $Dist = Join-Path $RepoRoot 'frontend\dist'
    Write-Host "Copiando $Dist -> ${SshHost}:$RemoteDir/frontend/dist/" -ForegroundColor Cyan
    Get-ChildItem $Dist | ForEach-Object {
        scp -r $_.FullName "${SshHost}:$RemoteDir/frontend/dist/"
        if ($LASTEXITCODE -ne 0) { throw "Fallo copiando $($_.Name)" }
    }
}

# --- API ---------------------------------------------------------------------
if (-not $SkipApi) {
    if ($Tag) {
        Write-Host "Rollback de $Env a ${Image}:$Tag" -ForegroundColor Yellow
        Invoke-Remote "docker pull ${Image}:$Tag && docker tag ${Image}:$Tag ${Image}:$FloatingTag"
        Invoke-Remote "$Compose up -d --no-build --remove-orphans"
    } else {
        Write-Host "Desplegando ultima imagen :$FloatingTag en $Env" -ForegroundColor Cyan
        Invoke-Remote "$Compose pull"
        Invoke-Remote "$Compose up -d --remove-orphans"
    }
    Invoke-Remote "$Compose ps"
}

# --- Verificacion ------------------------------------------------------------
$HealthUrl = "https://$Domain/api/health"
Write-Host "Verificando $HealthUrl ..." -ForegroundColor Cyan
$ok = $false
for ($i = 1; $i -le 10; $i++) {
    try {
        $health = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 5
        if ($health.status -eq 'healthy') { $ok = $true; break }
        Write-Host "  intento ${i}: status=$($health.status) database=$($health.database)"
    } catch {
        Write-Host "  intento ${i}: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds 3
}

if (-not $ok) {
    throw "Health check fallido en $HealthUrl. Ver references/troubleshooting.md"
}

Write-Host "OK: $Env sano -> version $($health.version), database $($health.database)" -ForegroundColor Green
