#!/usr/bin/env python

import sys
import groovespark
import proplist
from twisted.internet import reactor, defer

@defer.inlineCallbacks
def main(token):
    gs = groovespark.GroovesharkAPI()
    yield gs.initialize()
    result = yield gs.send('getSongFromToken', dict(token=token), "more.php")
    print result['SongID']

if __name__ == "__main__":
    main(*sys.argv[1:])
    reactor.run()
