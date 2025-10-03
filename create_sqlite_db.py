#!/usr/bin/env python3
"""Create a local SQLite database and initialize tables for development.

Usage:
  python create_sqlite_db.py

This script sets POSTGRES_URI to an SQLite file, loads the app config and runs init_db()
which creates the tables used by the application.
"""
import os
import sys
from pathlib import Path

# Ensure repository root is on path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Use a local SQLite file to avoid needing PostgreSQL for quick dev
os.environ['POSTGRES_URI'] = 'sqlite:///local_dev.db'

# Create Flask app and initialize DB
from flask import Flask
from config import get_config
from app_lib.db import init_db

app = Flask(__name__)
config_class = get_config()
app.config.from_object(config_class)

with app.app_context():
    init_db(app)
    print("✓ SQLite database 'local_dev.db' initialized with tables.")

print("Done.")
