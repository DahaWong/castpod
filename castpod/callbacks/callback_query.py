from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from castpod.components import PodcastPage, ManagePage
from castpod.models import User, Podcast
from castpod.utils import delete_manage_starter, save_manage_starter, generate_opml, delete_update_message
from castpod.callbacks.command import help
from config import manifest
import re


def delete_message(update, context):
    context.dispatcher.run_async(update.callback_query.delete_message)


def logout(update, context):
    context.dispatcher.run_async(
        update.callback_query.edit_message_text,
        text="注销账号之前，也许希望先导出订阅数据？",
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
    if message.text:
        deleting_note = run_async(message.edit_text, "注销中…").result()
        user.delete()
        run_async(deleting_note.delete)
        run_async(
            bot.send_message,
            chat_id=user.user_id,
            text='账号已注销，感谢这段时间的使用',
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    '重新开始', url=f"https://t.me/{manifest.bot_id}?start=login")
            )
        )
    else:
        user.delete()
    run_async(delete_manage_starter, context)
    context.chat_data.clear()
    context.user_data.clear()

# Podcast


def fav_podcast(update, context):
    toggle_fav_podcast(update, context, to="fav")


def unfav_podcast(update, context):
    toggle_fav_podcast(update, context, to="unfav")


def toggle_fav_podcast(update, context, to: str):
    query = update.callback_query
    user = User.objects.get(user_id=update.effective_user.id)
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
    podcast_id = re.match(r'unsubscribe_podcast_(.+)', query.data)[1]
    podcast_name = Podcast.objects(id=podcast_id).only('name').first().name
    run_async(
        query.message.edit_text,
        text=f"确认退订 {podcast_name} 吗？",
        reply_markup=InlineKeyboardMarkup.from_row([
            InlineKeyboardButton(
                "返回", callback_data=f"back_to_actions_{podcast_id}"),
            InlineKeyboardButton("退订", callback_data=f"confirm_unsubscribe_{podcast_id}")]
        )
    )
    run_async(query.answer, f"退订后，未来将不会收到 {podcast_name} 的更新。")


def confirm_unsubscribe(update, context):
    run_async = context.dispatcher.run_async
    query = update.callback_query
    podcast_id = re.match(r'confirm_unsubscribe_(.+)', query.data)[1]
    user = User.objects.get(user_id=query.from_user.id)
    podcast = Podcast.objects.get(id=podcast_id)
    user.unsubscribe(podcast)

    manage_page = ManagePage(
        podcasts=Podcast.subscribe_by(user, 'name'),
        text=f'`{podcast.name}` 退订成功'
    )
    run_async(query.message.delete)
    msg = run_async(
        context.bot.send_message,
        chat_id=user.id,
        text=manage_page.text,
        reply_markup=ReplyKeyboardMarkup(
            manage_page.keyboard(), resize_keyboard=True, one_time_keyboard=True)
    ).result()

    save_manage_starter(context.chat_data, msg)


def back_to_actions(update, context):
    query = update.callback_query
    user = User.objects.get(user_id=query.from_user.id)
    podcast_id = re.match(r'back_to_actions_(.+)', query.data)[1]
    podcast = Podcast.objects.get(id=podcast_id)
    if user in podcast.fav_subscribers:
        page = PodcastPage(podcast, fav_text="⭐️",
                           fav_action="unfav_podcast")
    else:
        page = PodcastPage(podcast)
    context.dispatcher.run_async(
        query.edit_message_text,
        text=page.text(),
        reply_markup=InlineKeyboardMarkup(
            page.keyboard()),
        parse_mode="HTML"
    )


def export(update, context):
    run_async = context.dispatcher.run_async
    user = User.validate_user(update.effective_user)
    message = update.callback_query.message
    podcasts = Podcast.objects(subscribers__in=[user])
    if not podcasts:
        run_async(message.reply_text, '还没有订阅播客，请先订阅再导出')
        return
    subscribed_podcasts = Podcast.subscribe_by(user)
    run_async(
        message.reply_document,
        filename=f"{user.username} 的 {manifest.name} 订阅.xml",
        document=generate_opml(user, subscribed_podcasts),
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                '注销账号', callback_data='delete_account')
        )
    )

# Help
def logout(update, context):
    keyboard = [[InlineKeyboardButton("返回", callback_data=f"back_to_help"),
                 InlineKeyboardButton("注销", callback_data="logout")]]

    update.callback_query.edit_message_text(
        "确认注销账号吗？\n",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # Tips('logout', "⦿ 这将清除所有存储在后台的个人数据。").send(update, context)


def settings(update, context):
    keyboard = [[InlineKeyboardButton('显示设置', callback_data="display_setting")], [
        InlineKeyboardButton('返回', callback_data="back_to_help")]]
    msg = context.dispatcher.run_async(
        update.callback_query.edit_message_text,
        text=f'已启动设置面板',
        reply_markup=InlineKeyboardMarkup(keyboard)
    ).result()
    save_manage_starter(context.chat_data, msg)


def about(update, context):
    keyboard = [[InlineKeyboardButton("源代码", url=manifest.repo),
                 InlineKeyboardButton("工作室", url=manifest.author_url)],
                [InlineKeyboardButton('返回', callback_data="back_to_help")]
                ]
    context.dispatcher.run_async(
        update.callback_query.edit_message_text,
        text=(
            f"*{manifest.name}*  "
            f"`{manifest.version}`"
            f"\nby [{manifest.author}](https://t.me/{manifest.author_id})\n"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def back_to_help(update, context):
    context.dispatcher.run_async(
        update.callback_query.edit_message_text,
        text=f"*{manifest.name} 使用说明*\n\n",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("导出播客", callback_data="export"),
             InlineKeyboardButton('偏好设置', callback_data="settings")],
            [InlineKeyboardButton('注销账号', callback_data="logout"),
             InlineKeyboardButton('更多信息', callback_data="about")]
        ])
    )
