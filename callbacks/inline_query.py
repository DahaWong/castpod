from utils.api_method import search
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, constants
from manifest import manifest
import re
from models import Podcast

def handle_inline_query(update, context):
    query = update.inline_query
    if not query.query:
        

def welcome(update, context):
    print('wel')
    user_id = query.from_user.id
    if user_id not in  context.dispatcher.user_data.keys():
        results = []
        login = {
            "auto_pagination": True,
            "switch_pm_text": "登 录",
            "switch_pm_parameter": "login",
            "cache_time": 0
        }
    else:
        # trending
        keyboard = [[InlineKeyboardButton('开    始', switch_inline_query_current_chat = '')]]
        results = [InlineQueryResultArticle(
            id='0',
            title = "欢迎使用播客搜索功能",
            description = "继续输入关键词以检索播客节目",
            input_message_content = InputTextMessageContent("🔍️"),
            reply_markup = InlineKeyboardMarkup(keyboard)
        )]
        login = {}

    query.answer(
        results,
        **login
    )

def subscribe_feed(update, context):
    query = update.inline_query
    query_text = query.query

    user_id = query.from_user.id
    users = context.dispatcher.user_data
    podcasts = context.bot_data['podcasts']
    user_subscription = context.user_data['user'].subscription
    podcast = Podcast(url)
    podcasts.update({podcast.name: podcast})
    results = []
    kwargs = {
        "switch_pm_text": "订阅播客：" + podcast.name,
        "switch_pm_parameter": podcast.name,
        "cache_time": 0
    }
    return results, kwargs

def show_episodes(update, context):
    query = update.inline_query
    podcast_name = re.match(r'^podcast (\w+)', query.query)[1]
    podcasts = context.bot_data['podcasts']
    podcast = podcasts.get(podcast_name)
    episodes = podcast.episodes
    results_per_page = constants.MAX_INLINE_QUERY_RESULTS

    listed_results = [InlineQueryResultArticle(
        id = index,
        title = episode.title,
        input_message_content = InputTextMessageContent((
            f"[📻️]({podcast.logo_url})  *{podcast_name}*\n"
            f"{episode.title}\n\n"
            f"{episode.get('subtitle') or ''}"
            # and then use Telegraph api to generate summary link!
            )),
        reply_markup = InlineKeyboardMarkup.from_row(
                [InlineKeyboardButton(
                    "📻️", 
                    callback_data = f"download_episode_{podcast_name}_"),
                 InlineKeyboardButton(
                    "全  部  单  集", 
                    switch_inline_query_current_chat = f"podcast {podcast_name}"),
                 InlineKeyboardButton(
                    "订  阅  列  表", 
                    switch_inline_query_current_chat="podcast")]
        ),
        description = episode.get('subtitle') or podcast_name,
        thumb_url = podcast.logo_url,
        thumb_width = 60, 
        thumb_height = 60 
    ) for index, episode in enumerate(episodes)]
        
    query.answer(
        listed_results,
        auto_pagination = True
    )

def search_podcast(update, context):
    query = update.inline_query

    user_id = query.from_user.id
    users = context.dispatcher.user_data
    podcasts = context.bot_data['podcasts']
    user_subscription = context.user_data['user'].subscription
    searched_results = search(query.query) # 需要缓存搜索结果⚠️？
    listed_results = []

    if not query.query:
        print('done')

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
            [InlineKeyboardButton('返    回', switch_inline_query_current_chat = query.query)]
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

    query.answer(
        listed_results,
        auto_pagination = True,
    )

def show_subscription(update, context):
    query = update.inline_query
    subscription = context.user_data['user'].subscription

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
                    switch_inline_query_current_chat = f"podcast {feed.podcast.name}"
                ), InlineKeyboardButton(
                    "关      于", url = feed.podcast.website)
            ]),
            description = feed.podcast.host,
            thumb_url = feed.podcast.logo_url,
            thumb_width = 30, 
            thumb_height = 30 
        ) for index, feed in enumerate(list(subscription.values()))
    ]

    query.answer(
        results,
        auto_pagination = True,
    )
