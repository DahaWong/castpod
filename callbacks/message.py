from utils.persistence import persistence
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
    persistence.flush()


def save_feed(update, context):
    user = context.user_data['user']
    podcasts = context.bot_data['podcasts']

    url = update['message']['text']
    new_podcast = user.add_feed(url)

    # 检查播客是否存在、添加新播客的逻辑可以复用。应该重构出来。
    if new_podcast.name not in podcasts.keys():
        podcasts.update({new_podcast.name:new_podcast})
    new_podcast.subscribers.add(user)

    persistence.flush()


def handle_text(update, context):
    text = update.message.text
    user = context.user_data['user']
    # user = context.bot_data['users'][update.message.from_user['id']]
    print(user.subscription.keys())

    if text in user.subscription.keys():
        feed_name = text
        manage_feed(update, context, feed_name)
    else:
        #del msg
        #show alert
        pass


def manage_feed(update, context, feed_name):
    feed = context.user_data['user'].subscription[feed_name]
    podcast = feed.podcast
    podcast_info = (
        f'[📻️]({podcast.logo_url})  *{podcast.name}*'
        f'\n{podcast.host}'
    )

    will_delete = update.message.reply_text(
        text = "OK.",
        reply_markup = ReplyKeyboardRemove()
    )

    will_delete.delete()

    # ⚠️ Conversation handler here: 
    keyboard = [[InlineKeyboardButton("退    订", callback_data = f"unsubscribe_podcast{podcast.name}"),
                 InlineKeyboardButton("所 有 单 集", callback_data = f"show_episodes{podcast.name}"),
                 InlineKeyboardButton("喜    欢", callback_data = f"like_podcast{podcast.name}"),
               [InlineKeyboardButton("返      回", callback_data= = f"")]],
               [InlineKeyboardButton("关      于", url = podcast.website)]]

    update.message.reply_text(
        text = podcast_info,
        reply_markup = InlineKeyboardMarkup(keyboard)
    )