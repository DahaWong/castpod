from utils.api_method import search
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, constants
from manifest import manifest
from utils.url_shortener import shorten
import re

def handle_inline_query(update, context):
    query = update.inline_query
    query_text = query.query

    user_id = query.from_user.id
    users = context.dispatcher.user_data
    podcasts = context.bot_data['podcasts']

    episodes_query_pattern = r'^episodes (.+) page ([0-9]+)'
    match_episodes_query = re.match(episodes_query_pattern, query_text)

    switch_to_login = {}

    if not query_text:
        results, switch_to_login = welcome(users, user_id)
    elif match_episodes_query:
        match = match_episodes_query
        results = show_episodes(query_text, podcasts, podcast_name = match[1], current_page = int(match[2]))
    else:
        results = search_podcast(query_text)

    query.answer(
        results,
        **switch_to_login
    )

def welcome(users, user_id):
    switch_to_login = {}
    if user_id not in users.keys():
        listed_results = []
        switch_to_login = {
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
            input_message_content = InputTextMessageContent("点击按钮以搜索播客"),
            reply_markup = InlineKeyboardMarkup(keyboard)
        )]
    return listed_results, switch_to_login

def show_episodes(query, podcasts, podcast_name, current_page):
    pattern = r'^episodes (.+) page ([0-9]+)'

    podcast = podcasts[podcast_name]
    episodes = podcast.episodes
    episodes_count = len(episodes)

    results_per_page = constants.MAX_INLINE_QUERY_RESULTS

    no_more_episodes = episodes_count <= results_per_page * (current_page - 1)

    if no_more_episodes:
        listed_results = [InlineQueryResultArticle(
            id = "-1",
            title = "没有更多的节目了 :(",
            description = "前往查看订阅中的其他播客",
            input_message_content = InputTextMessageContent("/manage")
        )]
    else:
        listed_results = [InlineQueryResultArticle(
            id = index,
            title = episode.title,
            input_message_content = InputTextMessageContent((
                f"[📻️]({podcast.logo_url})  *{podcast_name}*\n"
                f"{episode.title}\n\n"
                f"{episode.get('subtitle')}"
                )),
            reply_markup = InlineKeyboardMarkup.from_column(
                [InlineKeyboardButton("收   听   本   集", callback_data=f"download_episode_{podcast_name}_{(current_page-1) * results_per_page + index}"),
                 InlineKeyboardButton(
                    "返  回  单  集  列  表", 
                    switch_inline_query_current_chat = query
                )]
            ),
            description = episode.get("subtitle") or podcast_name,
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

        podcast_info = f"[📻️]({thumbnail_full})  `{name}` \n_by_ {host}\n\n订阅：`{feed}`"
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