#!/usr/bin/python

import os, subprocess, re, plistlib, shlex
from urllib.parse import unquote
from urllib.parse import urlparse
from urllib.parse import quote
from pprint import pprint as pp

debug = True

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

def getTracksFromiTunesXML(xmlPath):
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

def getTracksFromFolder(dirPath, extensions=('mp3', 'm4a')):
	tracks = []
	count = 0
	for root, dirs, files in os.walk(dirPath):
		for name in files:
			if(name.lower().endswith(extensions)):
				track = os.path.join(root, name)
				tracks.append(track)
				count+=1
				if count % 500 == 0:
					print("[Info]: Found %s Tracks.." % count)
	if(debug): print("[Debug]: Tracks in Folder = %i" % len(tracks))
	return tracks

def filterTracksForImport(dirTracks, libTracks):
	newTracks = list(set(dirTracks) - set(libTracks))
	if(debug): print("[Debug]: New Tracks in Folder = %i" % len(newTracks))
	return newTracks

def importTracksToiTunes(newTracks):
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

# Get iTunes XML File
xmlPath = getiTunesXMLPath()

# Read all Tracks from Library
libTracks = getTracksFromiTunesXML(xmlPath)

# Read all Tracks from Folder
dirTracks = getTracksFromFolder("/Volumes/audio/Library/artists")

# Diff Arrays and only keep Tracks not already in Library
newTracks = filterTracksForImport(dirTracks, libTracks)

# Import Tracks into iTunes with AppleScript
importTracksToiTunes(newTracks)

# EOF