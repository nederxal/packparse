CREATE TABLE dataSongs (
    id           INTEGER       PRIMARY KEY AUTOINCREMENT
                               UNIQUE
                               NOT NULL,
    pack         VARCHAR (255) DEFAULT PackLess,
    songTitle    VARCHAR (255) NOT NULL,
    songSpeed    INTEGER,
    songStepper  VARCHAR (255) DEFAULT BLANK_ARTISTE,
    singlePlay   BOOLEAN       NOT NULL
                               DEFAULT (1),
    songDiffName VARCHAR (255) NOT NULL,
    songDiff     INTEGER       NOT NULL
);
