from utils.parser import parse_opml
from models import Podcast
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove

def save_subscription(update, context):
    user = context.user_data['user']
    cached_podcasts = context.bot_data['podcasts']

    doc = update['message']['document']
    doc_name, doc_file = doc['file_name'], context.bot.getFile(doc['file_id'])
    path = doc_file.download(f"public/subscriptions/{user.user_id}.xml")

    with open(path, 'r') as f:
        feeds = parse_opml(f)

    podcasts = []
    for feed in feeds:
        if feed['name'] not in cached_podcasts.keys():
            podcast = Podcast(feed['url'])
            if podcast.name:
                cached_podcasts.update({podcast.name: podcast})
        else:
            podcast = cached_podcasts[feed['name']]
        podcasts.append(podcast)
    user.import_feeds(podcasts)


def save_feed(update, context):
    context.bot.send_chat_action(
        chat_id = update.message.chat_id, 
        action = 'typing'
    )
    user = context.user_data['user']
    podcasts = context.bot_data['podcasts']
    url = update['message']['text']
    new_podcast = user.add_feed(url)

    # 检查播客是否存在、添加新播客的逻辑可以复用。应该重构出来。
    if new_podcast.name not in podcasts.keys():
        podcasts.update({new_podcast.name:new_podcast})

    new_podcast.subscribers.add(user.user_id)

    update.message.reply_text(f"成功订阅 {new_podcast.name}！")

def handle_exit(update, context):
    text = update.message.text
    user = context.user_data['user']
    print(user.subscription.keys())

    if text == '退出播客管理':
        update.message.reply_text('已退出 /manage 模式', reply_markup = ReplyKeyboardRemove())
    elif text == '退出偏好设置':
        update.message.reply_text('已退出 /settings 模式', reply_markup = ReplyKeyboardRemove())
    else:
        pass