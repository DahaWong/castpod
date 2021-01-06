from utils.parser import parse_opml
import feedparser
import socket, datetime, re
from urllib.error import URLError
from uuid import NAMESPACE_URL, uuid5
from telegraph import Telegraph
from manifest import manifest

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
        # self.id = uuid5(NAMESPACE_URL, feed_url)
        self.parse_feed(feed_url)
        self.subscribers = set()

    def parse_feed(self, url):
        socket.setdefaulttimeout(5)
        result = feedparser.parse(url)
        if str(result.status)[0]!= '2' and str(result.status)[0]!= '3':
            raise Exception(f'Feed URL Open Error. {result.status}')
        feed = result.feed
        self.name = feed.get('title')
        if not self.name: raise Exception("Error when parsing feed.")
        self.logo_url = feed.get('image').get('href')
        self.episodes = self.set_episodes(result['items'])
        self.latest_episode = self.episodes[0]
        self.host = feed.author_detail.name
        self.website = feed.link
        self.email = feed.author_detail.get('email') or ""

    def update(self):
        last_published_time = self.latest_episode.published_time
        self.parse_feed(self.feed_url)
        if self.latest_episode.published_time != last_published_time:
            return self.latest_episode
        else: 
            return None

    def set_episodes(self, results):
        episodes = []
        for episode in result['items']:
            episodes.append(Episode(self.name, episode, self.logo_url))

class Episode(object):
    """
    Episode of a specific podcast.
    """
    def __init__(self, from_podcast:str, episode, podcast_logo):
        self.podcast_name = from_podcast
        self.podcast_logo = podcast_logo
        self.host = episode.get('author') or ''
        self.audio = self.set_audio(episode.enclosures)
        if self.audio:
            self.audio_url = self.audio.href
            self.audio_size = self.audio.get('length') or ''
        else:
            self.audio_url = ""
            self.audio_size = 0
        self.title = self.set_title(episode.get('title'))
        self.subtitle = episode.get('subtitle') or ''
        if self.title == self.subtitle: self.subtitle = ''
        self.logo_url = episode.get('image').href if episode.get('image') else ''
        self.duration = self.set_duration(episode.get('itunes_duration'))
        self.content = episode.get('content')
        self.summary = episode.get('summary') or ''
        self.shownotes = self.set_shownotes()
        self.shownotes_url = self.set_shownotes_url()
        self.published_time = episode.published_parsed
        self.tags = episode.get('tags')[0].get('term') if episode.get('tags') else None
        self.message_id = None

    def set_duration(self, duration:str) -> int:
        if duration:
            if ':' in duration:
                time = duration.split(':')
                if len(time) == 3:
                    duration_timedelta = datetime.timedelta(
                        hours=int(time[0]), 
                        minutes=int(time[1]), 
                        seconds=int(time[2])
                    )
                elif len(time) == 2:
                    duration_timedelta = datetime.timedelta(
                        hours=0, 
                        minutes=int(time[0]), 
                        seconds=int(time[1])
                    )
            else:
                duration_timedelta = datetime.timedelta(seconds=int(duration))
        else:
            duration_timedelta = datetime.timedelta(seconds=0)
        return duration_timedelta

    def set_audio(self, enclosure):
        if enclosure:
            return enclosure[0]
        else:
            return None

    def set_title(self, title):
        if not title: return ''
        return title.lstrip(self.podcast_name)

    def set_shownotes(self):
        shownotes = self.content[0]['value'] if self.content else self.summary
        img_content = f"<img src='{self.logo_url or self.podcast_logo}'>" if 'img' not in shownotes else ''
        return img_content + self.replace_invalid_tags(shownotes)

    def replace_invalid_tags(self, html_content):
        html_content = html_content.replace('h2', 'h3')
        html_content = re.sub(r'<div.*?>', '', html_content).replace('</div>', '')
        html_content = re.sub(r'<span.*>', '', html_content).replace('</span>', '')
        html_content = html_content.replace('’', "'")
        # print(html_content)
        return html_content
    
    def set_shownotes_url(self):
        telegraph = Telegraph()

        telegraph.create_account(
            short_name = manifest.name,
            author_name = manifest.name,
            author_url = f'https://t.me/{manifest.bot_id}'
        )

        try:
            res = telegraph.create_page(
                title = f"{self.title}",
                html_content=self.shownotes,
                author_name = self.host
            )
            print(f"https://telegra.ph/{res['path']}")
            return f"https://telegra.ph/{res['path']}"
        except Exception as e:
            print(e)
            return ''

class Feed(object):
    """
    Feed of each user subscription.
    """
    def __init__(self, podcast):
        self.podcast = podcast
        self.is_latest = False
        self.is_liked = False
        self.audio_path = f'public/audio/{podcast.name}/'