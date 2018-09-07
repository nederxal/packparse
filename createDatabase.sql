CREATE TABLE pack (
    id         INTEGER       PRIMARY KEY ON CONFLICT ROLLBACK AUTOINCREMENT
                             UNIQUE,
    pack_name  VARCHAR (255) NOT NULL
                             UNIQUE,
    entry_date DATE,
    desc_pack  TEXT
);

CREATE TABLE stepper (
    id           INTEGER       PRIMARY KEY AUTOINCREMENT
                               UNIQUE,
    stepper_name VARCHAR (255) UNIQUE
                               NOT NULL,
    desc_stepper TEXT
);

CREATE TABLE banner (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    banner BLOB
);

CREATE TABLE difficulty (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    difficulty_name         UNIQUE
);

INSERT INTO difficulty (difficulty_name)
VALUES ("Beginner"), ("Easy"), ("Medium"), ("Hard"), ("Challenge"), ("Edit")

CREATE TABLE songs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT
                               UNIQUE,
    fk_pack_name               REFERENCES pack (id) ON DELETE CASCADE
                                                    ON UPDATE CASCADE
                               NOT NULL,
    song_name          VARCHAR (255) NOT NULL,
    speed              VARCHAR (255),
    fk_stepper_name            REFERENCES stepper (id) ON DELETE NO ACTION
                                                       ON UPDATE CASCADE
                               NOT NULL,
    single             BOOLEAN NOT NULL
                               DEFAULT True,
    fk_difficulty_name         NOT NULL
                               REFERENCES difficulty (id) ON DELETE SET NULL
                                                          ON UPDATE CASCADE,
    difficulty_block   INTEGER NOT NULL,
    fk_banner                  REFERENCES banners (id) ON DELETE SET NULL
);

CREATE VIEW v_songs AS
SELECT p.pack_name, s.song_name, s.difficulty_block, d.difficulty_name, st.stepper_name
FROM pack p, songs s, difficulty d, stepper st
WHERE p.id = s.fk_pack_name
AND d.id = s.fk_difficulty_name
AND st.id = s.fk_stepper_name
ORDER BY s.fk_pack_name, s.song_name, s.difficulty_block