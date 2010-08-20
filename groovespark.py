
import os
import functools
import hashlib
import json
import random
import uuid
import urllib

from twisted.python import runtime, log
from twisted.internet import defer
from twisted.web import error, client

# Always use https, since getting a token requires it.
API_URL = "https://cowbell.grooveshark.com/"
ART_BASE_URL = "http://beta.grooveshark.com/static/amazonart/m"

class JSONFault(Exception): pass

### TWISTED MONKEY PATCHING
### SHIELD YOUR EYES, #twisted!

# HTTPClient, when using afterFoundGet on a 302
# handles 301 twice, leaving to two requests
# to the server
def stupid_bug_handleStatus_302(self):
    if self.afterFoundGet:
        self.handleStatus_303()
    else:
        self.handleStatus_301()
client.HTTPPageGetter.handleStatus203 = stupid_bug_handleStatus_302

# I have to do this because downloadPage/HTTPDownloader
# doesn't support afterFoundGet, which is required
# to download from the Akamai servers
def stupid_bug_HTTPDownloader(factory=client.HTTPDownloader):
    def inner(*a, **kw):
        I = factory(*a, **kw)
        I.afterFoundGet = True
        return I
    return inner
client.HTTPDownloader = stupid_bug_HTTPDownloader()

class GroovesharkAPI(object):
    def __init__(self, url=API_URL):
        self.url = url

        # ok, I'm just copying the stuff from the requests.
        self.headers = dict(client="gslite", clientRevision="20100412.83",
                            privacy=1, uuid=str(uuid.uuid4()).upper())

        # Content-Type headers for usual stuff.
        self.jsonContent = {"Content-Type":"application/json"}
        self.formContent = {"Content-Type":"application/x-www-form-urlencoded"}

        # shhh...
        self.httpHeaders = {"User-Agent":"Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2.8) Gecko/20100721  Firefox/3.6.8"}

        # Token expiration date.
        self.tokenExpire = None
        self.country = None

    @defer.inlineCallbacks
    def initialize(self):
        yield self.fetchSessionID()
        yield self.fetchToken()
        # I'm not sure if you *need* a country,
        # but the official client uses it.
        yield self.fetchCountry()

    def getURL(self, script, *args, **kwargs):
        return "%s%s?%s%s" % (self.url, script,
            '&'.join(map(urllib.quote, args)), urllib.urlencode(kwargs))

    @defer.inlineCallbacks
    def fetchSessionID(self):
        cookies = dict()
        result = yield client.getPage(self.url, method="POST", cookies=cookies)
        self.headers['session'] = cookies['PHPSESSID']
        self.httpHeaders['Cookie'] = "PHPSESSID=%s" % (cookies['PHPSESSID'],)

    @defer.inlineCallbacks
    def fetchToken(self):
        self.rawToken = yield self.send('getCommunicationToken',
            dict(secretKey=hashlib.md5(self.headers['session']).hexdigest()),
            tokenRequired=False)
        self.tokenExpire = runtime.seconds() + 25000

    @defer.inlineCallbacks
    def fetchCountry(self):
        self.country = yield self.send('getCountry', script="more.php")

    @defer.inlineCallbacks
    def generateCallToken(self, action):
        if runtime.seconds() > self.tokenExpire:
            yield self.fetchToken()
        seed = "%06x" % random.getrandbits(24)
        defer.returnValue(seed + hashlib.sha1("%s:%s:quitStealinMahShit:%s" % (
            action, self.rawToken, seed)).hexdigest())

    @defer.inlineCallbacks
    def send(self, action, params=None, script="service.php", tokenRequired=True):
        headers = dict(self.headers)
        dataDict = dict(method=action, parameters=params, header=headers)

        if self.country:
            params['country'] = self.country

        if tokenRequired:
            dataDict['header']['token'] = yield self.generateCallToken(action)

        dataJSON = json.dumps(dataDict)

        resultJSON = yield client.getPage(self.getURL(script, action), method="POST",
            headers=dict(self.httpHeaders, **self.jsonContent), postdata=dataJSON)

        resultDict = json.loads(resultJSON)

        result = resultDict.get('result')

        if result is not None:
            defer.returnValue(result)

        fault = JSONFault(resultDict['fault']['message'])
        fault.code = resultDict['fault']['code']
        raise fault

    @defer.inlineCallbacks
    def search(self, query, type="Songs"):
        result = yield self.send('getSearchResultsEx',
            dict(query=query, type=type), "more.php")
        result = result['result']
        defer.returnValue(result)

    @defer.inlineCallbacks
    def getStreamingInfo(self, songID):
        result = yield self.send('getStreamKeyFromSongIDEx',
            dict(songID=songID, prefetch=False, mobile=False), "more.php")
        defer.returnValue(result)

    def downloadSong(self, streamingInfo, filename):
        if streamingInfo not in ([], None): # For unplayable songs in the web client
            url = "http://%s/stream.php" % str(streamingInfo['ip'])
            postdata = "streamKey=" + str(streamingInfo['streamKey'])
            return client.downloadPage(url, filename, client.HTTPDownloader,
                method="POST", postdata=postdata, headers=self.formContent)
        return defer.succeed(True)

    def downloadCoverArt(self, coverArtFilename, filename):
        _, extension = os.path.splitext(coverArtFilename)
        if coverArtFilename not in (u'None', u'False'):
            return client.downloadPage(ART_BASE_URL + str(coverArtFilename),
                                       filename + extension)

    def downloadSongID(self, songID, filename):
        print ("Downloading %s to %s" % (songID, filename))
        return self.getStreamingInfo(songID).addCallbacks(
            functools.partial(self.downloadSong, filename=filename))

    def downloadSongInfo(self, songInfo, filename, artFilename=None):
        songID = songInfo[u'SongID']
        L = []
        if artFilename and songInfo.get(u'CoverArtFilename'):
            d = self.downloadCoverArt(songInfo[u'CoverArtFilename'],
                                      artFilename)
            if d: L.append(d)
        L.append(self.downloadSongID(songID, filename))
        return defer.DeferredList(L)

    @defer.inlineCallbacks
    def getPlaylist(self, playlistID):
        result = yield self.send('playlistGetSongs',
            dict(playlistID=playlistID), "more.php")
        defer.returnValue(result['Songs'])
