---
trigger: always_on
---

# Arquitectura del proyecto

## Visión general

Estación meteorológica Ecowitt WS90 con datos recogidos vía Zigbee2MQTT → Home Assistant → API REST → TimescaleDB. El frontend web muestra los datos en tiempo real.

## Stack tecnológico

- **API**: Python 3.12 + FastAPI + uvicorn (2 workers)
- **Base de datos**: TimescaleDB (PostgreSQL 16) con hypertables, vistas materializadas (hourly/daily) y retención de 1 año
- **ORM**: SQLAlchemy (async) con `asyncpg`
- **Config**: pydantic-settings, variables de entorno vía `.env`
- **Frontend**: HTML/CSS/JS estático servido por Nginx
- **Proxy/SSL**: Nginx + Let's Encrypt (certbot)
- **Contenedores**: Docker Compose
- **CI/CD**: GitHub Actions → GHCR → deploy SSH
- **Registro de imágenes**: `ghcr.io/victormss/shelly-ws90-web/weather-api`

## Entornos e infraestructura

| Entorno | Servidor SSH | Dominio | Rama | Docker Compose | Imagen tag |
|---|---|---|---|---|---|
| Producción | `MeteoProd` | `meteo.victorsantos.com.es` | `main` | `docker-compose.yml` | `:latest` |
| Staging | `MeteoTest` | `meteotest.victorsantos.com.es` | `develop` | `docker-compose.staging.yml` | `:staging` |
| Local | localhost | `localhost:8080` | cualquiera | `docker-compose.local.yml` | build local |

Los servidores MeteoProd y MeteoTest son **máquinas separadas** (Oracle Cloud, 1GB RAM cada una). No comparten puertos ni volúmenes.

## Estrategia de ramas y CI/CD

```
feature/* → PR a develop → CI (lint + pytest + docker build) → merge → build :staging → deploy MeteoTest automático
develop  → PR a main     → CI (lint + pytest + docker build) → aprobación PR → merge → build :latest → aprobación environment → deploy MeteoProd
```

- **`main`**: Protegida. Solo recibe PRs aprobados desde `develop`. Deploy a producción requiere aprobación del environment `production` en GitHub.
- **`develop`**: Integración y staging. Push dispara build + deploy automático a MeteoTest.
- **`feature/*`**: Desarrollo. PRs hacia `develop`.

## Estructura del proyecto

```
├── .github/workflows/
│   ├── ci.yml              # CI/CD producción (main)
│   └── staging.yml         # CI/CD staging (develop)
├── weather-api/
│   ├── app/
│   │   ├── main.py         # FastAPI app, health check, lifespan
│   │   ├── config.py       # pydantic-settings (env vars)
│   │   ├── database.py     # SQLAlchemy async engine
│   │   ├── models.py       # WeatherData model
│   │   ├── schemas.py      # Pydantic schemas (ingest, response, health)
│   │   ├── auth.py         # API key auth
│   │   └── routers/
│   │       ├── ingest.py   # POST /api/weather/ingest (autenticado)
│   │       └── weather.py  # GET /api/weather/* (público)
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_health.py  # Smoke tests (schemas, models, validaciones)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/dist/           # Frontend estático (HTML/CSS/JS)
├── nginx/conf.d/
│   ├── default.conf         # Nginx HTTP (desarrollo local)
│   ├── default.ssl.conf.template  # Nginx HTTPS producción
│   └── staging.conf         # Nginx HTTPS staging
├── db/init.sql              # Schema TimescaleDB + vistas materializadas
├── docker-compose.yml       # Producción
├── docker-compose.staging.yml  # Staging
├── docker-compose.local.yml    # Desarrollo local
└── .env.example / .env.staging.example
```

## Convenciones importantes

- Los endpoints API van bajo el prefijo `/api/` (ej: `/api/health`, `/api/weather/ingest`)
- Docs Swagger en `/api/docs`, ReDoc en `/api/redoc`
- La ingestión de datos (`POST /api/weather/ingest`) requiere API key en el header `Authorization`
- Los endpoints de lectura (`GET /api/weather/*`) son públicos
- Nginx aplica rate limiting: 30r/m para API pública, 15r/m para ingest
- Las imágenes Docker se publican en GHCR, el login en los servidores usa un PAT (`GHCR_PAT` secret)
- Los tests se ejecutan sin base de datos real (mocks/unit tests sobre schemas y modelos)
