from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from castpod.components import PodcastPage, ManagePage
from castpod.models import User, Podcast
from castpod.utils import delete_manage_starter, save_manage_starter, generate_opml
from .command import settings as command_settings
from .command import help_ as command_help
from config import manifest
from ..constants import TICK_MARK
import re


def delete_message(update, context):
    context.dispatcher.run_async(update.callback_query.delete_message)


def logout(update, context):
    context.dispatcher.run_async(
        update.callback_query.edit_message_text,
        text="注销账号之前，也许您希望先导出订阅数据？",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "不，直接注销", callback_data="confirm_delete_account"),
            InlineKeyboardButton(
                "导出订阅", callback_data="export_before_logout")], [
            InlineKeyboardButton(
                "返回", callback_data="back_to_help")
        ]])
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
            text='账号已注销，感谢您这段时间的使用！',
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


def export_before_logout(update, context):
    run_async = context.dispatcher.run_async
    user = User.validate_user(update.effective_user)
    message = update.callback_query.message
    podcasts = Podcast.objects(subscribers__in=[user])
    if not podcasts:
        run_async(message.reply_text, '还没有订阅播客，请先订阅后导出~')
        return
    subscribed_podcasts = Podcast.subscribe_by(user)
    run_async(
        message.reply_document,
        filename=f"{user.username} 的 {manifest.name} 订阅.xml",
        document=generate_opml(user, subscribed_podcasts),
        reply_markup=InlineKeyboardMarkup.from_column(
            [InlineKeyboardButton("继续注销账号", callback_data="confirm_delete_account"),
             InlineKeyboardButton(
                 "返回帮助界面", callback_data="back_to_help")
             ])
    )
    message.delete()


def export(update, context):
    run_async = context.dispatcher.run_async
    user = User.validate_user(update.effective_user)
    message = update.callback_query.message
    podcasts = Podcast.objects(subscribers__in=[user])
    if not podcasts:
        run_async(message.reply_text, '还没有订阅播客，请先订阅后导出~')
        return
    subscribed_podcasts = Podcast.subscribe_by(user)
    run_async(
        message.reply_document,
        filename=f"{user.username} 的 {manifest.name} 订阅.xml",
        document=generate_opml(user, subscribed_podcasts)
    )

# Help


def confirm_delete_account(update, context):
    keyboard = [[InlineKeyboardButton("注销", callback_data="delete_account"),
                 InlineKeyboardButton("返回", callback_data=f"back_to_help")]]

    update.callback_query.edit_message_text(
        "确认注销账号吗？该操作将会*清除您的全部数据*\n",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # Tips('logout', "⦿ 这将清除所有存储在后台的个人数据。").send(update, context)


def back_to_help(update, context):
    command_help(update, context)

# settings
def settings(update, context):
    command_settings(update, context)

def display_setting(update, context):
    context.dispatcher.run_async(
        update.callback_query.edit_message_text,
        text=f"点击修改外观设置：",
        reply_markup=InlineKeyboardMarkup.from_column(
            [InlineKeyboardButton(f"显示时间线    {TICK_MARK}", callback_data="toggle_timeline"),
             InlineKeyboardButton(
                 f'倒序显示单集    {TICK_MARK}', callback_data="toggle_episodes_order"),
             InlineKeyboardButton(
                 '返回', callback_data="settings"),
             ]
        )
    )


def feed_setting(update, context):
    context.dispatcher.run_async(
        update.callback_query.edit_message_text,
        text=f"点击修改推送设置：",
        reply_markup=InlineKeyboardMarkup.from_column(
            [InlineKeyboardButton("更新频率    60 分钟", callback_data="feed_freq"),
             InlineKeyboardButton('返回', callback_data="settings")
             ])
    )


def host_setting(update, context):
    context.dispatcher.run_async(
        update.callback_query.edit_message_text,
        text=f"*主播设置*",
        reply_markup=InlineKeyboardMarkup.from_column(
            [InlineKeyboardButton("申请主播认证", callback_data="request_host"),
             InlineKeyboardButton('返回', callback_data="settings")
             ]
        )
    )


def confirm_host(update, context):
    # re.match ...
    # context.bot.send_message(
    #   chat_id =
    #   text = '恭喜，您已成功通过认证主播的初步审核！\n\n\n\n我们将发送一条最终确认消息到您在其他平台留下的官方联络地址，得到您的回复后即可完成主播认证。请留意您的信箱 :)
    # )
    pass


def deny_host(update, context):
    # re.match ...
    # context.bot.send_message(
    #   chat_id =
    #   text = f'我们没能通过收到的图片资料核实您的主播身份，您可以重新发送资料或联系我们：\n\n{dev_email}',
    #   reply_markup = InlineKeyboardMarkup.from_button('重新申请主播认证',callback_data='request_host')
    # )
    pass
