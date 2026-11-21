#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
from codecs import BOM_UTF8
from pathlib import Path
from shutil import make_archive, rmtree
from lark import Lark
from lark.exceptions import UnexpectedInput
from sqlalchemy import exc
from sqlalchemy.orm.exc import NoResultFound
from weblistor import app, db
from weblistor.tables import Pack
from weblistor.simfile import SimFile, SscFile


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


def read_simfile(path):
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        if raw.startswith(BOM_UTF8):
            raise
        text = raw.decode("cp1252")
        logging.warning("%s : lu en Windows-1252 (UTF-8 invalide)", path)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def song_extract(db, pack):
    formats = {".sm": ("simfile.lark", SimFile),
               ".ssc": ("simfile_ssc.lark", SscFile)}
    parsers = {}
    paths = sorted(Path("pack", pack.name).glob("*/*"))
    ssc_stems = {path.with_suffix("") for path in paths
                 if path.suffix.lower() == ".ssc" and path.is_file()}

    for simfile_path in paths:
        suffix = simfile_path.suffix.lower()
        if suffix not in formats or not simfile_path.is_file():
            continue
        if suffix == ".sm" and simfile_path.with_suffix("") in ssc_stems:
            continue
        grammar, visitor = formats[suffix]
        if suffix not in parsers:
            parsers[suffix] = Lark(Path(__file__).with_name(grammar).read_text(encoding="utf-8"),
                                   parser="lalr", maybe_placeholders=False)
        logging.debug("Parse : %s", simfile_path)
        try:
            simfile = read_simfile(simfile_path)
            simfile_tree = parsers[suffix].parse(simfile)
            # Chart callbacks depend on metadata from the header.
            visitor(simfile_path, pack, db).visit_topdown(simfile_tree)
        except UnexpectedInput as e:
            logging.critical("%s du pack %s a une règle inconnue :\n %s",
                             simfile_path, pack.name, e)
            return 1
        except UnicodeDecodeError as e:
            logging.critical("%s du pack %s : encodage invalide : %s",
                             simfile_path, pack.name, e)
            return 1
        except (AssertionError, ValueError) as e:
            logging.critical("%s du pack à un problème : %s", simfile_path, e)
            return 1

    assert (len(pack.songs) > 0), "Le pack %s est vide" % (pack.name)

    if db_insert(db, pack) != 1:
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

    with app.app_context():
        for pack_name in os.scandir("pack/"):
            if pack_name.is_dir(follow_symlinks=False):
                pack = Pack(pack_name.name)
                try:
                    db.session.query(Pack).filter(Pack.name == pack.name).one()
                except NoResultFound:
                    logging.debug("Extraction des songs du pack %s", pack.name)
                    song_extract(db.session, pack)
                except AssertionError as e:
                    logging.info(e)

    return 0


if __name__ == '__main__':
    main()
    sys.exit(0)
