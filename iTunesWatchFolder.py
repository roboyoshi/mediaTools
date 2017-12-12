#/usr/bin/env python3

"""
	iTunesWatchFolder Script
	- Synchronize iTunes Library <--> Folder
	Written by u/RoboYoshi
"""

# Mandatory Imports
import sys, time, itertools, threading, queue
import os, subprocess, re, plistlib, datetime, shutil, encodings
from urllib.parse import quote, unquote, urlparse
from pprint import pprint as pp

# SETTINGS
DEBUG = True
WITH_PYOBJC = False

# TASKS
CREATE_BACKUP = True
ADD_NEW_TRACKS = True
REMOVE_DEAD_TRACKS = False

"""
̀ 	COMBINING GRAVE ACCENT (U+0300) 	cc80
́ 	COMBINING ACUTE ACCENT (U+0301) 	cc81
̂ 	COMBINING CIRCUMFLEX ACCENT (U+0302) 	cc82
̃ 	COMBINING TILDE (U+0303) 	cc83
̄ 	COMBINING MACRON (U+0304) 	cc84
̅ 	COMBINING OVERLINE (U+0305) 	cc85
̆ 	COMBINING BREVE (U+0306) 	cc86
̇ 	COMBINING DOT ABOVE (U+0307) 	cc87
̈ 	COMBINING DIAERESIS (U+0308) 	cc88
̉ 	COMBINING HOOK ABOVE (U+0309) 	cc89
̊ 	COMBINING RING ABOVE (U+030A) 	cc8a
̋ 	COMBINING DOUBLE ACUTE ACCENT (U+030B) 	cc8b
̌ 	COMBINING CARON (U+030C) 	cc8c
̍ 	COMBINING VERTICAL LINE ABOVE (U+030D) 	cc8d
̎ 	COMBINING DOUBLE VERTICAL LINE ABOVE (U+030E) 	cc8e
̏ 	COMBINING DOUBLE GRAVE ACCENT (U+030F) 	cc8f
̐ 	COMBINING CANDRABINDU (U+0310) 	cc90
̑ 	COMBINING INVERTED BREVE (U+0311) 	cc91
̒ 	COMBINING TURNED COMMA ABOVE (U+0312) 	cc92
̓ 	COMBINING COMMA ABOVE (U+0313) 	cc93
̔ 	COMBINING REVERSED COMMA ABOVE (U+0314) 	cc94
̕ 	COMBINING COMMA ABOVE RIGHT (U+0315) 	cc95
̖ 	COMBINING GRAVE ACCENT BELOW (U+0316) 	cc96
̗ 	COMBINING ACUTE ACCENT BELOW (U+0317) 	cc97
̘ 	COMBINING LEFT TACK BELOW (U+0318) 	cc98
̙ 	COMBINING RIGHT TACK BELOW (U+0319) 	cc99
̚ 	COMBINING LEFT ANGLE ABOVE (U+031A) 	cc9a
̛ 	COMBINING HORN (U+031B) 	cc9b
̜ 	COMBINING LEFT HALF RING BELOW (U+031C) 	cc9c
̝ 	COMBINING UP TACK BELOW (U+031D) 	cc9d
̞ 	COMBINING DOWN TACK BELOW (U+031E) 	cc9e
̟ 	COMBINING PLUS SIGN BELOW (U+031F) 	cc9f
̠ 	COMBINING MINUS SIGN BELOW (U+0320) 	cca0
̡ 	COMBINING PALATALIZED HOOK BELOW (U+0321) 	cca1
̢ 	COMBINING RETROFLEX HOOK BELOW (U+0322) 	cca2
̣ 	COMBINING DOT BELOW (U+0323) 	cca3
̤ 	COMBINING DIAERESIS BELOW (U+0324) 	cca4
̥ 	COMBINING RING BELOW (U+0325) 	cca5
̦ 	COMBINING COMMA BELOW (U+0326) 	cca6
̧ 	COMBINING CEDILLA (U+0327) 	cca7
̨ 	COMBINING OGONEK (U+0328) 	cca8
̩ 	COMBINING VERTICAL LINE BELOW (U+0329) 	cca9
̪ 	COMBINING BRIDGE BELOW (U+032A) 	ccaa
̫ 	COMBINING INVERTED DOUBLE ARCH BELOW (U+032B) 	ccab
̬ 	COMBINING CARON BELOW (U+032C) 	ccac
̭ 	COMBINING CIRCUMFLEX ACCENT BELOW (U+032D) 	ccad
̮ 	COMBINING BREVE BELOW (U+032E) 	ccae
̯ 	COMBINING INVERTED BREVE BELOW (U+032F) 	ccaf
̰ 	COMBINING TILDE BELOW (U+0330) 	ccb0
"""

# for some wierd reason itunes is using
# the 'added' diacritics form 
# instead of the ogirinal unicode character
ITUNES_FIX_DICT = {
	'A&CC%80' : '%C3%81', # À
	'O%CC%80' : '%C3%92', # Ò
	'o%CC%80' : '%C3%B2', # ò
	'e%CC%80' : '%C3%88', # È
	'e%CC%80' : '%C3%A8', # è
	'A%CC%81' : '%C3%81', # Á
	'a%CC%81' : '%C3%A1', # á
	'u%CC%81' :	'%C3%BA', # ú
	'e%CC%81' : '%C3%A9', # é
	'i%CC%81' : '%C3%AD', # í
	'c%CC%81' : '%C4%87', # ć
	'n%CC%81' : '%C5%84', # ń
	'o%CC%81' : '%C3%B3', # ó
	's%CC%81' : '%C5%9B', # ś
	'n%CC%83' : '%C3%B1', # ñ
	'a%CC%83' : '%C3%A3', # ã
	'z%CC%87' : '%C5%BC', # ż
	'A%CC%88' : '%C3%84', # Ä
	'a%CC%88' : '%C3%A4', # ä
	'E%CC%88' : '%C3%8B', # Ë
	'e%CC%88' : '%C3%AB', # ë
	'O%CC%88' : '%C3%96', # Ö
	'o%CC%88' : '%C3%B6', # ö
	'U%CC%88' : '%C3%9C', # Ü
	'u%CC%88' : '%C3%BC', # ü
	'a%CC%8A' : '%C3%A5', # å
	'A%CC%8A' : '%C3%85', # Å
	'e%CC%8C' : '%C4%9B', # ě
	'c%CC%8C' : '%C4%8D', # č
	'S%CC%8C' : '%C5%A0', # Š
	's%CC%8C' : '%C5%A1', # š
	'n%CC%8C' : '%C5%88', # ň
	's%CC%A7' : '%C5%9F', # ş
	'C%CC%A7' : '%C3%87', # Ç
	'c%CC%A7' : '%C3%A7', # ç
}

# Optional Import when using PyObjC
if(WITH_PYOBJC):
	from Foundation import NSURL
	from ScriptingBridge import SBApplication

# Optional Debug Imports
if(DEBUG):
	import chardet

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

# adapted from https://stackoverflow.com/a/2400577/3286178
def replaceWithDict(s, d):
	pattern = re.compile('|'.join(re.escape(key) for key in d.keys()))
	return pattern.sub(lambda x: d[x.group()], s)

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
			# trackPath = urlparse(trackPath).path
			if(noNSURL):
				# strip 'file://' and replace all wrong utf8-chars
				location = replaceWithDict(trackPath[7:], ITUNES_FIX_DICT)
				location = quote(unquote(location))
			else:
				location = NSURL.fileURLWithPath_(trackPath)
			if(DEBUG):
				print("[Debug]\t Location (lib) = %s" % location)
				print("[Debug]\t Type = ", type(location), "Hash = ", hash(location))
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
				trackPath = os.path.join(root, name)
				if(DEBUG): print("[Debug]\t Track Path in Folder = %s" % trackPath)
				if(noNSURL):
					location = quote(trackPath)
				else:
					location = NSURL.fileURLWithPath_(trackPath)
				if(DEBUG):
					print("[Debug]\t Location (dir) = %s" % location)
					print("[Debug]\t Type = ", type(location), "Hash = ", hash(location))
				dirTracks.append(location)
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
	:return list: (sorted) list with all missing tracks
	"""
	newTracks = list(set(dirTracks) - set(libTracks))
	print("--------- New Tracks ----------")
	for location in newTracks:
		print("[Debug]\t Location (new) = %s" % location)
		print("[Debug]\t Type = ", type(location), "Hash = ", hash(location))
	print("[Info]\t New Tracks to Import = %i" % len(newTracks))
	if not WITH_PYOBJC:
		# NSURLs appear to be non-comparable
		newTracks = sorted(newTracks)
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
		if(DEBUG): print("[Debug]\t NewTrackPath = %s" % track)
		batch.append(track)
		count += 1
		if(batchSize % count == 0):
			iTunes.add_to_(batch, None)
			batch.clear()
	return 0

def importTracksToiTunesViaAS(newTracks):
	print("[Info]\t Adding new Tracks to iTunes.")
	"""
	Import a Bunch of Tracks into iTunes
	:param newTracks: Python List with all new Tracks
	:return int: 0
	"""
	for track in newTracks:
		if not WITH_PYOBJC:
			track = unquote(track)
		if(DEBUG): print("[Debug]\t Importing Track => %s" % track)
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
		if(DEBUG):
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
if(WITH_PYOBJC):
	libTracksThread = threading.Thread(target=getTracksFromiTunesXML, args=(xmlPath,))
	dirTracksThread = threading.Thread(target=getTracksFromFolder, args=(musicFolder,), kwargs={'ext' : allowedExtensions})
else:
	libTracksThread = threading.Thread(target=getTracksFromiTunesXML, args=(xmlPath,), kwargs={'noNSURL' : True})
	dirTracksThread = threading.Thread(target=getTracksFromFolder, args=(musicFolder,), kwargs={'ext' : allowedExtensions, 'noNSURL' : True})

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
		if (WITH_PYOBJC):
			# Import via PyObjC Bridge
			importTracksToiTunesViaSB(newTracks)
		else:
			# Import via AppleScript
			importTracksToiTunesViaAS(newTracks)
		done = True
else: print("[Info]\t No New Tracks.")

# Remove Dead Tracks from iTunes
if(REMOVE_DEAD_TRACKS): removeDeadTracksFromiTunes()

# EOF