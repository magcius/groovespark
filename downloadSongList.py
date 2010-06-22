#!/usr/bin/env python

import sys
import api
import codecs

from twisted.internet import reactor, defer, task
from twisted.python import log
from twisted.web import client

from optparse import OptionParser

def parseSongList(filename):
    for line in codecs.open(filename, 'r', 'utf8'):
        line = line.strip()
        try:
            line = line[:line.index("#")].strip()
        except ValueError:
            pass
        if line:
            try:
                D = dict(s.strip().split(': ', 1) for s in line.split(';;'))
                yield D
            except ValueError:
                continue

def main():
    parser = OptionParser()
    parser.add_option('-s', '--song-format', dest='f', help="Format for the downloaded song. Uses"
                        "dict formatting, so %(ArtistName)s.mp3 is an example. For valid"
                        "things, see the songlist.", default="%(ArtistName)s - %(Name)s.mp3")
    parser.add_option('-c', '--cover-format', dest='c', help="yadda yadda, for cover art. Don't"
                        "include file extension as grooveshark has a bunch of them",
                        default="%(ArtistName)s - %(Name)s")
    options, args = parser.parse_args()
    songlist = parseSongList(args[0] if args else "songlist.txt")
    gs = api.GroovesharkAPI()

    log.startLogging(sys.stdout)

    def initialized(result):
        print "initialized"
        print gs.country
        coop = task.Cooperator()
        work = (gs.downloadSongInfo(i, options.f % i, options.c % i) for i in songlist)
        d = defer.DeferredList([coop.coiterate(work) for i in xrange(1)])
        d.addCallbacks(lambda res: reactor.stop, log.err)

    gs.initialize().addCallback(initialized)

if __name__ == "__main__":
    main()
    reactor.run()
