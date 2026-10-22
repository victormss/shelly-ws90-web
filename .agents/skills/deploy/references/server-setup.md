# Setup inicial de un servidor nuevo

Solo para preparar una máquina desde cero. Los ejemplos son de staging; para producción usa la columna correspondiente:

| | Staging | Producción |
|---|---|---|
| SSH | `MeteoTest` | `MeteoProd` |
| Compose (repo → servidor) | `docker-compose.staging.yml` | `docker-compose.yml` (**cambiar `build: ./weather-api` por `image: ghcr.io/victormss/shelly-ws90-web/weather-api:latest`**) |
| Nginx (repo → servidor) | `nginx/conf.d/staging.conf` → `nginx/conf.d/staging.conf` | `nginx/conf.d/default.ssl.conf.template` → `nginx/conf.d/default.conf` (sustituir dominio) |
| Servicios certbot / nginx | `certbot-staging` / `nginx-staging` | `certbot` / `nginx` |
| Env de ejemplo | `.env.staging.example` | `.env.example` |

## Prerrequisitos (verificar antes)

```powershell
ssh MeteoTest "docker --version && docker compose version"
ssh MeteoTest "free -m"                                  # ~1 GB esperado
Resolve-DnsName meteotest.victorsantos.com.es             # debe apuntar a la IP pública del servidor
```

Los puertos 80/443 deben estar abiertos en la Security List de Oracle Cloud **y** en el iptables de la VM.

## Pasos (todos no interactivos, desde la máquina local)

```powershell
# 1. Directorio
ssh MeteoTest "sudo mkdir -p /opt/weather-station && sudo chown `$USER:`$USER /opt/weather-station && mkdir -p /opt/weather-station/{nginx/conf.d,nginx/certbot-webroot,frontend/dist,db}"

# 2. Copiar archivos del repo
scp docker-compose.staging.yml MeteoTest:/opt/weather-station/
scp nginx/conf.d/staging.conf  MeteoTest:/opt/weather-station/nginx/conf.d/
scp db/init.sql                MeteoTest:/opt/weather-station/db/
.\.agents\skills\deploy\scripts\deploy.ps1 -Env staging -SyncFrontend -SkipApi   # fallará el health check: es normal aquí

# 3. .env: NO lo generes tú con secretos inventados en el chat. Pide al usuario que lo cree,
#    partiendo de .env.staging.example. Variables: DB_PASSWORD, API_SECRET_KEY, ALLOWED_ORIGINS, TZ.
#    Generar secreto: python -c "import secrets; print(secrets.token_urlsafe(32))"

# 4. Login en GHCR (el usuario debe introducir el PAT con scope read:packages)
#    ssh MeteoTest "echo <PAT> | docker login ghcr.io -u victormss --password-stdin"

# 5. Primer arranque
.\.agents\skills\deploy\scripts\deploy.ps1 -Env staging    # el health por HTTPS fallará hasta tener certificado
ssh MeteoTest "curl -sf http://localhost/api/health"
```

## Certificado SSL inicial

Nginx necesita el certificado para arrancar el bloque 443. Si nginx no arranca por falta de certificado, comenta temporalmente el `server` 443, arranca, emite el certificado y restaura.

```powershell
ssh MeteoTest "cd /opt/weather-station && docker compose -f docker-compose.staging.yml run --rm --entrypoint certbot certbot-staging certonly --webroot -w /var/www/certbot -d meteotest.victorsantos.com.es --email <email-del-usuario> --agree-tos --no-eff-email --non-interactive"
ssh MeteoTest "cd /opt/weather-station && docker compose -f docker-compose.staging.yml restart nginx-staging"
Invoke-RestMethod https://meteotest.victorsantos.com.es/api/health
```

> El servicio certbot del compose tiene un `entrypoint` propio (bucle de renovación). Por eso hay que usar `--entrypoint certbot` con `run`.

## Home Assistant

Tras el primer arranque, la URL de `rest_command.send_weather_data` en Home Assistant debe apuntar al dominio del entorno. El token (`input_text.weather_api_token`) debe ser igual que `API_SECRET_KEY`. Ver `homeassistant/weather_automation.yaml`.
