import os
import sys
import re
from lark import Visitor
from shutil import copy, SameFileError
from hashlib import sha256
from sqlalchemy import exc
from weblistor.tables import Pack, Stepper, Banners, Difficulties, Songs


class SimFile(Visitor):
    def __init__(self, simfile_path, p, dbconn):
        # specific for SongObject set with header
        self.name = None
        self.speed = None
        self.double = None
        self.fk_banner = None
        # specific for SongObject set with *-chart
        self.difficulty_block = None
        self.fk_difficulty_name = None
        self.fk_stepper_name = None
        self.breakdown = None
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
            self.breakdown_calculation(chart_len)
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
                print("ERROR sur les data après Single NOTES", self.sm_path)
                sys.exit(1)

            self.db_get_fk(difficulty_name)
            self.double = False
            song = Songs(self.name, self.speed, self.double,
                         self.difficulty_block, self.breakdown,
                         self.fk_stepper_name.id, self.fk_difficulty_name.id,
                         self.fk_banner.id)
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
                self.difficulty_block = str(tree.children[2])
            elif len(tree.children) == 4:
                self.stepper_name_cleaning('')
                difficulty_name = Difficulties(tree.children[0])
                self.difficulty_block = tree.children[1]
            else:
                print(len(tree.children))
                print(tree.children)
                print("ERROR sur les data après Double NOTES", self.sm_path)
                sys.exit(1)

            self.db_get_fk(difficulty_name)
            self.double = True
            song = Songs(self.name, self.speed, self.double,
                         self.difficulty_block, self.breakdown,
                         self.fk_stepper_name.id, self.fk_difficulty_name.id,
                         self.fk_banner.id)
            self.add_to_pack(song)

    # Operations on data to get something clean ...
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
        # If data exists we check for the id
        try:
            self.dbconn.add(data)
            self.dbconn.commit()
        except exc.IntegrityError as e:
            self.dbconn.rollback()
            pass

        if isinstance(data, Difficulties):
            self.fk_difficulty_name = (self.dbconn.query(Difficulties).
                                       filter(Difficulties.name == data.name).
                                       one())
        elif isinstance(data, Banners):
            self.fk_banner = (self.dbconn.query(Banners).
                              filter(Banners.name == data.name).one())
        elif isinstance(data, Stepper):
            self.fk_stepper_name = (self.dbconn.query(Stepper).
                                    filter(Stepper.name == data.name).one())
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
        self.breakdown = ''.join(map(str, final_bd))

    def add_to_pack(self, song):
        self.p.songs.append(song)
