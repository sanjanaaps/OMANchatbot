#!/usr/bin/env python3
"""Check which tables SQLAlchemy sees using the app's config."""
from flask import Flask
from config import get_config
from app_lib.models import db
from sqlalchemy import inspect

app = Flask(__name__)
app.config.from_object(get_config())

def main():
    db.init_app(app)
    with app.app_context():
        insp = inspect(db.engine)
        tables = insp.get_table_names()
        print('SQLAlchemy sees tables:')
        for t in tables:
            print('-', t)

if __name__ == '__main__':
    main()
