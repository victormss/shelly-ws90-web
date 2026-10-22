---
trigger: always_on
---

# Arquitectura del proyecto

## Visión general

Estación meteorológica Ecowitt WS90. Flujo de datos:

```
WS90 → Zigbee2MQTT → Home Assistant (rest_command cada 5 min)
     → POST /api/weather/ingest → FastAPI → TimescaleDB
     → GET /api/weather/* → frontend estático (Nginx)
```

## Stack tecnológico

- **API**: Python 3.12 + FastAPI + uvicorn (2 workers)
- **Base de datos**: TimescaleDB (PostgreSQL 16), hypertable `weather_data`, continuous aggregates `hourly_weather_stats` / `daily_weather_stats`, retención de 1 año
- **ORM**: SQLAlchemy async + `asyncpg` (los endpoints de lectura usan SQL crudo con `text()`)
- **Config**: pydantic-settings, variables de entorno vía `.env`
- **Frontend**: HTML/CSS/JS vanilla en `frontend/dist/`, sin build
- **Proxy/SSL**: Nginx + Let's Encrypt (certbot)
- **CI/CD**: GitHub Actions → build + push a GHCR. **No hay deploy automático**; los servidores hacen pull
- **Registro de imágenes**: `ghcr.io/victormss/shelly-ws90-web/weather-api`

## Entornos e infraestructura

| Entorno | Servidor SSH | Dominio | Rama | Docker Compose | Tags de imagen |
|---|---|---|---|---|---|
| Producción | `MeteoProd` | `meteo.victorsantos.com.es` | `main` | `docker-compose.yml` | `:latest`, `:sha-<sha7>` |
| Staging | `MeteoTest` | `meteotest.victorsantos.com.es` | `develop` | `docker-compose.staging.yml` | `:staging`, `:staging-<sha7>` |
| Local | localhost | `localhost:8080` (API directa en `:8000`) | cualquiera | `docker-compose.local.yml` | build local |

- MeteoProd y MeteoTest son **máquinas separadas** (Oracle Cloud, 1 GB RAM cada una). No comparten puertos ni volúmenes.
- Los servidores **no tienen el repo clonado**: solo `/opt/weather-station` con compose, `.env`, `nginx/`, `db/init.sql` y `frontend/dist/`.
- Por tanto, **la imagen Docker solo contiene la API**. Cambios en `frontend/`, `nginx/` o `db/` hay que copiarlos al servidor a mano (ver skill `deploy`).
- Para operar en los servidores, usar siempre la skill `deploy`.

## Estrategia de ramas y CI/CD

```
feature/* → PR a develop → CI (flake8 + pytest + docker build) → merge → push :staging a GHCR
develop   → PR a main    → CI → aprobación PR → merge → push :latest a GHCR
```

- **`main`**: protegida. Solo recibe PRs aprobados desde `develop`.
- **`develop`**: integración y staging.
- **`feature/*`**: desarrollo. PRs hacia `develop`.

## Mapa de piezas clave

| Qué | Dónde |
|---|---|
| App FastAPI, health check, lifespan | `weather-api/app/main.py` |
| Modelo ORM | `weather-api/app/models.py` |
| Validación ingest (rangos físicos) y respuestas | `weather-api/app/schemas.py` |
| Endpoints | `weather-api/app/routers/{ingest,weather}.py` |
| Schema de BD + continuous aggregates | `db/init.sql` |
| Payload que envía Home Assistant | `homeassistant/weather_automation.yaml` |
| Nginx: local / prod / staging | `nginx/conf.d/{default.conf, default.ssl.conf.template, staging.conf}` |
| Workflows | `.github/workflows/{ci.yml (main), staging.yml (develop)}` |

## Convenciones de la API

- Todos los endpoints bajo `/api/` (ej: `/api/health`, `/api/weather/ingest`). Swagger en `/api/docs`, ReDoc en `/api/redoc`.
- `POST /api/weather/ingest` requiere `Authorization: Bearer <API_SECRET_KEY>`.
- `GET /api/weather/*` son públicos.
- Nginx aplica rate limiting: 30 r/m API pública, 15 r/m ingest.
- Todos los campos meteorológicos son opcionales (`Optional[float]`); los rangos físicos se validan en `WeatherIngest`.
- Los tests corren **sin base de datos** (unit tests sobre schemas y modelos, mocks). No añadir tests que requieran Postgres al CI.
