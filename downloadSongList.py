#!/usr/bin/env python

import sys
import groovespark
import proplist

from twisted.internet import reactor, defer, task
from twisted.python import log

from optparse import OptionParser

def main():
    parser = OptionParser()
    parser.add_option('-s', '--song-format', dest='f', help="Format for the downloaded song. Uses"
                        "dict formatting, so %(ArtistName)s.mp3 is an example. For valid"
                        "things, see the songlist.", default="%(ArtistName)s - %(Name)s.mp3")
    parser.add_option('-c', '--cover-format', dest='c', help="yadda yadda, for cover art. Don't"
                        "include file extension as grooveshark has a bunch of them",
                        default="%(ArtistName)s - %(Name)s")
    options, args = parser.parse_args()
    songlist = proplist.load(args[0] if args else "songlist.txt")
    gs = groovespark.GroovesharkAPI()

    # log.startLogging(sys.stdout)

    def initialized(result):
        coop = task.Cooperator()
        work = (gs.downloadSongInfo(i, options.f % i, options.c % i) for i in songlist)
        d = defer.DeferredList([coop.coiterate(work) for i in xrange(1)])
        d.addCallbacks(lambda res: reactor.stop, log.err)

    gs.initialize().addCallback(initialized)

if __name__ == "__main__":
    main()
    reactor.run()
