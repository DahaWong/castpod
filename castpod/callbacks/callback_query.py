from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from castpod.components import PodcastPage, ManagePage
from castpod.models import User, Podcast, Episode
from castpod.utils import delete_manage_starter, save_manage_starter, generate_opml
from .command import help_ as command_help
from config import manifest
from ..constants import TICK_MARK, STAR_MARK
from datetime import date
import re


async def delete_message(update, context):
    await update.callback_query.delete_message()


async def logout(update, context):
    await update.callback_query.edit_message_text(text="注销账号之前，也许您希望先导出订阅数据？", reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "不，直接注销", callback_data="confirm_delete_account"),
        InlineKeyboardButton(
            "导出订阅", callback_data="export_before_logout")], [
        InlineKeyboardButton(
            "返回", callback_data="back_to_help")
    ]]))


async def delete_account(update, context):
    bot = context.bot
    message = update.callback_query.message
    user = User.validate_user(update.effective_user)
    if message.text:
        deleting_note = await message.edit_text("注销中…")
        user.delete()
        await deleting_note.delete()
        await bot.send_message(
            chat_id=user.user_id,
            text='账号已注销，感谢您这段时间的使用！',
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    '重新开始', url=f"https://t.me/{manifest.bot_id}?start=login")
            ))
    else:
        user.delete()
    await delete_manage_starter(context)
    context.chat_data.clear()
    context.user_data.clear()

# Podcast


async def fav_ep(update, context):
    query = update.callback_query
    episode_id = re.match(
        r'fav_ep_(.+)',
        query.data
    )[1]
    episode = Episode.objects.get(id=episode_id)
    podcast = episode.from_podcast
    user = User.objects.get(user_id=update.effective_user.id)
    user.fav_ep(episode)
    await query.edit_message_reply_markup(
        InlineKeyboardMarkup([[InlineKeyboardButton('❤️', callback_data=f'unfav_ep_{episode_id}')], [
            InlineKeyboardButton(
                "订阅列表", switch_inline_query_current_chat=""),
            InlineKeyboardButton(
                "单集列表", switch_inline_query_current_chat=f"{podcast.name}#")
        ]])
    )
    await update.effective_message.pin()


async def unfav_ep(update, context):
    query = update.callback_query
    episode_id = re.match(
        r'unfav_ep_(.+)',
        query.data
    )[1]
    episode = Episode.objects.get(id=episode_id)
    podcast = episode.from_podcast
    user = User.objects.get(user_id=update.effective_user.id)
    user.unfav_ep(episode)
    await query.edit_message_reply_markup(
        InlineKeyboardMarkup([[InlineKeyboardButton('收藏', callback_data=f'fav_ep_{episode_id}')], [
            InlineKeyboardButton(
                "订阅列表", switch_inline_query_current_chat=""),
            InlineKeyboardButton(
                "单集列表", switch_inline_query_current_chat=f"{podcast.name}#")
        ]]))
    await update.effective_message.unpin()


async def fav_podcast(update, context):
    toggle_fav_podcast(update, context, to="fav")


async def unfav_podcast(update, context):
    toggle_fav_podcast(update, context, to="unfav")


async def toggle_fav_podcast(update, context, to: str):
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
            'fav_text': STAR_MARK,
            'fav_action': "unfav_podcast"
        }

    user.toggle_fav(podcast)
    keyboard = PodcastPage(podcast, **kwargs).keyboard()
    await query.edit_message_reply_markup(InlineKeyboardMarkup(keyboard))


async def unsubscribe_podcast(update, context):
    query = update.callback_query
    podcast_id = re.match(r'unsubscribe_podcast_(.+)', query.data)[1]
    podcast_name = Podcast.objects(id=podcast_id).only('name').first().name
    await query.message.edit_text(
        text=f"确认退订 {podcast_name} 吗？",
        reply_markup=InlineKeyboardMarkup.from_row([
            InlineKeyboardButton(
                "返回", callback_data=f"back_to_actions_{podcast_id}"),
            InlineKeyboardButton("退订", callback_data=f"confirm_unsubscribe_{podcast_id}")]
        ))
    await query.answer(f"退订后，未来将不会收到 {podcast_name} 的更新。")


async def confirm_unsubscribe(update, context):
    query = update.callback_query
    podcast_id = re.match(r'confirm_unsubscribe_(.+)', query.data)[1]
    user = User.objects.get(user_id=query.from_user.id)
    podcast = Podcast.objects.get(id=podcast_id)
    user.unsubscribe(podcast)

    manage_page = ManagePage(
        podcasts=Podcast.subscribe_by(user, 'name'),
        text=f'`{podcast.name}` 退订成功'
    )
    await query.message.delete()
    msg = await context.bot.send_message(
        chat_id=user.id,
        text=manage_page.text,
        reply_markup=ReplyKeyboardMarkup(
            manage_page.keyboard(), resize_keyboard=True, one_time_keyboard=True
        )
    )

    save_manage_starter(context.chat_data, msg)


async def back_to_actions(update, context):
    query = update.callback_query
    user = User.objects.get(user_id=query.from_user.id)
    podcast_id = re.match(r'back_to_actions_(.+)', query.data)[1]
    podcast = Podcast.objects.get(id=podcast_id)
    if user in podcast.starrers:
        page = PodcastPage(podcast, fav_text=STAR_MARK,
                           fav_action="unfav_podcast")
    else:
        page = PodcastPage(podcast)
    await query.edit_message_text(
        text=page.text(),
        reply_markup=InlineKeyboardMarkup(
            page.keyboard()),
        parse_mode="HTML"
    )


async def export_before_logout(update, context):
    user = User.validate_user(update.effective_user)
    message = update.callback_query.message
    podcasts = Podcast.objects(subscribers__in=[user])
    if not podcasts:
        await message.reply_text('还没有订阅播客，请先订阅后导出~')
        return
    subscribed_podcasts = Podcast.subscribe_by(user)
    await message.reply_document(
        filename=f"castpod-{date.today()}.xml",
        document=generate_opml(user, subscribed_podcasts),
        reply_markup=InlineKeyboardMarkup.from_column(
            [InlineKeyboardButton("继续注销账号", callback_data="confirm_delete_account"),
             InlineKeyboardButton(
                 "返回帮助界面", callback_data="back_to_help")
             ])
    )
    await message.delete()


async def export(update, context):
    user = User.validate_user(update.effective_user)
    message = update.callback_query.message
    podcasts = Podcast.objects(subscribers__in=[user])
    if not podcasts:
        await message.reply_text('还没有订阅播客，请先订阅后导出~')
        return
    subscribed_podcasts = Podcast.subscribe_by(user)
    await message.reply_document(
        filename=f"castpod-{date.today()}.xml",
        document=generate_opml(user, subscribed_podcasts)
    )

# Help


async def confirm_delete_account(update, context):
    keyboard = [[InlineKeyboardButton("注销", callback_data="delete_account"),
                 InlineKeyboardButton("返回", callback_data=f"back_to_help")]]

    await update.callback_query.edit_message_text(
        "确认注销账号吗？该操作将会*清除您的全部数据*\n",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # Tips('logout', "⦿ 这将清除所有存储在后台的个人数据。").send(update, context)


async def back_to_help(update, context):
    command_help(update, context)