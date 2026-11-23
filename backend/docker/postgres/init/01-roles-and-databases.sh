#!/bin/bash
# Exécuté UNE SEULE FOIS par l'image postgres, à l'initialisation d'un volume vide.
# Crée les rôles à moindre privilège, la base de tests et active pgvector.
# Les privilèges sur les tables/vues sont accordés par la migration Alembic (reproductible).
set -euo pipefail

: "${SMARTCAMPUS_OWNER_PASSWORD:?SMARTCAMPUS_OWNER_PASSWORD manquant}"
: "${SMARTCAMPUS_APP_PASSWORD:?SMARTCAMPUS_APP_PASSWORD manquant}"
: "${AI_READONLY_PASSWORD:?AI_READONLY_PASSWORD manquant}"
TEST_DB="${POSTGRES_TEST_DB:-smartcampus_test}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  -v owner_pw="$SMARTCAMPUS_OWNER_PASSWORD" \
  -v app_pw="$SMARTCAMPUS_APP_PASSWORD" \
  -v ai_pw="$AI_READONLY_PASSWORD" \
  -v test_db="$TEST_DB" <<'EOSQL'
-- Propriétaire du schéma : exécute les migrations et le seed (DDL), pas superuser.
CREATE ROLE smartcampus_owner LOGIN PASSWORD :'owner_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
-- Rôle de l'API : DML limité (SELECT/INSERT/UPDATE, jamais DELETE ni DDL).
CREATE ROLE smartcampus_app LOGIN PASSWORD :'app_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION
  CONNECTION LIMIT 50;
ALTER ROLE smartcampus_app SET statement_timeout = '15s';
-- Outil SQL de l'agent IA : lecture seule, uniquement le schéma ai_views.
CREATE ROLE ai_readonly LOGIN PASSWORD :'ai_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT
  CONNECTION LIMIT 10;
ALTER ROLE ai_readonly SET default_transaction_read_only = on;
ALTER ROLE ai_readonly SET statement_timeout = '3s';
ALTER ROLE ai_readonly SET idle_in_transaction_session_timeout = '10s';
ALTER ROLE ai_readonly SET search_path = ai_views;

CREATE DATABASE :"test_db" OWNER smartcampus_owner;
EOSQL

for db in "$POSTGRES_DB" "$TEST_DB"; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" -v db="$db" <<'EOSQL'
ALTER DATABASE :"db" OWNER TO smartcampus_owner;
REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db" TO smartcampus_owner, smartcampus_app, ai_readonly;
GRANT TEMPORARY ON DATABASE :"db" TO smartcampus_app;

-- pgvector (nécessite un superuser : fait ici une fois pour toutes).
CREATE EXTENSION IF NOT EXISTS vector;

-- Schéma public : propriété du owner, personne d'autre ne peut y créer d'objets.
ALTER SCHEMA public OWNER TO smartcampus_owner;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO smartcampus_app;
-- ai_readonly n'a AUCUN droit sur public : il ne voit que les vues ai_views.
EOSQL
done

echo "SmartCampus : rôles, bases et pgvector initialisés."
