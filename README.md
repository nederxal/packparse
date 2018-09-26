Idée de départ :
pour chaque pack lister les fichier SM puis garder :
   - le pack parent                 --> le répertoire parsé
   - le nom de la musique           --> ligne #TITLE ou #TITLETRANSLIT (plus complet si existant)
   - vitesse                        --> ligne #DISPLAYBPM ou BPMS
   - stepper                        --> dans les lignes avec un [tab]
   - difficultés + nb de blocks     --> dans les lignes avec un [tab]
        sachant que 1 diff = 1 stepper la plupart du temps 
   - banner stockée en flat dans un répertoire songs_banners


Utilisation 

# packparse
1. créer une base song.db avec sqlite
2. jouer le script de création pour la table
3. mettre les packs à parser dans pack avec la même arbo que dans stepmania5/Songs
4. lancer le script et voir que tout a bien été importé dans la base

--> mettre tout ça en forme dans un site pour chercher ce que l'on veut

# Site avec Flask
- à faire 


FAIT : 
- Refonte de la base en 4 tables (pour des features futures)
- refonte de la partie insertion db
- ajout d'une partie pour NE PAS réinserer un pack déjà existants (et les songs avec)
- prise en compte des fichiers UTF-8 / des lignes vides
- amélioration pour la récupération du titre de la musique
- meilleure prise en charge ouverture smfile
- ajouter les banners pour le style


Axes d'amélioration :
- trouver comment extraire le plus efficacement possible le BPM quand #DISPLAYBPM n'est pas utilisé
    --> affichage bête comme sur SM / ITG valeur basse + valeur haute ou displayed value
- Ajouter un logger pour relever les erreurs et les actions
    --> trucs classique pour remonter ce qu'il se passe, à compléter avec les erreurs au fur et à mesure des ajouts

A faire : 
- créer le site pour exploiter les données --> en cours avec Flask
- Compteur de steps par difficulté + extraction des mesures ?
