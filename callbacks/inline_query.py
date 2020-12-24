from utils.api_method import search
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup

def handle_inline_query(update, context):
    inline_query = update.inline_query
    query_id = inline_query.id 
    query_text = inline_query.query
    listed_results = []
    deep_linking_root = "https://t.me/podcasted_bot/start="

    if not query_text:
        listed_results = [InlineQueryResultArticle(
            id='0',
            title="欢迎使用播客搜索功能！",
            input_message_content=InputTextMessageContent("请在对话框输入 `@podcasted_bot 关键词`","MARKDOWN"),
            description="继续输入关键词以检索播客节目"
        )]
    else:
        searched_results = search(query_text) # 需要缓存搜索结果⚠️

        for result in searched_results:
            itunes_id = result['collectionId']
            name = result['collectionName']
            feed = result['feedUrl']
            host = result['artistName']

            # 遍历 local podcasts， 如果没有，自动添加

            discription = ""
            local_id = "" # 需要配置一个本地 id
            logo_url = "" # 头像 

            podcast_info = f" **{name}** \n\n{host} 主持\n\n{discription}"

            keyboard = [[InlineKeyboardButton('订   阅', url=f"{deep_linking_root}{local_id}")]]
            result_item = InlineQueryResultArticle(
                id = itunes_id, 
                title = name, 
                input_message_content = InputTextMessageContent(podcast_info, "MARKDOWN"), 
                reply_markup= InlineKeyboardMarkup(keyboard),
                description = host
            )
            listed_results.append(result_item)

    bot = context.bot
    bot.answer_inline_query(query_id, listed_results)

# def handle_result_chosen(update, context):
#     print('test')
#     print(update)