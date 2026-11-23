#!/bin/sh
# Applique les migrations puis le seed (idempotent) avant de démarrer l'API.
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "[entrypoint] alembic upgrade head"
  alembic upgrade head
fi

if [ "${RUN_SEED:-false}" = "true" ]; then
  echo "[entrypoint] seed des données de démonstration (DEMO)"
  python -m seeds.seed
fi

exec "$@"
