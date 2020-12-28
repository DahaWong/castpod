from utils.api_method import search
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
from manifest import manifest
from base64 import urlsafe_b64encode as encode
from utils.url_shortener import shorten

def handle_inline_query(update, context):
    inline_query = update.inline_query
    query_id = inline_query.id 
    query_text = inline_query.query
    user_id = inline_query.from_user.id
    users = context.dispatcher.user_data
    listed_results = []

    deeplinking_root = f"https://t.me/{manifest.bot_id}?start="
    switch_to_login = {}

    if not query_text:
        if user_id not in users.keys():
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
    else:
        searched_results = search(query_text) # 需要缓存搜索结果⚠️？

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
                [InlineKeyboardButton('返 回 搜 索 模 式', switch_inline_query_current_chat = query_text)]
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

    bot = context.bot
    bot.answer_inline_query(
        query_id, 
        listed_results,
        **switch_to_login
    )
