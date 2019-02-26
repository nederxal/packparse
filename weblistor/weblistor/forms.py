#! /usr/bin/python
# -*- coding:utf-8 -*-

from flask_wtf import FlaskForm
from wtforms import TextField, IntegerField, BooleanField
from wtforms.validators import InputRequired

class SearchPack(FlaskForm):
    pack_name = TextField("Looking for a pack ?", [InputRequired()])