#!/usr/bin/env python

import sys
import proplist
from twisted.internet import reactor

def main(playlistID, filename="songlist.txt"):
    proplist.apiWrapper("getPlaylist", proplist.dumpSongs, filename,
        comments="# Playlist ID: %s" % playlistID, playlistID=playlistID)

if __name__ == "__main__":
    main(*sys.argv[1:])
    reactor.run()
