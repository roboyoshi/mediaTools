#!/usr/local/bin/python3

"""
	iTunesWatchFolder Script
	- Synchronize iTunes Library <--> Folder
	Written by u/RoboYoshi
"""

import sys, time, itertools, threading, queue
import os, subprocess, re, plistlib, datetime, shutil
from urllib.parse import quote, unquote, urlparse
from pprint import pprint as pp
from Foundation import NSURL
from ScriptingBridge import SBApplication

DEBUG = False
CREATE_BACKUP = True
ADD_NEW_TRACKS = True
REMOVE_DEAD_TRACKS = False

# If used in Application Context
if DEBUG: print("[Debug]\t sys.argv = ", sys.argv)
if len(sys.argv) > 1:
    musicFolder = sys.argv[1]
else:
	print("[Warn]\t No Library given to sync with.")
	musicFolder = "/Volumes/audio/Library/podcasts"
	# sys.exit(1)

allowedExtensions=('mp3', 'm4a', 'm4b') # can be extended to your liking

def loadingAnimation():
	for c in itertools.cycle(['|', '/', '-', '\\']):
		if done:
			sys.stdout.write('\r')
			sys.stdout.flush()
			break
		sys.stdout.write('\r' + c)
		sys.stdout.flush()
		time.sleep(0.1)
	sys.stdout.write('\rDone!')

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
		if(DEBUG): print("[Debug]\t xmlPath = %s" % xmlPath)
		return xmlPath
	else:
		print("[Error]\t Could not get XML Path from defaults. Are you sharing your XML in iTunes -> Settings -> Advanced?")
		return 1

def backupLibraryDB(xmlPath):
	print("[Info]\t Creating Backup of iTunes Library DB.")
	backupFiles = ['iTunes Library Extras.itdb', 'iTunes Library Genius.itdb', 'iTunes Library.itl', 'iTunes Library.xml', 'iTunes Music Library.xml']
	libPath = os.path.dirname(xmlPath)
	timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
	backupFolder = libPath + "/Backups/" + timestamp + "/"
	mkdir_p(backupFolder);
	for libFile in backupFiles:
		libFilePath = os.path.join(libPath, libFile)
		bakFilePath = os.path.join(backupFolder, libFile)
		try:
			shutil.copy(libFilePath, bakFilePath)
		except:
			if(DEBUG): print("[Debug]\t libFile Missing: %s" % libFile)
			pass
	if(DEBUG): print("[Debug]\t Created a Backup of your iTunes Library in %s" % backupFolder)
	return 0

def getTracksFromiTunesXML(xmlPath, noNSURL=False):
	"""
	Extract Track Paths from iTunes XML
	:param xmlPath:
		Path to your iTunes Library XML (Plist) file
	:param noNSURL:
		If False, the track Path is returned
	:return list:
		List with all Tracks
	"""
	# Thanks to https://github.com/liamks/libpytunes for some pointers
	print("[Info]\t Fetching all Tracks from iTunes Library..")
	libTracks = []
	library = plistlib.readPlist(xmlPath)
	for trackid, attributes in library['Tracks'].items():
		if attributes.get('Location'):
			trackPath = attributes.get('Location')
			if(DEBUG): print("[Debug]\t Track Path in iTunes = %s" % trackPath)
			# By default we take the raw NSURL from the iTunes.xml
			trackPath = unquote(urlparse(trackPath).path)
			if(noNSURL):
				location = trackPath
			else:
				# NoTE: We shall transform the locationAttr of the track into an NSURL Object
				# While we sure CAN, it's not useful:
				# the tracks would be double-encoded and gain other hashes for comparision later
				location = NSURL.fileURLWithPath_(trackPath)
			libTracks.append(location)
	print("[Info]\t Tracks in iTunes = %i" % len(libTracks))
	libTracksQueue.put(libTracks) # Put result in Queue
	return libTracks

def getTracksFromFolder(dirPath, ext=('mp3', 'm4a'), noNSURL=False):
	"""
	Retrieve all Songs from Folder
	:param dirPath:
		filePath to Music as String
	:param ext:
		A tuple list of allowed extensions
	:param noNSURL:
		Set True/False if you want to return Songs as NSURL Paths
		Note that the Songs need to be conform with iTunes Extractions for comparision.
	"""
	print("[Info]\t Search for Files in Folder with allowed Extensions..")
	dirTracks = []
	count = 0
	for root, dirs, files in os.walk(dirPath):
		for name in files:
			if(name.lower().endswith(ext)):
				track = os.path.join(root, name)
				if(noNSURL):
					location = track
				else:
					location = NSURL.fileURLWithPath_(track)
				dirTracks.append(location)
				if(DEBUG): print("[Debug]\t Track Path in Folder = %s" % location)
				count+=1
				if count % 500 == 0:
					if(DEBUG): print("[Debug]: Found %s Tracks.." % count)
	print("[Info]\t Tracks in Folder = %i" % len(dirTracks))
	dirTracksQueue.put(dirTracks)
	return dirTracks

def filterTracksForImport(dirTracks, libTracks):
	"""
	Match 2 Lists and check what Files are not in iTunes
	:param dirTracks, libTracks: Python Lists - Folder and iTunes
	:return list: sorted list with all missing tracks
	"""
	newTracks = list(set(dirTracks) - set(libTracks))
	# newTracks = sorted(newTracks) # NSURL are not sortable?
	print("[Info]\t New Tracks to Import = %i" % len(newTracks))		
	return newTracks

def importTracksToiTunesViaSB(newTracks):
	print("[Info]\t Adding new Tracks to iTunes.")
	"""
	Import a Bunch of Tracks into iTunes
	:param newTracks: Python List with all new Tracks
	:return int: 0
	"""
	iTunes = SBApplication.applicationWithBundleIdentifier_("com.apple.iTunes")
	count = 0
	batchSize = 100
	batch = []
	for track in newTracks:
		if(DEBUG): print("[Debug]\t TrackPath = %s" % track)
		batch.append(track)
		count += 1
		if(batchSize % count == 0):
			iTunes.add_to_(batch, None)
			batch.clear()
	return 0

def removeDeadTracksFromiTunes():
	print("[Info]\t Removing Dead Tracks from iTunes")
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
	if(DEBUG):
		if(stderr!= b''): print("[Debug]\t AppleScript Error: %s" % stderr)
	return 0


# Get iTunes XML File
xmlPath = getiTunesXMLPath()

# Backup iTunes Library Files
if(CREATE_BACKUP): backupLibraryDB(xmlPath)

# Prepare Queues to store values
libTracksQueue = queue.Queue()
dirTracksQueue = queue.Queue()

# Declare Threads
libTracksThread = threading.Thread(target=getTracksFromiTunesXML, args=(xmlPath,))
dirTracksThread = threading.Thread(target=getTracksFromFolder, args=(musicFolder,), kwargs={'ext' : allowedExtensions})

done = False
loadingThread = threading.Thread(target=loadingAnimation)
loadingThread.start()

# Start both Threads
libTracksThread.start()
dirTracksThread.start()

# Wait until both are finished
libTracksThread.join()
dirTracksThread.join()

done = True
# Get Arrays from Thread-Queues
libTracks = libTracksQueue.get()
dirTracks = dirTracksQueue.get()

# Diff Arrays and only keep Tracks not already in Library
newTracks = filterTracksForImport(dirTracks, libTracks)

if(len(newTracks) != 0):
	# Import Tracks into iTunes with AppleScript
	if(ADD_NEW_TRACKS):
		done = False
		loadingThread = threading.Thread(target=loadingAnimation)
		loadingThread.start()
		importTracksToiTunesViaSB(newTracks)
		done = True
else: print("[Info]\t No New Tracks.")

# Remove Dead Tracks from iTunes
if(REMOVE_DEAD_TRACKS): removeDeadTracksFromiTunes()

# EOF