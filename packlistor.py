#!/usr/bin/python3
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
from weblistor.tables import Pack, Stepper, Banners, Difficulties, Songs
from weblistor.simfile import SimFile


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
                logger.debug("Extraction des songs du pack %s", pack.name)
                song_extract(db, pack)
            except AssertionError as e:
                logger.info(e)

    db.close()

    return 0


def song_extract(db, pack):
    smpath = os.path.join("pack", pack.name, "*/*.sm")
    lark_parser = Lark(open('simfile.lark', 'r').read(), parser="lalr")

    for simfile_path in glob.glob(smpath):
        logger.debug("Parse : %s", simfile_path)
        try:
            simfile = open(simfile_path, 'r', encoding='utf-8-sig').read()
            simfile_tree = lark_parser.parse(simfile)
            SimFileResult = SimFile(simfile_path, pack, db)
            SimFileResult.visit(simfile_tree)
        except UnexpectedCharacters as e:
            logger.critical("%s du pack %s a une règle inconnue :\n %s",
                            simfile_path, pack.name, e)
            return 1
        except UnicodeDecodeError as e:
            logger.critical("%s du pack %s n'est pas UTF-8 ou ASCII",
                            simfile_path, pack.name)
            return 1
        except AssertionError as e:
            logger.critical("%s du pack à un problème : %s", simfile_path, e)
            return 1
        except Exception as e:
            logger.critical("%s du pack %s pose problème : %s",
                            simfile_path, pack.name, e)
            return 1

    assert (len(pack.songs) > 0), "Le pack %s est vide" % (pack.name)

    try:
        db_insert(db, pack)
    except Exception as e:
        logger.info(e)
        pass
    else:
        # Since pack is in database, compress and send it to another folder
        logger.info("%s a été ajouté --> move to DL folder", pack.name)
        src = os.path.join("pack", pack.name)
        dest = os.path.join("weblistor", "static", "download", pack.name)
        try:
            make_archive(dest, 'zip', src)
            rmtree(src)
        except Exception as e:
            logger.warning("un truc se passe mal : ", e)


def db_insert(db, pack):
    fk_pack = None
    try:
        db.add(pack)
        db.commit()
        fk_pack = db.query(Pack).filter(Pack.name == pack.name).one()

    except exc.IntegrityError as e:
        logger.debug("Une erreur lors de l'insertion du pack %s\n \
            %s", pack.name, e)
        db.rollback()
        return 1

    try:
        for s in pack.songs:
            s.fk_pack_name = fk_pack.id

        db.add_all(pack.songs)
        db.commit()
    except exc.IntegrityError as e:
        logger.debug("Une erreur lors de l'insertion de la song %s\n \
            %s", s.name, e)
        db.rollback()
        pass


if __name__ == '__main__':
    format = "%(asctime)s : %(name)s : %(levelname)s : %(message)s"
    logger = logging.basicConfig(filename='packlistor.log',
                                 format=format,
                                 level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    main()
    sys.exit(0)
