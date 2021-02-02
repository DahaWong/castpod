import datetime
import feedparser
import socket
from html import unescape

import castpod.models as models
from config import manifest
import random

class Podcast(object):
    def __init__(self, podcast):
        self.podcast = podcast

    def renew(self):
        self.set_job_group()
        socket.setdefaulttimeout(5)
        result = feedparser.parse(self.podcast.feed)
        if str(result.status)[0] != '2' and str(result.status)[0] != '3':
            raise Exception(f'Feed open error, status: {result.status}')
        feed = result.feed
        self.podcast.name = feed.get('title')
        if not self.podcast.name:
            self.podcast.delete()
            raise Exception("Cannot parse feed name.")
        self.podcast.name = unescape(self.podcast.name)[:63]
        if len(self.podcast.name) == 63:
            self.podcast.name += '…'
        self.podcast.logo = feed.get('image')['href']
        for i, item in enumerate(result['items']):
            episode = models.Episode(podcast=self.podcast, index=i).save()
            # episode.parse(item)
            self.podcast.update_one(push__episodes=episode)
            self.podcast.reload()
        # self.download_logo()
        self.podcast.host = unescape(feed.author_detail.name or '')
        if self.podcast.host == self.podcast.name:
            self.podcast.host = ''
        self.podcast.website = feed.link
        self.podcast.email = feed.author_detail.get('email') or ''
        self.podcast.save()

    def set_job_group(self):
        i = random.randint(0, 47)
        self.podcast.job_group = [i % 48 for i in range(i, i + 41, 8)]
        self.podcast.save()

class User(object):
    def __init__(self, user):
        self.user = user

    def subscribe(self, podcast):
        self.user.subscriptions.append(models.Subscription(podcast))
        podcast.subscribers.append(self.user)
        podcast.save()
        self.user.save()

    def generate_opml(self):
        body = ''
        for subscription in self.user.subscriptions:
            podcast = subscription.podcast
            outline = f'\t\t\t\t<outline type="rss" text="{podcast.name}" xmlUrl="{podcast.feed}"/>\n'
            body += outline
        head = (
            "<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>\n"
            "\t<opml version='1.0'>\n"
            "\t\t<head>\n"
            f"\t\t\t<title>{manifest.name} 订阅源</title>\n"
            "\t\t</head>\n"
            "\t\t<body>\n"
            "\t\t\t<outline text='feeds'>\n"
        )
        tail = (
            "\t\t\t</outline>\n"
            "\t\t</body>\n"
            "\t</opml>\n"
        )
        opml = head + body + tail 
        path = f"./public/subscriptions/{self.user.id}.xml"
        with open(path, 'w+') as f:
            f.write(opml)
        return path
