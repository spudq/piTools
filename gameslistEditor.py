#! /usr/bin/python

'''
TODO:
    fix bug with duplicate names
    close dialog
    clean up all footer messages, add some consistancy
    need better job keeping track of changes
    would be nice to see which things have changed
    save all XMLs option
    make messages more interactive (better feedback) (unified gui style)
    drop shadow on panel
'''

# - Imports -------------------------------------------------------------------

import os
import re
import errno
import shutil
import codecs
import urllib
import urllib2
import difflib
import tempfile
import argparse
import subprocess

from collections import OrderedDict
from operator import itemgetter

from xml.dom.minidom import parse, parseString, Document

import urwid

from pprint import pprint
from functools import partial

# - User Settings -------------------------------------------------------------

ROMS_DIR_WIN = '//retropie/roms'
ROMS_DIR_PI = '/home/pi/RetroPie/roms'
ROMS_DIR = ROMS_DIR_PI if os.path.exists(ROMS_DIR_PI) else ROMS_DIR_WIN

IMAGE_DIR = os.path.join(ROMS_DIR, '{system}', 'downloaded_images')
IMAGE_DIR_FULL = os.path.join(ROMS_DIR, '{system}', 'downloaded_images_large')
IMAGE_DIR_XML = os.path.join('.', 'downloaded_images')

SCRAPER_IMG_MAX_WIDTH = 400
SCRAPER_IMG_SUFFIX = '-image'
SCRAPER_USE_EXISTING_IMAGES = True

EXTERNAL_EDITOR = 'vim'

MISS_DATA_FIELDS = ['image', 'releasedate', 'developer',
                    'publisher', 'genre', 'desc']

ARCADE_DAT_FILE = {
        'mame-mame4all': None,
        'mame-advmame': None,
        'mame-libretro': r'\\retropie\roms\mame-libretro\MAME 078.dat',
        'arcade':None,
        }

# - Constants -----------------------------------------------------------------

MONTHS = ['jan', 'feb', 'mar', 'apr',
          'may', 'jun', 'jul', 'aug',
          'sep', 'oct', 'nov', 'dec']

# game data tags to extract from gamelist.xml files
GAMELIST_TAGS = ['path', 'name', 'kidgame', 'favorite', 'hidden', 'image', 'rating', 'releasedate',
                 'developer', 'publisher', 'genre', 'players',
                 'playcount', 'lastplayed', 'desc']

# from Emulation Station Wiki
ROM_EXTENSIONS = {
        '3do': ['.iso'],
        'amiga': ['.adf'],
        'amstradcpc': ['.dsk', '.cpc'],
        'apple2': ['.dsk'],
        'atari2600': ['.bin', '.a26', '.rom', '.zip', '.gz'],
        'atari800': ['.a52', '.bas', '.bin', '.xex', '.atr', '.xfd', '.dcm',
                     '.atr.gz', '.xfd.gz'],
        'atari5200': ['.a52', '.bas', '.bin', '.xex', '.atr', '.xfd', '.dcm',
                      '.atr.gz', '.xfd.gz'],
        'atari7800': ['.a78', '.bin'],
        'atarijaguar': ['.j64', '.jag'],
        'atarilynx': ['.lnx'],
        'atarist': ['.st', '.stx', '.img', '.rom', '.raw', '.ipf', '.ctr'],
        'coco': ['.cas', '.wav', '.bas', '.asc', '.dmk', '.jvc', '.os9',
                 '.dsk', '.vdk', '.rom', '.ccc', '.sna'],
        'coleco': ['.bin', '.col', '.rom', '.zip'],
        'c64': ['.crt', '.d64', '.g64', '.t64', '.tap', '.x64'],
        'daphne': [''],
        'dragon32': ['.cas', '.wav', '.bas', '.asc', '.dmk', '.jvc', '.os9',
                     '.dsk', '.vdk', '.rom', '.ccc', '.sna'],
        'dreamcast': ['.cdi', '.gdi'],
        'fba': ['.zip'],
        'neogeo': ['.zip'],
        'gc': ['.iso'],
        'gamegear': [''],
        'gb': ['.gb'],
        'gbc': ['.gbc'],
        'gba': ['.gba'],
        'intellivision': ['.int', '.bin'],
        'macintosh': ['.img', '.rom', '.dsk', '.sit'],
        'mame-mame4all': ['.zip'],
        'mame-advmame': ['.zip'],
        'mame-libretro': ['.zip'],
        'mastersystem': ['.sms'],
        'megadrive': ['.smd', '.bin', '.gen', '.md', '.sg', '.zip'],
        'genesis': ['.smd', '.bin', '.gen', '.md', '.sg', '.zip'],
        'msx': ['.rom', '.mx1', '.mx2', '.col', '.dsk'],
        'n64': ['.z64', '.n64', '.v64'],
        'nds': ['.nds', '.bin'],
        'nes': ['.zip', '.nes', '.smc', '.sfc', '.fig', '.swc', '.mgd'],
        'fds': ['.zip', '.nes', '.smc', '.sfc', '.fig', '.swc', '.mgd'],
        'neogeo': [''],
        'oric': ['.dsk', '.tap'],
        'pc': ['.com', '.sh', '.bat', '.exe'],
        'pcengine': ['.pce', '.cue', '.zip'],
        'psp': ['.cso', '.iso', '.pbp'],
        'psx': ['.cue', '.cbn', '.img', '.iso', '.m3u', '.mdf', '.pbp', '.toc',
                '.z', '.znx'],
        'ps2': ['.iso', '.img', '.bin', '.mdf', '.z', '.z2', '.bz2', '.dump',
                '.cso', '.ima', '.gz'],
        'samcoupe': ['.dsk', '.mgt', '.sbt', '.sad'],
        'saturn': ['.bin', '.iso', '.mdf'],
        'scummvm': ['.sh', '.svm'],
        'sega32x': ['.32x', '.smd', '.bin', '.md'],
        'segacd': ['.cue', '.iso'],
        'sg-1000': ['.sg', '.zip'],
        'snes': ['.zip', '.smc', '.sfc', '.fig', '.swc'],
        'ti99': ['.ctg'],
        'trs-80': ['.dsk'],
        'vectrex': ['.vec', '.gam', '.bin'],
        'videopac': ['.bin'],
        'wii': ['.iso'],
        'wonderswan': ['.ws'],
        'wonderswancolor': ['.wsc'],
        'zmachine': ['.dat', '.zip', '.z1', '.z2', '.z3', '.z4', '.z5', '.z6',
                     '.z7', '.z8'],
        'zxspectrum': ['sna', '.szx', '.z80', '.tap', '.tzx', '.gz', '.udi',
                       '.mgt', '.img', '.trd', '.scl', '.dsk']
        }

# from Emulation Station Source code
GAMESDB_SYSTEMS = {
        '3do': '3DO',
        'amiga': 'Amiga',
        'amstradcpc': 'Amstrad CPC',
        'arcade': 'Arcade',
        'atari2600': 'Atari 2600',
        'atari5200': 'Atari 5200',
        'atari7800': 'Atari 7800',
        'atarilynx': 'Atari Lynx',
        'atarijaguar': 'Atari Jaguar',
        'atarijaguarcd': 'Atari Jaguar CD',
        'atarixe': 'Atari XE',
        'colecovision': 'Colecovision',
        'c64': 'Commodore 64',
        'intellivision': 'Intellivision',
        'macintosh': 'Mac OS',
        'xbox': 'Microsoft Xbox',
        'xbox360': 'Microsoft Xbox 360',
        'neogeo': 'NeoGeo',
        'ngp': 'Neo Geo Pocket',
        'ngpc': 'Neo Geo Pocket Color',
        'n3ds': 'Nintendo 3DS',
        'n64': 'Nintendo 64',
        'nds': 'Nintendo DS',
        'nes': 'Nintendo Entertainment System (NES)',
        'mame-mame4all': 'Arcade',
        'mame-libretro': 'Arcade',
        'mame-advmame': 'Arcade',
        'gb': 'Nintendo Game Boy',
        'gba': 'Nintendo Game Boy Advance',
        'gbc': 'Nintendo Game Boy Color',
        'gc': 'Nintendo GameCube',
        'wii': 'Nintendo Wii',
        'wiiu': 'Nintendo Wii U',
        'pc': 'PC',
        'sega32x': 'Sega 32X',
        'segacd': 'Sega CD',
        'dreamcast': 'Sega Dreamcast',
        'gamegear': 'Sega Game Gear',
        'genesis': 'Sega Genesis',
        'mastersystem': 'Sega Master System',
        'megadrive': 'Sega Mega Drive',
        'saturn': 'Sega Saturn',
        'psx': 'Sony Playstation',
        'ps2': 'Sony Playstation 2',
        'ps3': 'Sony Playstation 3',
        'ps4': 'Sony Playstation 4',
        'psvita': 'Sony Playstation Vita',
        'psp': 'Sony PSP',
        'snes': 'Super Nintendo (SNES)',
        'pcengine': 'TurboGrafx 16',
        'wonderswan': 'WonderSwan',
        'wonderswancolor': 'WonderSwan Color',
        'zxspectrum': 'Sinclair ZX Spectrum',
        }

# from Wikipedia
GOODMERGE_COUNTRY_CODES = {
        '(A)': '(Australia)',
        '(As)': '(Asia)',
        '(B)': '(Brazil)',
        '(C)': '(Canada)',
        '(Ch)': '(China)',
        '(D)': '(Netherlands, Dutch)',
        '(E)': '(Europe)',
        '(F)': '(France)',
        '(G)': '(Germany)',
        '(Gr)': '(Greece)',
        '(HK)': '(Hong Kong)',
        '(I)': '(Italy)',
        '(J)': '(Japan)',
        '(JU)': '(Japan, USA)',
        '(K)': '(Korea)',
        '(Nl)': '(Netherlands)',
        '(No)': '(Norway)',
        '(R)': '(Russia)',
        '(S)': '(Spain)',
        '(Sw)': '(Sweden)',
        '(U)': '(USA)',
        '(UE)': '(USA, Europe)',
        '(UK)': '(United Kingdom)',
        '(W)': '(World)',
        '(Unl)': '(Unlicensed)',
        '(PD)': '(Public domain)',
        }

# hard coded rom name search fixes
# In case the rom name doesn't match games db title
# this doesn't seem very elegant might try something different
SCRAPER_NAME_SWAPS = {
        'megaman': 'Mega Man',
        }


# - Generic Functions ---------------------------------------------------------


def mkdir_p(path):
    '''make a directory
    from...
    http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python

    has good explanation on why this is better than
    if not os.path.exists(path):
        os.makedirs(path)
    '''
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def backupFile(path):

    sp = os.path.abspath(path)
    fp, fn = os.path.split(sp)
    backupdir = os.path.join(fp, '.backup')
    mkdir_p(backupdir)

    matcher = fn + '.backup.\d+'
    backups = [f for f in os.listdir(backupdir) if re.match(matcher, f)]
    versons = []
    for b in backups:
        try:
            versons.append(int(b.split('.').pop()))
        except:
            pass

    maxVersion = max(versons) if versons else 0
    version = maxVersion + 1

    tp = os.path.join(backupdir, fn + '.backup.' + str(version))
    shutil.copyfile(sp, tp)


def pathSplit(path):

    fp, fn = os.path.split(path)
    bn, ext = os.path.splitext(fn)
    return fp, bn, ext


# - Utils ---------------------------------------------------------------------


def readableDateToEsString(dateStr):

    # TODO: use datetime module instead

    if not dateStr:
        return None

    dateStr = re.findall(r'[\w]+', dateStr)

    if len(dateStr) == 1:
        # assume it's just the year
        if len(dateStr[0]) == 2:
            dateStr[0] = '19' + dateStr[0]
        if len(dateStr[0]) == 4:
            dateStr = ['01', '01'] + dateStr

    if not len(dateStr) == 3:
        return None

    mm, dd, yyyy = dateStr

    if not all([i.isdigit() for i in [dd, yyyy]]):
        return None

    if not mm.isdigit():
        mm = mm[:3].lower()
        if mm in MONTHS:
            mm = str(MONTHS.index(mm) + 1).zfill(2)
        else:
            return None

    mm = mm.zfill(2)
    dd = dd.zfill(2)
    rdate = yyyy+mm+dd + u'T000000'
    return rdate


def esStringToReadableDate(dateStr):

    # TODO: use datetime module instead

    if not dateStr:
        return u''

    dateStr = dateStr.split('T').pop(0)
    yyyy = dateStr[:4]
    mm = dateStr[4:6]
    dd = dateStr[6:8]
    return '/'.join([mm, dd, yyyy])


def getGamelist(system):

    return os.path.join(ROMS_DIR, system, u'gamelist.xml')


def getSystems():

    dirs = os.listdir(ROMS_DIR)
    for d in dirs:
        glpath = getGamelist(d)
        if os.path.exists(glpath):
            yield d


# - Scraper -------------------------------------------------------------------


def simplifySearchString(searchString):

    # everything before the matching parenthesis
    match = re.match('(.*)\(.*\).*', searchString)
    searchString = match.group(1) if match else searchString

    # swap any known name issues
    for before, after in SCRAPER_NAME_SWAPS.items():
        sr = re.compile(re.escape(before), re.IGNORECASE)
        searchString = sr.sub(after, searchString)

    return searchString


class Scraper(object):

    def __init__(self, system, searchQuery, timeout=None):

        # userAgent can be anything but python apparently
        # so I told gamesdb that this is my browser
        self.userAgent = ('Mozilla/5.0 (Windows NT 6.3; WOW64; rv:50.0) '
                          'Gecko/20100101 Firefox/50.0')
        self.system = system
        self.searchQuery = searchQuery
        self.timeout = timeout
        self.systemName = GAMESDB_SYSTEMS.get(system)
        self.dom = None
        self.domValid = False

    def __unicodeSafeify__(self, requestDict):

        for key, value in requestDict.items():
            if isinstance(value, basestring):
                requestDict[key] = value.encode('utf-8')
        return requestDict


    def __makeRequest__(self, url, request={}, retrys=3):

        request = self.__unicodeSafeify__(request)
        querry = urllib.urlencode(request)
        headers = {u'User-Agent': self.userAgent}
        request = urllib2.Request(url, querry, headers=headers)

        attempts = 0
        while attempts < retrys:
            try:
                fileObject = urllib2.urlopen(request, timeout=self.timeout)
                return fileObject
            except urllib2.URLError, e:
                attempts += 1

    def __xmlValue__(self, parent, tag):

        elements = parent.getElementsByTagName(tag)
        if len(elements) > 1:
            raise RuntimeError('more than one tag for ' + tag)
        if elements:
            node = elements[0].firstChild
            return node.data if node else None

    def getBigrams(self, string):
        '''
        Takes a string and returns a list of bigrams
        '''
        s = string.lower()
        return [s[i:i+2] for i in xrange(len(s) - 1)]

    def getSimilarity(self, str1, str2):
        '''
        Perform bigram comparison between two strings
        and return a percentage match in decimal form
        '''
        pairs1 = self.getBigrams(str1)
        pairs2 = self.getBigrams(str2)
        union = len(pairs1) + len(pairs2)
        hit_count = 0
        for x in pairs1:
            for y in pairs2:
                if x == y:
                    hit_count += 1
                    break
        return (2.0 * hit_count) / union

    def gameSearch(self, exactname=None):

        search = self.searchQuery
        url = u'http://thegamesdb.net/api/GetGame.php'

        if exactname:
            querry = {u'exactname': exactname,
                      u'platform': self.systemName}
        else:
            querry = {u'name': search,
                      u'platform': self.systemName}

        fileObject = self.__makeRequest__(url, querry)
        if not fileObject:
            return []

        self.dom = parse(fileObject)

        if len(self.dom.getElementsByTagName('GameTitle')):
            self.domValid = True
            return

        # If searching for the game with GetGame Failed
        # try using GetGamesList. It seems that given the same
        # query you can sometimes (rarely) gets better results using
        # GetGamesList rather than GetGame.
        # Unfortunately GetGamesList doesn't return
        # all of the data needed so the game will need
        # to be searched all over again once the game name is found
        url = u'http://thegamesdb.net/api/GetGamesList.php'
        querry = {u'name': search, u'platform': self.systemName}
        fileObject = self.__makeRequest__(url, querry)

        self.dom = parse(fileObject)
        self.domValid = False

    def getGames(self):

        if not self.dom:
            return []

        gameTitles = list()
        for node in self.dom.getElementsByTagName('GameTitle'):
            gameTitles.append(node.firstChild.data)

        # get sorting order lookup
        skeys = list()
        for title in gameTitles:
            ss = self.getSimilarity(self.searchQuery, title)
            skeys.append([ss, title])

        # sort
        sortedResults = list()
        for i, title in reversed(sorted(skeys, key=itemgetter(0))):
            sortedResults.append(title)

        return sortedResults

    def getGameInfo(self, exactName):

        if not self.domValid:
            self.gameSearch(exactName)

        # get the xml game node
        gameNode = None
        for node in self.dom.getElementsByTagName('GameTitle'):
            if node.firstChild.data == exactName:
                gameNode = node.parentNode
                break

        # boo
        if not gameNode:
            return {}

        # get genres (could be multiples)
        genres = list()
        elements = gameNode.getElementsByTagName('genre')
        for element in elements:
            genres.append(element.firstChild.data)

        return {
            'name':        self.__xmlValue__(gameNode, 'GameTitle'),
            'releasedate': self.__xmlValue__(gameNode, 'ReleaseDate'),
            'genre':       u', '.join(genres),
            'rating':      self.__xmlValue__(gameNode, 'Rating'),
            'developer':   self.__xmlValue__(gameNode, 'Developer'),
            'publisher':   self.__xmlValue__(gameNode, 'Publisher'),
            'players':     self.__xmlValue__(gameNode, 'Players'),
            'desc':        self.__xmlValue__(gameNode, 'Overview'),
            # new
            'kidgame':     self.__xmlValue__(gameNode, 'kidgame'),
            'favorite':    self.__xmlValue__(gameNode, 'favorite'),
            'hidden':      self.__xmlValue__(gameNode, 'hidden'),
            }

    def getBoxArtUrl(self, exactName):

        if not self.domValid:
            self.gameSearch(exactName)

        # url front
        baseImgUrl = self.__xmlValue__(self.dom, 'baseImgUrl')

        # get the matching game node
        gameNode = None
        for node in self.dom.getElementsByTagName('GameTitle'):
            if node.firstChild.data == exactName:
                gameNode = node.parentNode
                break
        if not gameNode:
            return

        # find the box art node under the game node
        boxArtNode = None
        for node in gameNode.getElementsByTagName('boxart'):
            if node.hasAttribute('side'):
                if node.getAttribute('side') == 'front':
                    boxArtNode = node
                    break

        # return the match
        if boxArtNode and baseImgUrl:
            url = baseImgUrl + boxArtNode.firstChild.data
            return url

    def getImageName(self, oldImageName, outputImgName):

        # get output directories
        imdDirFull = IMAGE_DIR_FULL.format(system=self.system)
        imgDirSmall = IMAGE_DIR.format(system=self.system)
        imgPathXML = IMAGE_DIR_XML.format(system=self.system)
        suffix = SCRAPER_IMG_SUFFIX

        # get image name
        imgExt = os.path.splitext(oldImageName)[1]
        imgName = os.sep + outputImgName + suffix + imgExt

        # output paths
        imgPathFull = imdDirFull + imgName
        imgPathSmall = imgDirSmall + imgName
        imgPathXML += imgName

        # make output directories
        mkdir_p(imdDirFull)
        mkdir_p(imgDirSmall)

        return imgPathFull, imgPathSmall, imgPathXML

    def resizeImage(self, source, target):

        s = 'x{}>'.format(SCRAPER_IMG_MAX_WIDTH)
        cmd = ['convert', '-resize', s, source, target]
        subprocess.check_call(cmd)

    def downloadArt(self, url, outputImgName):

        imgPathFull, imgPathSmall, imgPathXML = self.getImageName(
                url, outputImgName)

        # check if image alredy exists (use it)
        if SCRAPER_USE_EXISTING_IMAGES:
            # check to see if either a png or a jpg verison
            # of the thumb already exists any case
            xmlpath = IMAGE_DIR_XML.format(system=self.system)
            path, name, ext = pathSplit(imgPathSmall)
            for f in os.listdir(path):
                fn, fext = os.path.splitext(f)
                fn = fn + fext.lower()
                for e in ['.png', '.jpg']:
                    if name + e == fn:
                        np = os.path.join(path, f)
                        return np, os.path.join(xmlpath, f)

            # if os.path.exists(imgPathSmall):
            #    return imgPathSmall, imgPathXML

        # download image
        f = self.__makeRequest__(url)
        fd = f.read()
        with open(imgPathFull, 'w') as f:
            f.write(fd)

        # resize
        self.resizeImage(imgPathFull, imgPathSmall)

        return imgPathSmall, imgPathXML

    def ingestImage(self, origImgPath, outputImgName):

        imgPathFull, imgPathSmall, imgPathXML = self.getImageName(
                origImgPath, outputImgName)
        shutil.copyfile(origImgPath, imgPathFull)
        self.resizeImage(imgPathFull, imgPathSmall)
        return imgPathSmall, imgPathXML


# - XML Manager ---------------------------------------------------------------

def newGamesList(system):

    xmlpath = getGamelist(system)
    if os.path.exists(xmlpath):
        return
    dom = Document()
    root = dom.createElement('gameList')
    dom.appendChild(root)

    with open(xmlpath, 'w') as f:
        f = codecs.lookup('utf-8')[3](f)
        dom.writexml(f, indent=' ', addindent=' ', newl='\n', encoding='utf-8')

    return xmlpath


def elementTreeIndent(elem, level=0):
    '''
    '''
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            elementTreeIndent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


class ManageGameListXML(object):

    def __init__(self, system):

        self.changes = False
        self.xmlpath = getGamelist(system)
        self.system = system
        self.dom = parse(self.xmlpath)
        self.gameProperties = []
        self.__validate__()

    def __validate__(self):
        ''' make sure there are no missing names
        '''
        for node in self.dom.getElementsByTagName('game'):
            if not self.getData(node, 'name'):
                value = self.getData(node, 'path')
                self.setData(node, 'name', value)

    def __getNodeForGame__(self, game):

        for node in self.dom.getElementsByTagName('game'):
            if self.getData(node, 'name') == game:
                return node

    def findMissingGames(self):

        '''Just try and read this garbage :)'''

        exts = ROM_EXTENSIONS.get(self.system)
        path = os.path.join(ROMS_DIR, self.system)
        gamesOnDisc = [f for f in os.listdir(path) if any(
            e for e in exts if f.lower().endswith(e.lower()))]
        gamesInXML = [g.split('/').pop() for g in list(
            self.getGames(False)) if '/' in g]
        return list(set(gamesOnDisc) - set(gamesInXML))

    def setData(self, parentNode, name, value):

        if isinstance(value, str):
            value = unicode(value, errors='ignore')

        d = parentNode.getElementsByTagName(name)

        if not value:
            for item in d:
                parentNode.removeChild(item)
            return
        if d:
            if d[0].childNodes:
                d[0].firstChild.data = value
            else:
                textNode = self.dom.createTextNode(value)
                d[0].appendChild(textNode)
        else:
            textNode = self.dom.createTextNode(value)
            e = self.dom.createElement(name)
            e.appendChild(textNode)
            parentNode.appendChild(e)

        self.changes = True

    def getData(self, parentNode, name):

        d = parentNode.getElementsByTagName(name)
        data = d[0].firstChild.data if d and d[0].firstChild else None
        return data

    def getGames(self, asName=True):

        for node in self.dom.getElementsByTagName('game'):
            if asName:
                yield self.getData(node, 'name')
            else:
                yield self.getData(node, 'path')

    def getGamesWithMissingData(self, missingData=None):

        # TODO check image exists

        missingData = missingData or MISS_DATA_FIELDS
        for node in self.dom.getElementsByTagName('game'):
            name = self.getData(node, 'name')
            for tag in missingData:
                if not self.getData(node, tag):
                    yield name
                    break

    def getDataForGame(self, gameName):

        node = self.__getNodeForGame__(gameName)
        data = dict()

        if not node:
            return data

        for tag in GAMELIST_TAGS:
            data[tag] = self.getData(node, tag) or u''

        return data

    def setDataForGame(self, game, properties={}):

        node = self.__getNodeForGame__(game)
        for key, value in properties.items():
            self.setData(node, key, value)
        self.changes = True

    def toxml(self):

        ''' cleanup xml indents
        for the life of me I can't get simple dom to indent correctly
        so I've used element tree instead.
        '''
        import xml.etree.ElementTree as ET
        xmlstring = self.dom.toxml('utf-8')
        root = ET.fromstring(xmlstring, parser=ET.XMLParser(encoding='utf-8'))
        elementTreeIndent(root)
        string = ET.tostring(root, encoding='UTF-8')
        string = u'{}'.format(string.decode('utf-8'))
        return string

    def writeXML(self, path=None):

        if not path or path == self.xmlpath:
            backupFile(self.xmlpath)
            xmlOutPath = self.xmlpath
        else:
            xmlOutPath = path

        with open(xmlOutPath, 'w') as f:
            doc = self.toxml()
            f = codecs.lookup('utf-8')[3](f)
            f.write(doc)

        self.changes = False

    def addGame(self, fileName):

        gameRoot = self.dom.firstChild

        if not gameRoot.nodeName == 'gameList':
            raise RuntimeError('invalid gamelist.xml')

        gameNode = self.dom.createElement('game')
        gameRoot.appendChild(gameNode)
        gameName = os.path.splitext(fileName)[0]

        self.setData(gameNode, 'path', './' + fileName)
        self.setData(gameNode, 'name', gameName)

    def setGameTitlesFromDat(self):

        # get game names from .dat file
        datPath = ARCADE_DAT_FILE.get(self.system)
        if not datPath:
            return
        datData = dict()
        for gameTag in parse(datPath).getElementsByTagName('game'):
            if gameTag.hasAttribute('name'):
                name = gameTag.getAttribute('name')
                datData.setdefault(name, {})
                tag = gameTag.getElementsByTagName('description')
                if tag:
                    datData[name]['gameName'] = tag[0].firstChild.data
                tag = gameTag.getElementsByTagName('year')
                if tag:
                    datData[name]['year'] = tag[0].firstChild.data
                tag = gameTag.getElementsByTagName('manufacturer')
                if tag:
                    datData[name]['manufacturer'] = tag[0].firstChild.data

        for gamePath, oldName in zip(self.getGames(False), self.getGames(True)):
            p, baseName, ext = pathSplit(gamePath)
            gameData = self.getDataForGame(oldName)
            gameDatData = datData.get(baseName, {})
            dataToSet = dict()
            if not gameData.get('releasedate'):
                date = readableDateToEsString(gameDatData.get('year'))
                if date:
                    dataToSet['releasedate'] = date
            if not gameData.get('developer'):
                dev = gameDatData.get('manufacturer')
                if dev:
                    dataToSet['developer'] = dev
            newName = gameDatData.get('gameName', oldName)
            if newName:
                dataToSet['name'] = newName
            self.setDataForGame(oldName, dataToSet)


# - Temp Function -------------------------------------------------------------


def test():


    '''
    data = ['releasedate']

    system = 'mame-libretro'
    m = ManageGameListXML(system)

    # for game in m.getGamesWithMissingData(missingData=data):
        # print game

    m.setGameTitlesFromDat()

    return
    '''


    system = 'nes'

    # manager
    m = ManageGameListXML(system)
    j = m.getGames()
    game = j.next()

    print 'Game from xml:', game

    print 'Searching for scraping options'
    s = Scraper(system, simplifySearchString(game))
    s.gameSearch()
    print 'Done searching...'

    print s.getGames()
    return

    # get game result from scraper search
    games = s.getGames()
    game = games[0]

    pprint(s.getGameInfo(game))
    url = s.getBoxArtUrl(game)
    print url

    fp, xp = s.downloadArt(url, 'test')
    print fp


# - URWID Below ---------------------------------------------------------------


class fileButton(urwid.Button):
    def __init__(self, caption, callback=None):
        super(fileButton, self).__init__("")
        urwid.connect_signal(self, 'click', callback) if callback else None
        icon = urwid.SelectableIcon(caption, 0)
        self._w = urwid.AttrMap(icon, None, focus_map='activeButton')


class dirButton(urwid.Button):
    def __init__(self, caption, callback=None):
        super(dirButton, self).__init__("")
        urwid.connect_signal(self, 'click', callback) if callback else None
        icon = urwid.SelectableIcon(caption, 0)
        self._w = urwid.AttrMap(icon, 'bodyText', focus_map='activeButton')


class GameslistGUI(object):

    def __init__(self):

        self.currentSystem = None
        self.currentGame = None
        self.systems = list(getSystems())
        self.xmlManagers = dict()
        self.feildsEdited = False
        self.showOnlyMissingData = []

        self.panelOpen = False

        # widget instances
        self.systemMenu = self.menuWidget('Game Systems', self.systems,
                                          self.systemsWidgetCallback,
                                          hasFilter=False)
        self.gamesMenu = self.emptyBoxWidget('Games')
        self.gameEditWidget = self.mainEditWidget()
        self.blankWidget = self.emptyBoxWidget('Game Information')

        self.gameEditHolder = urwid.WidgetPlaceholder(self.blankWidget)

        # layout
        cwidget = urwid.Columns([self.systemMenu, self.gamesMenu])
        pwidget = urwid.Pile([
                    ('weight', 0.5, cwidget),
                    self.gameEditHolder,
                    (2, self.buttonsWidget()),
                    ])

        # footer
        self.footer = urwid.Text('')
        self.footer = urwid.AttrMap(self.footer, 'footerText')

        self.header = urwid.Text('')
        self.header = urwid.AttrMap(self.header, 'footerText')

        self.frameWidget = urwid.Frame(
                pwidget, header=None, footer=self.footer)
        self.frameWidget = self.main_shadow(self.frameWidget)

        self.body = urwid.WidgetPlaceholder(self.frameWidget)

        # do it
        self.loop = urwid.MainLoop(
                self.body,
                self.palette(),
                unhandled_input=self.keypress
                )

    def main_shadow(self, widget):

        bg = urwid.AttrWrap(urwid.SolidFill(u"\u2592"), 'deepBackground')
        shadow = urwid.AttrWrap(urwid.SolidFill(u" "), 'dropShadow')

        bg = urwid.Overlay(
            shadow, bg,
            ('fixed left', 3), ('fixed right', 1),
            ('fixed top', 2), ('fixed bottom', 1))
        widget = urwid.Overlay(
            widget, bg,
            ('fixed left', 2), ('fixed right', 3),
            ('fixed top', 1), ('fixed bottom', 2))

        return widget

    def start(self):

        self.loop.run()

    def paletteItm(self, name, fg='default', bg='default', mode=None,
                   mono=None, fghq=None, bghq=None):

        '''
        fg - foreground options:
            'white' 'black' 'brown' 'yellow'
            'dark red' 'dark green' 'dark blue'
            'dark cyan' 'dark magenta' 'dark gray'
            'light red' 'light green' 'light blue'
            'light cyan' 'light magenta' 'light gray'

        mode - foregroundSetting options:
            'bold' 'underline' 'blink' 'standout'

        bg - background options:
            'dark red' 'dark green' 'dark blue'
            'dark cyan' 'dark magenta' 'light gray'
            'black' 'brown'

        mono options:
            'bold' 'underline' 'blink' 'standout'

        fghq & bghq - foreground_high background_high example values:
            '#009' (0% red, 0% green, 60% red, like HTML colors)
            '#fcc' (100% red, 80% green, 80% blue)
            'g40'  (40% gray, decimal),
            'g#cc' (80% gray, hex),
            '#000', 'g0', ' g#00'   (black),
            '#fff', 'g100', rg#ff' (white)
            'h8'   (color number 8),
            'h255' (color number 255)
        '''

        fg = ','.join((fg, mode)) if mode else fg
        setting = (name, fg, bg, mono, fghq, bghq)
        return setting

    def palette(self):

        # color palette
        palette = [
            # for button selections
            self.paletteItm('activeButton', 'standout', mode='bold'),
            # for body text
            self.paletteItm('bodyText', 'yellow', 'dark blue', mode='bold'),
            # color for text being actively edited
            self.paletteItm('edittext', fg='white', bg='black'),
            # background color
            self.paletteItm('bodyColor', bg='dark blue'),
            # for footer text
            self.paletteItm('footerText', fg='dark blue', bg='light gray'),
            # for drop shadow
            self.paletteItm('dropShadow', bg='black'),
            # for farmost background
            self.paletteItm('deepBackground', fg='black', bg='light gray'),
            ]

        return palette

    def quit(self, button=None):

        raise urwid.ExitMainLoop()

    # - actions ---------------------------------------------------------------

    def getOrMakeManager(self, system):

        xmlManager = self.xmlManagers.get(system)

        if xmlManager:
            return xmlManager
        else:
            manager = ManageGameListXML(system)
            self.xmlManagers[system] = manager
            return manager

    def saveGameXml(self, *args):

        if not self.currentSystem:
            self.updateFooterText('no system xml active')
            return

        xmlManager = self.getOrMakeManager(self.currentSystem)
        self.updateGameXml()
        xmlpath = xmlManager.xmlpath
        xmlManager.writeXML()
        self.updateFooterText('wrote: ' + xmlpath)

    def updateGameXml(self):

        if not self.name.get_edit_text():
            p, n, e = pathSplit(self.path.get_edit_text())
            self.name.set_edit_text(n)

        if not self.feildsEdited:
            self.updateFooterText('no feilds edited')
            return
        if not self.currentSystem:
            self.updateFooterText('no system data to update')
            return
        if not self.currentGame:
            self.updateFooterText('no changes to save')
            return

        xmlManager = self.getOrMakeManager(self.currentSystem)

        # if self.name.get_edit_text() in list(xmlManager.getGames()):
        if self.currentGame not in list(xmlManager.getGames()):
            return

        # get field data
        data = dict()
        for tag in GAMELIST_TAGS:
            widget = getattr(self, tag)

            if isinstance(widget, urwid.Edit):
                data[tag] = widget.get_edit_text()

            if isinstance(widget, urwid.CheckBox):
                value = u'true' if widget.state else u'false'
                data[tag] = value 

        releasedate = data.get('releasedate')
        data['releasedate'] = readableDateToEsString(releasedate)

        xmlManager.setDataForGame(self.currentGame, data)

    def addMissingGames(self):

        if not self.currentSystem:
            self.updateFooterText('no system selected')
            return

        xmlManager = self.getOrMakeManager(self.currentSystem)
        games = xmlManager.findMissingGames()
        if not games:
            self.updateFooterText('no new games to add')
            return

        for game in games:
            xmlManager.addGame(game)

        self.refreshGames()
        xmlpath = xmlManager.xmlpath
        text = 'Updated: {} with {} games'.format(xmlpath, len(games))
        self.updateFooterText(text)

    def refreshGames(self):

        if self.currentSystem:
            self.systemsWidgetCallback(None, self.currentSystem)

    # - Widget helpers --------------------------------------------------------

    def updateFooterText(self, text):

        text = str(text) if not isinstance(text, basestring) else text
        text = urwid.Text(' ' + text)
        text = urwid.AttrMap(text, 'footerText')
        self.footer.original_widget = text

    def menuButtonList(self, choices, callback=None, buttonClass=urwid.Button):

        body = []
        for choice in choices:
            button = buttonClass(choice)
            if callback:
                urwid.connect_signal(button, 'click', callback, choice)
            button = urwid.AttrMap(button, None, focus_map='activeButton')
            body.append(button)
        return body

    def field(self, var, label=None, defaultText=u'', multiline=False,
              callback=None, button=None, buttonCallback=None):

        label = label or var
        label = label + u': '
        labelWidget = urwid.Text((u'bodyColor', label))
        editWidget = urwid.Edit(u'', defaultText, multiline=multiline)
        urwid.connect_signal(editWidget, 'change', callback) if callback else 0
        map = urwid.AttrMap(editWidget, u'bodyText', u'edittext')
        setattr(self, var, editWidget)

        if button:
            l = len(button) + 3
            buttonText = u'<{}>'.format(button)
            button = self.minimalButton(buttonText, callback=buttonCallback)
            return urwid.Columns([(u'pack', labelWidget), (l, button), map])
        else:
            return urwid.Columns([(u'pack', labelWidget), map])

    def checkbox(self, var, label=None, callback=None):

        ''' ccc
        '''

        label = label or var
        cb = urwid.CheckBox(label)

        if callback:
            urwid.connect_signal(cb, 'change', callback)

        setattr(self, var, cb)

        return cb

    def minimalButton(self, label, callback=None):

        button = fileButton(label)
        if callback:
            urwid.connect_signal(button, 'click', callback)
        return urwid.Padding(button, width=len(label)+1)

    def lineBoxWrap(self, widget, title, padding=2, attrMap='bodyColor'):

        widget = urwid.Padding(widget, left=padding, right=padding)
        widget = urwid.LineBox(widget, title)
        widget = urwid.AttrMap(widget, 'bodyColor')
        return widget

    # - Widgets ---------------------------------------------------------------

    def menuWidget(self, title, choices=[], callback=None, hasFilter=True):

        body = self.menuButtonList(choices, callback)
        lw = urwid.SimpleFocusListWalker(body)
        box = urwid.ListBox(lw)

        menu = urwid.WidgetPlaceholder(box)

        if hasFilter:
            editWidget = urwid.Edit(u'\u1401 ', u'', multiline=False)
            urwid.connect_signal(editWidget, 'change',
                                 self.filterMenu, user_args=[menu, body])
            widget = urwid.Pile([('pack', editWidget), menu])
        else:
            widget = menu

        return self.lineBoxWrap(widget, title)

    def filterMenu(self, menu, buttons, widget, filterText):

        body = list()
        for b in buttons:
            if filterText.lower() in b.original_widget.get_label().lower():
                body.append(b)

        lw = urwid.SimpleFocusListWalker(body)
        menu.original_widget = urwid.ListBox(lw)

    def buttonsWidget(self):

        body = [
            self.minimalButton(
                'F1:Help', partial(self.bottomButtonsCallback, 'f1')),
            self.minimalButton(
                'F2:+Sys', partial(self.bottomButtonsCallback, 'f2')),
            self.minimalButton(
                'F3:+Game', partial(self.bottomButtonsCallback, 'f3')),
            self.minimalButton(
                'F4:Save', partial(self.bottomButtonsCallback, 'f4')),
            self.minimalButton(
                'F5:SFull', partial(self.bottomButtonsCallback, 'f5')),
            self.minimalButton(
                'F6:SMiss', partial(self.bottomButtonsCallback, 'f6')),
            self.minimalButton(
                'F7:Edit', partial(self.bottomButtonsCallback, 'f7')),
            self.minimalButton(
                'F8:Desc', partial(self.bottomButtonsCallback, 'f8')),
            self.minimalButton(
                'F10:Quit', partial(self.bottomButtonsCallback, 'f10')),
            ]

        gridFlow = urwid.GridFlow(body, 8, 2, 0, 'left')
        lw = urwid.SimpleFocusListWalker([gridFlow])
        box = urwid.ListBox(lw)
        widget = urwid.Padding(box, left=2, right=2)
        widget = urwid.AttrMap(widget, 'bodyColor')

        return widget

    def emptyBoxWidget(self, title='Content Goes Here', text=''):

        body = [urwid.Text(text)]
        lw = urwid.SimpleFocusListWalker(body)
        box = urwid.ListBox(lw)
        return self.lineBoxWrap(box, title)

    def mainEditWidget(self):

        blank = urwid.Divider()

        checkboxes = urwid.Columns([
                self.checkbox(u'kidgame', callback=self.editCallback),
                self.checkbox(u'favorite', callback=self.editCallback),
                self.checkbox(u'hidden', callback=self.editCallback),
                blank,
                ])

        body = [
            blank, self.field(u'path', callback=self.editCallback),
            blank, self.field(u'name', callback=self.nameEditCallback),
            blank, self.field(
                u'image', button='browse',
                buttonCallback=partial(self.bottomButtonsCallback, 'b'),
                callback=self.editCallback
                ),
            blank, checkboxes,  # << checkboxes
            blank, self.field(u'rating', callback=self.editCallback),
            blank, self.field(
                u'releasedate',
                u'releasedate(MM/DD/YYYY)',
                callback=self.editCallback),
            blank, self.field(u'developer', callback=self.editCallback),
            blank, self.field(u'publisher', callback=self.editCallback),
            blank, self.field(u'genre', callback=self.editCallback),
            blank, self.field(u'players', callback=self.editCallback),
            blank, self.field(u'playcount', callback=self.editCallback),
            blank, self.field(u'lastplayed', callback=self.editCallback),
            blank, self.field(
                u'desc',
                callback=self.editCallback,
                multiline=True),
            ]

        lw = urwid.SimpleFocusListWalker(body)
        box = urwid.ListBox(lw)

        return self.lineBoxWrap(box, u'Game Information')

    def addSystemWidget(self):

        files = os.listdir(ROMS_DIR)
        dirs = [f for f in files if os.path.isdir(os.path.join(ROMS_DIR, f))]
        widget = self.menuWidget(
                'Add System', choices=dirs,
                callback=self.addSystemWidgetCallback)
        return widget

    # - pop-up stuffs ---------------------------------------------------------

    def openPopupWindow(self, widget=None, size=[50, 50], minimum=[10, 5]):

        widget = widget or self.emptyBoxWidget()
        overlay = urwid.Overlay(
                    top_w=widget,
                    bottom_w=self.frameWidget,
                    align='center',
                    width=('relative', size[0]),
                    valign='middle',
                    height=('relative', size[1]),
                    min_width=minimum[0],
                    min_height=minimum[1],
                    left=-1,
                    right=0,
                    top=0,
                    bottom=0
                    )
        self.body.original_widget = overlay
        self.panelOpen = widget

    def closePopupWindow(self, *args):

        self.body.original_widget = self.frameWidget
        self.panelOpen = None

    def togglePopupWindow(self, widget=None, w=50, h=None):

        if not self.panelOpen:
            widget = self.openPopupWindow(widget=widget, size=[w, h or w])
        else:
            self.closePopupWindow()

    # - pop-ups ---------------------------------------------------------------

    def helpWindow(self):

        blank = urwid.Divider()

        description = (
            'This tool is for editing gamelist.xml files. It is primaraly '
            'intended for making small changes and doesn\'t replace the need '
            'for a proper scraper. This being said it does include a very '
            'simple scraper to pull down data and images for a single game at '
            'a time. \n'
            'The fkeys listed below will work at any time. The alternate '
            'hotkeys however, (for example pressing the "n" key), will only '
            'work when not hovering over an editable field.')

        body = [
            blank,
            urwid.Text(description),
            blank,
            urwid.AttrMap(urwid.Text('<F1>, <h>'), 'bodyText'),
            urwid.Text('Open help panel'),
            blank,
            urwid.AttrMap(urwid.Text('<F2>, <n>'), 'bodyText'),
            urwid.Text(('Add new system, eg. create new gamelist.xml file '
                       'under a chosen games folder')),
            blank,
            urwid.AttrMap(urwid.Text('<F3>, <i>'), 'bodyText'),
            urwid.Text('Add games from disc missing '
                       'in xml for current gamelist.xml'),
            blank,
            urwid.AttrMap(urwid.Text('<F4>, <alt+s>, <u>'), 'bodyText'),
            urwid.Text('Save/Update current gamelist.xml'),
            blank,
            urwid.AttrMap(urwid.Text('<F5>, <shift + S>'), 'bodyText'),
            urwid.Text(('Scrape Full: Overwrite all fields with data ' +
                        'found on gamesdb.net. Images will be downloaded ' +
                        'if not in expected directory')),
            blank,
            urwid.AttrMap(urwid.Text('<F6>, <s>'), 'bodyText'),
            urwid.Text('Scrape Missing: Scrape only empty fields.'),
            blank,
            urwid.AttrMap(urwid.Text('<F7>, <v>'), 'bodyText'),
            urwid.Text('Edit gamelist.xml in {}'.format(EXTERNAL_EDITOR)),
            blank,
            urwid.AttrMap(urwid.Text('<F8>'), 'bodyText'),
            urwid.Text('Edit the desc field in {}'.format(EXTERNAL_EDITOR)),
            blank,
            urwid.AttrMap(urwid.Text('<F10>, <q>'), 'bodyText'),
            urwid.Text('Exit This Program'),
            blank,
            urwid.AttrMap(urwid.Text('<b>'), 'bodyText'),
            urwid.Text('Browse for new image on disc'),
            blank,
            urwid.AttrMap(urwid.Text('<d>'), 'bodyText'),
            urwid.Text('Scrape Date: Scrape only game release date.'),
            blank,
            urwid.AttrMap(urwid.Text('<v>'), 'bodyText'),
            urwid.Text('View current gamelist.xml '
                       '(not an editor just a viewer)'),
            blank,
            urwid.AttrMap(urwid.Text('<alt+t>'), 'bodyText'),
            urwid.Text('Load Titles From .dat file (used for arcade systems)'),
            blank,
            urwid.AttrMap(urwid.Text('<esc>'), 'bodyText'),
            urwid.Text('Cancel Popup'),
            blank,
            urwid.AttrMap(urwid.Text('<alt+m>'), 'bodyText'),
            urwid.Text('Toggle missing only mode (games with empty data fields)'),
            ]

        lw = urwid.SimpleFocusListWalker(body)
        box = urwid.ListBox(lw)

        return self.lineBoxWrap(box, u'Help / Information')

    def viewXml(self):

        if self.currentSystem:
            gm = self.getOrMakeManager(self.currentSystem)
            path = gm.xmlpath
            with open(path, 'r') as f:
                doc = f.read()
            return self.emptyBoxWidget(path, doc)
        else:
            return self.emptyBoxWidget('No System Chosen', '')

    def saveAndEditXmlExternal(self, *args):

        if not self.currentSystem:
            self.updateFooterText('No system chosen')
            return

        popup = self.saveWindow('Save changes and edit in external editor?',
                                self.editXmlExternal)
        self.togglePopupWindow(popup, 90, 15)

    def editXmlExternal(self, *args):

        gm = self.getOrMakeManager(self.currentSystem)
        path = gm.xmlpath

        self.updateFooterText(u'editing...')
        self.loop.screen.stop()
        subprocess.call([EXTERNAL_EDITOR + ' ' + path], shell=True)
        self.loop.screen.start()

        manager = ManageGameListXML(self.currentSystem)
        self.xmlManagers[self.currentSystem] = manager

        self.updateFooterText(u'done...')

    def editDescriptionExternal(self, *args):

        self.updateFooterText('ran')
        if self.currentSystem and self.currentGame:

            desc = self.desc.get_edit_text()
            with tempfile.NamedTemporaryFile(delete=False) as f:
                path = f.name
                f = codecs.lookup('utf-8')[3](f)
                f.write(desc)
            self.updateFooterText(u'editing desc...')
            self.loop.screen.stop()
            subprocess.call([EXTERNAL_EDITOR + ' ' + path], shell=True)
            self.loop.screen.start()
            with open(path, 'r') as f:
                desc = f.read().decode('utf8')
            self.desc.set_edit_text(desc)
            os.remove(path)
            self.updateFooterText('imported desc from ' + EXTERNAL_EDITOR)
        else:

            self.updateFooterText('game not chosen')

    def scraperChoices(self):

        ''' search for game matches
        '''

        if self.currentSystem and self.currentGame:

            title = self.currentGame
            title = simplifySearchString(title)

            self.scrapeInstance = Scraper(self.currentSystem, title)
            self.scrapeInstance.gameSearch()
            results = self.scrapeInstance.getGames()

            menu = self.menuWidget(
                    title,
                    choices=results,
                    callback=self.scraperChoiceCallback)

            return menu

        else:

            title = 'Nothing Selected to Scrape'
            return self.emptyBoxWidget(title, '')

    def scraperChoiceCallback(self, button, choice):

        self.closePopupWindow()

        pathText = self.path.get_edit_text()
        nameText = self.name.get_edit_text()
        pathName = pathSplit(pathText)[1]
        defaultName = pathName == nameText

        # attempt to get country code from rom name (on disc)
        rom = self.path.get_edit_text()
        founds = re.findall(r'\(.*?\)', rom)

        ccs = list()
        for found in founds:
            ccs.append(GOODMERGE_COUNTRY_CODES.get(found, found))
        cc = u' '.join(ccs)
        cc = u' ' + cc if cc else u''

        # cc = GOODMERGE_COUNTRY_CODES.get(founds[0], u'') if founds else u''
        # cc = u' ' + cc if cc else u''

        data = self.scrapeInstance.getGameInfo(choice)
        data['name'] += cc
        data['image'] = self.scrapeInstance.getBoxArtUrl(choice)

        strings = list()

        properties = ['name', 'image', 'rating', 'releasedate', 'developer',
                      'publisher', 'genre', 'players', 'desc']

        results = OrderedDict()

        if self.scraperMode == 'date only':

            date = data.get('releasedate', u'')
            oldDate = self.releasedate.get_edit_text()
            strings = [oldDate + ' --> ' + date]
            results['releasedate'] = date or None

        if self.scraperMode == 'full':

            for prop in properties:
                value = getattr(self, prop).get_edit_text()
                strings.append(u'{}: {}'.format(prop, value))

            strings.append(u'\nChange To -->\n')

            for prop in properties:
                value = data.get(prop, u'')
                strings.append(u'{}: {}'.format(prop, value))
                results[prop] = value

        if self.scraperMode == 'missing':

            # dates default to '01/01/0001' from EmulationStation when empty

            newProps = list()
            for prop in properties:
                value = getattr(self, prop).get_edit_text()
                if not value or value == '01/01/0001' or defaultName:
                    newProps.append(prop)
                    strings.append(u'{}: {}'.format(prop, value))

            strings.append(u'\nChange To -->\n')

            for prop in newProps:
                value = data.get(prop, u'')
                strings.append(u'{}: {}'.format(prop, value))
                results[prop] = value

        if isinstance(self.scraperMode, (list, tuple)):

            for prop in self.scraperMode:
                value = getattr(self, prop).get_edit_text()
                strings.append(u'{}: {}'.format(prop, value))

            strings.append(u'\nChange To -->\n')

            for prop in self.scraperMode:
                value = data.get(prop, u'')
                strings.append(u'{}: {}'.format(prop, value))
                results[prop] = value

        widgetTexts = [urwid.Text(t) for t in strings + ['\n']]
        pile = urwid.Pile(widgetTexts)
        btn_ok = urwid.Button('Ok', self.scrapeOkButtonAction, results)
        btn_ok = urwid.AttrMap(btn_ok, None, focus_map='activeButton')
        btn_cancel = urwid.Button('Cancel', self.closePopupWindow)
        btn_cancel = urwid.AttrMap(btn_cancel, None, focus_map='activeButton')
        lw = urwid.SimpleFocusListWalker([pile, btn_ok, btn_cancel])
        fillerl = urwid.ListBox(lw)
        widget = self.lineBoxWrap(fillerl, 'Review Changes')
        self.togglePopupWindow(widget, 70)

    def saveWindow(self, title=None, postCallback=None):

        if not self.currentSystem:
            return self.emptyBoxWidget('no system chosen', '')

        xmlManager = self.getOrMakeManager(self.currentSystem)

        if not self.feildsEdited:
            if not xmlManager.changes:
                self.updateFooterText('no changes to save')
                return self.emptyBoxWidget('no changes to save', '')

        path = xmlManager.xmlpath

        text = title or 'Save Changes to...'
        text = text + '\n'
        text += path + '?\n'

        tw = urwid.Text(text)

        btn_ok = urwid.Button('Ok', self.saveGameXmlCallback, postCallback)
        btn_ok = urwid.AttrMap(btn_ok, None, focus_map='activeButton')
        btn_cancel = urwid.Button('Cancel', self.closePopupWindow)
        btn_cancel = urwid.AttrMap(btn_cancel, None, focus_map='activeButton')

        lw = urwid.SimpleFocusListWalker([tw, btn_ok, btn_cancel])
        fillerl = urwid.ListBox(lw)
        widget = self.lineBoxWrap(fillerl, 'Save?')
        return widget

    def browseForThumbnail(self, directory):

        if not all([self.currentSystem, self.currentGame]):
            return self.emptyBoxWidget('no system chosen', '')

        root, dirs, files = next(os.walk(directory))

        matches = ['.png', '.jpg', '.jpeg']
        files = [f for f in files if os.path.splitext(f)[1].lower() in matches]
        msg = u'Choose Image for:\n{}\n'.format(self.currentGame)

        msgtext = urwid.Text(msg)
        text = urwid.Text(directory)
        blank = urwid.Divider()
        header = urwid.Pile([msgtext, text, blank])

        dirs = ['..'] + dirs
        bodyDirs = self.menuButtonList(
                dirs,
                callback=partial(self.browseDirCallback, root),
                buttonClass=dirButton)
        bodyFiles = self.menuButtonList(
                files,
                callback=partial(self.browseFileCallback, root),
                buttonClass=fileButton)
        body = bodyDirs + [blank] + bodyFiles

        lw = urwid.SimpleFocusListWalker(body)
        box = urwid.ListBox(lw)
        box.set_focus(len(body) - 1 - len(files))

        frameWidget = urwid.Frame(box, header=header, footer=None)
        widget = self.lineBoxWrap(frameWidget, 'Browse')

        return widget

    def filtersMenuPopup(self):

        boxes = ['image', 'rating', 'releasedate', 'developer',
                 'publisher', 'genre', 'players', 'desc']

        t = ('Choose which fields to filter. When checked the Games list will '
             'only show a game when one of these fields is missing data.')

        abutton = urwid.Button('Close', self.closePopupWindow)
        abutton = urwid.AttrMap(abutton, None, focus_map='activeButton')

        blank = urwid.Divider()

        body = [blank, urwid.Text(t), blank]
        for box in boxes:
            state = box in self.showOnlyMissingData
            cb = urwid.CheckBox(box, state, False, self.filterCheckStateChanged)
            body.append(cb)
        body += [blank, abutton]

        lw = urwid.SimpleFocusListWalker(body)
        box = urwid.ListBox(lw)
        widget = urwid.Padding(box, left=2, right=2)
        widget = self.lineBoxWrap(widget, 'Filter for missing data')
        return widget

    # - callbacks -------------------------------------------------------------

    def filterCheckStateChanged(self, widget, state, *args):

        lab = widget.get_label()
        if state:
            if not lab in self.showOnlyMissingData:
                self.showOnlyMissingData.append(lab)
        else:
            if lab in self.showOnlyMissingData:
                self.showOnlyMissingData.remove(lab)

        self.updateFooterText(str(self.showOnlyMissingData))
        self.refreshGames()

    def keypress(self, key):

        '''
        f1 help
        f2 open/rename/menu/setup
        f3 search/repeat/view
        f4 edit/filter
        f5 refresh browsers/start app/find,replace/copy/sort
        f6 toggles cursor location/move/collapse
        f7 mkdir/spell check/nice-
        f8 delete/nice+
        f9 pulldown/kill
        f10 menu/do/quit(when max key)
        f11 fullscreen
        f12 save as
        '''

        # show key names
        # self.updateFooterText(str(key))
        # return

        if key == 'f1':
            popup = self.helpWindow()
            self.togglePopupWindow(popup, 65, 80)

        if key == 'f2':
            popup = self.addSystemWidget()
            self.togglePopupWindow(popup)

        if key in ('f3', 'i', 'I'):
            self.addMissingGames()

        if key in ('f4', 'u', 'meta s', 'ctrl s'):
            popup = self.saveWindow()
            self.togglePopupWindow(popup, 90, 15)

        if key in ('f5', 'S'):
            self.scraperMode = 'full'
            popup = self.scraperChoices()
            self.togglePopupWindow(popup)

        if key in ('f6', 's'):
            self.scraperMode = 'missing'
            popup = self.scraperChoices()
            self.togglePopupWindow(popup)

        if key == 'f7':
            self.saveAndEditXmlExternal()

        if key == 'f8':
            self.editDescriptionExternal()

        if key in ('f10', 'q', 'Q'):
            self.quit()

        if key == 'v':
            popup = self.viewXml()
            self.togglePopupWindow(popup, 90)

        if key == 'b':
            popup = self.browseForThumbnail(ROMS_DIR)
            self.togglePopupWindow(popup)

        if key == 'd':
            self.scraperMode = 'date only'
            popup = self.scraperChoices()
            self.togglePopupWindow(popup)

        if key == 'D':
            self.scraperMode = ['desc']
            popup = self.scraperChoices()
            self.togglePopupWindow(popup)

        if key == 'c':
            self.checkForChanges()

        if key == 'esc':
            if self.panelOpen:
                self.closePopupWindow()

        if key in ('meta t', 'ctrl t'):
            self.addSystemNamesFromDat()

        text = urwid.Text(str(key))
        text = urwid.AttrMap(text, 'footerText')
        self.header.original_widget = text

        if key in ('meta m', 'ctrl m'):

            popup = self.filtersMenuPopup()
            self.togglePopupWindow(popup)
            return
            switch = False if self.showOnlyMissingData else True
            self.showOnlyMissingData = switch
            if self.showOnlyMissingData:
                msg = 'Showing only games with missing fields'
                self.updateFooterText(msg)
            else:
                msg = 'Showing all games'
                self.updateFooterText(msg)
            self.refreshGames()

        if key in ('meta f', 'ctrl f'):

            popup = self.filtersMenuPopup()
            self.togglePopupWindow(popup)

    def checkForChanges(self):

        output = dict()
        for system, manager in self.xmlManagers.items():
            output.setdefault(system, []).append(manager.changes)
        self.updateFooterText(str(output))

    def bottomButtonsCallback(self, *args):
        self.keypress(args[0])

    def browseDirCallback(self, folder, button, subfolder):

        self.closePopupWindow()
        if subfolder == '..':
            newdir = os.path.abspath(os.path.join(folder, os.pardir))
        else:
            newdir = os.path.join(folder, subfolder)
        popup = self.browseForThumbnail(newdir)
        self.togglePopupWindow(popup)

    def browseFileCallback(self, folder, button, resultFile):

        system = self.currentSystem
        game = self.currentGame
        p, name, e = pathSplit(self.path.get_edit_text())

        img = os.path.join(folder, resultFile)

        s = Scraper(system, game)
        imgPathSmall, imgPathXML = s.ingestImage(img, name)

        self.image.set_edit_text(imgPathXML)

        self.closePopupWindow()
        self.updateFooterText(imgPathSmall)

    def scrapeOkButtonAction(self, button, data):

        footerText = u'updated: '

        if data.get('image'):

            p, name, e = pathSplit(self.path.get_edit_text())
            url = data.get('image')
            img, imgXML = self.scrapeInstance.downloadArt(url, name)
            data['image'] = imgXML

        for prop, value in data.items():
            if value:
                widget = getattr(self, prop)
                widget.set_edit_text(value)
                footerText += prop + u' '

        self.updateGameXml()
        self.updateFooterText(footerText)
        self.closePopupWindow()

    def saveGameXmlCallback(self, button, callback=None):

        callback() if callback else None
        self.updateGameXml()
        self.saveGameXml()
        self.closePopupWindow()

    def systemsWidgetCallback(self, button, choice):

        self.updateGameXml()

        self.currentSystem = choice
        self.currentGame = None

        mngr = self.getOrMakeManager(choice)
        mode = self.showOnlyMissingData
        games = mngr.getGamesWithMissingData(mode) if mode else mngr.getGames()

        self.gameEditHolder.original_widget = self.blankWidget
        games = sorted(games, key=lambda s: s.lower())
        widget = self.menuWidget('Games ({})'.format(self.currentSystem),
                                 games,
                                 self.gamesWidgetCallback)
        self.gamesMenu.original_widget = widget
        txt = '{}, {} games listed'.format(getGamelist(choice), len(games))
        self.updateFooterText(txt)

        edited = self.feildsEdited  # mute callback

        for tag in GAMELIST_TAGS:
            widget = getattr(self, tag)

            if isinstance(widget, urwid.Edit):
                widget.set_edit_text(u'')

            if isinstance(widget, urwid.CheckBox):
                widget.set_state(False)

        self.feildsEdited = edited

    def gamesWidgetCallback(self, button, choice):

        self.currentGameInfoButton = button

        self.updateGameXml()
        self.currentGame = choice
        self.updateFooterText(self.currentSystem + ', ' + choice)
        xmlManager = self.getOrMakeManager(self.currentSystem)
        self.gameEditHolder.original_widget = self.gameEditWidget
        data = xmlManager.getDataForGame(choice)
        if not data:  # get the current button text, try that
            choice = button.get_label()
            data = xmlManager.getDataForGame(choice)

        if not data:  # if still no data, refresh the whole widget
            self.refreshGames()
            self.updateFooterText('game list out of date')
            return

        edited = self.feildsEdited  # mute callback
        releasedate = data.get('releasedate')
        data['releasedate'] = esStringToReadableDate(releasedate)

        for tag in GAMELIST_TAGS:

            widget = getattr(self, tag)
            result = data.get(tag, u'')

            if isinstance(widget, urwid.Edit):
                widget.set_edit_text(result)

            if isinstance(widget, urwid.CheckBox):
                widget.set_state(True if result == 'true' else False)

        self.feildsEdited = edited

    def addSystemWidgetCallback(self, button, choice):

        xml = newGamesList(choice)
        if xml:
            self.systems = list(getSystems())
            self.systemMenu.original_widget = self.menuWidget(
                    'Game Systems',
                    self.systems,
                    self.systemsWidgetCallback,
                    hasFilter = False
                    )
            self.updateFooterText('created: ' + choice)
        else:
            self.updateFooterText('Did Nothing')

        self.closePopupWindow()

    def addSystemNamesFromDat(self, *args):

        datPath = ARCADE_DAT_FILE.get(self.currentSystem)
        if self.currentSystem and datPath:
            xmlManager = self.getOrMakeManager(self.currentSystem)
            xmlManager.setGameTitlesFromDat()
            self.systemsWidgetCallback('', self.currentSystem)
            self.updateFooterText('titles updated')
        else:
            txt = 'no .dat file for {}'.format(self.currentSystem)
            self.updateFooterText(txt)

    def editCallback(self, widget, string, *args):

        # self.updateFooterText(string)
        self.feildsEdited = True

    def nameEditCallback(self, widget, string, *args):

        self.feildsEdited = True
        if self.currentGame:
            self.currentGameInfoButton.set_label(string)


# - Alternate Colors ----------------------------------------------------------


class GreenTheme(GameslistGUI):
    def palette(self):
        # color palette
        itm = self.paletteItm
        palette = [
            # for button selections
            itm('activeButton', 'light green', bg='black', mode='standout'),
            # for body text
            itm('bodyText', 'dark green', 'black', mode='bold'),
            # color for text being actively edited
            itm('edittext', fg='light green', bg='black', mode='bold'),
            # background color
            itm('bodyColor', fg='dark green', bg='black'),
            # for footer text
            itm('footerText', 'dark green', bg='black', mode='standout'),
            # for drop shadow
            itm('dropShadow', bg='black'),
            # for farmost background
            itm('deepBackground', fg='dark green', bg='black'),
            ]
        return palette


class GrayTheme(GameslistGUI):
    def palette(self):
        # color palette
        itm = self.paletteItm
        palette = [
            # for button selections
            itm('activeButton', 'dark cyan', bg='black', mode='standout'),
            # for body text
            itm('bodyText', 'black', bg='light gray', mode='bold'),
            # color for text being actively edited
            itm('edittext', fg='black', bg='light gray', mode='bold'),
            # background color
            itm('bodyColor', fg='black', bg='light gray'),
            # for footer text
            itm('footerText', mode='standout'),
            # for drop shadow
            itm('dropShadow', bg='black'),
            # for farmost background
            itm('deepBackground', fg='black', bg='light blue'),
            ]
        return palette


class DarkTheme(GameslistGUI):
    def palette(self):
        # color palette
        itm = self.paletteItm
        palette = [
            # for button selections
            itm('activeButton', 'light blue', bg='black', mode='standout'),
            # for body text
            itm('bodyText', 'light green', bg='black', mode='bold'),
            # color for text being actively edited
            itm('edittext', fg='white', bg='black', mode='bold'),
            # background color
            itm('bodyColor', fg='light cyan', bg='black'),
            # for footer text
            itm('footerText', fg='light blue', bg='black', mode='standout'),
            # for drop shadow
            itm('dropShadow', bg='black'),
            # for farmost background
            itm('deepBackground', fg='black', bg='dark gray', mode='bold'),
            ]

        return palette


class BWTheme(GameslistGUI):
    def palette(self):
        # color palette
        itm = self.paletteItm
        palette = [
            # for button selections
            itm('activeButton', 'white', bg='black', mode='standout'),
            # for body text
            itm('bodyText', 'white', bg='black', mode='bold'),
            # color for text being actively edited
            itm('edittext', fg='white', bg='black', mode='bold'),
            # background color
            itm('bodyColor', fg='white', bg='black'),
            # for footer text
            itm('footerText', fg='white', bg='black', mode='standout'),
            # for drop shadow
            itm('dropShadow', bg='black'),
            # for farmost background
            itm('deepBackground', fg='white', bg='black'),
            ]
        return palette


# - Launcher ------------------------------------------------------------------


def parseArgs():

    desc = 'Tool to edit gamelist.xml files'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('--colorsceme', '-c',
                        help='green, gray, or dark')
    parser.add_argument('--test', '-t', action='store_true',
                        help='run the debug crap')

    args = parser.parse_args()
    return args


if __name__ == '__main__':

    args = parseArgs()
    theme = args.colorsceme

    if args.test:
        test()
    elif theme == 'green':
        GreenTheme().start()
    elif theme == 'gray':
        GrayTheme().start()
    elif theme == 'dark':
        DarkTheme().start()
    elif theme == 'bw':
        BWTheme().start()
    else:
        GameslistGUI().start()

#
