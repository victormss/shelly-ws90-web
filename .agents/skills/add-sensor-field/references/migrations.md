# Migraciones de base de datos

`db/init.sql` solo se ejecuta cuando el volumen está vacío. Las BD de staging y producción **ya existen**, así que cada cambio de schema necesita un script en `db/migrations/` y además el cambio equivalente en `init.sql`, para que las instalaciones nuevas queden iguales.

## Convenciones

- Nombre: `db/migrations/YYYYMMDD_<descripcion>.sql` (ej. `20261022_add_dew_point.sql`).
- Idempotente siempre que se pueda (`IF NOT EXISTS`, `IF EXISTS`).
- Una transacción por script cuando sea posible (`BEGIN; ... COMMIT;`). Excepción: `CALL refresh_continuous_aggregate` **no puede ir dentro de una transacción**. Ponlo después del `COMMIT`.

## Añadir una columna cruda (barato, sin riesgo)

```sql
ALTER TABLE weather_data ADD COLUMN IF NOT EXISTS dew_point DOUBLE PRECISION;
```

## Añadir la columna a los continuous aggregates (cuidado)

TimescaleDB **no permite añadir columnas** a un continuous aggregate existente. Hay que hacer `DROP` y recrearlo con la definición completa (copiarla de `init.sql` ya actualizado):

```sql
BEGIN;
ALTER TABLE weather_data ADD COLUMN IF NOT EXISTS dew_point DOUBLE PRECISION;

DROP MATERIALIZED VIEW IF EXISTS hourly_weather_stats;
CREATE MATERIALIZED VIEW hourly_weather_stats
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', time) AS bucket,
       -- ... TODAS las columnas existentes de init.sql ...
       AVG(dew_point) AS avg_dew_point,
       COUNT(*) AS sample_count
FROM weather_data GROUP BY bucket
WITH NO DATA;
SELECT add_continuous_aggregate_policy('hourly_weather_stats',
    start_offset => INTERVAL '3 hours', end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour', if_not_exists => TRUE);

-- Igual para daily_weather_stats (offsets 3 days / 1 day / 1 day)
COMMIT;

CALL refresh_continuous_aggregate('hourly_weather_stats', NULL, NULL);
CALL refresh_continuous_aggregate('daily_weather_stats', NULL, NULL);
```

> [!WARNING]
> Al recrear un aggregate se recalcula **solo a partir de los datos crudos que existen**. Los datos crudos tienen retención de 1 año: si los aggregates tienen estadísticas de hace más de 1 año, **se perderán**. Avisa al usuario antes de ejecutar esto en producción.

Durante la ventana entre el `DROP` y el `refresh`, `/api/weather/stats` devuelve vacío o un 500. Es breve, pero en producción conviene avisar.

## Aplicar la migración (PowerShell, sin `<`)

```powershell
# Local
Get-Content db/migrations/20261022_add_dew_point.sql -Raw | docker exec -i timescaledb-local psql -U weather -d weatherdb -v ON_ERROR_STOP=1

# Staging
Get-Content db/migrations/20261022_add_dew_point.sql -Raw | ssh MeteoTest "docker exec -i timescaledb-staging psql -U weather -d weatherdb -v ON_ERROR_STOP=1"

# Producción: SOLO con confirmación explícita del usuario y tras probar en staging
Get-Content db/migrations/20261022_add_dew_point.sql -Raw | ssh MeteoProd "docker exec -i timescaledb psql -U weather -d weatherdb -v ON_ERROR_STOP=1"
```

## Verificar

```powershell
ssh MeteoTest "docker exec timescaledb-staging psql -U weather -d weatherdb -c '\d weather_data'"
ssh MeteoTest "docker exec timescaledb-staging psql -U weather -d weatherdb -c 'SELECT bucket, avg_dew_point, sample_count FROM hourly_weather_stats ORDER BY bucket DESC LIMIT 3'"
```

## Backup antes de producción (recomendado)

```powershell
# Comillas simples: $(date) lo debe evaluar bash en el servidor, no PowerShell
ssh MeteoProd 'docker exec timescaledb pg_dump -U weather -d weatherdb -Fc > /opt/weather-station/backup_$(date +%Y%m%d_%H%M).dump'
```
Comprueba antes el espacio en disco (`df -h`).
