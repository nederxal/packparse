#! /usr/bin/python
# -*- coding:utf-8 -*-


from datetime import datetime
from weblistor import db
from sqlalchemy.orm import relationship, session


class Pack(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    entry_date = db.Column(db.DateTime, nullable=True)
    desc = db.Column(db.Text, nullable=True)
    songs = db.relationship('Songs', cascade="all, delete")

    def __init__(self, name):
        self.name = name
        self.entry_date = datetime.now()
        self.songs = []


class Stepper(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)

    def __init__(self, name):
        self.name = name


class Banners(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)

    def __init__(self, name):
        self.name = name


class Difficulties(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)

    def __init__(self, name):
        self.name = name
# Gérer l'auto populate ...
# INSERT INTO difficulties (name)
# VALUES ("Beginner"), ("Easy"), ("Medium"), ("Hard"), ("Challenge"), ("Edit")


class Songs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=False, nullable=False)
    min_speed = db.Column(db.Integer, nullable=False)
    max_speed = db.Column(db.Integer, nullable=False)
    double = db.Column(db.Boolean, nullable=False)
    difficulty_block = db.Column(db.Integer, nullable=False)
    breakdown = db.Column(db.String(255), nullable=True)
    fk_stepper_name = db.Column(db.Integer, db.ForeignKey("stepper.id"))
    fk_pack_name = db.Column(db.Integer, db.ForeignKey("pack.id",
                                                       ondelete="cascade"))
    fk_difficulty_name = db.Column(db.Integer,
                                   db.ForeignKey("difficulties.id"))
    fk_banner = db.Column(db.Integer, db.ForeignKey("banners.id"))

    def __init__(self, name, min_speed, max_speed, double, difficulty_block,
                 breakdown, fk_stepper_name, fk_difficulty_name, fk_banner):
        self.name = name
        self.min_speed = min_speed
        self.max_speed = max_speed
        self.double = double
        self.difficulty_block = difficulty_block
        self.breakdown = breakdown
        self.fk_stepper_name = fk_stepper_name
        self.fk_difficulty_name = fk_difficulty_name
        self.fk_banner = fk_banner
        self.fk_pack_name = None

    @staticmethod
    def get_songs_pack(id):
        songs_pack = (db.session.query(Songs.name, Songs.speed, Banners.name)
                      .filter(Songs.fk_pack_name == id)
                      .filter(Songs.fk_banner == Banners.id)
                      .group_by(Songs.name)
                      .order_by(Songs.name)
                      .all()
                      )
        songs_data = (db.session.query(Songs.name,
                                       Stepper.name,
                                       Songs.difficulty_block,
                                       Difficulties.name,
                                       Songs.breakdown)
                      .filter(Songs.fk_pack_name == id)
                      .filter(Songs.fk_difficulty_name == Difficulties.id)
                      .filter(Songs.fk_stepper_name == Stepper.id)
                      .order_by(Songs.difficulty_block)
                      .all()
                      )
        return (songs_pack, songs_data)

    # @staticmethod
    # def search_song(name, speed, stepper, double, block, difficulty):
