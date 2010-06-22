#!/usr/bin/env python

import operator
import sys
import api
import codecs
from twisted.internet import reactor, defer

@defer.inlineCallbacks
def main(playlistID, filename=None):
    filename = filename or "songlist.txt"
    gs = api.GroovesharkAPI()
    result = yield gs.getPlaylist(playlistID)
    with codecs.open(filename, "w", "utf8") as file:
        print >>file, "# Comment out songs you don't want downloaded"
        print >>file, "# Download with downloadSongList.py\n"
        print >>file, "# Changing the "
        for songinfo in sorted(result['Songs'], key=lambda k: int(k[u'Sort'])):
            songinfo.pop(u'Sort')
            songinfo.pop(u'CoverArtFilename')
            songinfo.pop(u'Flags')
            songinfo.pop(u'Popularity')
            songinfo.pop(u'EstimateDuration')
            print >>file, ' ;; '.join(u'%s: %s' % (k, v) for k, v in songinfo.iteritems())
    reactor.stop()

if __name__ == "__main__":
    main(*sys.argv[1:])
    reactor.run()
