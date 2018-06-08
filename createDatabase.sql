CREATE TABLE pack (
    id         INTEGER       PRIMARY KEY ON CONFLICT ROLLBACK AUTOINCREMENT
                             UNIQUE,
    pack_name  VARCHAR (255) NOT NULL
                             UNIQUE,
    entry_date DATE
);

CREATE TABLE stepper (
    id           INTEGER       PRIMARY KEY AUTOINCREMENT
                               UNIQUE,
    stepper_name VARCHAR (255) UNIQUE
                               NOT NULL
);

CREATE TABLE difficulty (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    difficulty_name         UNIQUE
);

INSERT INTO difficulty (difficulty_name)
VALUES ("Beginner"), ("Easy"), ("Medium"), ("Hard"), ("Challenge"), ("Edit")


CREATE TABLE songs (
    id                 INTEGER       PRIMARY KEY AUTOINCREMENT
                                     UNIQUE,
    fk_pack_name                     REFERENCES pack (id) ON DELETE CASCADE
                                                          ON UPDATE CASCADE
                                     NOT NULL,
    song_name          VARCHAR (255) NOT NULL,
    speed              INTEGER,
    fk_stepper_name                  REFERENCES stepper (id) ON DELETE NO ACTION
                                                             ON UPDATE CASCADE
                                     NOT NULL,
    single             BOOLEAN       NOT NULL
                                     DEFAULT True,
    fk_difficulty_name               NOT NULL
                                     REFERENCES difficulty (id) ON DELETE SET NULL
                                                                ON UPDATE CASCADE,
    difficulty_block   INTEGER       NOT NULL
);

