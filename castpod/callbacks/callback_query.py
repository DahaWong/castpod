from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup
from castpod.components import PodcastPage, ManagePage
from castpod.models import User, Podcast
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
                "直接注销", callback_data="delete_account"),
            InlineKeyboardButton(
                "导出订阅", callback_data="export")
        ])
    )


def delete_account(update, context):
    run_async = context.dispatcher.run_async
    bot = context.bot
    message = update.callback_query.message
    user = User.validate_user(update.effective_user)
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


def fav_podcast(update, context):
    toggle_fav_podcast(update, context, to="fav")


def unfav_podcast(update, context):
    toggle_fav_podcast(update, context, to="unfav")


def toggle_fav_podcast(update, context, to: str):
    query = update.callback_query
    user = User.objects(user_id=update.effective_user.id).only(
        'subscriptions').first()
    podcast_id = re.match(
        r'(un)?fav_podcast_(.+)',
        query.data
    )[2]
    podcast = Podcast.objects.get(id=podcast_id)
    kwargs = {}

    if (to == 'fav'):
        kwargs = {
            'fav_text': '⭐️',
            'fav_action': "unfav_podcast"
        }

    user.toggle_fav(podcast)
    keyboard = PodcastPage(podcast, **kwargs).keyboard()
    context.dispatcher.run_async(
        query.edit_message_reply_markup,
        InlineKeyboardMarkup(keyboard)
    )


def unsubscribe_podcast(update, context):
    run_async = context.dispatcher.run_async
    query = update.callback_query
    podcast_id = re.match(r'(unsubscribe_podcast_)(.+)', query.data)[2]
    podcast_name = Podcast.objects(id=podcast_id).only('name').name
    run_async(
        query.message.edit_text,
        text=f"确认退订 {podcast_name} 吗？",
        reply_markup=InlineKeyboardMarkup.from_row([
            InlineKeyboardButton(
                "返回", callback_data=f"back_to_actions_{podcast_id}"),
            InlineKeyboardButton("退订", callback_data="confirm_unsubscribe_{podcast_id}")]
        )
    )
    run_async(query.answer, f"退订后，您将不会收到 {podcast_name} 的更新。")


def confirm_unsubscribe(update, context):
    run_async = context.dispatcher.run_async
    query = update.callback_query
    podcast_id = re.match(r'(confirm_unsubscribe_)(.+)', query.data)[2]
    user = User.objects.get(user_id=query.from_user.id)
    podcast = Podcast.objects.get(id=podcast_id)
    user.unsubscribe(podcast)

    manage_page = ManagePage(
        podcasts=Podcast.of_subscriber(user, subsets='name'),
        text=f'`{podcast.name}` 退订成功'
    )
    run_async(query.message.delete)
    run_async(
        context.bot.send_message,
        chat_id=user.id,
        text=manage_page.text,
        reply_markup=ReplyKeyboardMarkup(
            manage_page.keyboard(), resize_keyboard=True, one_time_keyboard=True)
    )


def back_to_actions(update, context):
    query = update.callback_query
    user = User.objects.get(user_id=query.from_user.id)
    podcast_id = re.match(r'(back_to_actions_)(.+)', query.data)[2]
    podcast = Podcast.objects.get(id=podcast_id)
    if user.subscriptions.get(podcast=podcast).is_fav:
        page = PodcastPage(podcast, fav_text="⭐️",
                           fav_action="unfav_podcast")
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
    # ⚠️ 简化 userid 的获得，也许 update.effective_user 就可以:
    user = User.validate_user(update.effective_user)
    message = update.callback_query.message
    if not user.subscriptions:
        run_async(message.reply_text, '您还没有订阅播客，请先订阅再导出～')
        return
    run_async(
        message.reply_document,
        filename=f"{user.name} 的 {manifest.name} 订阅.xml",
        document=user.generate_opml(),
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                '注销账号', callback_data='delete_account')
        )
    )
