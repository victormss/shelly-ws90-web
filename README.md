# 🌤️ Weather Station — Ecowitt WS90

Estación meteorológica pública con datos en tiempo real de una **Ecowitt WS90** conectada via **Zigbee2MQTT** → **Home Assistant** → **Oracle Cloud**.

## 🏗️ Arquitectura

```
WS90 → Zigbee2MQTT → Home Assistant → [HTTP POST] → FastAPI → TimescaleDB
                                                                    ↓
                                                        Nginx ← Frontend
                                                          ↓
                                                      🌍 Usuarios
```

## 📋 Requisitos

- **Servidor cloud**: Instancia con Docker y Docker Compose (Oracle Cloud Free Tier funciona)
- **Dominio**: Un dominio o subdominio apuntando a la IP del servidor
- **Home Assistant**: Con la WS90 integrada via Zigbee2MQTT

## 🚀 Despliegue Rápido

### 1. Clonar y configurar

```bash
# En tu servidor Oracle Cloud
git clone <tu-repo> weather-station
cd weather-station

# Copiar y editar variables de entorno
cp .env.example .env
nano .env
```

Edita el `.env` con:
- `DB_PASSWORD`: Una contraseña segura para la base de datos
- `API_SECRET_KEY`: Un token seguro (genera con `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`)
- `DOMAIN`: Tu dominio (ej: `meteo.midominio.com`)

### 2. Configurar SSL

#### Opción A: Let's Encrypt (producción)

```bash
# Crear directorio para Certbot
mkdir -p nginx/certbot-webroot

# Primero, arrancar solo Nginx sin SSL para el challenge
# (comenta las líneas ssl_certificate en nginx/conf.d/default.conf)
docker compose up -d nginx

# Generar certificado
docker compose run --rm certbot certonly \
    --webroot -w /var/www/certbot \
    -d TU_DOMINIO \
    --email tu@email.com \
    --agree-tos --no-eff-email

# Ahora edita nginx/conf.d/default.conf:
# - Descomenta las líneas ssl_certificate y ssl_certificate_key
# - Reemplaza TU_DOMINIO por tu dominio real
nano nginx/conf.d/default.conf

# Reiniciar con SSL
docker compose restart nginx
```

#### Opción B: Certificado autofirmado (desarrollo)

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/conf.d/selfsigned.key \
    -out nginx/conf.d/selfsigned.crt \
    -subj "/CN=localhost"
```

### 3. Arrancar el stack

```bash
docker compose up -d
```

### 4. Verificar

```bash
# Health check
curl http://localhost:8000/api/health

# Enviar dato de prueba
curl -X POST http://localhost:8000/api/weather/ingest \
    -H "Authorization: Bearer TU_API_SECRET_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "temperature": 22.5,
        "humidity": 65,
        "pressure": 1013.25,
        "wind_speed": 12.3,
        "wind_direction": 180,
        "wind_gust": 25.1,
        "rain": 0,
        "uv_index": 3,
        "illuminance": 45000
    }'

# Consultar último dato
curl http://localhost:8000/api/weather/current
```

### 5. Configurar Home Assistant

Añade el contenido de `homeassistant/weather_automation.yaml` a tu `configuration.yaml` de Home Assistant.

**Importante**:
1. Cambia los `sensor.ws90_*` por los entity IDs reales de tu WS90
2. Crea un helper `input_text.weather_api_token` con el valor de tu `API_SECRET_KEY`
3. Cambia la URL por la de tu dominio
4. Reinicia Home Assistant

## 📡 API Endpoints

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/api/weather/ingest` | Bearer token | Ingesta de datos desde HA |
| `GET` | `/api/weather/current` | No | Último dato meteorológico |
| `GET` | `/api/weather/history?range=24h` | No | Histórico (1h, 6h, 12h, 24h, 7d, 30d) |
| `GET` | `/api/weather/stats?period=daily&days=7` | No | Estadísticas agregadas |
| `GET` | `/api/health` | No | Estado del sistema |
| `GET` | `/api/docs` | No | Documentación Swagger |

## 🔧 Firewall Oracle Cloud

Recuerda abrir los puertos en las Security Lists de Oracle Cloud:

```bash
# En la instancia (iptables)
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

Y en la consola web de Oracle Cloud:
- **Networking → Virtual Cloud Networks → tu VCN → Security Lists**
- Añadir regla de ingreso para TCP puertos 80 y 443

## 📁 Estructura del Proyecto

```
weather-station/
├── docker-compose.yml          # Stack completo
├── .env.example                # Variables de entorno
├── db/
│   └── init.sql                # Esquema TimescaleDB
├── nginx/
│   ├── conf.d/
│   │   └── default.conf        # Reverse proxy + SSL
│   └── certbot-webroot/        # Para Let's Encrypt
├── weather-api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI app
│       ├── config.py           # Settings
│       ├── database.py         # Conexión DB
│       ├── models.py           # SQLAlchemy models
│       ├── schemas.py          # Pydantic schemas
│       ├── auth.py             # Autenticación
│       └── routers/
│           ├── ingest.py       # POST endpoint
│           └── weather.py      # GET endpoints
├── frontend/
│   └── dist/
│       ├── index.html          # Dashboard
│       ├── manifest.json       # PWA
│       ├── css/
│       │   └── style.css       # Estilos
│       └── js/
│           ├── app.js          # Lógica principal
│           └── charts.js       # Gráficos Chart.js
└── homeassistant/
    └── weather_automation.yaml # Config para HA
```

## 🛡️ Seguridad

- **API key**: El endpoint de ingesta está protegido con Bearer token
- **HTTPS**: Certificado Let's Encrypt con renovación automática
- **Rate limiting**: 30 req/min para API pública, 15 req/min para ingesta
- **DB aislada**: PostgreSQL solo accesible dentro de la red Docker
- **Security headers**: X-Frame-Options, CSP, HSTS configurados en Nginx

## 📊 Mantenimiento

```bash
# Ver logs
docker compose logs -f weather-api

# Backup de la base de datos
docker exec timescaledb pg_dump -U weather weatherdb > backup_$(date +%Y%m%d).sql

# Actualizar
git pull
docker compose build weather-api
docker compose up -d
```
