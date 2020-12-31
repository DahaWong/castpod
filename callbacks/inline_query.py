from utils.api_method import search
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, constants
from manifest import manifest
import re
from models import Podcast

def handle_inline_query(update, context):
    query = update.inline_query
    query_text = query.query

    user_id = query.from_user.id
    users = context.dispatcher.user_data
    podcasts = context.bot_data['podcasts']
    user_subscription = context.user_data['user'].subscription

    episodes_query_pattern = r'^episodes (.+) page ([0-9]+)'
    podcasts_query_pattern = r'^podcasts page ([0-9]+)'
    switch_to_bot = {}

    if not query_text:
        results, switch_to_bot = welcome(users, user_id)
    elif re.match(episodes_query_pattern, query_text):
        match = re.match(episodes_query_pattern, query_text)
        results = show_episodes(
            podcasts, 
            podcast_name = match[1], 
            current_page = int(match[2])
        )
    elif re.match(podcasts_query_pattern, query_text):
        match = re.match(podcasts_query_pattern, query_text)
        results = show_subscription(
            user_subscription, 
            current_page = int(match[1])
        )
    else:
        results = search_podcast(query_text)

    query.answer(
        results,
        **switch_to_bot
    )

def welcome(users, user_id):
    switch_to_bot = {}
    if user_id not in users.keys():
        listed_results = []
        switch_to_bot = {
            "switch_pm_text": "登 录",
            "switch_pm_parameter": "login",
            "cache_time": 0
        }
    else:
        keyboard = [[InlineKeyboardButton('🔍️', switch_inline_query_current_chat = '')]]
        listed_results = [InlineQueryResultArticle(
            id='0',
            title = "欢迎使用播客搜索功能",
            description = "继续输入关键词以检索播客节目",
            input_message_content = InputTextMessageContent("点按以搜索播客"),
            reply_markup = InlineKeyboardMarkup(keyboard)
        )]
    return listed_results, switch_to_bot

def subscribe_feed(podcasts, url):
    print("in!")
    podcast = Podcast(url)
    podcasts.update({podcast.name: podcast})
    results = []
    switch_to_bot = {
        "switch_pm_text": "订阅播客：" + podcast.name,
        "switch_pm_parameter": podcast.name,
        "cache_time": 0
    }
    return results, switch_to_bot

def show_episodes(podcasts, podcast_name, current_page):
    podcast = podcasts[podcast_name]
    episodes = podcast.episodes
    episodes_count = len(episodes)

    results_per_page = constants.MAX_INLINE_QUERY_RESULTS

    no_more_episodes = episodes_count <= results_per_page * (current_page - 1)

    if no_more_episodes:
        listed_results = [InlineQueryResultArticle(
            id = "-1",
            title = "没有更多的节目了 :(",
            description = "前往订阅列表",
            input_message_content = InputTextMessageContent("/manage")
        )]
    else:
        listed_results = [InlineQueryResultArticle(
            id = index,
            title = episode.title,
            input_message_content = InputTextMessageContent((
                f"[📻️]({podcast.logo_url})  *{podcast_name}*\n"
                f"{episode.title}\n\n"
                f"{episode.get('subtitle') or ''}"
                # and then use Telegraph api to generate summary link!
                )),
            reply_markup = InlineKeyboardMarkup.from_column(
                [InlineKeyboardButton("收   听   本   集", callback_data=f"download_episode_{podcast_name}_{(current_page-1) * results_per_page + index}"),
                 InlineKeyboardButton(
                    "返  回  单  集  列  表", 
                    switch_inline_query_current_chat = f"episodes {podcast_name} page {current_page}"
                 ),
                 InlineKeyboardButton("查  看  订  阅  列  表", switch_inline_query_current_chat="podcasts page 1")]
            ),
            description = episode.get('subtitle') or podcast_name,
            thumb_url = podcast.logo_url,
            thumb_width = 30, 
            thumb_height = 30 
        ) for index, episode in enumerate(
            episodes[
                results_per_page * (current_page - 1): 
                results_per_page * current_page])
            ]
    return listed_results

def search_podcast(query):
    searched_results = search(query) # 需要缓存搜索结果⚠️？
    listed_results = []

    for result in searched_results:
        itunes_id = result['collectionId']
        name = result['collectionName']
        feed = result.get('feedUrl')
        host = result['artistName']
        thumbnail_full = result['artworkUrl600']
        thumbnail_small = result['artworkUrl60']

        podcast_info = f"[📻️]({thumbnail_full})  {name} \n_by_ {host}\n\n订阅：`{feed}`"
        keyboard = [
            # 如果不在 机器人主页，则：
            # [InlineKeyboardButton('前  往  B O T', url = f"https://t.me/{manifest.bot_id}")],
            [InlineKeyboardButton('返 回 搜 索 模 式', switch_inline_query_current_chat = query)]
        ]

        result_item = InlineQueryResultArticle(
            id = itunes_id, 
            title = name, 
            input_message_content = InputTextMessageContent(podcast_info), 
            reply_markup= InlineKeyboardMarkup(keyboard),
            description = host,
            thumb_url = thumbnail_small,
            thumb_height = 60,
            thumb_width = 60
        )
        listed_results.append(result_item)
    return listed_results

def show_subscription(subscription, current_page):
    subscription_count = len(subscription)
    results_per_page = constants.MAX_INLINE_QUERY_RESULTS
    no_more_subscription = subscription_count <= results_per_page * (current_page - 1)

    if no_more_subscription:
        results = [InlineQueryResultArticle(
            id = "-1",
            title = "没有更多的订阅了 :(",
            description = "前往搜索播客",
            input_message_content = InputTextMessageContent("/search")
        )]
    else:
        print(subscription.values())
        results = [InlineQueryResultArticle(
            id = index,
            title = feed.podcast.name,
            input_message_content = InputTextMessageContent((
                f"[📻️]({feed.podcast.logo_url})  *{feed.podcast.name}*\n"
                f"{feed.podcast.host}\n\n"
                f"{feed.podcast.email}"
                )),
            reply_markup = InlineKeyboardMarkup.from_column([
                InlineKeyboardButton(
                    "查 看 单 集", 
                    switch_inline_query_current_chat = f"episodes {feed.podcast.name} page 1"
                ), InlineKeyboardButton(
                    "关      于", url = feed.podcast.website)
            ]),
            description = feed.podcast.host,
            thumb_url = feed.podcast.logo_url,
            thumb_width = 30, 
            thumb_height = 30 
        ) for index, feed in enumerate(
            list(subscription.values())[
                results_per_page * (current_page - 1): 
                results_per_page * current_page]
            )
        ]
    return results
