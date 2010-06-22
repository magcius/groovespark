#!/usr/bin/env python

import sys
import proplist
from twisted.internet import reactor

def main(query, filename="searchlist.txt", type="Songs"):
    proplist.apiWrapper("get", proplist.dumpSongs, filename,
        comments="# Query: %s" % query, query=query, type=type)

if __name__ == "__main__":
    main(*sys.argv[1:])
    reactor.run()
