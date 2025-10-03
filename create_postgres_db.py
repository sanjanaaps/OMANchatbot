#!/usr/bin/env python3
"""Create the PostgreSQL database `doc_analyzer` by connecting to the default
postgres database. This bypasses the migration test which requires the target DB
already exist.

Usage:
  .venv\Scripts\python.exe create_postgres_db.py
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

HOST = 'localhost'
PORT = 5432
USER = 'postgres'
PASSWORD = '1234'
DBNAME = 'doc_analyzer'

try:
    conn = psycopg2.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, database='postgres')
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DBNAME,))
    exists = cur.fetchone()
    if not exists:
        cur.execute(f'CREATE DATABASE {DBNAME}')
        print(f"✓ Database '{DBNAME}' created successfully")
    else:
        print(f"✓ Database '{DBNAME}' already exists")
    cur.close()
    conn.close()
except Exception as e:
    print(f"✗ Error creating database: {e}")
    raise
