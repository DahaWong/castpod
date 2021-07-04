from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, InputMediaAudio
from config import manifest
from castpod.models import User, Podcast, Episode
from castpod.components import ManagePage, PodcastPage
from castpod.utils import save_manage_starter, delete_update_message, delete_manage_starter
from manifest import manifest
from ..constants import RIGHT_SEARCH_MARK, DOC_MARK
import re
# Private


@delete_update_message
def start(update, context):
    run_async = context.dispatcher.run_async
    message = update.message
    user = User.validate_user(update.effective_user)

    if context.args and context.args[0] != 'login':
        if re.match(r'^via_.*$', context.args[0]):
            user_id = context.args[0][4:]
            from_user = User.objects.get(id=user_id).only('bonus')
            from_user.update(inc__bonus=10)
            welcome_text = (
                f'欢迎使用 {manifest.name}！                                            '
                f'\n\n您可以发送 OPML 文件或 RSS 链接以*导入播客订阅*。\n'
                f'\n⚠️ 目前还*没有正式上线*，主要的问题是订阅的播客还不能更新。遇到问题或提供建议请移步[内测聊天室](https://t.me/castpodchat)。'
            )
            run_async(
                message.reply_text,
                text=welcome_text,
                reply_markup=InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton(
                        '搜索播客', switch_inline_query_current_chat=""
                    )
                )
            )
            return
        podcast_id = context.args[0]
        podcast = Podcast.objects(id=podcast_id).first()
        if not podcast:
            update.reply_message(
                f'抱歉，该播客不存在。如需订阅，请尝试在对话框输入 `@{manifest.bot_id} 播客关键词` 检索。')
            return
        if not user in podcast.subscribers:
            subscribing_note = run_async(
                update.message.reply_text, "正在订阅…").result()
            user.subscribe(podcast)
            run_async(subscribing_note.delete)
        page = PodcastPage(podcast)
        manage_page = ManagePage(
            Podcast.subscribe_by(user), f'`{podcast.name}` 订阅成功！'
        )
        photo = podcast.logo.file_id or podcast.logo.url
        msg = run_async(message.reply_photo,
                        photo=photo,
                        caption=page.text(),
                        reply_markup=InlineKeyboardMarkup(page.keyboard()),
                        parse_mode="HTML"
                        ).result()
        podcast.logo.file_id = msg.photo[0].file_id
        podcast.save()

        run_async(
            update.message.reply_text,
            text=manage_page.text,
            reply_markup=ReplyKeyboardMarkup(manage_page.keyboard())
        )

    else:
        welcome_text = (
            f'欢迎使用 {manifest.name}！                                            '
            f'\n\n您可以发送 OPML 文件或 RSS 链接以*导入播客订阅*。\n'
            f'\n⚠️ 目前还*没有正式上线*，主要的问题是订阅的播客还不能更新。遇到问题或提供建议请移步[内测聊天室](https://t.me/castpodchat)。'
        )
        run_async(
            message.reply_text,
            text=welcome_text,
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    '搜索播客', switch_inline_query_current_chat=""
                )
            )
        )


@delete_update_message
def manage(update, context):
    run_async = context.dispatcher.run_async
    user = User.validate_user(update.effective_user)

    page = ManagePage(Podcast.subscribe_by(user, 'name'))
    msg = run_async(
        update.effective_message.reply_text,
        text=page.text,
        reply_markup=ReplyKeyboardMarkup(
            page.keyboard(), resize_keyboard=True, one_time_keyboard=True, selective=True)
    ).result()
    delete_manage_starter(context)
    save_manage_starter(context.chat_data, msg)


@delete_update_message
def star(update, context):
    run_async = context.dispatcher.run_async
    user = User.validate_user(update.effective_user)

    page = ManagePage(Podcast.star_by(user, 'name'), text='已启动收藏面板')
    msg = run_async(
        update.message.reply_text,
        text=page.text,
        reply_markup=ReplyKeyboardMarkup(
            page.keyboard(null_text='还没有收藏播客～', jump_to=DOC_MARK), resize_keyboard=True, one_time_keyboard=True, selective=True)
    ).result()
    delete_manage_starter(context)
    save_manage_starter(context.chat_data, msg)


@delete_update_message
def search(update, context):
    context.dispatcher.run_async(
        update.message.reply_text,
        text=RIGHT_SEARCH_MARK,
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton('搜索播客', switch_inline_query_current_chat=''))
    )


@delete_update_message
def about(update, context):
    keyboard = [[InlineKeyboardButton("源代码", url=manifest.repo),
                 InlineKeyboardButton("工作室", url=manifest.author_url)],
                [InlineKeyboardButton('关闭', callback_data="delete_message")]
                ]
    context.dispatcher.run_async(
        update.message.reply_text,
        text=(
            f"*{manifest.name}*  "
            f"`{manifest.version}`"
            f"\nby [{manifest.author}](https://t.me/{manifest.author_id})\n"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@delete_update_message
def favorite(update, context):
    user = User.validate_user(update.effective_user)
    fav_episodes = Episode.objects(starrers=user)
    if len(fav_episodes) == 1:
        update.message.reply_audio(
            audio=fav_episodes.first().file_id
        )
    elif len(fav_episodes) >= 2 and len(fav_episodes) <= 5:
        update.message.reply_media_group(
            media=list(map(lambda episode: InputMediaAudio(
                media=episode.file_id
            ), fav_episodes))
        )
    elif len(fav_episodes) > 5:
        #!!!
        update.message.reply_media_group(
            media=list(map(lambda x: InputMediaAudio(x.file_id), fav_episodes))
        )
    else:
        update.message.reply_text(
            text='还没有收藏的单集～',
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton('订阅列表', switch_inline_query_current_chat=''))
        )


@delete_update_message
def share(update, context):
    update.message.reply_text(
        text='💌',
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton('分享播客', switch_inline_query=''))
    )

# @delete_update_message


def wander(update, context):
    update.message.reply_text(
        '功能正在开发中，敬请等待！', reply_to_message_id=update.effective_message.message_id)


@delete_update_message
def settings(update, context):
    keyboard = [
        [InlineKeyboardButton('外观设置', callback_data="display_setting"),
         InlineKeyboardButton('推送设置', callback_data="feed_setting"),
         InlineKeyboardButton('主播设置', callback_data="host_setting"),
         ],
        [InlineKeyboardButton('关闭', callback_data="delete_message")]]
    text_handler = update.message.reply_text if update.message else update.callback_query.edit_message_text
    msg = context.dispatcher.run_async(
        text_handler,
        text=f'请选择想要编辑的偏好设置：',
        reply_markup=InlineKeyboardMarkup(keyboard)
    ).result()
    save_manage_starter(context.chat_data, msg)


@delete_update_message
def help_(update, context):
    run_async = context.dispatcher.run_async
    text_handler = update.message.reply_text if update.message else update.callback_query.edit_message_text
    run_async(
        text_handler,
        text=f"[{manifest.name} 入门指南](https://github.com/DahaWong/castpod/wiki/%E5%85%A5%E9%97%A8%E6%8C%87%E5%8D%97)\n\n",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('注销账号', callback_data="logout"),
             InlineKeyboardButton('导出订阅', callback_data="export")],
            [InlineKeyboardButton('关闭', callback_data="delete_message")]]
        )
    )


@delete_update_message
def invite(update, context):
    update.message.reply_text(
        text=f"邀请你的伙伴一起听播客！",
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                '呼朋唤友', switch_inline_query=f"#invite"
            )
        )
    )


def bonus(update, context):
    update.message.reply_text(
        text='您的积分是：'+str(User.objects.get(
            user_id=update.effective_user.id).bonus),
        reply_to_message_id=update.message.message_id
    )
