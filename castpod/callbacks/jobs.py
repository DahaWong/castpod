import asyncio
from pprint import pprint
from telegram.ext import ContextTypes
from config import manifest
from ..models import Episode, Podcast, User, UserSubscribePodcast


async def update_episodes(context: ContextTypes.DEFAULT_TYPE):
    """Check new episodes of all podcasts every 15 minute."""
    podcasts = Podcast.select()
    try:
        async with asyncio.TaskGroup() as tg:
            for podcast in podcasts:
                task = tg.create_task(podcast.update_feed())
    except ExceptionGroup as eg:
        for err in eg.exceptions:
            pprint(err)


# TODO: complete this after code refactoring.
async def send_new_episodes(context: ContextTypes.DEFAULT_TYPE):
    """Send new undownloaded episodes to subscribers every 40 minute."""
    episodes = Episode.select().where(Episode.is_downloaded == False)
    for episode in episodes:
        bot = context.bot
        subscribers = (
            User.select()
            .join(UserSubscribePodcast)
            .where(UserSubscribePodcast.podcast == episode.from_podcast)
        )
        episode.download()
        path = ""  # TODO
        async with asyncio.TaskGroup() as tg:
            for user in subscribers:
                audio = episode.file_id if episode.file_id else path
                tg.create_task(bot.send_audio(audio))
