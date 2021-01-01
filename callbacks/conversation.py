import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from models import Episode
from components import PodcastPage

END = -1
ACTIONS, SHOW_EPISODES, UNSUBSCRIBE = range(3)

def pin_message(update, context):
    update.callback_query.pin_message(disable_notification=True)

def unpin_message(update, context):
    update.callback_query.unpin_message()

def subscribe_podcast(update, context):
    pattern = r'(subscribe_podcast_)(.+)'
    query = update.callback_query
    feed = re.match(pattern, query.data)[2]
    context.user['user'].add_feed(feed)

def toggle_like_podcast(update, context, to:str):
    pattern = r'(un)?like_podcast_(.+)'
    query = update.callback_query
    podcast_name = re.match(pattern, query.data)[2]
    podcast = context.bot_data['podcasts'].get(podcast_name)

    if (to == 'liked'):
        pin_method = pin_message
        kwargs = {
            'like_text': '❤️',
            'like_action': "unlike_podcast"            
        }
    elif (to == 'unliked'):
        pin_method = unpin_message
        kwargs = {}

    keyboard = PodcastPage(podcast, **kwargs).keyboard()
    query.edit_message_reply_markup(InlineKeyboardMarkup(keyboard))
    pin_method(update, context)

def like_podcast(update, context):
    toggle_like_podcast(update, context, to="liked")
    return ACTIONS

def unlike_podcast(update, context):
    toggle_like_podcast(update, context, to="unliked")
    return ACTIONS

def unsubscribe_podcast(update, context):
    pattern = r'(unsubscribe_podcast_)(.+)'
    query = update.callback_query
    podcast_name = re.match(pattern, query.data)[2]
    update.callback_query.message.edit_text(
        f"确认退订 {podcast_name} ？", 
        reply_markup = InlineKeyboardMarkup.from_row([
            InlineKeyboardButton("返    回", callback_data=f"back_to_actions_{podcast_name}"), 
            InlineKeyboardButton("退    订", callback_data="confirm_unsubscribe")]
        )
    )
    update.callback_query.answer((
        f"您即将退订播客：{podcast_name}。"
        f"\n\n退订后，您将不再收到该节目的更新。"), show_alert = True)

    return UNSUBSCRIBE

def confirm_unsubscribe(update, context):
    podcast_name = re.match(r'确认退订 (.+) ？', update.callback_query.message.text)[1]
    context.user_data['user'].subscription.pop(podcast_name)
    update.callback_query.message.edit_text(f'已退订`{podcast_name}`')
    return END

def back_to_actions(update, context):
    pattern = r'(back_to_actions_)(.+)'
    query = update.callback_query
    podcast_name = re.match(pattern, query.data)[2]
    podcast = context.bot_data['podcasts'].get(podcast_name)

    page = PodcastPage(podcast)
    query.edit_message_text(
        text = page.text(),
        reply_markup = InlineKeyboardMarkup(page.keyboard())
    )

    return ACTIONS

def show_feed(update, context):
    text = update.message.text
    user = context.user_data['user']
    if text in user.subscription.keys():
        feed_name = text
        feed = context.user_data['user'].subscription[feed_name]
        podcast = feed.podcast
        delete_keyboard = update.message.reply_text(
            text = "OK",
            reply_markup = ReplyKeyboardRemove()
        )
        delete_keyboard.delete()

        page = PodcastPage(podcast)
        update.message.reply_text(
            text = page.text(),
            reply_markup = InlineKeyboardMarkup(page.keyboard())
        )
    return ACTIONS