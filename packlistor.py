#! /usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import glob
import logging
from shutil import make_archive, rmtree
from lark import Lark
from lark.exceptions import UnexpectedCharacters
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from weblistor.tables import Pack
from weblistor.simfile import SimFile


def setup_logs():
    _RED = '\033[31m'
    _GREEN = '\033[32m'
    _YELLOW = '\033[33m'
    _BLUE = '\033[34m'
    _RESET = '\033[39m'

    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s][%(asctime)s] %(message)s',
        stream=sys.stderr)

    logging.addLevelName(logging.CRITICAL, 'C')
    logging.addLevelName(logging.ERROR, 'E')
    logging.addLevelName(logging.WARNING, 'W')
    logging.addLevelName(logging.INFO, 'I')
    logging.addLevelName(logging.DEBUG, 'D')

    # Set colors
    def overrideLog(func, color):
        def info(msg, *args, **kwargs):
            msg = color + msg + _RESET
            func(msg, *args, **kwargs)

        return info

    logging.critical = overrideLog(logging.critical, _RED)
    logging.error = overrideLog(logging.error, _RED)
    logging.warning = overrideLog(logging.warning, _YELLOW)
    logging.info = overrideLog(logging.info, _GREEN)
    logging.debug = overrideLog(logging.debug, _BLUE)


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
            return 1
        except UnicodeDecodeError as e:
            logging.critical("%s du pack %s n'est pas UTF-8 ou ASCII",
                             simfile_path, pack.name)
            return 1
        except AssertionError as e:
            logging.critical("%s du pack à un problème : %s", simfile_path, e)
            return 1

    assert (len(pack.songs) > 0), "Le pack %s est vide" % (pack.name)

    db_insert(db, pack)
    move_pack(pack)


def db_insert(db, pack):
    fk_pack = None
    try:
        db.add(pack)
        db.commit()
        fk_pack = db.query(Pack).filter(Pack.name == pack.name).one()

    except exc.IntegrityError as e:
        logging.warning("Une erreur lors de l'insertion du pack %s\n %s",
                        pack.name, e)
        db.rollback()
        return 1

    try:
        for s in pack.songs:
            s.fk_pack_name = fk_pack.id

        db.add_all(pack.songs)
        db.commit()
    except exc.IntegrityError as e:
        logging.warning("Une erreur lors de l'insertion de la song %s\n %s",
                        s.name, e)
        db.rollback()
        db.delete(pack)
        db.commit()
        return 1


def move_pack(pack):
    # Since pack is in database, compress and send it to another folder
    logging.info("%s a été ajouté --> move to DL folder", pack.name)
    src = os.path.join("pack", pack.name)
    dest = os.path.join("weblistor", "static", "download", pack.name)
    try:
        make_archive(dest, 'zip', src)
        rmtree(src)
    except PermissionError as e:
        logging.error("Impossible de supprimer le pack :", pack.name)
    except Exception as e:
        logging.critical("un truc se passe mal : ", e)


def main():
    setup_logs()

    engine = create_engine('sqlite:///songs2.db')
    session = sessionmaker(bind=engine)
    db = session()

    for pack_name in os.scandir("pack/"):
        if pack_name.is_dir(follow_symlinks=False):
            pack = Pack(pack_name.name)
            try:
                db.query(Pack).filter(Pack.name == pack.name).one()
            except NoResultFound:
                logging.debug("Extraction des songs du pack %s", pack.name)
                song_extract(db, pack)
            except AssertionError as e:
                logging.info(e)

    db.close()

    return 0


if __name__ == '__main__':
    main()
    sys.exit(0)
