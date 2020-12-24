from utils.parser import parse_feed, parse_opml


class User(object):
    """
    docstring
    """
    def __init__(self, name, user_id):
        self.name = name
        self.user_id = user_id
        self.subscription = {}
        self.subscription_path = "public/subscriptions/{self.user_id}.xml"

    @property
    def subscription(self):
        return self._subscription
    
    @subscription.setter
    def subscription(self, subscription):
        self._subscription = subscription

    def set_favorite(feed):
        pass

    def import_feeds(self, path):
        with open(path, 'r') as f:
            feeds = parse_opml(f)
            self.subscription  = {feed['name']: Feed(Podcast(**feed)) for feed in feeds}

    def add_feed(self, url:str):
        name = parse_feed(url)[0]
        new_podcast = Podcast(name, url)
        self.subscription.update({name: Feed(new_podcast)})
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
    # latest_episode = ...

    def __init__(self, name, feed):
        self.name = name
        self.feed = feed
        self.need_update = False
        self.subscribers = set()

    def check_update(self):
        pass

    # should async:
    def download_update(self):
        pass


class Feed(object):
    """
    Feed of each user subscription.
    """
    def __init__(self, podcast):
        self.podcast = podcast
        self.can_update = False
        self.is_favorite = False
        self.audio_path = f'public/audio/{podcast.name}/'


# class Episode(object):
#     """
#     docstring
#     """
#     from_podcast:Podcast
#     name:str
#     message_url:str
