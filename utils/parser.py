import feedparser
from bs4 import BeautifulSoup

def parse_feed(url):
    result = feedparser.parse(url)
    print('test')
    title = result.feed.title
    logo = result.feed.image['href']
    latest_audio =  result.entries[0].enclosures[0]['href']
    return (title, logo, latest_audio)

def parse_opml(f):
    feeds = []
    soup = BeautifulSoup(f, 'xml')
    for podcast in soup.find_all(type="rss"):
        _, name, feed = podcast.attrs.values()
        feeds.append({"name":name, "feed":feed})
    return feeds

# feedparser.parse("https://yitianshijie.net/episodes/feed.xml")
# r = feedparser.parse("https://renjianzhinan.xyz/podcast.xml")


# print(r.feed.title) #一天世界
# print(r.feed.image) # logo
# e = r.entries[0].enclosures #mp3
# 'title' in d.feed # test if exists
# d.feed.get('title', 'No title') # test/search item