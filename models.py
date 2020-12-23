from utils.parser import parse_feed, parse_opml


class User(object):
    """
    docstring
    """
    def __init__(self, name, user_id):
        self.name = name
        self.user_id = user_id
        self.subscription = {}

    @property
    def subscription(self):
        return self._subscription
    
    @subscription.setter
    def subscription(self, subscription):
        self._subscription = subscription

    def set_favorite(podcast):
        pass

    def import_feeds(self, path):
        with open(path, 'r') as f:
            feeds = parse_opml(f)
            self.subscription  = {feed['name']:Podcast(**feed) for feed in feeds}

    def add_feed(self, url:str):
        name = parse_feed(url)[0]
        new_podcast = Podcast(name, url)
        self.subscription.update({name: new_podcast})
        return new_podcast

class Podcast(object):
    """
    docstring
    """
    # latest_episode
    def __init__(self, name, feed):
        self.name = name
        self.feed = feed
        self.needUpdate = False
        self.subscribers = set()

    def check_update(self):
        pass



class Episode(object):
    """
    docstring
    """
    from_podcast:Podcast
    name:str
    message_url:str
