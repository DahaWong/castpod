from utils.persistence import persistence
from utils.parser import parse_opml
from models import Podcast

def save_subscription(update, context):
    user_id = update['message']['from_user']['id']
    user = context.bot_data['users'][user_id]
    cached_podcasts = context.bot_data['podcasts']

    doc = update['message']['document']
    doc_name, doc_file = doc['file_name'], context.bot.getFile(doc['file_id'])
    path = doc_file.download(f"public/subscriptions/{user_id}.xml")

    with open(path, 'r') as f:
        feeds = parse_opml(f)

    podcasts = []
    for feed in feeds:
        if feed['name'] not in cached_podcasts.items():
            podcast = Podcast(**feed)
            cached_podcasts.update({podcast.name: podcast})
        else:
            podcast = cached_podcasts[feed['name']]
        podcasts.append(podcast)

    user.import_feeds(podcasts)
    persistence.flush()


def save_feed(update, context):
    user_id = update['message']['from_user']['id']
    user = context.bot_data['users'][user_id]
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

    user_id = update.message['from_user']['id']
    user = context.bot_data['users'][user_id]

    if text in user.subscription.keys():
        feed_name = text
        feed_info = {"from_user":user, "feed_name":name}
        manage_feed(update, **feed_info)
    else:
        #del msg
        #show alert
        pass


def manage_feed(update, from_user, feed_name):
    # 是否用 conversaion handler?
    feed = from_user.subscription[feed_name]

    keyboard = [[[InlineKeyboardButton("退 订", url = manifest.repo)],[InlineKeyboardButton("喜 欢", url = manifest.author_url)]], # toggle
                [InlineKeyboardButton("关于此节目", url = manifest.author_url)]] # 删除记得加「撤销」

    update.message.reply_text(
        text = "mmm",
        reply_markup = InlineKeyboardMarkup(keyboard)
    )