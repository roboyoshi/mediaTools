#!/usr/bin/python3

"""
	iTunesWatchFolder Script
	- Synchronize iTunes Library <--> Folder
	
	Written by u/RoboYoshi
"""

import sys, time, itertools, threading, queue
import os, subprocess, re, plistlib, datetime, shutil
from urllib.parse import quote, unquote, urlparse
from pprint import pprint as pp

debug = False
backup = True
addnew = True
rmdead = True

# If used in Application Context
if(debug): print("[Debug]\t sys.argv = ", sys.argv)
if(len(sys.argv))>1:
	musicFolder = sys.argv[1]
else:
	print("[Warn]\t No Library given to sync with.")
	sys.exit(1)

allowedExtensions=('mp3', 'm4a', 'm4b') # can be extended to your liking

def loadingAnimation():
	for c in itertools.cycle(['|', '/', '-', '\\']):
		if done:
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
		if(debug): print("[Debug]\t xmlPath = %s" % xmlPath)
		return xmlPath
	else:
		print("[Error]\t Could not get XML Path from defaults. Are you sharing your XML in iTunes -> Settings -> Advanced?")
		return 1

def backupLibraryDB(xmlPath):
	print("[Info]\t Create Backup of iTunes Library DB.")
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
			if(debug): print("[Debug]\t libFile Missing: %s" % libFile)
			pass
	if(debug): print("[Debug]\t Created a Backup of your iTunes Library in %s" % backupFolder)


def getTracksFromiTunesXML(xmlPath):
	"""
	Extract Track Paths from iTunes XML
	:param xmlPath: Path to your iTunes Library XML (Plist) file
	:return list: List with all Tracks
	"""
	# Thanks to https://github.com/liamks/libpytunes for some pointers
	print("[Info]\t Fetching all Tracks from iTunes Library..")
	libTracks = [] # RAW POSIX PATH PLS
	library = plistlib.readPlist(xmlPath)
	for trackid, attributes in library['Tracks'].items():
		if attributes.get('Location'):
			location = unquote(urlparse(attributes.get('Location')).path)
			if(debug): print("[Debug]\t Track Path in iTunes = %s" % location)
			libTracks.append(location)
	print("[Info]\t Tracks in iTunes = %i" % len(libTracks))
	q_libTracks.put(libTracks)
	return libTracks

def getTracksFromFolder(dirPath, ext=('mp3', 'm4a')):
	print("[Info]\t Search for Files in Folder with allowed Extensions..")
	dirTracks = [] # RAW POSIX PATH PLS
	count = 0
	for root, dirs, files in os.walk(dirPath):
		for name in files:
			if(name.lower().endswith(ext)):
				track = os.path.join(root, name)
				dirTracks.append(track)
				count+=1
				if count % 500 == 0:
					if(debug): print("[Debug]: Found %s Tracks.." % count)
	print("[Info]\t Tracks in Folder = %i" % len(dirTracks))
	q_dirTracks.put(dirTracks)
	return dirTracks

def filterTracksForImport(dirTracks, libTracks):
	"""
	Match 2 Lists and check what Files are not in iTunes
	:param dirTracks, libTracks: Python Lists - Folder and iTunes
	:return list: sorted list with all missing tracks
	"""
	newTracks = list(set(dirTracks) - set(libTracks))
	if(debug): print("[Debug]\t New Tracks in Folder = %i" % len(newTracks))
	return sorted(newTracks)

def importTracksToiTunes(newTracks):
	print("[Info]\t Adding new Tracks to iTunes.")
	"""
	Import a Bunch of Tracks into iTunes
	:param newTracks: Python List with all new Tracks
	:return int: 0
	"""
	for track in newTracks:
		if(debug): print("[Debug]\t TrackPath = %s" % track)
		# Script Notes: Unicode is needed for files with special characters.
		script = '''
        on run {input}
			set trackFile to POSIX file input as Unicode text
			tell app "iTunes"
				add trackFile to playlist 1
			end tell
        end run
		'''
		args = [track]
		p = subprocess.Popen(['/usr/bin/osascript', '-'] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = p.communicate(script.encode('UTF-8'))
		if(debug):
			if(stderr!= b''): print("[Debug]\t AppleScript Error: %s" % stderr)
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
	if(debug):
		if(stderr!= b''): print("[Debug]\t AppleScript Error: %s" % stderr)
	return 0


# Get iTunes XML File
xmlPath = getiTunesXMLPath()

# Backup iTunes Library Files
if(backup): backupLibraryDB(xmlPath)

# Prepare Queues to store values
q_libTracks = queue.Queue()
q_dirTracks = queue.Queue()

# Declare Threads
t_libTracks = threading.Thread(target=getTracksFromiTunesXML, args=(xmlPath,))
t_dirTracks = threading.Thread(target=getTracksFromFolder, args=(musicFolder,), kwargs={'ext' : allowedExtensions})

done = False
t_loading = threading.Thread(target=loadingAnimation)
t_loading.start()

# Start both Threads
t_libTracks.start()
t_dirTracks.start()

# Wait until both are finished
t_libTracks.join()
t_dirTracks.join()

done = True
# Get Arrays from Thread-Queues
libTracks = q_libTracks.get()
dirTracks = q_dirTracks.get()

# Diff Arrays and only keep Tracks not already in Library
newTracks = filterTracksForImport(dirTracks, libTracks)

if(len(newTracks) != 0):
	# Import Tracks into iTunes with AppleScript
	if(addnew):
		done = False
		t_loading = threading.Thread(target=loadingAnimation)
		t_loading.start()
		importTracksToiTunes(newTracks)
		done = True
else: print("[Info]\t No New Tracks.")

# Remove Dead Tracks from iTunes
if(rmdead): removeDeadTracksFromiTunes()

# EOF