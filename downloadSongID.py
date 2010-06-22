#!/usr/bin/env python

import sys
import api

from twisted.internet import reactor, defer

@defer.inlineCallbacks
def main(songid):
    gs = api.GroovesharkAPI()
    yield gs.initialize()
    yield gs.downloadSongID(songid, "ss_%s" % (songid,))
    reactor.stop()

if __name__ == "__main__":
    main(*sys.argv[1:])
    reactor.run()
