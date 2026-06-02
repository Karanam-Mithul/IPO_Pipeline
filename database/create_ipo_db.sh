#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER ipo_user WITH PASSWORD 'ipo_pass';
    CREATE DATABASE ipo_db OWNER ipo_user;
    GRANT ALL PRIVILEGES ON DATABASE ipo_db TO ipo_user;
EOSQL
