import os
import sys
import re
import logging
from lark import Visitor
from shutil import copy, SameFileError
from hashlib import sha256
from sqlalchemy import exc
from weblistor.breakdown import stream_breakdown
from weblistor.tables import Pack, Stepper, Banners, Difficulties, Songs


class SimFile(Visitor):
    def __init__(self, simfile_path, p, dbconn):
        # see tables.py for songs attributes
        self.songs_attr = {}
        self.sm_path = simfile_path
        self.p = p
        self.dbconn = dbconn

    def header(self, tree):
        tags = {str(key): str(value) for key, value in
                (tag.children for tag in tree.children if len(tag.children) == 2)}
        self.set_header(tags)
        self.set_bpm(*self.bpm_range(tags))

    def set_header(self, tags):
        title = tags.get("TITLE")
        if not title:
            raise ValueError("TITLE manquant")
        subtitle = tags.get("SUBTITLE")
        self.songs_attr["name"] = f"{title} - {subtitle}" if subtitle else title
        self.get_banner_id(tags.get("BANNER") or "default_banner.png")

    @staticmethod
    def bpm_range(tags):
        display = tags.get("DISPLAYBPM")
        if display == "*":
            return 0, 0
        if display:
            speeds = [int(float(value)) for value in display.split(":")]
            return speeds[0], speeds[-1]

        speeds = [int(float(change.partition("=")[2]))
                  for change in tags.get("BPMS", "").split(",") if change.strip()]
        if not speeds:
            raise ValueError("BPMS manquant")
        return min(speeds), max(speeds)

    def set_bpm(self, min_speed, max_speed):
        self.songs_attr.update(min_speed=min_speed, max_speed=max_speed)

    def single_chart(self, tree):
        self.sm_chart(tree, double=False)

    def double_chart(self, tree):
        self.sm_chart(tree, double=True)

    def sm_chart(self, tree, double):
        *metadata, notes = tree.children
        measures = [[row.children[0] for row in measure.children]
                    for measure in notes.children]
        if len(measures) <= 1:
            return
        if len(metadata) == 3:
            metadata.insert(0, "")
        author, difficulty, meter, _radar = metadata
        self.store_chart(measures, author, difficulty, meter, double)

    def couple_chart(self, tree):
        self.double_chart(tree)

    def store_chart(self, measures, author, difficulty, meter, double):
        self.songs_attr["breakdown"] = stream_breakdown(measures)
        self.stepper_name_cleaning(author)
        self.db_get_fk(Difficulties(str(difficulty)))
        self.songs_attr.update(difficulty_block=int(meter), double=double)
        self.add_to_pack(Songs(**self.songs_attr))

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

    def add_to_pack(self, song):
        self.p.songs.append(song)


class SscFile(SimFile):
    @staticmethod
    def tags(tree):
        tags = {}
        for tag in tree.children:
            name, *value = tag.children
            tags[name.upper()] = re.sub(r"\\([;:\\])", r"\1", value[0]).strip() if value else ""
        return tags

    def ssc_header(self, tree):
        self.header_tags = self.tags(tree)
        self.set_header(self.header_tags)

    def ssc_chart(self, tree):
        tags = self.tags(tree)
        style = tags.get("STEPSTYPE", "").lower()
        if style not in ("dance-single", "dance-double"):
            return

        notes = tags.get("NOTES") or tags.get("NOTES2", "")
        notes = re.sub(r"//[^\n]*", "", notes)
        notes = re.sub(r"\[[^\]\n]*\]", "", notes)  # Keysound indices.
        measures = [measure.split() for measure in notes.split(",") if measure.strip()]
        if not any(row.strip("0") for measure in measures for row in measure):
            return

        double = style == "dance-double"
        row_width = 8 if double else 4
        if any(len(row) != row_width or not re.fullmatch(r"[01234MLFK]+", row)
               for measure in measures for row in measure):
            raise ValueError(f"notes invalides pour {style}")

        timing = tags if tags.get("DISPLAYBPM") or tags.get("BPMS") else self.header_tags
        self.set_bpm(*self.bpm_range(timing))
        author = tags.get("CREDIT") or self.header_tags.get("CREDIT", "")
        self.store_chart(measures, author, tags.get("DIFFICULTY", ""),
                         tags.get("METER", ""), double)
