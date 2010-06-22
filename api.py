import functools
import hashlib
import json
import random
import uuid
import urllib

from twisted.python import runtime, log
from twisted.internet import defer
from twisted.web import error, client

API_URL = "http://cowbell.grooveshark.com/"

class JSONFault(Exception): pass

class GroovesharkAPI(object):
    def __init__(self, secure=True, url=API_URL):
        self.secure = secure
        if secure:
            url = url.replace("http", "https")
        self.url = url
        self.headers = dict(client="gslite", clientRevision="20100412.39",
                            privacy=1, uuid=str(uuid.uuid4()).upper())
        self.jsonContent = {"content-type":"application/json"}
        self.formContent = {"content-type":"application/x-www-form-urlencoded"}
        self.tokenExpire = None
        self.country = None
        self.initialized = False
        self.commandQueue = []
        self.initialize()

    @defer.inlineCallbacks
    def initialize(self):
        yield self.fetchSessionID()
        yield self.fetchToken()
        yield self.fetchCountry()
        self.initialized = True
        for func, deferred in self.commandQueue:
            result = yield func()
            deferred.callback(result)

    def getURL(self, script, *args, **kwargs):
        return "%s%s?%s%s" % (self.url, script,
            '&'.join(map(urllib.quote, args)), urllib.urlencode(kwargs))

    @defer.inlineCallbacks
    def fetchSessionID(self):
        cookies = dict()
        result = yield client.getPage(self.url, method="POST", cookies=cookies)
        self.headers['session'] = cookies['PHPSESSID']

    @defer.inlineCallbacks
    def fetchToken(self):
        self.rawToken = yield self._send('getCommunicationToken',
            dict(secretKey=hashlib.md5(self.headers['session']).hexdigest()),
            tokenRequired=False)
        self.tokenExpire = runtime.seconds() + 25000

    @defer.inlineCallbacks
    def fetchCountry(self):
        self.country = yield self._send('getCountry', script="more.php")

    @defer.inlineCallbacks
    def generateCallToken(self, action):
        if runtime.seconds() > self.tokenExpire:
            yield self.fetchToken()
        seed = "%06x" % random.getrandbits(24)
        defer.returnValue(seed + hashlib.sha1("%s:%s:quitStealinMahShit:%s" % (
            action, self.rawToken, seed)).hexdigest())

    def send(self, action, params=None, script="service.php"):
        if self.initialized:
            return self._send(action, params, script)
        else:
            d = defer.Deferred()
            self.commandQueue.append((
                functools.partial(self._send, action, params, script), d))
            return d

    @defer.inlineCallbacks
    def _send(self, action, params=None, script="service.php", tokenRequired=True):
        headers = dict(self.headers)
        dataDict = dict(method=action, parameters=params, header=headers)

        if self.country:
            params['country'] = self.country

        if tokenRequired:
            dataDict['header']['token'] = yield self.generateCallToken(action)

        dataJSON = json.dumps(dataDict)

        resultJSON = yield client.getPage(self.getURL(script, action), method="POST",
                                          headers=dict(self.jsonContent), postdata=dataJSON)
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
        defer.returnValue(result)

    @defer.inlineCallbacks
    def getStreamingInfo(self, songID):
        result = yield self.send('getStreamKeyFromSongIDEx',
            dict(songID=songID, prefetch=True, mobile=False), "more.php")
        defer.returnValue(result)

    @defer.inlineCallbacks
    def downloadSong(self, streamingInfo, filename):
        url = "http://%s/stream.php" % str(streamingInfo['ip'])
        postdata = "streamKey=" + str(streamingInfo['streamKey'])
        # I have to do this because downloadPage/HTTPDownloader
        # doesn't support afterFoundGet, which is required
        # to download from the Akamai servers
        factory = client._makeGetterFactory(url, client.HTTPDownloader,
            method="POST", postdata=postdata, headers=self.formContent,
            fileOrName=filename)
        factory.afterFoundGet = True
        yield factory.deferred

    def downloadSongID(self, songID, filename):
        d = self.getStreamingInfo(songID)
        d.addCallback(functools.partial(self.downloadSong, filename=filename))
        return d

    @defer.inlineCallbacks
    def getPlaylist(self, playlistID):
        result = yield self.send('playlistGetSongs',
            dict(playlistID=playlistID), "more.php")
        defer.returnValue(result)
