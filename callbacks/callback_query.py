from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup
from components import PodcastPage, ManagePage
from manifest import manifest
import re


# Message
def delete_message(update, _):
    update.callback_query.delete_message()


def delete_command_context(update, context):
    pattern = r'(delete_command_context_)([0-9]+)'
    query = update.callback_query
    command_message_id = re.match(pattern, query.data)[2]
    query.delete_message()
    context.bot.delete_message(query.message.chat_id, command_message_id)

# Tips


def close_tips(update, context):
    query = update.callback_query
    pattern = r'close_tips_(\w+)'
    from_command = re.match(pattern, query.data)[1]
    context.user_data['tips'].remove(from_command)
    delete_message(update, context)
    show_tips_alert = 'alert' in context.user_data['tips']
    if show_tips_alert:
        query.answer("阅读完毕，它不会再出现在对话框中～", show_alert=True)
        context.user_data['tips'].remove('alert')

# Account:


def logout(update, _):
    message = update.callback_query.message
    message.edit_text(
        "注销账号之前，您可能希望导出订阅数据？",
        reply_markup=InlineKeyboardMarkup.from_row([
            InlineKeyboardButton("直  接  注  销", callback_data="delete_account"),
            InlineKeyboardButton("导  出  订  阅", callback_data="export")
        ])
    )


def delete_account(update, context):
    user = context.user_data['user']
    message = update.callback_query.message
    deleting_note = message.edit_text("注销中…")
    if user.subscription.values():
        for feed in user.subscription.values():
            if user.user_id in feed.podcast.subscribers:
                feed.podcast.subscribers.remove(user.user_id)
    context.user_data.clear()
    deleting_note.delete()
    context.bot.send_message(
        chat_id=user.user_id,
        text='您的账号已注销～',
        reply_markup=ReplyKeyboardRemove())
    context.bot.send_message(
        chat_id=user.user_id, text="👋️",
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                '重 新 开 始', url=f"https://t.me/{manifest.bot_id}?start=login")
        ))

# Podcast


def subscribe_podcast(update, context):
    pattern = r'(subscribe_podcast_)(.+)'
    query = update.callback_query
    feed = re.match(pattern, query.data)[2]
    context.user['user'].add_feed(feed)


def toggle_save_podcast(update, context, to: str):
    pattern = r'(un)?save_podcast_(.+)'
    query = update.callback_query
    podcast_name = re.match(pattern, query.data)[2]
    podcast = context.bot_data['podcasts'].get(podcast_name)
    kwargs = {}

    if (to == 'saved'):
        kwargs = {
            'save_text': '❤️',
            'save_action': "unsave_podcast"
        }
        context.user_data['saved_podcasts'].update({podcast_name: podcast})
    else:
        context.user_data['saved_podcasts'].pop(podcast_name)

    keyboard = PodcastPage(podcast, **kwargs).keyboard()
    query.edit_message_reply_markup(InlineKeyboardMarkup(keyboard))


def save_podcast(update, context):
    toggle_save_podcast(update, context, to="saved")


def unsave_podcast(update, context):
    toggle_save_podcast(update, context, to="unsaved")


def unsubscribe_podcast(update, _):
    pattern = r'(unsubscribe_podcast_)(.+)'
    query = update.callback_query
    podcast_name = re.match(pattern, query.data)[2]
    update.callback_query.message.edit_text(
        f"确认退订 {podcast_name} ？",
        reply_markup=InlineKeyboardMarkup.from_row([
            InlineKeyboardButton(
                "返回", callback_data=f"back_to_actions_{podcast_name}"),
            InlineKeyboardButton("退订", callback_data="confirm_unsubscribe")]
        )
    )
    update.callback_query.answer((
        f"\n确认退订后，将不会收到 {podcast_name} 的更新。"))


def confirm_unsubscribe(update, context):
    podcast_name = re.match(
        r'确认退订 (.+) ？', update.callback_query.message.text)[1]
    user = context.user_data['user']
    user.subscription.pop(podcast_name)
    update.callback_query.message.delete()
    context.bot_data['podcasts'][podcast_name].subscribers.remove(user.user_id)
    manage_page = ManagePage(
        podcast_names=user.subscription.keys(),
        text=f'`{podcast_name}` 退订成功'
    )
    context.bot.send_message(
        update.callback_query.from_user.id,
        manage_page.text,
        reply_markup=ReplyKeyboardMarkup(
            manage_page.keyboard(), resize_keyboard=True, one_time_keyboard=True)
    )


def back_to_actions(update, context):
    pattern = r'(back_to_actions_)(.+)'
    query = update.callback_query
    podcast_name = re.match(pattern, query.data)[2]
    podcast = context.bot_data['podcasts'].get(podcast_name)
    if podcast_name in context.user_data['saved_podcasts']:
        page = PodcastPage(podcast, save_text="❤️", save_action="unsave_podcast")
    else:
        page = PodcastPage(podcast)
    query.edit_message_text(
        text=page.text(),
        reply_markup=InlineKeyboardMarkup(page.keyboard())
    )


def export(update, context):
    user = context.user_data['user']
    if not user.subscription:
        update.callback_query.message.reply_text('你还没有订阅的播客，请先订阅再导出～')
        return
    update.callback_query.message.reply_document(
        filename=f"{user.name} 的 {manifest.name} 订阅.xml",
        document=user.update_opml(),
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton('彻 底 注 销 账 号', callback_data='delete_account')
        )
    )
