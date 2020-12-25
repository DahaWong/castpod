import feedparser
from bs4 import BeautifulSoup
import pprint

def parse_feed(url):
    result = feedparser.parse(url)
    feed = result.feed
    latest_entry = result.entries[0]

    website = feed.link
    # print(website)
    # pprint.pp(feed)
    title = result.feed.title
    logo_url = feed.image.href
    email = feed.author_detail.email
    update_time =  latest_entry.published_parsed
    latest_audio_url =  latest_entry.enclosures[0].href
    return (link, title, logo_url)


# parse_feed('https://renjianzhinan.xyz/podcast.xml')

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