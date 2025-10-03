#!/usr/bin/env python3
import psycopg2

HOST='localhost'
PORT=5432
USER='postgres'
PASSWORD='1234'
DB='doc_analyzer'

try:
    conn = psycopg2.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, database=DB)
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;")
    rows = cur.fetchall()
    if not rows:
        print('No tables found in public schema')
    else:
        print('Tables in public schema:')
        for r in rows:
            print('-', r[0])
    cur.close()
    conn.close()
except Exception as e:
    print('Error:', e)
    raise
