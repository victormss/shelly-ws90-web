---
name: deploy
description: >
  Instrucciones paso a paso para desplegar en staging (MeteoTest) y producción (MeteoProd).
  Incluye setup inicial de servidor, certificados SSL, deploy manual, rollback y troubleshooting.
---

# Skill: Deploy

## Arquitectura de despliegue

Los servidores **no tienen el repositorio clonado**. Solo contienen los archivos de configuración necesarios (`docker-compose.yml`, `.env`, nginx conf, `db/init.sql`, frontend) creados manualmente una única vez.

**GitHub Actions** solo se encarga de:
- Lint + tests
- Build de la imagen Docker
- Push a GHCR con el tag correspondiente (`:staging` o `:latest`)

**Los servidores** se encargan de descargar las imágenes desde GHCR ellos mismos (manual o automáticamente vía Watchtower/cron).

## Flujo CI/CD

### Staging

```
Push a develop
    │
    ▼
GitHub Actions (staging.yml)
    ├── 1. Lint (flake8)
    ├── 2. Tests (pytest)
    ├── 3. Build imagen Docker
    └── 4. Push a GHCR con tag :staging
            → ghcr.io/victormss/shelly-ws90-web/weather-api:staging

(La imagen queda disponible en GHCR para que MeteoTest la descargue)
```

### Producción

```
PR develop → main
    │
    ▼
Aprobación del PR (branch protection)
    │
    ▼
Merge a main → GitHub Actions (ci.yml)
    ├── 1. Lint + Tests
    ├── 2. Build imagen Docker
    └── 3. Push a GHCR con tag :latest
            → ghcr.io/victormss/shelly-ws90-web/weather-api:latest

(La imagen queda disponible en GHCR para que MeteoProd la descargue)
```

---

## Deploy en los servidores (pull manual)

### Staging (MeteoTest)
```bash
ssh MeteoTest
cd /opt/weather-station
docker compose -f docker-compose.staging.yml pull
docker compose -f docker-compose.staging.yml up -d --remove-orphans
docker compose -f docker-compose.staging.yml ps
```

### Producción (MeteoProd)
```bash
ssh MeteoProd
cd /opt/weather-station
docker compose pull
docker compose up -d --remove-orphans
docker compose ps
```

> Nota: Si el login en GHCR ha expirado, ejecutar primero:
> `docker login ghcr.io -u victormss` (usar GHCR_PAT como password)

---

## Setup inicial de un servidor nuevo

### Prerrequisitos
- Ubuntu/Debian con Docker y Docker Compose instalados
- Puerto 80 y 443 abiertos
- DNS del dominio apuntando a la IP del servidor

### Pasos

```bash
# 1. Crear directorio del proyecto
sudo mkdir -p /opt/weather-station
sudo chown $USER:$USER /opt/weather-station
cd /opt/weather-station

# 2. Crear docker-compose.staging.yml (o docker-compose.yml para producción)
# Copiar el contenido del archivo correspondiente del repositorio
nano docker-compose.staging.yml

# 3. Crear archivo .env con los valores reales
nano .env
# Variables necesarias: DB_PASSWORD, API_SECRET_KEY, ALLOWED_ORIGINS, TZ
# Generar secret: python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 4. Crear directorios auxiliares
mkdir -p nginx/conf.d nginx/certbot-webroot frontend/dist db

# 5. Crear la configuración de Nginx
# Copiar el contenido del staging.conf (o default.ssl.conf.template) del repo
nano nginx/conf.d/default.conf

# 6. Copiar los archivos del frontend (index.html, CSS, JS)
# scp -r frontend/dist/ MeteoTest:/opt/weather-station/frontend/dist/

# 7. Crear db/init.sql
# Copiar el contenido del init.sql del repositorio
nano db/init.sql

# 8. Login en GHCR para descargar la imagen
echo "TU_GHCR_PAT" | docker login ghcr.io -u victormss --password-stdin

# 9. Primer arranque
docker compose -f docker-compose.staging.yml pull
docker compose -f docker-compose.staging.yml up -d

# 10. Verificar que el stack arranca
docker compose -f docker-compose.staging.yml ps
curl http://localhost/api/health

# 11. Obtener certificado SSL (requiere DNS apuntando al servidor)
docker compose -f docker-compose.staging.yml run --rm certbot-staging \
  certbot certonly --webroot -w /var/www/certbot \
  -d meteotest.victorsantos.com.es \
  --email tu@email.com --agree-tos --no-eff-email

# 12. Reiniciar nginx para activar SSL
docker compose -f docker-compose.staging.yml restart nginx-staging

# 13. Verificar HTTPS
curl -sf https://meteotest.victorsantos.com.es/api/health
```

---

## Rollback

### Rollback rápido (imagen anterior)
```bash
# Ver tags disponibles en GHCR
docker image ls ghcr.io/victormss/shelly-ws90-web/weather-api

# Editar docker-compose para usar un tag específico (ej: staging-abc1234)
# Cambiar la línea image: ... :staging por image: ... :staging-abc1234
nano docker-compose.staging.yml
docker compose -f docker-compose.staging.yml up -d
```

### Rollback vía CI/CD
```bash
# En tu máquina local, revertir el commit problemático
git revert <commit-hash>
git push origin develop  # o main
# El CI/CD reconstruirá la imagen, después hay que hacer pull en el servidor
```

---

## Troubleshooting

### Los contenedores no arrancan
```bash
docker compose -f docker-compose.staging.yml logs --tail=50
docker compose -f docker-compose.staging.yml logs weather-api-staging --tail=30
docker compose -f docker-compose.staging.yml logs timescaledb-staging --tail=30
```

### La DB no está healthy
```bash
docker exec timescaledb-staging pg_isready -U weather -d weatherdb
docker exec timescaledb-staging psql -U weather -d weatherdb -c "SELECT 1"
```

### Nginx devuelve 502 Bad Gateway
```bash
# Verificar que la API está corriendo
docker compose -f docker-compose.staging.yml ps weather-api-staging
# Verificar conectividad interna
docker exec weather-nginx-staging wget -qO- http://weather-api-staging:8000/api/health
```

### SSL no funciona
```bash
# Verificar que el certificado existe
docker exec weather-nginx-staging ls -la /etc/letsencrypt/live/meteotest.victorsantos.com.es/
# Renovar manualmente
docker compose -f docker-compose.staging.yml run --rm certbot-staging certbot renew
docker compose -f docker-compose.staging.yml restart nginx-staging
```

### Memoria insuficiente (servidor 1GB)
```bash
# Ver uso de memoria por contenedor
docker stats --no-stream
# Si la DB consume demasiado, ajustar shared_buffers en docker-compose
# Parar servicios no esenciales temporalmente
docker compose -f docker-compose.staging.yml stop certbot-staging
```

---

## Secrets / Tokens necesarios

| Token | Scope | Dónde se usa |
|---|---|---|
| `GHCR PAT` | `read:packages` | En los servidores para `docker login ghcr.io` |
| `GITHUB_TOKEN` | automático | En GitHub Actions para push de imágenes (no necesita config) |

### Crear el PAT para GHCR
GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token:
- Scope: `read:packages`
- Expiration: sin expiración o 1 año
- Usar en los servidores con `docker login ghcr.io -u victormss`
