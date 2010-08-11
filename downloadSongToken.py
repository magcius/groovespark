#!/usr/bin/env python

import sys
import groovespark

from twisted.internet import reactor, defer

@defer.inlineCallbacks
def main(token, filename="id_%s.mp3"):
    gs = groovespark.GroovesharkAPI()
    yield gs.initialize()
    songid = yield gs.send('getSongFromToken', dict(token=token), "more.php")['SongID']
    yield gs.downloadSongID(songid, filename % (songid,))
    reactor.stop()

if __name__ == "__main__":
    main(*sys.argv[1:])
    reactor.run()
