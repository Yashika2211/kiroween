import urllib2
from collections import Mapping


def total(prices):
    result = 0
    for name, price in prices.iteritems():
        result += price
    return result


def shout(word):
    if isinstance(word, basestring):
        print "shouting", word
        return word.upper()
    raise TypeError, "need a string"


def fetch(url):
    try:
        return urllib2.urlopen(url).read()
    except urllib2.URLError, e:
        return None
