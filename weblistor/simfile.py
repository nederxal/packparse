import os
import sys
import re
import logging
from lark import Visitor
from shutil import copy, SameFileError
from hashlib import sha256
from sqlalchemy import exc
from weblistor.tables import Pack, Stepper, Banners, Difficulties, Songs


class SimFile(Visitor):
    def __init__(self, simfile_path, p, dbconn):
        # see tables.py for songs attributes
        self.songs_attr = {}
        self.sm_path = simfile_path
        self.p = p
        self.dbconn = dbconn

    # Lark rules
    def header(self, tree):
        for data in tree.children:
            try:
                if data.children[0] == "TITLE":
                    self.songs_attr["name"] = str(data.children[1])

                if data.children[0] == "SUBTITLE":
                    self.songs_attr["name"] = ' - '.join(
                        [self.songs_attr["name"], str(data.children[1])])

                if data.children[0] == "BANNER":
                    self.get_banner_id(data.children[1])

                if data.children[0] == "DISPLAYBPM":
                    self.songs_attr["max_speed"] = re.sub(
                        r"\.[0-9]*", "", data.children[1])

                if data.children[0] == "BPMS":
                    bpms = data.children[1]

            except IndexError:
                pass

        if "max_speed" not in self.songs_attr:
            bpms = re.sub("[0-9.]*=", "", bpms)
            bpms = re.sub(r"\.[0-9]*", "", bpms)
            t_line = bpms.split(",")
            t_line = list(map(int, t_line))

            if max(t_line) != min(t_line):
                self.songs_attr["min_speed"] = min(t_line)
                self.songs_attr["max_speed"] = max(t_line)
            else:
                self.songs_attr["min_speed"] = max(t_line)
                self.songs_attr["max_speed"] = max(t_line)

        elif re.search(":", self.songs_attr["max_speed"]):
            (self.songs_attr["min_speed"],
             self.songs_attr["max_speed"]) = (self.songs_attr["max_speed"].
                                              split(":"))
        elif self.songs_attr["max_speed"] == "*":
            # From : https://github.com/stepmania/stepmania/wiki/sm#displaybpm
            # If we can't set BPM set it to 0 :/
            self.songs_attr["min_speed"] = self.songs_attr["max_speed"] = 0
        else:
            self.songs_attr["min_speed"] = self.songs_attr["max_speed"]

        if "fk_banner" not in self.songs_attr:
            self.get_banner_id("default_banner.png")

    def single_chart(self, tree):
        # Maybe stepchart is empty ... we won't add it
        # Empty chart count at least 1 measure
        chart_len = tree.children[-1]

        if len(chart_len.children) <= 1:
            pass
        else:
            self.breakdown_calculation(chart_len)

            if len(tree.children) == 5:
                self.stepper_name_cleaning(tree.children[0])
                difficulty_name = Difficulties(tree.children[1])
                self.songs_attr["difficulty_block"] = str(tree.children[2])
            elif len(tree.children) == 4:
                self.stepper_name_cleaning('')
                difficulty_name = Difficulties(tree.children[0])
                self.songs_attr["difficulty_block"] = tree.children[1]
            else:
                # if 5 = name artist exist if 4 = name artist inexistent
                assert (4 <= len(tree.children) <= 5), \
                    logging.error("ERROR sur les data : %s", self.sm_path)

            self.db_get_fk(difficulty_name)
            self.songs_attr["double"] = False
            song = Songs(**self.songs_attr)
            self.add_to_pack(song)

    def double_chart(self, tree):
        chart_len = tree.children[-1]

        if len(chart_len.children) <= 1:
            pass
        else:
            self.breakdown_calculation(chart_len)

            if len(tree.children) == 5:
                self.stepper_name_cleaning(tree.children[0])
                difficulty_name = Difficulties(tree.children[1])
                self.songs_attr["difficulty_block"] = str(tree.children[2])
            elif len(tree.children) == 4:
                self.stepper_name_cleaning('')
                difficulty_name = Difficulties(tree.children[0])
                self.songs_attr["difficulty_block"] = tree.children[1]
            else:
                assert (4 <= len(tree.children) <= 5), \
                    logging.error("ERROR sur les data : %s", self.sm_path)

            self.db_get_fk(difficulty_name)
            self.songs_attr["double"] = True
            song = Songs(**self.songs_attr)
            self.add_to_pack(song)

    def couple_chart(self, tree):
        self.double_chart(tree)

    ##########
    # Operations on data to get something clean ...
    ##########

    # Sometimes the file defined in smfile has not the same extention
    # than the real file
    # Fun fact : If the file has not the same extension BUT has 'banner' in
    # the name, stepmania found the banner.
    # Also it seems if the extension is not good, stepmania can still find
    # the banner ... (maybe related to previous fact)
    def get_banner_id(self, banner_path):
        set_path = os.path.join(os.getcwd(), "weblistor", "static", "images")
        banner_path = os.path.join(os.path.dirname(self.sm_path), banner_path)
        filename, ext = os.path.splitext(banner_path)

        for extension in ["jpeg", "jpg", "png"]:
            try:
                banner_path_ext = '.'.join([filename, extension])
                banner_rename = (sha256(open(banner_path_ext, 'rb').read())
                                 .hexdigest()+'.'+extension)
                banner_dest = os.path.join(set_path, banner_rename)
                copy(banner_path_ext, banner_dest)
                banner = Banners(banner_rename)
                self.db_get_fk(banner)
                return None
            except FileNotFoundError as e:
                logging.debug("le fichier n'existe pas : %s", banner_path)
                pass
            except SameFileError as e:
                logging.debug("le fichier existe déjà : %s", banner_path)
                self.db_get_fk(banner)
                return None

        logging.warning("Impossible de trouver : %s", banner_path)
        banner = Banners("default_banner.png")
        self.db_get_fk(banner)

    def stepper_name_cleaning(self, stepper_name):
        clean_regex = r"\(?\b[\d+(\/|\-|\*|\||')*bpmBPMths]+\b[*\)+]*"
        stepper_name = re.sub(clean_regex, '', stepper_name)
        stepper_name = re.sub(r"^\s*", "", stepper_name)

        # Last try to get it ...
        if len(stepper_name) == 0:
            find_regex = r"(?<=\[|\()[\w\s\-\+&]+(?=\]|\))"
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
        try:
            self.dbconn.add(data)
            self.dbconn.commit()
        except exc.IntegrityError as e:
            logging.debug("La donnée existe déjà : %s", e)
            self.dbconn.rollback()
            pass

        if isinstance(data, Difficulties):
            self.songs_attr["fk_difficulty_name"] = data.get_id()
        elif isinstance(data, Banners):
            self.songs_attr["fk_banner"] = data.get_id()
        elif isinstance(data, Stepper):
            self.songs_attr["fk_stepper_name"] = data.get_id()
        else:
            raise
            sys.exit(1)

    # Too lazy to do something clean and accurate ...
    def breakdown_calculation(self, chart_len):
        pause = 0
        stream = 0
        final_bd = []

        for m in chart_len.children:
            if len(m.children) <= 8:
                if stream >= 1:
                    final_bd.append(stream)
                    stream = 0
                    pause += 1
                else:
                    pause += 1
            else:
                s = 0
                for steps in m.children:
                    if any(x in steps.children[0] for x in ["1", "2", "4"]):
                        s += 1

                # Don't forget range : [a, b[
                if s == len(m.children):
                    if pause == 1:
                        final_bd.append("'")
                        pause = 0
                        stream += 1
                    elif pause in range(2, 5):
                        final_bd.append("-")
                        pause = 0
                        stream += 1
                    elif pause in range(5, 16):
                        final_bd.append('/')
                        pause = 0
                        stream += 1
                    elif pause >= 16:
                        final_bd.append('|')
                        pause = 0
                        stream += 1
                    else:
                        stream += 1
                else:
                    if stream > 0:
                        final_bd.append(stream)
                    stream = 0
                    pause += 1

        if stream > 0:
            final_bd.append(stream)

        try:
            if not str(final_bd[0]).isdigit():
                final_bd.pop(0)

        except IndexError:
            pass

        self.songs_attr["breakdown"] = ''.join(map(str, final_bd))

    def add_to_pack(self, song):
        self.p.songs.append(song)
