#!/usr/bin/env python3
"""Create pg_trgm extension in doc_analyzer DB if not exists."""
import psycopg2

HOST='localhost'
PORT=5432
USER='postgres'
PASSWORD='1234'
DB='doc_analyzer'

try:
    conn = psycopg2.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DB)
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    conn.commit()
    cur.close()
    conn.close()
    print('✓ pg_trgm extension ensured in doc_analyzer')
except Exception as e:
    print('✗ Error creating extension:', e)
    raise
