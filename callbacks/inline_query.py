from utils.api_method import search
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup

def handle_inline_query(update, context):
    inline_query = update.inline_query
    query_id = inline_query.id 
    query_text = inline_query.query
    user_id = inline_query.from_user.id
    users = context.bot_data['users']
    listed_results = []

    deep_linking_root = "https://t.me/podcasted_bot/start="
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
                input_message_content = InputTextMessageContent("点击下方按钮开始搜索播客"),
                reply_markup = InlineKeyboardMarkup(keyboard)
            )]
    else:
        searched_results = search(query_text) # 需要缓存搜索结果⚠️？

        for result in searched_results:
            itunes_id = result['collectionId']
            name = result['collectionName']
            feed = result['feedUrl']
            host = result['artistName']

            # 遍历 local podcasts， 如果没有，自动添加

            discription = ""
            local_id = "" # 需要配置一个本地 id
            logo_url = "" # 头像 

            podcast_info = f"主播：**{name}** \n\n{host}\n\n{discription}"

            keyboard = [[InlineKeyboardButton('返   回', switch_inline_query_current_chat = query_text),
                         InlineKeyboardButton('订   阅', url=f"{deep_linking_root}{local_id}")]]

            result_item = InlineQueryResultArticle(
                id = itunes_id, 
                title = name, 
                input_message_content = InputTextMessageContent(podcast_info), 
                reply_markup= InlineKeyboardMarkup(keyboard),
                description = host
            )
            listed_results.append(result_item)

    bot = context.bot
    bot.answer_inline_query(
        query_id, 
        listed_results,
        **switch_to_login
    )
