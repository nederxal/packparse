#! /usr/bin/python
# -*- coding:utf-8 -*-

import os
import re
import sys
from lark import Visitor
from shutil import copy, SameFileError
from hashlib import sha256
from datetime import datetime
from weblistor import db
from sqlalchemy import exc
from sqlalchemy.orm import relationship, session


class SimFile(Visitor):
    def __init__(self, simfile_path, p, dbconn):
        # specific for SongObject set with header
        self.name = None
        self.speed = None
        self.single = None
        self.fk_banner = None
        # specific for SongObject set with *-chart
        self.difficulty_block = None
        self.fk_difficulty_name = None
        self.fk_stepper_name = None
        self.breakdown = None  # to set later ...

        # specific for the simfile
        self.sm_path = simfile_path
        self.p = p
        self.dbconn = dbconn

    # Lark rules
    def header(self, tree):
        for data in tree.children:
            try:
                if data.children[0] == "TITLE":
                    self.name = str(data.children[1])
                if data.children[0] == "SUBTITLE":
                    self.name = ' - '.join([self.name, str(data.children[1])])
                if data.children[0] == "BANNER":
                    self.get_banner_id(data.children[1])
                if data.children[0] == "DISPLAYBPM":
                    self.speed = re.sub(r"\.[0-9]*", "", data.children[1])
                if data.children[0] == "BPMS":
                    bpms = data.children[1]
            except IndexError:
                pass

        if not self.speed:
            bpms = re.sub("[0-9.]*=", "", bpms)
            bpms = re.sub(r"\.[0-9]*", "", bpms)
            t_line = bpms.split(",")
            t_line = list(map(int, t_line))

            if max(t_line) != min(t_line):
                self.speed = str(min(t_line))+":"+str(max(t_line))
            else:
                self.speed = max(t_line)

        if not self.fk_banner:
            self.get_banner_id("default_banner.png")

    def single_chart(self, tree):
        # Maybe stepchart is empty ... we won't add it
        # Empty chart count at least 1 measure

        chart_len = tree.children[-1]

        if len(chart_len.children) <= 1:
            pass
        else:
            # if 5 = name artist exist if 4 = name artist inexistent
            if len(tree.children) == 5:
                self.stepper_name_cleaning(tree.children[0])
                difficulty_name = Difficulties(tree.children[1])
                self.difficulty_block = str(tree.children[2])
            elif len(tree.children) == 4:
                self.stepper_name_cleaning('')
                difficulty_name = Difficulties(tree.children[0])
                self.difficulty_block = tree.children[1]
            else:
                print("ERROR sur les data après NOTES")
                sys.exit(1)

            self.db_get_fk(difficulty_name)
            self.single = True
            song = Songs(self.name, self.speed, self.single,
                         self.difficulty_block, self.fk_stepper_name.id,
                         self.fk_difficulty_name.id, self.fk_banner.id)
            self.add_to_pack(song)

    # To do some stuff ...
    def get_banner_id(self, banner_path):
        set_path = os.path.join(os.getcwd(), "weblistor", "static", "images")
        banner_path = os.path.join(os.path.dirname(self.sm_path), banner_path)
        filename, ext = os.path.splitext(banner_path)

        try:
            banner_rename = (sha256(open(banner_path, 'rb')
                                    .read()).hexdigest()+ext)
            banner_dest = os.path.join(set_path, banner_rename)
            copy(banner_path, banner_dest)
            banner = Banners(banner_rename)
            self.db_get_fk(banner)
        except FileNotFoundError as e:
            # It happens sometime people set the banner with specific
            # name in the SM file BUT they kept the name "banner.png" ...
            try:
                reg = r'(/|\\\\)[\ a-zA-Z0-9_-]*.(png|jpg|jpeg)$'
                banner_path = re.sub(reg, "/banner.png", banner_path)
                banner_rename = (sha256(open(banner_path, 'rb')
                                        .read()).hexdigest()+ext)
                banner_dest = os.path.join(set_path, banner_rename)
                copy(banner_path, banner_dest)
                banner = Banners(banner_rename)
                self.db_get_fk(banner)
            except FileNotFoundError as e:
                banner = Banners("default_banner.png")
                self.db_get_fk(banner)
        except SameFileError as e:
            self.db_get_fk(banner)

    def stepper_name_cleaning(self, stepper_name):
        clean_regex = r"\b[\d+(\/|\-|\*|\||')*bpmBPMths]+\b[*]*"
        stepper_name = re.sub(clean_regex, '', stepper_name)
        stepper_name = re.sub("^\s*", "", stepper_name)

        if not stepper_name:
            # Last try to get it ...
            find_regex = r"(?<=\[|\()[\w\s\-&]+(?=\]|\))"
            folder_song = os.path.basename(os.path.dirname(self.sm_path))
            result = re.findall(find_regex, folder_song)

            if result:
                stepper = Stepper(result[-1])
            else:
                stepper = Stepper("UNAMED_STEPPER")

        else:
            stepper = Stepper(stepper_name)
        self.db_get_fk(stepper)

    def db_get_fk(self, data):
        # If data exists we check for the id
        try:
            self.dbconn.add(data)
            self.dbconn.commit()
        except exc.IntegrityError as e:
            self.dbconn.rollback()
            pass

        if isinstance(data, Difficulties):
            self.fk_difficulty_name = self.dbconn.query(Difficulties)\
                .filter(Difficulties.name == data.name).one()
        elif isinstance(data, Banners):
            self.fk_banner = self.dbconn.query(Banners)\
                .filter(Banners.name == data.name).one()
        elif isinstance(data, Stepper):
            self.fk_stepper_name = self.dbconn.query(Stepper)\
                .filter(Stepper.name == data.name).one()
        else:
            raise
            sys.exit(1)

    def add_to_pack(self, song):
        self.p.songs.append(song)


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
    desc = db.Column(db.Text)

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
    speed = db.Column(db.String(255), nullable=False)
    single = db.Column(db.Boolean, nullable=False)
    difficulty_block = db.Column(db.Integer, nullable=False)
    fk_stepper_name = db.Column(db.Integer, db.ForeignKey("stepper.id"))
    fk_pack_name = db.Column(db.Integer, db.ForeignKey("pack.id",
                                                       ondelete="cascade"))
    fk_difficulty_name = db.Column(db.Integer,
                                   db.ForeignKey("difficulties.id"))
    fk_banner = db.Column(db.Integer, db.ForeignKey("banners.id"))

    def __init__(self, name, speed, single, difficulty_block,
                 fk_stepper_name, fk_difficulty_name, fk_banner):
        self.name = name
        self.speed = speed
        self.single = single
        self.difficulty_block = difficulty_block
        self.fk_stepper_name = fk_stepper_name
        self.fk_difficulty_name = fk_difficulty_name
        self.fk_banner = fk_banner
        self.fk_pack_name = None

    def get_songs_pack(id):
        return (db.session.query(Songs.name, Songs.speed, Banners.name)
                .filter(Songs.fk_pack_name == id)
                .filter(Songs.fk_banner == Banners.id)
                .group_by(Songs.name)
                .order_by(Songs.name)
                .all()
                )

    def get_songs_data(id):
        return (db.session.query(Songs.name,
                                 Stepper.name,
                                 Songs.difficulty_block,
                                 Difficulties.name)
                .filter(Songs.fk_pack_name == id)
                .filter(Songs.fk_difficulty_name == Difficulties.id)
                .filter(Songs.fk_stepper_name == Stepper.id)
                .all()
                )
