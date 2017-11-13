import os,re

# Metadata IO
# from mutagen.flac import FLAC

# The Selfhosted Music-Toolbox

root='/Volumes/audio/Lossless/'

def validateArtistFolder():
	# artist.(jpg|png)
	# <ALBUMS>
	print("todo")

def validateAlbumFolder(albumPath):
	# Single Disc Album:
	# TRACKNUMBER - TRACKTITLE.EXT
	# Cover.jpg
	# Scans/Artwork / Front.jpg, Back.jpg
	# ALBUMARTIST - ALBUM.cue
	# ALBUMARTIST - ALBUM.log
	# ------
	# Multi-Disc Album:
	# CD1 / TRACKNUMBER - TRACKTITLE.EXT
	# CD1 / Cover.jpeg
	# CD1 / Scans|Artwork / ...
	# CD1 / ALBUMARTIST - ALBUM.cue
	# ------
	root = os.listdir(albumPath)

	if root == []:
		print("! - Album is empty")

	multiDiscPattern = '^((CD ?[0-9]+)|(Disc ?[0-9]+))$'
	multiDisc = False
	discCount = 0
	# Test if Splitted in Multiple Discs first
	for element in root:
		if (re.match(multiDiscPattern, element)):
			discCount += 1
			if discCount > 1: multiDisc=True
	if (multiDisc == True):
		for element in root:
			if (re.match(multiDiscPattern, element)):
				validateAlbumFolder(os.path.join(albumPath, element))
	else:
		print("----> Check Files")
		


def validateAlbumFolderName(albumFolder):
	# ALBUMARTIST - YEAR - ALBUM (VARIANT) [SRC - FORMAT - QUALITY] {CATALOG#, RELEASE-INFO}
	pattern='^(.*) - ([1-2][0-9][0-9][0-9]) - (.*) \[(CD|WEB|Vinyl) - (WAVE|FLAC|ALAC|MP3|AAC) - (Lossless|24-48|16-44|320|224|192|128|V0|V1)\]( \{.*\})?$'
	result = re.match(pattern, albumFolder)
	return result

def validateArtistSection(sectionPath, printGood=False, printBad=True):
	good=0
	bad=0
	excludes=['.DS_Store', 'Artwork', 'artist.jpg']
	for artist in sorted(os.listdir(sectionPath)):
		artistPath = os.path.join(sectionPath, artist)
		for album in sorted(os.listdir(artistPath)):
			albumPath = os.path.join(artistPath, album)
			if album in excludes:
				continue
			valid = validateAlbumFolder(albumPath)
			result = validateAlbumFolderName(album)
			if (result):
				if (printGood):
					print("\`--> ", result[0])
				good+=1
			else:
				if (printBad):
					print(artist, '|', album)
				bad+=1
	print('Total Bad: ', bad)
	print('Total Good: ', good)

validateArtistSection("/Volumes/audio/Lossless/artists")