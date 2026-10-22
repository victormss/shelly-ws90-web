---
name: deploy
description: >-
  Usar cuando el usuario pida desplegar, actualizar o hacer rollback en
  staging (MeteoTest, meteotest.victorsantos.com.es) o producción
  (MeteoProd, meteo.victorsantos.com.es); copiar frontend/nginx/init.sql a
  los servidores; preparar un servidor nuevo; renovar SSL; o diagnosticar
  errores (502, contenedores caídos, falta de memoria) en esos servidores.
---

# Deploy

Los servidores **no tienen el repo**. Todo vive en `/opt/weather-station`.
GitHub Actions publica la imagen de la API en GHCR. El servidor hace `pull` + `up`.

| | Staging | Producción |
|---|---|---|
| SSH | `MeteoTest` | `MeteoProd` |
| Compose | `docker-compose.staging.yml` | `docker-compose.yml` |
| Contenedores | `weather-api-staging`, `timescaledb-staging`, `weather-nginx-staging`, `weather-certbot-staging` | `weather-api`, `timescaledb`, `weather-nginx`, `weather-certbot` |
| Servicio nginx (compose) | `nginx-staging` | `nginx` |
| Tag imagen | `:staging` / `:staging-<sha7>` | `:latest` / `:sha-<sha7>` |
| Health | `https://meteotest.victorsantos.com.es/api/health` | `https://meteo.victorsantos.com.es/api/health` |

## Reglas

1. **Producción requiere confirmación explícita del usuario** antes de cualquier comando que modifique el servidor. Pide confirmación mostrando el tag/commit que se va a desplegar.
2. Desplegar en producción solo lo que ya se ha probado en staging.
3. Ejecuta siempre comandos SSH **no interactivos**: `ssh MeteoTest "cd /opt/weather-station && ..."`. No abras sesiones interactivas ni uses `nano`/`vim`.
4. El shell local es PowerShell: no uses `<` para redirigir. Usa `Get-Content archivo -Raw | ssh ...`.

## Procedimiento

### 1. Comprobaciones previas

- Confirma que el commit está en la rama correcta (`develop` → staging, `main` → prod):
  `git fetch origin; git log origin/develop --oneline -n 5`
- Confirma que el workflow ha terminado bien. `gh` no está instalado: pide al usuario que lo verifique en
  `https://github.com/victormss/shelly-ws90-web/actions`, o comprueba que existe el tag `staging-<sha7>`/`sha-<sha7>` en GHCR.
- Revisa qué ha cambiado desde el último deploy. Si hay cambios en `frontend/`, `nginx/` o `db/`, **no basta con el pull** (paso 3).

### 2. Desplegar la API

Usa el script:

```powershell
# Staging
.\.agents\skills\deploy\scripts\deploy.ps1 -Env staging

# Producción (solo tras confirmación del usuario)
.\.agents\skills\deploy\scripts\deploy.ps1 -Env prod -ConfirmProd
```

El script hace `pull` + `up -d --remove-orphans` + `ps` por SSH y luego verifica `/api/health` desde local.

### 3. Copiar archivos que no van en la imagen (si han cambiado)

```powershell
# Frontend (no requiere reinicio: nginx lo sirve desde el volumen)
.\.agents\skills\deploy\scripts\deploy.ps1 -Env staging -SyncFrontend -SkipApi

# Nginx: copiar y recargar
scp nginx/conf.d/staging.conf MeteoTest:/opt/weather-station/nginx/conf.d/staging.conf
ssh MeteoTest "cd /opt/weather-station && docker compose -f docker-compose.staging.yml exec nginx-staging nginx -t && docker compose -f docker-compose.staging.yml exec nginx-staging nginx -s reload"
```

En producción, el archivo que monta nginx es `nginx/conf.d/` completo (generado desde `default.ssl.conf.template`). Revisa el contenido en el servidor antes de sobrescribirlo.

Cambios en `db/init.sql`: **no** basta con copiarlo, porque solo se ejecuta con el volumen vacío. Usa la migración de la skill `add-sensor-field`.

### 4. Verificación (obligatoria)

- El script ya comprueba `/api/health`. Además:
  `Invoke-RestMethod https://<dominio>/api/weather/current` debe devolver datos recientes (menos de 10 min si Home Assistant está enviando).
- Si algo falla: [references/troubleshooting.md](references/troubleshooting.md).

## Rollback

Cada build publica un tag inmutable con el SHA corto del commit. Para volver a uno anterior sin editar el compose:

```powershell
git log origin/develop --oneline -n 10   # elegir <sha7> bueno (origin/main para prod)
.\.agents\skills\deploy\scripts\deploy.ps1 -Env staging -Tag staging-<sha7>
.\.agents\skills\deploy\scripts\deploy.ps1 -Env prod -Tag sha-<sha7> -ConfirmProd
```

El script hace `pull` del tag, lo re-etiqueta como `:staging`/`:latest` localmente y hace `up -d` sin volver a hacer pull.
El siguiente deploy normal volverá a la última imagen. Para un rollback permanente: `git revert` + push y esperar al CI.

## Referencias (leer solo si hace falta)

- [references/server-setup.md](references/server-setup.md): preparar un servidor nuevo y el primer certificado SSL.
- [references/troubleshooting.md](references/troubleshooting.md): diagnóstico por síntoma, SSL, memoria y GHCR login.
