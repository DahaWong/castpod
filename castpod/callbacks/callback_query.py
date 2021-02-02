from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup
from castpod.components import PodcastPage, ManagePage
from castpod.utils import toggle_save_podcast
from castpod.models import User
from config import manifest
import re


def delete_command_context(update, context):
    run_async = context.dispatcher.run_async
    pattern = r'(delete_command_context_)([0-9]+)'
    query = update.callback_query
    command_message_id = re.match(pattern, query.data)[2]
    run_async(context.bot.delete_message,
              query.message.chat_id,
              command_message_id
    )
    run_async(query.delete_message)


# Account:


def logout(update, context):
    context.dispatcher.run_async(
        update.callback_query.edit_message_text,
        text="注销账号之前，您可能希望导出订阅数据？",
        reply_markup=InlineKeyboardMarkup.from_row([
            InlineKeyboardButton(
                "直  接  注  销", callback_data="delete_account"),
            InlineKeyboardButton(
                "导  出  订  阅", callback_data="export")
        ])
    )


def delete_account(update, context):
    run_async = context.dispatcher.run_async
    bot = context.bot
    message = update.callback_query.message
    user = User.objects(user_id=message.from_user.id)
    deleting_note = run_async(message.edit_text, "注销中…").result()
    user.delete()
    context.user_data.clear()
    run_async(deleting_note.delete)
    run_async(bot.send_message,
              chat_id=user.user_id,
              text='您的账号已注销～',
              reply_markup=ReplyKeyboardRemove()
              )
    run_async(bot.send_message,
              chat_id=user.user_id, text="👋️",
              reply_markup=InlineKeyboardMarkup.from_button(
                  InlineKeyboardButton(
                      '重新开始', url=f"https://t.me/{manifest.bot_id}?start=login")
              )
    )

# Podcast


def subscribe_podcast(update, context):
    feed = re.match(r'(subscribe_podcast_)(.+)', update.callback_query.data)[2]
    context.user['user'].add_feed(feed)


def save_podcast(update, context):
    toggle_save_podcast(update, context, to="saved")


def unsave_podcast(update, context):
    toggle_save_podcast(update, context, to="unsaved")


def unsubscribe_podcast(update, context):
    run_async = context.dispatcher.run_async
    query = update.callback_query
    podcast_name = re.match(r'(unsubscribe_podcast_)(.+)', query.data)[2]
    run_async(
        query.message.edit_text,
        text=f"确认退订 {podcast_name} 吗？",
        reply_markup=InlineKeyboardMarkup.from_row([
            InlineKeyboardButton(
                "返回", callback_data=f"back_to_actions_{podcast_name}"),
            InlineKeyboardButton("退订", callback_data="confirm_unsubscribe")]
        )
    )
    run_async(query.answer, f"退订后，您将不会收到 {podcast_name} 的更新。")


def confirm_unsubscribe(update, context):
    run_async = context.dispatcher.run_async
    podcast_name = re.match(
        r'确认退订 (.+) 吗？', update.callback_query.message.text)[1]
    user = context.user_data['user']
    user.subscription.pop(podcast_name)

    context.bot_data['podcasts'][podcast_name].subscribers.remove(user.user_id)
    manage_page = ManagePage(
        podcast_names=user.subscription.keys(),
        text=f'`{podcast_name}` 退订成功'
    )
    run_async(update.callback_query.message.delete())
    run_async(
        context.bot.send_message,
        chat_id=update.callback_query.from_user.id,
        text=manage_page.text,
        reply_markup=ReplyKeyboardMarkup(
            manage_page.keyboard(), resize_keyboard=True, one_time_keyboard=True)
    )


def back_to_actions(update, context):
    pattern = r'(back_to_actions_)(.+)'
    query = update.callback_query
    podcast_name = re.match(pattern, query.data)[2]
    podcast = context.bot_data['podcasts'].get(podcast_name)
    if podcast_name in context.user_data['saved_podcasts']:
        page = PodcastPage(podcast, save_text="⭐️",
                           save_action="unsave_podcast")
    else:
        page = PodcastPage(podcast)
    context.dispatcher.run_async(
        query.edit_message_text,
        text=page.text(),
        reply_markup=InlineKeyboardMarkup(
            page.keyboard())
    )


def export(update, context):
    run_async = context.dispatcher.run_async
    user = context.user_data['user']
    message = update.callback_query.message
    if not user.subscription:
        run_async(message.reply_text, '您还没有订阅播客，请先订阅再导出～')
        return
    run_async(
        message.reply_document,
        filename=f"{user.name} 的 {manifest.name} 订阅.xml",
        document=user.update_opml(),
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                '注销账号', callback_data='delete_account')
        )
    )
