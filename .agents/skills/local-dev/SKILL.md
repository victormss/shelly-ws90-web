---
name: local-dev
description: >-
  Usar para arrancar el stack en local (docker-compose.local.yml), ejecutar
  lint y tests igual que el CI, enviar datos de prueba al endpoint de ingest
  o verificar un cambio antes de hacer commit o abrir un PR.
---

# Desarrollo y verificación en local

Stack local: API en `http://localhost:8000` (directa), web + API vía nginx en `http://localhost:8080`, Postgres en `localhost:5432` (`weather` / `devpassword`).
Token de ingest local: `local-secret-key-for-testing`.

## 1. Lint y tests (igual que el CI)

Ejecutar desde la raíz del repo. Si faltan dependencias: `pip install flake8 pytest pytest-asyncio httpx -r weather-api/requirements.txt`.

```powershell
flake8 weather-api/app --count --select=E9,F63,F7,F82 --show-source --statistics   # bloqueante en CI
flake8 weather-api/app --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
Push-Location weather-api; python -m pytest tests/ -v --tb=short; Pop-Location
```

Los tests no necesitan BD. Si un test nuevo la necesita, está mal planteado para este CI: usa mocks.

## 2. Arrancar el stack

```powershell
docker compose -f docker-compose.local.yml up -d --build
docker compose -f docker-compose.local.yml ps          # timescaledb debe estar "healthy"
Invoke-RestMethod http://localhost:8000/api/health
```

## 3. Datos de prueba

```powershell
$headers = @{ Authorization = "Bearer local-secret-key-for-testing" }
$body = @{ temperature = 21.4; humidity = 58; pressure = 1015.2; wind_speed = 8.5;
           wind_direction = 225; wind_gust = 14.1; rain = 0.2; uv_index = 4; illuminance = 32000 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/weather/ingest -Headers $headers -ContentType 'application/json' -Body $body
Invoke-RestMethod http://localhost:8000/api/weather/current
Invoke-RestMethod "http://localhost:8000/api/weather/history?range=1h"
```

- Sin token → 403. Valor fuera de rango → 422. Ambos son comportamientos esperados.
- `/api/weather/stats` estará vacío al principio: los aggregates se refrescan por política (1 h / 1 día). Para forzarlo:
  `docker exec timescaledb-local psql -U weather -d weatherdb -c "CALL refresh_continuous_aggregate('hourly_weather_stats', NULL, NULL);"`

Frontend: abrir `http://localhost:8080`. Los archivos de `frontend/dist` se montan como volumen, así que basta con recargar el navegador.

## 4. Cambios de schema

- Probar la migración: `Get-Content db/migrations/<archivo>.sql -Raw | docker exec -i timescaledb-local psql -U weather -d weatherdb -v ON_ERROR_STOP=1`
- Probar `init.sql` desde cero: `docker compose -f docker-compose.local.yml down -v` (**borra los datos locales**) y después `up -d --build`.

## 5. Parar

```powershell
docker compose -f docker-compose.local.yml down        # conserva datos
```
