
import groovespark
import codecs

from twisted.internet import reactor, defer

def dump(filename, result, comments=""):
    with codecs.open(filename, "w", "utf8") as file:
        print >>file, """
%s
""" % (comments,)
        # Need float here because sometimes I get 1.2345e+16 as a string back.
        for songinfo in sorted(result, key=lambda k: int(float(k.get('Sort', 0)))):
            songinfo.pop('Flags')
            songinfo.pop('Popularity')
            songinfo.pop('EstimateDuration')
            print >>file, ' ;; '.join(u'%s: %s' % (k, v) for k, v in songinfo.iteritems())

def load(filename):
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

def dumpSongs(filename, result, comments=""):
    dump(filename, result, """
# Comment out songs you don't want downloaded.
# Download with downloadSongList.py

# Don't change the song ID.
# Changing any other metadata isn't going to change the ID3 info of the tag.

%s
""" % (comments,))

@defer.inlineCallbacks
def apiWrapper(method, dumper, filename, comments, **kwargs):    
    gs = groovespark.GroovesharkAPI()
    yield gs.initialize()
    if getattr(gs, method, None):
        result = yield getattr(gs, method)(**kwargs)
    else:
        script = kwargs.pop('script')
        result = yield gs.send(method, kwargs, script)
    dumper(filename, result, comments)
    reactor.stop()
