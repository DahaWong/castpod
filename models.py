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
        self.subscription = {}
        self.subscription_path = "public/subscriptions/{self.user_id}.xml"

    def import_feeds(self, podcasts):
        self.subscription = {podcast.name: Feed(podcast) for podcast in podcasts}

    def add_feed(self, url:str):
        new_podcast = Podcast(url)
        # 这里应该用 setter
        # 与此同时，更新 podcast 中的订阅者
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
    def __init__(self, feed_url):
        self.feed_url = feed_url
        self.parse_feed(feed_url)
        self.subscribers = set()

    def parse_feed(self, url):
        result = feedparser.parse(url)
        if result.status != 200: raise Exception('Feed URL Open Error.')
        feed = result.feed
        self.episodes = result['items']
        latest_episode = self.episodes[0]
        self.name = feed.get('title')
        if not self.name: raise Exception("Error when parsing feed.")
        print(self.name)
        self.latest_episode = Episode(self.name, latest_episode)
        self.host = feed.author_detail.name
        self.website = feed.link
        self.email = feed.author_detail.get('email') or ""
        self.logo_url = feed.get('image').get('href')

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
        print(self.podcast_name)
        self.host = episode.get('author') or ''
        self.audio = episode.enclosures[0]
        self.audio_url = self.audio.href
        self.audio_size = self.audio.get('length') or 0
        self.title = episode.get('title') or ''
        self.subtitle = episode.get('subtitle') or ''
        self.summary = episode.get('summary') or ''
        self.published_time = episode.published_parsed
        self.duration = episode.get('itunes_duration') # string, (hh:)mm:ss or sec
        self.logo_url = logo.href if episode.get('image') else ''
        self.tags = tags[0].get('term') if episode.get('tags') else None
 
class Feed(object):
    """
    Feed of each user subscription.
    """
    def __init__(self, podcast):
        self.podcast = podcast
        self.is_latest = False
        self.is_liked = False
        self.audio_path = f'public/audio/{podcast.name}/'