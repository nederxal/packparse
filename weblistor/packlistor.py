#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import logging
import glob
from shutil import copy, SameFileError
from hashlib import sha256
from datetime import datetime
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from weblistor.tables import Pack, Stepper, Banners, Difficulties, Songs


def main():
    logging.basicConfig(filename='packlistor.log', level=logging.INFO)
    engine = create_engine('sqlite:///songs2.db')
    session = sessionmaker(bind=engine)
    db = session()

    for pack_name in os.scandir("../pack/"):
        if pack_name.is_dir(follow_symlinks=False):
            pack = Pack(pack_name.name)
            try:
                db.query(Pack).filter(Pack.name == pack.name).one()
            except NoResultFound:
                song_extract(db, pack)
            else:
                pass

    db.close()

    return 0


def song_extract(db, pack):
    lines_tmp = []
    smpath = os.path.join("../pack", pack.name, "*/*.sm")

    for sim_file in glob.glob(smpath):
        speed = None
        try:
            sim_file_tmp = open(sim_file, 'r', encoding='utf-8-sig')
        except Exception:
            logging.error("%s du pack %s pose problème", sim_file, pack.name)
            raise

        for line in sim_file_tmp:
            if re.match("[\ \r]*#TITLE:", line):
                title = re.sub("#TITLE:", '', line, count=1).strip()

            if re.match("[\ \t]*#SUBTITLE:", line):
                subt = re.sub("#SUBTITLE:", '', line, count=1).strip()
                if len(subt) > 1:
                    title = " ".join([title, subt])

            if re.match("[\ \t]*#TITLETRANSLIT:", line):
                title_tmp = re.sub("#TITLETRANSLIT:", '',
                                   line, count=1).strip()
                if len(title_tmp) > 1:
                    title = title_tmp

            if re.match("[\ \t]*#BANNER:", line):
                banner_path = re.sub("#BANNER:", '', line,
                                     count=1).strip()
                banner_path = re.sub(";", '', banner_path)
                banner_path_base = os.path.dirname(sim_file)

                if len(banner_path) == 0:
                    banner_path = os.path.join(banner_path_base, "banner.png")
                else:
                    banner_path = os.path.join(banner_path_base, banner_path)

                fk_banner = get_banner_placement(db, banner_path)

            if re.match("[\ \t]*#DISPLAYBPM:", line):
                speed = re.sub("#DISPLAYBPM:", '', line).strip()
                speed = re.sub(r"\.[0-9]*", "", speed)
                speed = speed[:-1]

            if re.match("[\ \t]*#BPMS", line) and not speed:
                speed = get_speed(line)

            if re.match('^(\ |\t)+[^#]+\:', line):
                line = re.sub(":", "", line)
                line = re.sub(r"//.*", "", line).strip()
                lines_tmp.append(line)

        title = re.sub(";", '', title)
        del lines_tmp[4::5]
        while lines_tmp:
            if re.match('dance-single', lines_tmp[0]):
                single = 1
            elif (re.match('dance-couple', lines_tmp[0]) or
                    re.match('dance-double', lines_tmp[0])):
                single = 0
            else:
                # Lof of other stuff than dance-single/double/couple
                # to avoid ...
                del lines_tmp[0]
                del lines_tmp[0]
                del lines_tmp[0]
                del lines_tmp[0]
                continue
            del lines_tmp[0]

            if len(lines_tmp[0]) == 0:
                lines_tmp[0] = "UNAMED_STEPPER"
            stepper = Stepper(lines_tmp[0])
            fk_stepper_name = db_get_fk(db, stepper)
            del lines_tmp[0]

            difficulty = Difficulties(lines_tmp[0])
            fk_difficulty_name = db_get_fk(db, difficulty)
            del lines_tmp[0]

            difficulty_block = lines_tmp.pop(0)

            song = Songs(title, speed, single, difficulty_block,
                         fk_stepper_name, fk_difficulty_name, fk_banner)
            pack.songs.append(song)

    if len(pack.songs) == 0:
        logging.warning("Le pack %s semble ne pas avoir de songs", pack.name)
    else:
        db_insert(db, pack)


def get_speed(line):
    line = re.sub("#BPMS:", '', line).strip()
    line = line[:-1]
    line = re.sub("[0-9.]*=", "", line)
    line = re.sub(r"\.[0-9]*", "", line)
    t_line = line.split(",")
    t_line = list(map(int, t_line))

    if max(t_line) != min(t_line):
        speed = str(min(t_line))+":"+str(max(t_line))
    else:
        speed = max(t_line)

    return speed


def get_banner_placement(db, banner_path):
    set_path = os.path.join(os.getcwd(), "weblistor", "static", "images")

    try:
        filename, ext = os.path.splitext(banner_path)
        banner_rename = sha256(open(banner_path,
                                    'rb').read()).hexdigest()+ext
        banner_dest = os.path.join(set_path, banner_rename)
        copy(banner_path, banner_dest)
        banner = Banners(banner_rename)
        fk_banner = db_get_fk(db, banner)
    except FileNotFoundError as e:
        # It happens sometime people set the banner with specific
        # name in the SM file BUT they kept the name "banner.png" ...
        try:
            reg = r'(/|\\\\)[\ a-zA-Z0-9_-]*.(png|jpg|jpeg)$'
            banner_path = re.sub(reg, "/banner.png", banner_path)
            banner_rename = sha256(open(banner_path,
                                   'rb').read()).hexdigest()+ext
            banner_dest = os.path.join(set_path, banner_rename)
            copy(banner_path, banner_dest)
            banner = Banners(banner_rename)
            fk_banner = db_get_fk(db, banner)
        except FileNotFoundError as e:
            logging.warning("la banner %s n'est pas trouvable : %s",
                            banner_path, e)
            banner = Banners("default_banner.png")
            fk_banner = db_get_fk(db, banner)
    except SameFileError as e:
        logging.info("La banner %s est déjà présente %s",
                     banner_path, e)
        fk_banner = db_get_fk(db, banner)

    return fk_banner


def db_get_fk(db, data):
    try:
        db.add(data)
        db.commit()
    except exc.IntegrityError as e:
        # If data exists we check for the id
        logging.info("%s est déjà présent dans la base : %s",
                     data.name, e)
        db.rollback()
        pass

    if isinstance(data, Difficulties):
        fk = db.query(Difficulties)\
               .filter(Difficulties.name == data.name).one()
    elif isinstance(data, Banners):
        fk = db.query(Banners)\
               .filter(Banners.name == data.name).one()
    elif isinstance(data, Stepper):
        fk = db.query(Stepper)\
               .filter(Stepper.name == data.name).one()
    else:
        logging.error("Gros soucis ...")
        sys.exit(1)

    return fk.id


def db_insert(db, pack):
    try:
        db.add(pack)
        db.commit()
        fk_pack = db.query(Pack).filter(Pack.name == pack.name).one()

        for s in pack.songs:
            s.fk_pack_name = fk_pack.id

        db.add_all(pack.songs)
        db.commit()
    except exc.IntegrityError as e:
        logging.info("Le pack %s est déjà présent dans la base : %s",
                     pack.name, e)
        db.rollback()
        pass


if __name__ == '__main__':
    main()
    sys.exit(0)
