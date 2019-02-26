from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import urandom
from base64 import b64encode


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../songs2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['WTF_CSRF_SECRET_KEY'] = b64encode(urandom(16)).decode('utf-8')
app.secret_key = b64encode(urandom(16)).decode('utf-8')

db = SQLAlchemy(app)

import weblistor.views

db.create_all()
