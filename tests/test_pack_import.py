import codecs
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def chart(style, author, difficulty, meter, row):
    measure = "\n".join([row] * 16)
    return (
        f"#NOTES:{style}:{author}:{difficulty}:{meter}:0,0,0,0,0:\n"
        f"{measure}\n,\n{measure}\n;\n"
    )


class PackImportTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        for filename in ("packlistor.py", "simfile.lark", "simfile_ssc.lark"):
            shutil.copyfile(PROJECT_ROOT / filename, self.root / filename)
        shutil.copytree(
            PROJECT_ROOT / "weblistor", self.root / "weblistor",
            ignore=shutil.ignore_patterns("__pycache__", "images", "download"),
        )
        static = self.root / "weblistor" / "static"
        for folder in ("images", "download"):
            (static / folder).mkdir()
        self.archive = static / "download" / "Test Pack.zip"
        self.simfile = self.root / "pack" / "Test Pack" / "[Fallback Author] Song" / "Song.sm"
        self.simfile.parent.mkdir(parents=True)

    def run_importer(self):
        result = subprocess.run(
            [sys.executable, "packlistor.py"], cwd=self.root,
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stderr

    def query(self, sql):
        with closing(sqlite3.connect(self.root / "songs2.db")) as db:
            return db.execute(sql).fetchall()

    def test_imports_single_and_double_charts_with_metadata(self):
        simfile = "#TITLE:Test Song;\n#SUBTITLE:Remix;\n#BPMS:0=120,16=180;\n"
        simfile += chart("dance-single", "Chart Author", "Hard", 9, "1000")
        simfile += chart("dance-double", "", "Challenge", 11, "10000000")
        simfile += chart("dance-solo", "Chart Author", "Hard", 8, "100000")
        original = codecs.BOM_UTF8 + simfile.encode("utf-8")
        self.simfile.write_bytes(original)

        log = self.run_importer()

        self.assertEqual(self.query("SELECT name FROM pack"), [("Test Pack",)], log)
        self.assertEqual(
            self.query("""
                SELECT songs.name, min_speed, max_speed, double, difficulty_block,
                       difficulties.name, stepper.name, breakdown
                FROM songs
                JOIN difficulties ON difficulties.id = songs.fk_difficulty_name
                JOIN stepper ON stepper.id = songs.fk_stepper_name
                ORDER BY difficulty_block
            """),
            [
                ("Test Song - Remix", 120, 180, 0, 9, "Hard", "Chart Author", "2"),
                ("Test Song - Remix", 120, 180, 1, 11, "Challenge", "Fallback Author", "2"),
            ],
            log,
        )
        with ZipFile(self.archive) as archive:
            self.assertEqual(archive.read("[Fallback Author] Song/Song.sm"), original)

    def test_imports_legacy_encoding_and_archives_original_bytes(self):
        simfile = "#TITLE:The Man²;\r\n#ARTIST:Kitsune²;\r\n#BPMS:0=150;\r\n"
        simfile += chart("dance-single", "Chart Author", "Hard", 9, "1000")
        original = simfile.encode("cp1252")
        self.simfile.write_bytes(original)

        log = self.run_importer()

        self.assertIn("Windows-1252", log)
        self.assertEqual(self.query("SELECT name FROM songs"), [("The Man²",)], log)
        with ZipFile(self.archive) as archive:
            self.assertEqual(archive.read("[Fallback Author] Song/Song.sm"), original)

    def test_rejects_malformed_simfile_and_preserves_source(self):
        self.simfile.write_bytes(b"!")

        log = self.run_importer()

        self.assertIn("règle inconnue", log)
        self.assertEqual(self.query("SELECT name FROM pack"), [])
        self.assertEqual(self.query("SELECT name FROM songs"), [])
        self.assertFalse(self.archive.exists())
        self.assertEqual(self.simfile.read_bytes(), b"!")

    def test_rejects_invalid_utf8_when_bom_declares_utf8(self):
        original = codecs.BOM_UTF8 + b"#TITLE:Broken\xb2;\n#BPMS:0=150;\n"
        self.simfile.write_bytes(original)

        log = self.run_importer()

        self.assertIn("encodage invalide", log)
        self.assertNotIn("Windows-1252", log)
        self.assertEqual(self.query("SELECT name FROM pack"), [])
        self.assertFalse(self.archive.exists())
        self.assertEqual(self.simfile.read_bytes(), original)

    def test_imports_ssc_charts_with_independent_tags_and_timing(self):
        # If both formats exist, use the SSC so the charts are not duplicated.
        self.simfile.write_bytes(b"!")
        ssc = self.simfile.with_suffix(".ssc")
        ssc.write_text(
            "#TITLE:SSC Song;\n#SUBTITLE:Remix;\n#BPMS:0=120;\n#CREDIT:Song Author;\n"
            "// chart comment\n#NOTEDATA:;\n#STEPSTYPE:dance-single;\n"
            "#DIFFICULTY:Hard;\n#METER:9;\n#CREDIT:Chart Author;\n"
            "#BPMS:0=150,\n16=180;\n#NOTES:\n1000\n0000\n;\n"
            "#NOTEDATA:;\n#STEPSTYPE:dance-double;\n"
            "#DIFFICULTY:Challenge;\n#METER:11;\n#NOTES2:\n10000000[1]\n;\n"
            "#NOTEDATA:;\n#STEPSTYPE:pump-single;\n#NOTES:10000;\n",
            encoding="utf-8",
        )

        log = self.run_importer()

        self.assertEqual(
            self.query("""
                SELECT songs.name, min_speed, max_speed, double, difficulty_block, stepper.name
                FROM songs JOIN stepper ON stepper.id = songs.fk_stepper_name
                ORDER BY difficulty_block
            """),
            [
                ("SSC Song - Remix", 150, 180, 0, 9, "Chart Author"),
                ("SSC Song - Remix", 120, 120, 1, 11, "Song Author"),
            ],
            log,
        )

    def test_stream_uses_note_spacing_and_fractional_breaks(self):
        # The 32-row measure still contains 16ths. Its empty rows are padding.
        padded_16ths = ["1100", "00M0"] * 16
        half_stream = ["2000"] * 8 + ["3000"] * 8
        # Leave the downbeat empty so the 12th notes start outside the prior run.
        slower_measure = ["0000"] + ["1000"] * 11
        measures = [padded_16ths, half_stream, padded_16ths, slower_measure,
                    padded_16ths, half_stream]
        notes = ",\n".join("\n".join(measure) for measure in measures)
        self.simfile.write_text(
            "#TITLE:Stream;\n#BPMS:0=150;\n"
            "#NOTES:dance-single:Test:Hard:9:0,0,0,0,0:\n" + notes + ";\n",
            encoding="utf-8",
        )

        log = self.run_importer()

        self.assertEqual(
            self.query("SELECT breakdown FROM songs"), [("2'1-2",)], log
        )
