#! /usr/bin/python
# -*- coding:utf-8 -*-

from flask import flash
from flask_wtf import FlaskForm
from wtforms import TextField, IntegerField, BooleanField, SelectField
from wtforms.validators import InputRequired, Optional, NumberRange
from wtforms.validators import DataRequired, Length


def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash('%s - %s' %
                  (getattr(form, field).label.text, error), "danger")


class SearchPack(FlaskForm):
    pack_name = TextField("Pack name :",
                          [InputRequired(),
                           Length(min=3,
                                  message="Au moins 3 lettres fé pa tapute")])


class SearchSong(FlaskForm):
    song_name = TextField("Song name")
    stepper = TextField("Step artist")
    speed_low = IntegerField("Min BPM")
    speed_high = IntegerField("Max BPM")
    double = BooleanField("Double ?")
    block = IntegerField("Difficulté")
