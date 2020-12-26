import feedparser
from bs4 import BeautifulSoup
import pprint

def parse_opml(f):
    feeds = []
    soup = BeautifulSoup(f, 'xml')
    for podcast in soup.find_all(type="rss"):
        _, name, feed = podcast.attrs.values()
        feeds.append({"name":name, "feed":feed})
    return feeds
