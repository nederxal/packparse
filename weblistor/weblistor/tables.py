#! /usr/bin/python
# -*- coding:utf-8 -*-

from datetime import datetime
from weblistor import db


class Pack(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    entry_date = db.Column(db.DateTime, nullable=True)
    desc = db.Column(db.Text, nullable=True)
    songs = db.relationship('Songs', backref="pack", lazy='joined')

    def __init__(self, name):
        self.name = name
        self.entry_date = datetime.now()
        self.song_list = []


class Stepper(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    desc = db.Column(db.Text)
    songs = db.relationship('Songs', backref="stepper", lazy="joined")

    def __init__(self, name):
        self.name = name


class Banners(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    songs = db.relationship('Songs', backref="banners", lazy="joined")

    def __init__(self, name):
        self.name = name


class Difficulties(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    songs = db.relationship('Songs', backref="difficulties", lazy="joined")

    def __init__(self, name):
        self.name = name
    # Gérer l'auto populate ...


class Songs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=False, nullable=False)
    speed = db.Column(db.String(255), nullable=False)
    single = db.Column(db.Boolean, nullable=False)
    difficulty_block = db.Column(db.Integer, nullable=False)
    fk_stepper_name = db.Column(db.Integer, db.ForeignKey("stepper.id"),
                                nullable=False)
    fk_pack_name = db.Column(db.Integer, db.ForeignKey("pack.id"),
                             nullable=False)
    fk_difficulty_name = db.Column(db.Integer,
                                   db.ForeignKey("difficulties.id"),
                                   nullable=False)
    fk_banner = db.Column(db.Integer, db.ForeignKey("banners.id"),
                          nullable=False)

    def __init__(self, name, speed, single, difficulty_block,
                 fk_stepper_name, fk_difficulty_name, fk_banner):
        self.name = name
        self.speed = speed
        self.single = single
        self.difficulty_block = difficulty_block
        self.fk_stepper_name = fk_stepper_name
        self.fk_difficulty_name = fk_difficulty_name
        self.fk_banner = fk_banner
