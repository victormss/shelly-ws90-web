# Troubleshooting

Todos los comandos son de solo lectura salvo que se indique otra cosa. En producción, los marcados **(modifica)** requieren confirmación del usuario.

Variables según entorno:

| | Staging | Producción |
|---|---|---|
| `H` (host SSH) | `MeteoTest` | `MeteoProd` |
| `C` (compose) | `docker compose -f docker-compose.staging.yml` | `docker compose` |
| api / db / nginx | `weather-api-staging` / `timescaledb-staging` / `weather-nginx-staging` | `weather-api` / `timescaledb` / `weather-nginx` |
| servicio api / db / nginx / certbot | `weather-api` / `timescaledb-staging` / `nginx-staging` / `certbot-staging` | `weather-api` / `timescaledb` / `nginx` / `certbot` |
| dominio | `meteotest.victorsantos.com.es` | `meteo.victorsantos.com.es` |

Patrón: `ssh <H> "cd /opt/weather-station && <C> <comando>"`

## Diagnóstico rápido (empezar siempre aquí)

```powershell
ssh MeteoTest "cd /opt/weather-station && docker compose -f docker-compose.staging.yml ps"
ssh MeteoTest "cd /opt/weather-station && docker compose -f docker-compose.staging.yml logs --tail=50"
ssh MeteoTest "free -m && docker stats --no-stream"
```

## Por síntoma

### Contenedor reiniciando / no arranca
- `logs <servicio> --tail=100`
- API con `connection refused` a la BD → la BD no está healthy (ver abajo).
- API con `KeyError`/validation error de settings → falta una variable en `.env` del servidor.
- `manifest unknown` / `denied` en el pull → login de GHCR caducado (ver abajo).

### La BD no está healthy
```powershell
ssh MeteoTest "docker exec timescaledb-staging pg_isready -U weather -d weatherdb"
ssh MeteoTest "docker exec timescaledb-staging psql -U weather -d weatherdb -c 'SELECT max(time) FROM weather_data'"
```

### 502 Bad Gateway
```powershell
ssh MeteoTest "docker exec weather-nginx-staging wget -qO- http://weather-api:8000/api/health"
```
- Si falla: la API está caída o en otra red de Docker → `ps` y `logs weather-api`.
- Si funciona: revisar el `upstream` de la conf de nginx y recargarla.

### `/api/weather/current` devuelve datos antiguos o `null`
El problema está antes de la API: Home Assistant no está enviando.
- `logs weather-api --tail=100 | grep ingest`: ¿llegan POST? ¿con 403 (token incorrecto) o 422 (valor fuera de rango en `WeatherIngest`)?
- 429 → rate limit de nginx (15 r/m en ingest).
- Si no llega nada: revisar en Home Assistant la URL del `rest_command` y el logbook "Weather Cloud Sync".

### SSL caducado / no funciona
```powershell
ssh MeteoTest "docker exec weather-nginx-staging ls -la /etc/letsencrypt/live/meteotest.victorsantos.com.es/"
ssh MeteoTest "cd /opt/weather-station && docker compose -f docker-compose.staging.yml logs certbot-staging --tail=30"
```
**(modifica)** Renovar a mano:
```powershell
ssh MeteoTest "cd /opt/weather-station && docker compose -f docker-compose.staging.yml run --rm --entrypoint certbot certbot-staging renew && docker compose -f docker-compose.staging.yml exec nginx-staging nginx -s reload"
```

### Memoria insuficiente (1 GB)
- `docker stats --no-stream`: la BD debería rondar ≤ 300 MB con `shared_buffers=128MB`.
- `dmesg | tail` o `journalctl -k | grep -i oom` → ¿OOM killer?
- **(modifica)** Liberar temporalmente: parar certbot (`<C> stop <servicio-certbot>`). Avisar al usuario antes de cambiar parámetros de Postgres o workers de uvicorn.

### Login GHCR caducado
El PAT (scope `read:packages`) lo tiene el usuario. Pídele que ejecute:
`ssh MeteoTest "echo <PAT> | docker login ghcr.io -u victormss --password-stdin"`
No escribas ni guardes el PAT en archivos del repo.

### Firewall / no hay acceso externo
Docker publica puertos por `PREROUTING/FORWARD`, no por `INPUT`. Revisar en orden: Security List de Oracle Cloud → `sudo iptables -L FORWARD -n` → `docker ps` (¿puertos 80/443 publicados?). Hay un diagnóstico previo de este problema en `reports/diagnostico_conexion.md` (solo local, no versionado).
