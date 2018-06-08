#!/usr/bin/python3
#-*- coding: utf-8 -*-
# pour chaque pack lister les fichier SM --> garder :
#    le pack parent             --> le répertoire parsé
#    le nom de la musique    --> ligne #TITLE ou #TITLETRANSLIT (plus complet si existant)
#    vitesse                 --> ligne #DISPLAYBPM ou BPMS ou autre chose ... à voir ... on laisse de côté pour le moment.
#    stepper                 -->
#    difficultés    + nb de blocks    -->
#    sachant que 1 diff = 1 stepper la plupart du temps 
#    (banner a récup en bonux --> https://stackoverflow.com/questions/3715493/encoding-an-image-file-with-base64?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa)


import os
import sys
import re
import sqlite3
from datetime import datetime

def main():
    os.chdir("pack")
    pack_list = os.listdir(".")
    for pack_name in pack_list:
        # On ajoute le pack dans la table correspondante et on
        # récupère son ID pour la table songs
        fk_pack_name = db_insert("pack", pack_name)
        for dirPath, dirName, sim_files in os.walk(pack_name):
            for sim_file in sim_files:
                if sim_file.endswith(".sm") and fk_pack_name > 0:
                    title = sim_extract(os.path.join(dirPath,sim_file))
                    diff_extract(os.path.join(dirPath,sim_file),
                                fk_pack_name,
                                title)
    return 0

# Extraction du titre de la chanson
# possibilité d'étendre avec BPMs / bpm change, banner etc 
def sim_extract(sim_file):
    with open (sim_file, 'r', encoding='utf-8-sig') as sim_file_tmp:
        for line in sim_file_tmp:
            if line.startswith("#TITLE:"):
                title = re.sub("#TITLE:", '', line, count=1).strip()
            if line.startswith("#TITLETRANSLIT:"):
                title_tpm = re.sub("#TITLETRANSLIT:", '', line, count=1).strip()
                if len(title_tpm) > 1:
                    title = title_tpm
    sim_file_tmp.close()
    title = re.sub(";", '', title)
    return title


# Extraction difficulté / stepper artiste / double-single / difficulté blocks
def diff_extract(sim_file, pack, title):
    lines_tmp = []
    init_tab = [pack, title, "SPEED"]
    with open (sim_file, 'r', encoding='utf-8-sig') as sim_file_tmp:
        for line in sim_file_tmp:
            if re.match('[ \t]', line) \
                        and re.search(":", line) \
                        and not re.search("//", line):
                line = re.sub("[\[\]#;:\t]", '', line).strip()
                lines_tmp.append(line)
    sim_file_tmp.close()
    del lines_tmp[4::5]
    while lines_tmp:
        song_info_tab = []
        song_info_tab = list(init_tab)
        if re.match('dance-single', lines_tmp[0]):
            song_info_tab.append("True")
        else:
            song_info_tab.append("False")
        lines_tmp.pop(0)
        fk_stepper_name = db_insert("stepper", lines_tmp[0])
        lines_tmp.pop(0)
        song_info_tab.append(fk_stepper_name)
        fk_difficulty_name = db_insert("difficulty", lines_tmp[0])
        lines_tmp.pop(0)
        song_info_tab.append(fk_difficulty_name)
        song_info_tab.append(lines_tmp.pop(0))
        db_insert("songs", *song_info_tab)

def db_insert(table, *args):
    conn = sqlite3.connect("../songs.db")
    c = conn.cursor()
    if table == 'pack':
        try:
            c.execute("INSERT INTO pack(pack_name, entry_date) VALUES (?,?)", 
                    (args[0], datetime.now().year))
            conn.commit()
            c.execute('SELECT id FROM pack WHERE pack_name = ?', (args))
        except sqlite3.IntegrityError as e:
            #on fait zapper l'intégration de toute les musiques de ce pack
            print(args[0]," probablment déjà présent dans la base :", e) 
    elif table == 'stepper':
        try:
            c.execute('INSERT INTO stepper(stepper_name) VALUES (?)', (args))
        except sqlite3.IntegrityError as e:
            pass #print("Erreur sur stepper ",e)
        conn.commit()
        c.execute('SELECT id FROM stepper WHERE stepper_name = ?', (args))
    elif table == 'difficulty':
        c.execute('SELECT id FROM difficulty WHERE difficulty_name = ?', (args))
    elif table == 'songs':
        c.execute("INSERT INTO songs(fk_pack_name, \
                                    song_name, \
                                    speed, \
                                    single, \
                                    fk_stepper_name,\
                                    fk_difficulty_name,\
                                    difficulty_block)  \
                                    VALUES (?,?,?,?,?,?,?)", (args))
        conn.commit()
    value_fk = c.fetchone()
    if not value_fk:
        value_fk = [0]
    c.close()
    return value_fk[0]

if __name__ == '__main__':
    main()
    sys.exit(0)
    