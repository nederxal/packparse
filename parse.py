#!/usr/bin/python3
#-*- coding: utf-8 -*-
# pour chaque pack lister les fichier SM --> garder :
#	le pack parent 			--> le répertoire parsé
#	le nom de la musique	--> ligne #TITLE
#	vitesse 				--> ligne #DISPLAYBPM ou BPMS ou autre chose ... à voir ... on laisse de côté pour le moment.
#	stepper 				-->
#	difficultés	+ nb de blocks	-->
#	sachant que 1 diff = 1 stepper la plupart du temps 
#	(banner a récup en bonux --> https://stackoverflow.com/questions/3715493/encoding-an-image-file-with-base64?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa)


import os
import sys
import re
import sqlite3

def main():
	os.chdir("pack")
	packList = os.listdir(".")
	songsInfo = []
	for pack in packList:
		packName = pack
		for dirPath, dirName, simFiles in os.walk(packName):
			for simFile in simFiles:
				if simFile.endswith(".sm"):
					songInfos = sim_extract(packName, os.path.join(dirPath,simFile))
					insert_song(songInfos)
	sys.exit(0)

###début bloc extract données SMFILE
def sim_extract(_packName, _simFile):
	lines = []
	with open (_simFile, 'r') as simFile:
		for line in simFile:
			if line.startswith("#TITLE:"):
				line = re.sub("[\[\]#;]", '', line).strip()
				line_tmp = re.split(":", line)
				line = ' - '.join(line_tmp[1:])
				lines.append(_packName)
				lines.append(line)
				lines.append('null') #servira un jour pour la speed
				songInfos = diff_extract(lines, _simFile)
	simFile.close()
	return songInfos


def diff_extract(_lines, _simFile):
	tmpLines = []
	songInfos = []
	with open (_simFile, 'r') as simFile:
		for line in simFile:
			if re.match(r'[ \t]', line) and not re.search("//", line):
				line = re.sub("[\[\]#;:\t]", '', line).strip()
				tmpLines.append(line)
	simFile.close()
	del tmpLines[4::5]
	while tmpLines:
		lines = []
		lines = list(_lines)
		if re.match('dance-single', tmpLines[0]):
			lines.append(1)
		else:
			lines.append(0)
		tmpLines.pop(0)
		lines.append(tmpLines.pop(0))
		lines.append(tmpLines.pop(0))
		lines.append(tmpLines.pop(0))
		songInfos.append(tuple(lines))
	return songInfos


def insert_song(songsInfo):
	conn = sqlite3.connect("../songs.db")
	c = conn.cursor()
	c.executemany('INSERT INTO dataSongs(pack,songTitle,songSpeed,singlePlay,songStepper,songDiffName,songDiff) VALUES(?,?,?,?,?,?,?)',songsInfo)
	conn.commit()
	c.close()


if __name__ == '__main__':
    main()
    sys.exit(0)
