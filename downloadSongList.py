#!/usr/bin/env python

import sys
import api
import codecs

from twisted.internet import reactor, defer, task
from twisted.python import log
from twisted.web import client

def parseSongList(filename):
    for line in codecs.open(filename, 'r', 'utf8'):
        line = line.strip()
        try:
            line = line[line.index("#"):].strip()
        except ValueError:
            pass
        if line:
            try:
                D = dict(s.strip().split(': ', 1) for s in line.split(';;'))
                yield D
            except ValueError:
                continue

def main(songlist='songlist.txt', format="%(ArtistName)s - %(Name)s.mp3"):
    gs = api.GroovesharkAPI()
    coop = task.Cooperator()
    work = (gs.downloadSongID(i[u'SongID'], format % i) for i in parseSongList(songlist))
    d = defer.DeferredList([coop.coiterate(work) for i in xrange(1)])
    d.addCallbacks(lambda res: reactor.stop, log.err)

if __name__ == "__main__":
    main(*sys.argv[1:])
    reactor.run()
