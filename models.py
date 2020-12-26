from utils.parser import parse_opml
import feedparser


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
        self.subscription.update({new_podcast.name: Feed(new_podcast)})
        self.update_subscription_file()
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
        self.feed_url = feed_url
        self.parse_feed(feed_url)
        self.subscribers = {}

    def parse_feed(self, url):
        result = feedparser.parse(feed_url)
        feed = result.feed
        latest_episode = result.entries[0]
        self.name = feed.title
        self.latest_episode = Episode(latest_episode, self)
        self.host = feed.author
        self.email = feed.author_detail.email
        self.logo_url = feed.image.href

    def update(self):
        last_published_time = self.latest_episode.published_time
        self.parse_feed(self.feed_url)
        if self.latest_episode.published_time != last_published_time
            return self.latest_episode
        else: 
            return None


class Feed(object):
    """
    Feed of each user subscription.
    """
    def __init__(self, podcast):
        self.podcast = podcast
        self.is_latest = False
        self.is_liked = False
        self.audio_path = f'public/audio/{podcast.name}/'


class Episode(object):
    """
    Episode of a specific podcast.
    """

    def __init__(self, from_podcast, episode):
        self.from_podcast = from_podcast
        self.audio_url = episode.links[0].href,
        self.title = episode.title,
        self.subtitle = episode.subtitle
        self.published_time = episode.published_parsed,
        self.file_size = episode.length,
        self.duration = episode.itunes_duration, # string, mm:ss