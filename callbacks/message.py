from utils.parser import parse_opml
from models import Podcast
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove

def save_subscription(update, context):
    context.bot.send_chat_action(update.message.chat_id, "typing")
    subscribing_note = update.message.reply_text("订阅中，请稍等片刻…")
    user = context.user_data['user']
    cached_podcasts = context.bot_data['podcasts']

    doc = update['message']['document']
    print(doc)
    doc_name, doc_file = doc['file_name'], context.bot.getFile(doc['file_id'])
    print(doc_file)
    path = doc_file.download(f"public/subscriptions/{user.user_id}.xml")
    print(path)

    try:
        with open(path, 'r') as f:
            feeds = parse_opml(f)
    except Exception as e:
        print(e)
        subscribing_note.delete()
        update.message.reply_text("订阅失败 :(\n请检查订阅文件是否格式正确/完好无损")
        return

    podcasts = []
    failed_feeds = []

    for feed in feeds:
        if feed['name'] not in cached_podcasts.keys():
            try:
                podcast = Podcast(feed['url'])
                cached_podcasts.update({podcast.name: podcast})
            except Exception as e: 
                print(e)
                failed_feeds.append(feed['url'])
                continue
        else:
            podcast = cached_podcasts[feed['name']]
        podcasts.append(podcast)
    print(podcasts)
    user.import_feeds(podcasts)
    
    subscribing_note.delete()
    if len(podcasts):
        newline = '\n'
        reply = f"成功订阅 {len(podcasts)} 部播客！" if not len(failed_feeds) else (
            f"成功订阅 {len(podcasts)} 部播客，部分订阅源解析失败。"
            f"\n\n可能损坏的订阅源："
            f"\n{newline.join(['`'+feed+'`' for feed in failed_feeds])}"
        )
    else:
        reply = "订阅失败。请检查订阅文件以及其中的订阅源是否受损 :("

    update.message.reply_text(
        reply, 
        reply_markup = InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                "查 看 订 阅 列 表", 
                switch_inline_query_current_chat="podcasts page 1"
            )
        )
    )

def save_feed(update, context):
    subscribing_message = update.message.reply_text(f"订阅中，请稍候…")
    context.bot.send_chat_action(chat_id = update.message.chat_id, action = 'typing')
    user = context.user_data['user']
    podcasts = context.bot_data['podcasts']
    url = update['message']['text']
    promise = context.dispatcher.run_async(user.add_feed, url = url)
    if promise.done:
        try:
            new_podcast = promise.result()  
            subscribing_message.delete()
            update.message.reply_text(
                f"成功订阅播客：`{new_podcast.name}`",
                reply_markup = InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton(
                        "查  看  单  集", 
                        switch_inline_query_current_chat = f"episodes {new_podcast.name} page 1"
                    ))
                )
            new_podcast.subscribers.add(user.user_id)
            if new_podcast.name not in podcasts.keys():
                podcasts.update({new_podcast.name:new_podcast})
        except:
            update.message.reply_text("订阅失败，这可能是订阅源损坏造成的 :(")

def handle_exit(update, context):
    exit_command = update.message.text
    if exit_command == '退出播客管理':
        update.message.reply_text('已退出 /manage 模式', reply_markup = ReplyKeyboardRemove())
    elif exit_command == '退出偏好设置':
        update.message.reply_text('已退出 /settings 模式', reply_markup = ReplyKeyboardRemove())
