from utils.parser import parse_opml
import feedparser
import socket
from urllib.error import URLError

socket.setdefaulttimeout(3)

class User(object):
    """
    docstring
    """
    def __init__(self, name, user_id):
        self.name = name
        self.user_id = user_id
        self.refresh_interval = 1800
        self.subscription = {}
        self.subscription_path = "public/subscriptions/{self.user_id}.xml"

    def import_feeds(self, podcasts):
        self.subscription = {podcast.name: Feed(podcast) for podcast in podcasts}

    def add_feed(self, url:str):
        new_podcast = Podcast(url)
        # 这里应该用 setter:
        self.subscription.update({new_podcast.name: Feed(new_podcast)})
        # self.update_subscription_file()
        return new_podcast

    def update_subscription_file(self):
        feeds_as_opml = encode_feeds(self.subscription)
        with open(self.subscription_path,'w') as subscription:
            subscription.write(feeds_as_opml)

    def encode_feeds(self, subscription) -> str:
        pass


class Podcast(object):
    """
    docstring
    """

    def __init__(self, feed_url):
        self.name = None
        self.feed_url = feed_url
        self.parse_feed(feed_url)
        self.subscribers = set()

    def parse_feed(self, url):
        try:
            result = feedparser.parse(url)
            if result.status != 200:
                raise Exception('404 Not Found')
        except:
            return
        else:
            feed = result.feed
            latest_episode = result['items'][0]
            self.name = feed.title
            print(f'podcast:{self.name}')
            self.latest_episode = Episode(self.name, latest_episode)
            self.host = feed.author_detail.name
            self.website = feed.link
            self.email = feed.author_detail.get('email')
            self.logo_url = feed.image.href

    def update(self):
        last_published_time = self.latest_episode.published_time
        self.parse_feed(self.feed_url)
        if self.latest_episode.published_time != last_published_time:
            return self.latest_episode
        else: 
            return None



class Episode(object):
    """
    Episode of a specific podcast.
    """

    def __init__(self, from_podcast:str, episode):
        self.podcast_name = from_podcast
        print(f'from:{self.podcast_name}')
        self.audio = episode.enclosures[0]
        # self.audio_url = self.audio.href
        # self.audio_size = self.audio.length
        self.title = episode.title
        self.subtitle = episode.get('subtitle')
        self.published_time = episode.published_parsed
        self.duration = episode.itunes_duration # string, (hh:)mm:ss

class Feed(object):
    """
    Feed of each user subscription.
    """
    def __init__(self, podcast):
        self.podcast = podcast
        self.is_latest = False
        self.is_liked = False
        self.audio_path = f'public/audio/{podcast.name}/'

# for test:
def check(url):
    r = feedparser.parse(url)
    f = r.feed
    # l = f.entries[0]
    # e = l.enclosures[0]

    print(
        f'title: {f.title}\n'
        f'host: {f.author}\n'
        f'email: {f.author_detail.email}\n'
        # f'length: {e.length}\n'
    )
