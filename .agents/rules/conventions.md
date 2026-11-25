---
trigger: always_on
---

# Convenciones y límites de seguridad

## Producción (MeteoProd) — siempre pedir confirmación

- **Nunca** ejecutar comandos que modifiquen MeteoProd (pull, up, restart, migraciones SQL, copia de archivos) sin confirmación explícita del usuario en ese mismo turno.
- Comandos de solo lectura (`ps`, `logs`, `docker stats`, `curl /api/health`) sí se pueden ejecutar sin preguntar.
- Todo cambio se prueba primero en MeteoTest (staging).

## Git

- Commits en inglés con Conventional Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:`.
- Nunca hacer push directo a `main`. Los cambios llegan vía PR `develop → main`.
- Nunca commitear `.env`, `.env.staging` ni secretos. Solo los `*.example`.
- Si se cambia la arquitectura, el CI/CD o el proceso de despliegue, actualizar en el mismo commit `.agents/rules/architecture.md` y/o `.agents/skills/deploy/`.

## Código

- Docstrings y nombres en inglés. Comentarios de configuración (SQL, YAML, compose) y documentación en español.
- Lint igual que el CI: `flake8 weather-api/app --select=E9,F63,F7,F82` (bloqueante) y `--max-line-length=127`.
- Mantener la RAM en mente: los servidores tienen 1 GB. No añadir servicios ni subir `shared_buffers`/workers sin avisar.

## Base de datos

- `db/init.sql` **solo se ejecuta cuando el volumen de datos está vacío**. Editarlo no cambia las bases de datos existentes de staging ni producción.
- Cualquier cambio de schema necesita además un script de migración. Ver skill `add-sensor-field`.
