from utils.parser import parse_opml
from models import Podcast
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
import re
from components import PodcastPage

def save_subscription(update, context):
    context.bot.send_chat_action(update.message.chat_id, "typing")
    subscribing_note = update.message.reply_text("订阅中，请稍等片刻…")
    user = context.user_data['user']
    cached_podcasts = context.bot_data['podcasts']

    doc = update['message']['document']
    doc_name, doc_file = doc['file_name'], context.bot.getFile(doc['file_id'])
    path = doc_file.download(f"public/subscriptions/{user.user_id}.xml")

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
    feeds_count = len(feeds)

    for i, feed in enumerate(feeds):
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
    user.import_feeds(podcasts)
    
    subscribing_note.delete()
    if len(podcasts):
        newline = '\n'
        reply = f"成功订阅 {feeds_count} 部播客！" if not len(failed_feeds) else (
            f"成功订阅 {len(podcasts)} 部播客，部分订阅源解析失败。"
            f"\n\n可能损坏的订阅源："
            f"\n{newline.join(['`'+feed+'`' for feed in failed_feeds])}"
        )
    else:
        reply = "订阅失败:( \n\n请检查订阅文件以及其中的订阅源是否受损"

    update.message.reply_text(
        reply, 
        reply_markup = InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                "查 看 订 阅 列 表", 
                switch_inline_query_current_chat="podcasts page 1"
            )
        )
    )

def subscribe_feed(update, context):
    context.bot.send_chat_action(chat_id = update.message.chat_id, action = 'typing')
    feed = update.message.text
    subscribing_message = update.message.reply_text(f"订阅中，请稍候…")
    user = context.user_data['user']
    podcasts = context.bot_data['podcasts']
    promise = context.dispatcher.run_async(user.add_feed, url = feed)
    if promise.done:
        try:
            new_podcast = promise.result()
            success_note = subscribing_message.edit_text("订阅成功！")
            update.message.delete()
            page = PodcastPage(new_podcast)
            success_note.edit_text(page.text(), reply_markup=InlineKeyboardMarkup(page.keyboard()))
            new_podcast.subscribers.add(user.user_id)
            if new_podcast.name not in podcasts.keys():
                podcasts.update({new_podcast.name:new_podcast})
        except:
            subscribing_message.edit_text("订阅失败。可能是因为订阅源损坏 :(")

def exit_reply_keyboard(update, context):
    message = update.message
    message.reply_text(
        '好', 
        reply_markup = ReplyKeyboardRemove()
    ).delete()
    message.delete()