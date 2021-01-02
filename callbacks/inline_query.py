from utils.api_method import search
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, constants
from manifest import manifest
import re
from models import Podcast
from components import PodcastPage
from uuid import uuid4

def handle_inline_query(update, context):
    query = update.inline_query
    query_text = query.query
    podcast_match = re.match('^podcast(.*)', query_text)
    if not query_text:
        welcome(query, context)
    elif not podcast_match:
        search_podcast(query, context)
    elif not podcast_match[1]:
        show_subscription(query, context)
    else: 
        podcast = podcast_match[1].lstrip()
        show_episodes(query, context, podcast)

def welcome(query, context):
    user_id = query.from_user.id
    users = context.dispatcher.user_data.keys()
    if user_id not in users:
        results = []
        login = {
            "auto_pagination": True,
            "switch_pm_text": "登 录",
            "switch_pm_parameter": "login",
            "cache_time": 0
        }
    else:
        # trending, sorted by ...
        user = context.user_data['user']
        podcasts = context.bot_data['podcasts']
        results = [InlineQueryResultArticle(
            id = uuid4(),
            title = podcast.name,
            description = podcast.host,
            input_message_content = InputTextMessageContent((
                f"*{podcast.name}*"
            )),
            # reply_markup = InlineKeyboardMarkup(),
            thumb_url = podcast.logo_url,
            thumb_width = 60,
            thumb_height = 60
        ) for podcast in podcasts.values() if not user.subscription.get(podcast.name)]
        login = {}

    query.answer(
        results,
        **login
    )

def search_podcast(query, context):
    query_text = query.query
    searched_results = search(query_text)
    if not searched_results:
        listed_results = [
            InlineQueryResultArticle(
                id = '0',
                title = "没有与此相关的博客呢 :(",
                description = "换个关键词试试",
                input_message_content = InputTextMessageContent("🔍️"),
                reply_markup=InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton('返 回 搜 索 模 式', switch_inline_query_current_chat=query_text)
                )
            )
        ]
    else:
        listed_results = []
        for result in searched_results:
            name = re.sub(r'[_*`]', ' ', result['collectionName'])
            host = re.sub(r'[_*`]', ' ', result['artistName'])
            feed = result['feedUrl']
            thumbnail_full = result['artworkUrl600']
            thumbnail_small = result['artworkUrl60']

            # 如果不在 机器人主页，则：
            # [InlineKeyboardButton('前  往  B O T', url = f"https://t.me/{manifest.bot_id}")],

            result_item = InlineQueryResultArticle(
                id = result['collectionId'], 
                title = name, 
                input_message_content = InputTextMessageContent(feed),
                description = host,
                thumb_url = thumbnail_small,
                thumb_height = 60,
                thumb_width = 60
            )
            listed_results.append(result_item)

    query.answer(
        listed_results,
        auto_pagination = True,
    )

def show_episodes(query, context, podcast_name):
    podcasts = context.bot_data['podcasts']
    podcast = podcasts.get(podcast_name)
    episodes = podcast.episodes
    # if context.user_data['preference'].get('reverse_episodes'): episodes.reverse()
    def keyboard(i):
        return [
        [InlineKeyboardButton("收      听", callback_data = f"download_episode_{podcast_name}_{i}")],
        [InlineKeyboardButton("订  阅  列  表", switch_inline_query_current_chat="podcast"),
         InlineKeyboardButton("单  集  列  表", switch_inline_query_current_chat = f"podcast {podcast_name}")]
    ]
    listed_results = [InlineQueryResultArticle(
        id = index,
        title = episode.title,
        input_message_content = InputTextMessageContent((
            f"*{podcast.name}*  [🎙️]({episode.logo_url or podcast.logo_url})  {episode.host or podcast.host}\n\n"
            f"{episode.title}\n\n"
            f"{episode.subtitle}"
            # and then use Telegraph api to generate summary link!
            )),
        reply_markup = InlineKeyboardMarkup(keyboard(index)),
        description = episode.subtitle or podcast_name,
        thumb_url = podcast.logo_url,
        thumb_width = 40, 
        thumb_height = 40
    ) for index, episode in enumerate(episodes)]

    query.answer(
        listed_results,
        auto_pagination = True
    )

def show_subscription(query, context):
    subscription = context.user_data['user'].subscription
    results = [InlineQueryResultArticle(
            id = index,
            title = feed.podcast.name,
            input_message_content = InputTextMessageContent(PodcastPage(feed.podcast).text()),
            reply_markup = InlineKeyboardMarkup(PodcastPage(feed.podcast).keyboard()),
            description = feed.podcast.host,
            thumb_url = feed.podcast.logo_url,
            thumb_width = 60, 
            thumb_height = 60 
        ) for index, feed in enumerate(list(subscription.values()))]
    query.answer(
        results,
        auto_pagination = True,
    )
