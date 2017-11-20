#!/usr/bin/python3

"""
	iTunesWatchFolder Script
	- Synchronize iTunes Library <--> Folder
	
	Written by u/RoboYoshi
"""

import os, subprocess, re, plistlib, datetime, shutil
from urllib.parse import unquote
from urllib.parse import urlparse
from urllib.parse import quote
from pprint import pprint as pp

debug = True
backup = True
addnew = True
rmdead = True

musicFolder = "/Volumes/audio/Library/artists" # define path to your music here
allowedExtensions=('mp3', 'm4a', 'm4b') # can be extended to your liking

def mkdir_p(path):
	try:
		os.makedirs(path)
	except OSError as exc:  # Python >2.5
		if exc.errno == errno.EEXIST and os.path.isdir(path):
			pass
		else:
			raise


def getiTunesXMLPath():
	"""
	Read iTunes XML Path from user defaults
	:return string: xmlPath as String
	"""
	# The user needs to enable 'Share iTunes Library XML with other applications' under Settings -> Advanced
	xmlPattern = ".*(file:.*xml).*"
	xmlProcess = subprocess.Popen(['defaults', 'read', 'com.apple.iApps', 'iTunesRecentDatabases'], stdout=subprocess.PIPE)
	xmlOutput = str(xmlProcess.stdout.read())
	xmlMatch = re.match(xmlPattern, xmlOutput)
	if(xmlMatch):
		xmlPath = xmlMatch.group(1).replace("file://","")
		xmlPath = unquote(xmlPath)
		if(debug): print("[Debug]: xmlPath = %s" % xmlPath)
		return xmlPath
	else:
		print("[Error] Could not get XML Path from defaults. Are you sharing your XML in iTunes -> Settings -> Advanced?")
		return 1

def backupLibraryDB(xmlPath):
	print("[Info]: Create Backup of iTunes Library DB.")
	backupFiles = ['iTunes Library Extras.itdb', 'iTunes Library Genius.itdb', 'iTunes Library.itl', 'iTunes Library.xml', 'iTunes Music Library.xml']
	libPath = os.path.dirname(xmlPath)
	timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
	backupFolder = libPath + "/Backups/" + timestamp + "/"
	mkdir_p(backupFolder);
	for libFile in backupFiles:
		libFilePath = os.path.join(libPath, libFile)
		bakFilePath = os.path.join(backupFolder, libFile)
		shutil.copy(libFilePath, bakFilePath)
	if(debug): print("[Debug]: Created a Backup of your iTunes Library in %s" % backupFolder)


def getTracksFromiTunesXML(xmlPath):
	print("[Info]: Fetching all Tracks from iTunes Library..")
	"""
	Extract Track Paths from iTunes XML
	:param xmlPath: Path to your iTunes Library XML (Plist) file
	:return list: List with all Tracks
	"""
	# Thanks to https://github.com/liamks/libpytunes for some pointers
	tracks = []
	library = plistlib.readPlist(xmlPath)
	for trackid, attributes in library['Tracks'].items():
		if attributes.get('Location'):
			location = unquote(urlparse(attributes.get('Location')).path)
			tracks.append(location)
	if(debug): print("[Debug]: Tracks in iTunes = %i" % len(tracks))
	return tracks

def getTracksFromFolder(dirPath, ext=('mp3', 'm4a')):
	print("[Info]: Search for Files in Folder with allowed Extensions..")
	print("[Info]: .... This might take a while ....")
	tracks = []
	count = 0
	for root, dirs, files in os.walk(dirPath):
		for name in files:
			if(name.lower().endswith(ext)):
				track = os.path.join(root, name)
				tracks.append(track)
				count+=1
				if count % 500 == 0:
					if(debug): print("[Debug]: Found %s Tracks.." % count)
	if(debug): print("[Debug]: Tracks in Folder = %i" % len(tracks))
	return tracks

def filterTracksForImport(dirTracks, libTracks):
	"""
	Match 2 Lists and check what Files are not in iTunes
	:param dirTracks, libTracks: Python Lists - Folder and iTunes
	:return list: sorted list with all missing tracks
	"""
	newTracks = list(set(dirTracks) - set(libTracks))
	if(debug): print("[Debug]: New Tracks in Folder = %i" % len(newTracks))
	return sorted(newTracks)

def importTracksToiTunes(newTracks):
	print("[Info]: Adding new Tracks to iTunes.")
	"""
	Import a Bunch of Tracks into iTunes
	:param newTracks: Python List with all new Tracks
	:return int: 0
	"""
	for track in newTracks:
		if(debug): print("[Debug]: TrackPath = %s" % track)
		script = '''
        on run {input}
			set trackFile to POSIX file input
			tell app "iTunes"
				add trackFile to playlist 1
			end tell
        end run
		'''
		args = [track]
		p = subprocess.Popen(['/usr/bin/osascript', '-'] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = p.communicate(script.encode('UTF-8'))
		if(debug):
			if(stderr!= b''): print("[Debug]: AppleScript Errors = %s" % stderr)
	return 0

def removeDeadTracksFromiTunes():
	print("[Info]: Removing Dead Tracks from iTunes")
	# Script thankfully taken from https://apple.stackexchange.com/a/52860/71498
	script = '''
	tell application "iTunes"
    	repeat with t in (get file tracks of library playlist 1)
        	if location of t is missing value then delete t
    	end repeat
	end tell
	'''
	p = subprocess.Popen(['/usr/bin/osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = p.communicate(script.encode('UTF-8'))
	if(debug):
		if(stderr!= b''): print("[Debug]: AppleScript Errors = %s" % stderr)
	return 0

# Get iTunes XML File
xmlPath = getiTunesXMLPath()

# Backup iTunes Library Files
if(backup): backupLibraryDB(xmlPath)

# Read all Tracks from Library
libTracks = getTracksFromiTunesXML(xmlPath)

# Read all Tracks from Folder
dirTracks = getTracksFromFolder(musicFolder, ext=allowedExtensions)

# Diff Arrays and only keep Tracks not already in Library
newTracks = filterTracksForImport(dirTracks, libTracks)

# Import Tracks into iTunes with AppleScript
if(addnew): importTracksToiTunes(newTracks)

# Remove Dead Tracks from iTunes
if(rmdead): removeDeadTracksFromiTunes()

# EOF