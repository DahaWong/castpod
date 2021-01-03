import feedparser
from bs4 import BeautifulSoup

def parse_opml(f):
    feeds = []
    soup = BeautifulSoup(f, 'xml', from_encoding = 'utf-8').encode('utf-8')
    for podcast in soup.find_all(type="rss"):
        _, name, url = podcast.attrs.values()
        feeds.append({"name":name, "url":url})
    return feeds
