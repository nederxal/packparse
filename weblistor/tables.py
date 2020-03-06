#! /usr/bin/python
# -*- coding:utf-8 -*-


from datetime import datetime
from weblistor import db
from sqlalchemy import and_, func, distinct
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

    @staticmethod
    def get_name(id):
        return(db.session.query(Pack.name).filter(Pack.id == id).one())

    @staticmethod
    def get_stats(id):
        total_songs = (db.session.query(func.count(distinct(Songs.name)))
                       .filter(Songs.fk_pack_name == id).one())
        lowest_bpm = (db.session.query(func.min(distinct(Songs.min_speed)))
                      .filter(Songs.fk_pack_name == id).one())
        highest_bpm = (db.session.query(func.max(distinct(Songs.max_speed)))
                       .filter(Songs.fk_pack_name == id).one())
        lowest_diff = (db.session
                       .query(func.min(distinct(Songs.difficulty_block)))
                       .filter(Songs.fk_pack_name == id).one())
        highest_diff = (db.session
                        .query(func.max(distinct(Songs.difficulty_block)))
                        .filter(Songs.fk_pack_name == id).one())
        return total_songs, lowest_bpm, highest_bpm, lowest_diff, highest_diff


class Stepper(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)

    def __init__(self, name):
        self.name = name

    def get_id(self):
        r = Stepper.query.filter(Stepper.name == self.name).one()
        return r.id


class Banners(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)

    def __init__(self, name):
        self.name = name

    def get_id(self):
        r = Banners.query.filter(Banners.name == self.name).one()
        return r.id


class Difficulties(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)

    def __init__(self, name):
        self.name = name

    def get_id(self):
        r = Difficulties.query.filter(Difficulties.name == self.name).one()
        return r.id


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
        songs_pack = (db.session.query(Banners.name, Songs.name,
                                       Songs.min_speed, Songs.max_speed)
                      .filter(Songs.fk_pack_name == id)
                      .filter(Songs.fk_banner == Banners.id)
                      .group_by(Songs.name)
                      .order_by(Songs.name)
                      .all()
                      )
        songs_data = (db.session.query(Songs.name, Stepper.name,
                                       Songs.difficulty_block,
                                       Difficulties.name, Songs.breakdown)
                      .filter(Songs.fk_pack_name == id)
                      .filter(Songs.fk_difficulty_name == Difficulties.id)
                      .filter(Songs.fk_stepper_name == Stepper.id)
                      .order_by(Songs.difficulty_block)
                      .all()
                      )
        return (songs_pack, songs_data)

    @staticmethod
    def search_song(song_name, speed_low, speed_high, block, double, stepper):
        song_list = (db.session.query(Pack.name, Pack.id,
                                      Songs.name, Songs.min_speed,
                                      Songs.max_speed, Banners.name)
                     .filter(Songs.fk_pack_name == Pack.id)
                     .filter(Songs.fk_banner == Banners.id)
                     .filter(Songs.name.ilike("%"+song_name+"%"))
                     .filter(and_(Songs.min_speed >= speed_low,
                                  Songs.max_speed <= speed_high))
                     .filter(Songs.double == double)
                     .join(Stepper).filter(Stepper.name.ilike("%"+stepper+"%"))
                     .group_by(Pack.name)
                     .group_by(Songs.name)
                     .order_by(Pack.name)
                     .order_by(Songs.name)
                     )

        if len(block) == 0:
            song_list = song_list.filter(Songs.difficulty_block >= 1)
        else:
            song_list = song_list.filter(Songs.difficulty_block == block)

        return song_list.all()
