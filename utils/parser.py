from bs4 import BeautifulSoup
def parse_opml(f):
    feeds = []
    soup = BeautifulSoup(f, 'lxml', from_encoding="utf-8")
    for podcast in soup.find_all(type="rss"):
        feeds.append({"name":podcast.attrs.get('text'), "url":podcast.attrs.get('xmlurl')})
    return feeds

# with open('public/subscriptions/subs.opml', 'r') as f:
#     parse_opml(f)
