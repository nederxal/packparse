#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import logging
from shutil import copy, SameFileError
from hashlib import sha256
from datetime import datetime
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker
from weblistor.tables import Pack, Stepper, Banners, Difficulties, Songs


def main():
    logging.basicConfig(filename='packlistor.log', level=logging.INFO)
    engine = create_engine('sqlite:///songs2.db')
    session = sessionmaker(bind=engine)
    db = session()

    for pack_name in os.listdir("../pack/"):
        pack = Pack(pack_name)
        song_extract(db, pack)

    db.close()

    return 0


def song_extract(db, pack):
    lines_tmp = []

    for dir_path, dir_name, files in os.walk("../pack/"+pack.name):
        for sim_file in files:
            if sim_file.endswith(".sm"):
                speed = None
                try:
                    sim_file_tmp = open(os.path.join(dir_path, sim_file),
                                        'r', encoding='utf-8-sig')
                except Exception:
                    logging.error("%s du pack %s pose problème",
                                  sim_file,
                                  pack.name)
                    raise

                for line in sim_file_tmp:
                    if line.startswith("#TITLE:"):
                        title = re.sub("#TITLE:", '', line, count=1).strip()

                    if line.startswith("#TITLETRANSLIT:"):
                        title_tmp = re.sub("#TITLETRANSLIT:", '', line,
                                           count=1).strip()

                        if len(title_tmp) > 1:
                            title = title_tmp

                    if line.startswith("#BANNER:"):
                        banner_path = re.sub("#BANNER:", '', line,
                                             count=1).strip()
                        banner_path = re.sub(";", '', banner_path)

                        if len(banner_path) == 0:
                            banner_path = os.path.join(dir_path, "banner.png")
                        else:
                            banner_path = os.path.join(dir_path, banner_path)

                        fk_banner = get_banner_placement(db, banner_path)

                    if line.startswith("#DISPLAYBPM:"):
                        speed = re.sub("#DISPLAYBPM:", '', line).strip()
                        speed = re.sub(r"\.[0-9]*", "", speed)
                        speed = speed[:-1]

                    if line.startswith("#BPMS") and not speed:
                        speed = get_speed(line)

                    if re.match('[ \t]', line) \
                            and re.search(":", line) \
                            and not re.search("//", line):
                        line = re.sub(r"[\[\]#;:\t]", '', line).strip()
                        lines_tmp.append(line)

                title = re.sub(";", '', title)
                del lines_tmp[4::5]

                while lines_tmp:
                    if re.match('dance-single', lines_tmp[0]):
                        single = 1
                    else:
                        single = 0

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
                                 fk_stepper_name, fk_difficulty_name,
                                 fk_banner)
                    pack.songs.append(song)

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
