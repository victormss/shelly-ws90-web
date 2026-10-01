---
name: deploy
description: >
  Instrucciones paso a paso para desplegar en staging (MeteoTest) y producción (MeteoProd).
  Incluye setup inicial de servidor, certificados SSL, deploy manual, rollback y troubleshooting.
---

# Skill: Deploy

## Flujo normal (automático vía CI/CD)

### Deploy a staging
1. Pushear o mergear a la rama `develop`
2. GitHub Actions ejecuta `.github/workflows/staging.yml`:
   - Lint + pytest
   - Build imagen `ghcr.io/victormss/shelly-ws90-web/weather-api:staging`
   - SSH a MeteoTest → `docker compose -f docker-compose.staging.yml pull && up -d`
3. Verificar en https://meteotest.victorsantos.com.es

### Deploy a producción
1. Crear PR de `develop` → `main`
2. Esperar aprobación del PR (branch protection)
3. Merge a `main`
4. GitHub Actions ejecuta `.github/workflows/ci.yml`:
   - Lint + pytest
   - Build imagen `ghcr.io/victormss/shelly-ws90-web/weather-api:latest`
   - Espera aprobación del environment `production` en GitHub
   - SSH a MeteoProd → `docker compose pull && up -d`
5. Verificar en https://meteo.victorsantos.com.es

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

# 2. Clonar el repositorio
git clone https://github.com/victormss/shelly-ws90-web.git .

# 3. Checkout de la rama correcta
git checkout develop   # para staging
# git checkout main    # para producción

# 4. Crear archivo .env
cp .env.staging.example .env   # para staging
# cp .env.example .env          # para producción
nano .env
# Rellenar: DB_PASSWORD, API_SECRET_KEY con valores seguros
# Generar secret: python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 5. Crear directorio para certbot
mkdir -p nginx/certbot-webroot

# 6. Primer arranque SIN SSL
# Editar temporalmente nginx conf para servir solo HTTP (comentar bloque 443)
# o usar un conf temporal sin SSL
docker compose -f docker-compose.staging.yml up -d
# Para producción: docker compose up -d

# 7. Verificar que el stack arranca
docker compose -f docker-compose.staging.yml ps
curl http://localhost/api/health

# 8. Obtener certificado SSL
docker compose -f docker-compose.staging.yml run --rm certbot-staging \
  certbot certonly --webroot -w /var/www/certbot \
  -d meteotest.victorsantos.com.es \
  --email tu@email.com --agree-tos --no-eff-email
# Para producción: usar certbot (sin -staging) y el dominio meteo.victorsantos.com.es

# 9. Reiniciar nginx para activar SSL
docker compose -f docker-compose.staging.yml restart nginx-staging
# Para producción: docker compose restart nginx

# 10. Verificar HTTPS
curl -sf https://meteotest.victorsantos.com.es/api/health
```

---

## Deploy manual (sin CI/CD)

Conectarse al servidor por SSH y ejecutar:

### Staging (MeteoTest)
```bash
ssh MeteoTest
cd /opt/weather-station
git pull origin develop
docker compose -f docker-compose.staging.yml pull
docker compose -f docker-compose.staging.yml up -d --remove-orphans
docker compose -f docker-compose.staging.yml ps
```

### Producción (MeteoProd)
```bash
ssh MeteoProd
cd /opt/weather-station
git pull origin main
docker compose pull
docker compose up -d --remove-orphans
docker compose ps
```

---

## Rollback

### Rollback rápido (imagen anterior)
```bash
# Ver tags disponibles en GHCR
docker image ls ghcr.io/victormss/shelly-ws90-web/weather-api

# Editar docker-compose para usar un tag específico (ej: staging-abc1234)
# Cambiar la línea image: ... :staging por image: ... :staging-abc1234
docker compose -f docker-compose.staging.yml up -d
```

### Rollback de código
```bash
git log --oneline -10
git revert <commit-hash>
git push
# El CI/CD se encargará del redeploy
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

## Secrets necesarios en GitHub Actions

| Secret | Descripción |
|---|---|
| `STAGING_HOST` | IP del servidor MeteoTest |
| `STAGING_USER` | Usuario SSH (ej: `ubuntu`) |
| `STAGING_SSH_KEY` | Clave privada SSH para MeteoTest |
| `PROD_HOST` | IP del servidor MeteoProd |
| `PROD_USER` | Usuario SSH para MeteoProd |
| `PROD_SSH_KEY` | Clave privada SSH para MeteoProd |
| `GHCR_PAT` | Personal Access Token con scope `read:packages` |
| `GHCR_USER` | `victormss` |

### Crear el PAT para GHCR
GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token:
- Scope: `read:packages`
- Expiration: sin expiración o 1 año
- Guardar como secret `GHCR_PAT` en el repositorio
