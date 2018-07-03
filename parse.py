#!/usr/bin/python3
#-*- coding: utf-8 -*-

import os
import sys
import re
import sqlite3
import base64
from datetime import datetime
from collections import namedtuple

def main():
     
    Pack = namedtuple('Pack',
        ['name',
         'songs'])

    db = db_open("songs.db")
     
    os.chdir("pack")
    for pack_name in os.listdir("."):
        pack = Pack(pack_name,[])
        song_extract(db, pack)
    
    db.close()

    return 0

def song_extract(db, pack):

    Song = namedtuple('Song',
    ['name',
     'speed',
     'single',
     'fk_stepper_name',
     'fk_difficulty_name',
     'difficulty_block',
     'banner'])

    lines_tmp = []
    speed = ''
    
    for dir_path, dir_name, files in os.walk(pack.name):
        for sim_file in files:
            if sim_file.endswith(".sm"):
                try:
                    sim_file_tmp = open(os.path.join(dir_path,sim_file),
                                    'r',
                                    encoding='utf-8-sig')
                except:
                    print(sim_file, "pose problème")
                    raise

                for line in sim_file_tmp:
                    if line.startswith("#TITLE:"):
                        title = re.sub("#TITLE:", '', line, count=1).strip()
                    if line.startswith("#TITLETRANSLIT:"):
                        title_tmp = re.sub("#TITLETRANSLIT:",
                                    '',
                                    line, count=1).strip()
                        if len(title_tmp) > 1:
                            title = title_tmp
                    if line.startswith("#BANNER:"):
                        banner_path = re.sub("#BANNER:", '', line, count=1).strip()
                        banner_path = re.sub(";", '', banner_path)
                        try:
                            banner = open(os.path.join(dir_path,banner_path), 'rb')
                            banner_b64 = base64.b64encode(banner.read())
                        except FileNotFoundError as e:
                            print("la banner n'existe pas on set à NULL")
                            banner_b64 = ''
                        fk_banner = db_get_fk(db, "banners", banner_b64)
                    if line.startswith("#DISPLAYBPM:"):
                        speed = re.sub("#DISPLAYBPM:", '', line).strip()
                        speed = speed[:-1]
                    if line.startswith("#BPMS") and not speed:
                        speed = 0 #get_speed(line)
                    if re.match('[ \t]', line) \
                            and re.search(":", line) \
                            and not re.search("//", line):
                        line = re.sub("[\[\]#;:\t]", '', line).strip()
                        lines_tmp.append(line)
                
                title = re.sub(";", '', title)
                del lines_tmp[4::5]
                
                while lines_tmp:
                    if re.match('dance-single', lines_tmp[0]):
                        single_double = "True"
                    else:
                        single_double = "False"
                    del lines_tmp[0]
                    if len(lines_tmp[0]) == 0:
                        lines_tmp[0] = "UNAMED_STEPPER"
                    fk_stepper_name = db_get_fk(db, "stepper", lines_tmp[0])
                    del lines_tmp[0]
                    fk_difficulty_name = db_get_fk(db, "difficulty", lines_tmp[0])
                    del lines_tmp[0]
                    difficulty_block = lines_tmp.pop(0)
                    s = Song(title,
                        speed,
                        single_double,
                        fk_stepper_name,
                        fk_difficulty_name,
                        difficulty_block,
                        fk_banner)
                    pack.songs.append(s)
    
    db_insert(db, pack)
    
def db_open(path):
    conn = sqlite3.connect(path)
    return conn
    
    
def db_get_fk(db, table, fk):

    c = db.cursor()
    
    if table == 'stepper':
        try:
            c.execute('INSERT INTO stepper(stepper_name) VALUES (?)', (fk,))
        except sqlite3.IntegrityError as e:
            pass #print("Erreur sur stepper ",e)
        db.commit()
        c.execute('SELECT id FROM stepper WHERE stepper_name = ?', (fk,))
    elif table == 'difficulty':
        c.execute('SELECT id FROM difficulty WHERE difficulty_name = ?', (fk,))
    elif table == 'banners':
        try:
            c.execute('INSERT INTO banners(banner) VALUES (?)', (fk,))
        except sqlite3.IntegrityError as e:
            pass
        db.commit()
        c.execute('SELECT id FROM banners WHERE banner = ?', (fk,))
        
    value_fk = c.fetchone()
    
    return value_fk[0]
    
def db_insert(db, pack):
    c = db.cursor()
    
    try:
        c.execute("INSERT INTO pack(pack_name, entry_date) VALUES (?,?)", 
                (pack.name, datetime.now().year))
        db.commit()
        c.execute('SELECT id FROM pack WHERE pack_name = ?', (pack.name,))
        fk_pack_name = c.fetchone()
    
        for t in pack.songs:
            print(fk_pack_name," ",t)
            c.execute("INSERT INTO songs(fk_pack_name, \
                                        song_name, \
                                        speed, \
                                        single, \
                                        fk_stepper_name,\
                                        fk_difficulty_name,\
                                        difficulty_block,\
                                        fk_banner)  \
                                        VALUES (?,?,?,?,?,?,?,?)",
                                        (fk_pack_name[0],
                                        t.name,
                                        t.speed,
                                        t.single,
                                        t.fk_stepper_name,
                                        t.fk_difficulty_name,
                                        t.difficulty_block,
                                        t.banner))
        db.commit()
    except sqlite3.IntegrityError as e:
        #on fait zapper l'intégration de toute les musiques de ce pack
        print(pack.name," probablment déjà présent dans la base :", e)
    
# def get_speed(line):
    # line = re.sub("#DISPLAYBPM:", '', line).strip()
    # line = re.sub(";", "", line)
    
    
if __name__ == '__main__':
    main()
    sys.exit(0)
    