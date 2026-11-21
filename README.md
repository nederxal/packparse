# PackParse

PackParse importe des packs de chansons StepMania dans un catalogue SQLite. L’interface Flask permet de rechercher les packs et les chansons, de consulter leurs charts et de télécharger les packs. Le projet s’inspire de StepMania Online.

## Installation

Depuis la racine du dépôt, créez un environnement virtuel avec Python 3.15. Le projet a été testé avec Python 3.15.2 et Lark 1.3.1.

```bash
python3.15 -m venv env_packparse
source env_packparse/bin/activate
python -m pip install -r requirements.txt
```

## Importer un pack

Placez une copie du dossier du pack sous `pack/`. Chaque chanson doit avoir son propre sous-dossier contenant son fichier `.sm` ou `.ssc` et ses ressources. Si deux fichiers du même sous-dossier ont le même nom de base, l’importeur privilégie le `.ssc`.

```bash
python packlistor.py
```

L’importeur enregistre les charts `dance-single` et `dance-double` dans `songs2.db`. Après avoir créé le ZIP dans `weblistor/static/download/`, il supprime le dossier de préparation correspondant sous `pack/`. Un pack dont le nom figure déjà dans la base est ignoré.

Les simfiles sont lus en UTF-8 avec ou sans BOM. Si le décodage échoue en l’absence de BOM UTF-8, l’importeur essaie Windows-1252 et journalise le recours à cet encodage. Le ZIP contient les octets des fichiers d’origine.

## Consulter le catalogue

```bash
python start.py
```

Ouvrez [le catalogue local](http://127.0.0.1:5000/). Pour activer le mode débogage, lancez `FLASK_DEBUG=1 python start.py`.

## Lire un breakdown

Un stream est une suite de pas à la cadence des doubles croches ou plus rapide, sur au moins quatre temps. La position d’un pas dépend du nombre de lignes de sa mesure. Les lignes vides et les mines ne comptent pas comme des pas.

Les longueurs sont arrondies à la mesure la plus proche, avec les demies arrondies vers le haut. Les séparateurs utilisent la durée exacte des pauses en mesures.

| Symbole | Durée de la pause |
| --- | --- |
| `'` | Jusqu’à 0,5 mesure |
| `-` | Plus de 0,5 et jusqu’à 4 mesures |
| `/` | Plus de 4 et jusqu’à 32 mesures |
| `\|` | Plus de 32 mesures |

Un breakdown `1/4/4` indique trois streams séparés par deux pauses de plus de quatre mesures. Les longueurs sont mesurées en temps du chart. Les variations de BPM, les arrêts et les warps ne sont pas convertis en temps de repos réel.

Voir la documentation des [fichiers SM](https://github.com/stepmania/stepmania/wiki/sm), des [fichiers SSC](https://github.com/stepmania/stepmania/wiki/ssc) et de la [notation ITG](https://itgwiki.dominick.cc/en/playstyles/stamina-and-footspeed).

## Tests

```bash
python -m unittest discover -s tests -v
```

Les tests importent des packs synthétiques dans des dossiers temporaires avec leur propre base SQLite.
