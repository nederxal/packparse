#! /usr/bin/python
# -*- coding:utf-8 -*-

from flask_wtf import FlaskForm
from wtforms import TextField, IntegerField, BooleanField, SelectField
from wtforms.validators import InputRequired, Optional


class SearchPack(FlaskForm):
    pack_name = TextField("Pack name :", [InputRequired()])


class SearchSong(FlaskForm):
    song_name = TextField("Song name :", [Optional()])
    stepper = TextField("Step artist :", [Optional()])
    speed_low = IntegerField("Min BPM :", [Optional()])
    speed_high = IntegerField("Max BPM :", [Optional()])
    double = BooleanField("Double / Couple ?")
    block = IntegerField("Block :", [Optional()])
    diff = SelectField('Difficulté ?',
                       [Optional()],
                       choices=[('%', 'Any diff'),
                                ('1', 'Beginner'),
                                ('2', 'Easy'),
                                ('3', 'Medium'),
                                ('4', 'Hard'),
                                ('5', 'Challenge'),
                                ('6', 'Edit')],
                       default='%')
