#! /usr/bin/python
# -*- coding:utf-8 -*-


from flask import request, render_template,g
from flask_wtf import FlaskForm
from datetime import datetime

from weblistor import app
from weblistor.tables import Pack

@app.route('/')
def index():
    return 'Hello World!'
