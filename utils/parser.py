import feedparser
from bs4 import BeautifulSoup

def parse_opml(f):
    feeds = []
    soup = BeautifulSoup(f, 'xml')
    print('1')
    for podcast in soup.find_all(type="rss"):
        print('2')
        _, name, url = podcast.attrs.values()
        print('3')
        feeds.append({"name":name, "url":url})
    return feeds
