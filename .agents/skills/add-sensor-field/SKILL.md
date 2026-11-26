---
name: add-sensor-field
description: >-
  Usar cuando el usuario quiera añadir, renombrar o eliminar una medida
  meteorológica (p. ej. punto de rocío, batería, radiación solar, sensación
  térmica) o cambiar el schema de la base de datos (columnas de weather_data,
  continuous aggregates hourly/daily). Cubre BD, API, frontend, Home
  Assistant, tests y la migración de las bases de datos existentes.
---

# Añadir (o cambiar) una medida meteorológica

Una medida recorre 6 capas. Si olvidas una, falla en silencio: el dato se descarta o se muestra como `--`.
Ejemplo usado abajo: `dew_point` (°C).

## 0. Decidir antes de tocar código (preguntar al usuario si no está claro)

- Nombre en `snake_case` y unidad.
- Rango físico válido (para `ge`/`le` en el schema).
- Agregación en las estadísticas: `AVG` / `MIN` / `MAX` / `SUM` (acumulados como lluvia) / ninguna.
- Si es acumulado o ángulo (como `wind_direction`), `AVG` no tiene sentido. Avísalo.
- ¿Se muestra en el frontend? ¿Como tarjeta, en gráfica o en ambas?

## 1. Checklist de archivos

| # | Archivo | Cambio |
|---|---|---|
| 1 | `db/init.sql` | Columna en `weather_data` y, si se agrega, en **ambas** vistas `hourly_weather_stats` y `daily_weather_stats` (`avg_dew_point`, etc.) |
| 2 | `db/migrations/YYYYMMDD_<desc>.sql` | **Nuevo.** Migración para las BD existentes. Ver [references/migrations.md](references/migrations.md) |
| 3 | `weather-api/app/models.py` | `Column(Float, nullable=True, comment="... in <unidad>")` + entrada en `to_dict()` |
| 4 | `weather-api/app/schemas.py` | `WeatherIngest` (con `ge`/`le` + `json_schema_extra.example`), `WeatherResponse`, `WeatherStatsResponse` si se agrega |
| 5 | `weather-api/app/routers/ingest.py` | Asignar el campo en `WeatherData(...)` |
| 6 | `weather-api/app/routers/weather.py` | **4 sitios**: SELECT de `/current`, SELECT agregado y SELECT crudo de `/history`, SELECT de `/stats`. Y los constructores `WeatherResponse(...)`/`WeatherStatsResponse(...)` de cada uno |
| 7 | `weather-api/tests/test_health.py` | Test de valor válido y de rechazo fuera de rango |
| 8 | `frontend/dist/index.html` + `js/app.js` | Tarjeta (seguir el patrón de `card-illuminance` / `updateIlluminance()`) y llamada en el render. `js/charts.js` si va en la gráfica |
| 9 | `homeassistant/weather_automation.yaml` | Línea en el `payload` con el entity id real (preguntar al usuario). Ojo con la coma JSON del último elemento |

Comprueba que no falta ningún sitio comparando con un campo existente. Ambos recuentos deben coincidir:

```powershell
$files = Get-ChildItem weather-api/app -Recurse -Filter *.py
($files | Select-String "illuminance").Count; ($files | Select-String "dew_point").Count
```

## 2. Validar en local

Usa la skill `local-dev`:
1. Lint + tests.
2. Recrear la BD local (`down -v`) para que `init.sql` se ejecute, **o** aplicar la migración sobre la BD local existente. Mejor esta segunda opción: así pruebas la migración.
3. Ingest de prueba con el campo nuevo y `GET /api/weather/current` → el campo aparece.
4. `GET /api/weather/stats?period=hourly&days=1` no da error 500 (comprueba las columnas de las vistas).

## 3. Orden de despliegue (importante)

La API nueva hace `SELECT dew_point`, así que **la migración va antes que la imagen nueva**. Si no, `/current` devuelve 500.

1. Migración en **staging** → deploy API staging → sync frontend staging → verificar.
2. Home Assistant: añadir el campo al payload. Pydantic ignora campos desconocidos, así que es seguro en cualquier orden. Pero mientras no se añada, el campo quedará `null`.
3. Tras merge a `main`: migración en **producción** (con confirmación) → deploy API → sync frontend.

Comandos de deploy: skill `deploy`. Comandos de migración: [references/migrations.md](references/migrations.md).
