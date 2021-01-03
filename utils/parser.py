import feedparser
from bs4 import BeautifulSoup

def parse_opml(f):
    feeds = []
    soup = BeautifulSoup(f, 'lxml')
    print(soup.original_encoding)
    print(soup)
    for podcast in soup.find_all(type="rss"):
        _, name, url = podcast.attrs.values()
        feeds.append({"name":name, "url":url})
    return feeds

