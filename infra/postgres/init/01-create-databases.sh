#!/bin/bash
# Runs once, the first time the Postgres volume is created.
# Creates the warehouse DB and the Metabase application DB with their own users.
# (No `set -u` here: on Windows this file may lack the exec bit, in which case
#  the Postgres entrypoint *sources* it, and strict flags would leak into it.)

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER ${WAREHOUSE_DB_USER} WITH PASSWORD '${WAREHOUSE_DB_PASSWORD}';
    CREATE DATABASE jobradar OWNER ${WAREHOUSE_DB_USER};

    CREATE USER ${METABASE_DB_USER} WITH PASSWORD '${METABASE_DB_PASSWORD}';
    CREATE DATABASE metabase OWNER ${METABASE_DB_USER};
EOSQL

echo "Created databases: jobradar, metabase"
