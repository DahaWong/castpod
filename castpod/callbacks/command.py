from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, InputMediaAudio
from config import manifest
from castpod.models import User, Podcast, Episode
from castpod.components import ManagePage, PodcastPage
from manifest import manifest
from ..constants import RIGHT_SEARCH_MARK, DOC_MARK, STAR_MARK
import re
# Private


async def start(update, context):
    message = update.message
    if User.objects(user_id=update.effective_user.id):
        await message.reply_text('您已经注册过啦，无需接受邀请 :)')
        return
    user = User.validate_user(update.effective_user)
    if context.args and context.args[0] != 'login':
        match = re.match(r'^(u|p)([0-9]*)$', context.args[0])
        id_type, id_value = match[1], int(match[2])
        if id_type == 'u':  # 由其他用户推荐登入
            from_user = User.objects.get(user_id=id_value)
            text = (
                f'您已接受 {from_user.first_name} 的邀请，欢迎使用 {manifest.name}！                                            '
                f'\n\n发送 OPML 文件或者 RSS 链接均可以导入播客订阅。\n'
                f'\n⚠️ 目前还*没有正式上线*，主要的问题是订阅的播客不能获取更新。遇到问题或提供建议请移步[内测聊天室](https://t.me/castpodchat)。'
            )
            await  message.reply_text(
                text=text,
                reply_markup=InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton(
                        '搜索播客', switch_inline_query_current_chat=""
                    )
                )
            )
            return
        elif id_type == 'p':  # 订阅播客
            podcast = Podcast.objects(id=id_value).first()
            if not podcast:
                await update.reply_message(
                    f'抱歉，该播客不存在。如需订阅，请尝试在对话框输入 `@{manifest.bot_id} 播客关键词` 检索。')
                return
            if not user in podcast.subscribers:
                subscribing_note = await update.message.reply_text("正在订阅…")
                user.subscribe(podcast)
                await subscribing_note.delete()
            page = PodcastPage(podcast)
            manage_page = ManagePage(
                Podcast.subscribe_by(user), f'`{podcast.name}` 订阅成功！'
            )
            photo = podcast.logo.file_id or podcast.logo.url
            msg = await message.reply_photo(
                photo=photo,
                caption=page.text(),
                reply_markup=InlineKeyboardMarkup(page.keyboard()),
                parse_mode="HTML"
            )
            podcast.logo.file_id = msg.photo[0].file_id
            podcast.save()

            await update.message.reply_text(
                text=manage_page.text,
                reply_markup=ReplyKeyboardMarkup(manage_page.keyboard())
            )

    else:
        welcome_text = (
            f'欢迎使用 {manifest.name}！                                            '
            f'\n\n发送 OPML 文件或者 RSS 链接均可以导入播客订阅。\n'
            f'\n⚠️ 目前还*没有正式上线*，主要的问题是订阅的播客还不能更新。遇到问题或提供建议请移步[内测聊天室](https://t.me/castpodchat)。'
        )
        await message.reply_text(
            text=welcome_text,
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    '搜索播客', switch_inline_query_current_chat=""
                )
            )
        )


async def manage(update, context):
    user = User.validate_user(update.effective_user)
    page = ManagePage(Podcast.subscribe_by(user, 'name'))
    if context.chat_data.get('reply_keyboard'):
        await context.chat_data['reply_keyboard'].delete()
    msg = await update.message.reply_text(
        text=page.text,
        reply_markup=ReplyKeyboardMarkup(
            page.keyboard(
                null_text='还没有订阅播客～',
                jump_to=STAR_MARK
            ),
            resize_keyboard=True,
            one_time_keyboard=True,
            selective=True
        )
    )
    context.chat_data.update(reply_keyboard=msg)
    await update.message.delete()


async def star(update, context):
    user = User.validate_user(update.effective_user)
    page = ManagePage(Podcast.star_by(user, 'name'), text='已启动收藏面板')
    if context.chat_data.get('reply_keyboard'):
        await context.chat_data['reply_keyboard'].delete()
    msg = await update.message.reply_text(
        text=page.text,
        reply_markup=ReplyKeyboardMarkup(
            page.keyboard(
                null_text='还没有收藏播客～',
                jump_to=DOC_MARK
            ),
            resize_keyboard=True,
            one_time_keyboard=True,
            selective=True
        )
    )
    await update.message.delete()
    context.chat_data.update(reply_keyboard=msg)


async def search(update, context):
    await update.message.reply_text(
        text=RIGHT_SEARCH_MARK,
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton('搜索播客', switch_inline_query_current_chat=''))
    )


async def about(update, context):
    keyboard = [[InlineKeyboardButton("源代码", url=manifest.repo),
                 InlineKeyboardButton("工作室", url=manifest.author_url)]]
    await update.message.reply_text(
        text=(
            f"*{manifest.name}*  "
            f"`{manifest.version}`"
            f"\nby [{manifest.author}](https://t.me/{manifest.author_id})\n"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def favorite(update, context):
    user = User.validate_user(update.effective_user)
    fav_episodes = Episode.objects(starrers=user)
    if len(fav_episodes) == 1:
        await update.message.reply_audio(
            audio=fav_episodes.first().file_id
        )
    elif len(fav_episodes) >= 2 and len(fav_episodes) <= 5:
        await update.message.reply_media_group(
            media=list(map(lambda episode: InputMediaAudio(
                media=episode.file_id
            ), fav_episodes))
        )
    elif len(fav_episodes) > 5:
        #!!!
        await update.message.reply_media_group(
            media=list(map(lambda x: InputMediaAudio(x.file_id), fav_episodes))
        )
    else:
        await update.message.reply_text(
            text='还没有收藏的单集～',
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton('订阅列表', switch_inline_query_current_chat=''))
        )


async def share(update, context):
    await update.message.reply_text(
        text='💌',
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton('分享播客', switch_inline_query=''))
    )


async def wander(update, context):
    await update.message.reply_text(
        '功能开发中，敬请等待！', reply_to_message_id=update.effective_message.message_id)


async def help_(update, context):
    message = update.message
    text_handler = message.reply_text if message else update.callback_query.edit_message_text
    await text_handler(
        text=f"[{manifest.name} 入门指南](https://github.com/DahaWong/castpod/wiki/%E5%85%A5%E9%97%A8%E6%8C%87%E5%8D%97)\n\n",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('注销账号', callback_data="logout"),
             InlineKeyboardButton('导出订阅', callback_data="export")]]
        )
    )


async def invite(update, context):
    await update.message.reply_text(
        text=f"邀请你的伙伴一起听播客！",
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                '呼朋唤友', switch_inline_query=f"#invite"
            )
        )
    )
