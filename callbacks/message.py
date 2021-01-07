from utils.parser import parse_opml
from models import Podcast
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup
import re
from components import PodcastPage, ManagePage

def save_subscription(update, context):
    parsing_note = update.message.reply_text("正在解析订阅文件…")
    user = context.user_data['user']
    cached_podcasts = context.bot_data['podcasts']

    doc = update.message['document']
    doc_name, doc_file = doc['file_name'], context.bot.getFile(doc['file_id'])
    path = doc_file.download(f"public/subscriptions/{user.user_id}.xml")

    try:
        with open(path, 'r') as f:
            feeds = parse_opml(f)
    except Exception as e:
        print(e)
        parsing_note.delete()
        update.message.reply_text("订阅失败 :(\n请检查订阅文件是否格式正确/完好无损")
        return
    feeds_count = len(feeds)
    subscribing_note = parsing_note.edit_text(f"订阅中 (0/{feeds_count})")
    podcasts = []
    failed_feeds = []
    for i, feed in enumerate(feeds):
        if feed['name'] not in cached_podcasts.keys():
            try:
                promise = context.dispatcher.run_async(Podcast, feed_url=feed['url'])
                podcast = promise.result()
                if podcast:
                    cached_podcasts.update({podcast.name: podcast})
                    podcasts.append(podcast)
                    subscribing_note = subscribing_note.edit_text(f"订阅中 ({len(podcasts)}/{feeds_count})")
                else:
                    failed_feeds.append(feed['url'])
                    raise Exception(f"Error when adding feed {feed['url']}")
            except Exception as e: 
                print(e)
                failed_feeds.append(feed['url'])
                continue
        else:
            podcast = cached_podcasts[feed['name']]
            podcasts.append(podcast)
            subscribing_note = subscribing_note.edit_text(f"订阅中 ({len(podcasts)}/{feeds_count})")

    while len(podcasts) != len(failed_feeds) + len(podcasts):
        pass
    else:
        if len(podcasts):
            user.import_feeds(podcasts)
            newline = '\n'
            reply = f"成功订阅 {feeds_count} 部播客！" if not len(failed_feeds) else (
                f"成功订阅 {len(podcasts)} 部播客，部分订阅源解析失败。"
                f"\n\n可能损坏的订阅源："
                f"\n{newline.join(['`'+feed+'`' for feed in failed_feeds])}"
            )
        else:
                reply = "订阅失败:( \n\n请检查订阅文件以及其中的订阅源是否受损"

        subscribing_note.edit_text(
            reply, 
            reply_markup = InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    "查 看 订 阅 列 表", 
                    switch_inline_query_current_chat=""
                )
            )
        )

def subscribe_feed(update, context):
    context.bot.send_chat_action(chat_id = update.message.chat_id, action = 'typing')
    feed_url = update['message']['text']
    subscribing_message = update.message.reply_text(f"订阅中，请稍候…")
        
    user = context.user_data['user']
    podcasts = context.bot_data['podcasts']
    podcast = Podcast(feed_url) # 判断是否存在于音乐库中！
    user.add_feed(podcast)
    try:
        manage_page = ManagePage(
            podcast_names = user.subscription.keys(), 
            text = f"`{podcast.name}` 订阅成功！"
        )
        subscribing_message.delete()
        message = update.message
        message.reply_text(
            text = manage_page.text, 
            reply_markup = ReplyKeyboardMarkup(
                manage_page.keyboard(), 
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        podcast_page = PodcastPage(podcast)
        message.reply_text(
            text = podcast_page.text(), 
            reply_markup=InlineKeyboardMarkup(podcast_page.keyboard())
        )
        message.delete()
        podcast.subscribers.add(user.user_id)
        if podcast.name not in podcasts.keys():
            podcasts.update({podcast.name: podcast})
    except Exception as e:
        print(e)
        subscribing_message.edit_text("订阅失败。可能是因为订阅源损坏 :(")

def exit_reply_keyboard(update, context):
    message = update.message
    message.reply_text(
        '好', 
        reply_markup = ReplyKeyboardRemove()
    ).delete()
    message.delete()