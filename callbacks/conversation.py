import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from models import Episode

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
        button_text = '  ❤️  '
        callback_data = f"unlike_podcast_{podcast_name}"
    elif (to == 'unliked'):
        pin_method = unpin_message
        button_text = '喜    欢'
        callback_data = f"like_podcast_{podcast_name}"

    message = update.callback_query.message

    keyboard = [[InlineKeyboardButton("退    订", callback_data = f"unsubscribe_podcast_{podcast.name}"),
                 InlineKeyboardButton("所 有 单 集", callback_data = f"show_episodes_{podcast.name}"),
                 InlineKeyboardButton(button_text, callback_data = callback_data)],
                [InlineKeyboardButton("关      于", url = podcast.website)]
    ]

    update.callback_query.edit_message_reply_markup(InlineKeyboardMarkup(keyboard))
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
            InlineKeyboardButton("退    订", callback_data="confirm_unsubscribe"), 
            InlineKeyboardButton("返    回", callback_data=f"back_to_actions_{podcast_name}")]
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

    podcast_info = (
            f'[📻️]({podcast.logo_url})  *{podcast.name}*'
            f'\n_by_  {podcast.host}'
            f'\n信箱： {podcast.email}'
        )

    keyboard = [[InlineKeyboardButton("退    订", callback_data = f"unsubscribe_podcast_{podcast.name}"),
                InlineKeyboardButton("所 有 单 集", callback_data = f"show_episodes_{podcast.name}"),
                InlineKeyboardButton("喜    欢", callback_data = f"like_podcast_{podcast.name}")],
            [InlineKeyboardButton("关      于", url = podcast.website)]]

    update.callback_query.edit_message_text(
        text = podcast_info,
        reply_markup = InlineKeyboardMarkup(keyboard)
    )

    return ACTIONS


def show_episodes(update, context):
    query = update.callback_query
    pattern = r'show_podcast_(.+)_([0-9]+)'
    podcast_name = re.match(pattern, query.data)[1]
    current_page = int(re.match(pattern, query.data)[2])
    podcast = context.bot_data['podcasts'].get(podcast_name)
    episodes = podcast.episodes

    if current_page == 0:
        query.answer("已经在第一页了")
        current_page = 1
    elif current_page == 1:
        query.answer("已回到首页")
    # 根据长度，判断末尾
    keyboard = [[InlineKeyboardButton(f"{episode.title}  {episode.get('itunes_duration')}", 
                callback_data = "show_episode_{episode.title}")] for episode in episodes[10 * (current_page - 1): 10 * current_page]]

    keyboard.append([
        InlineKeyboardButton("prev", callback_data=f"show_podcast_{podcast_name}_{current_page-1}"),
        InlineKeyboardButton("home", callback_data=f"show_podcast_{podcast_name}_1"),
        InlineKeyboardButton("next", callback_data=f"show_podcast_{podcast_name}_{current_page+1}")
    ])

    query.edit_message_text(
        text = f"{podcast_name} 的全部单集如下：",
        reply_markup = InlineKeyboardMarkup(keyboard)
    )
    return ACTIONS
        

def show_feed(update, context):
    text = update.message.text
    user = context.user_data['user']
    if text in user.subscription.keys():
        feed_name = text
        feed = context.user_data['user'].subscription[feed_name]
        podcast = feed.podcast
        podcast_info = (
            f'[📻️]({podcast.logo_url})  *{podcast.name}*'
            f'\n_by_  {podcast.host}'
            f'\n信箱： {podcast.email}'
        )

        delete_keyboard = update.message.reply_text(
            text = "OK",
            reply_markup = ReplyKeyboardRemove()
        )

        delete_keyboard.delete()

        keyboard = [[InlineKeyboardButton("退    订", callback_data = f"unsubscribe_podcast_{podcast.name}"),
                     InlineKeyboardButton("所 有 单 集", callback_data = f"show_podcast_{podcast.name}_1"),
                     InlineKeyboardButton("喜    欢", callback_data = f"like_podcast_{podcast.name}")],
                    [InlineKeyboardButton("关      于", url = podcast.website)]]

        update.message.reply_text(
            text = podcast_info,
            reply_markup = InlineKeyboardMarkup(keyboard)
        )
    return ACTIONS