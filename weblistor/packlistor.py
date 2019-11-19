#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import sys
import glob
import logging
from lark import Lark
from lark.exceptions import UnexpectedCharacters
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from weblistor.tables import Pack, Stepper, Banners, Difficulties, Songs
from weblistor.simfile import SimFile

logging.basicConfig(filename='packlistor.log', level=logging.INFO)


def main():
    engine = create_engine('sqlite:///songs2.db')
    session = sessionmaker(bind=engine)
    db = session()

    for pack_name in os.scandir("pack/"):
        if pack_name.is_dir(follow_symlinks=False):
            pack = Pack(pack_name.name)
            try:
                db.query(Pack).filter(Pack.name == pack.name).one()
            except NoResultFound:
                song_extract(db, pack)
            else:
                logging.info("Le pack %s est déjà présent", pack.name)

    db.close()

    return 0


def song_extract(db, pack):
    smpath = os.path.join("pack", pack.name, "*/*.sm")
    lark_parser = Lark(open('simfile.lark', 'r').read(), parser="lalr")

    for simfile_path in glob.glob(smpath):
        logging.debug("Parse : %s", simfile_path)
        try:
            simfile = open(simfile_path, 'r', encoding='utf-8-sig').read()
            simfile_tree = lark_parser.parse(simfile)
            SimFileResult = SimFile(simfile_path, pack, db)
            SimFileResult.visit(simfile_tree)
        except UnexpectedCharacters as e:
            logging.critical("%s du pack %s a une règle inconnue :\n %s",
                             simfile_path, pack.name, e)
            raise
        except UnicodeDecodeError as e:
            logging.critical("%s du pack %s n'est pas UTF-8 ou ASCII",
                             simfile_path, pack.name)
            raise
        except Exception as e:
            logging.critical("%s du pack %s pose problème : %s",
                             simfile_path, pack.name, e)
            raise

    if len(pack.songs) == 0:
        logging.warning("Le pack %s semble ne pas avoir de songs", pack.name)
    else:
        db_insert(db, pack)


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
        logging.debug("Le pack %s est déjà présent dans la base", pack.name)
        db.rollback()
        pass


if __name__ == '__main__':
    main()
    sys.exit(0)
