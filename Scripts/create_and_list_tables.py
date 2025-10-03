#!/usr/bin/env python3
from flask import Flask
from config import get_config
from app_lib.models import db
from sqlalchemy import inspect

app = Flask(__name__)
app.config.from_object(get_config())

with app.app_context():
    db.init_app(app)
    db.create_all()
    insp = inspect(db.engine)
    tables = insp.get_table_names()
    print('Tables after create_all:')
    for t in tables:
        print('-', t)
