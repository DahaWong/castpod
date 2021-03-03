from castpod.models import User, Podcast
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ChatAction, ParseMode, ReplyKeyboardRemove
from castpod.components import PodcastPage, ManagePage
from config import podcast_vault, manifest, dev_user_id
from castpod.utils import delete_update_message, local_download, parse_doc, delete_manage_starter
from mongoengine.queryset.visitor import Q
import re

# @is_group??


def subscribe_feed(update, context):
    run_async = context.dispatcher.run_async
    message = update.message
    chat_type = update.effective_chat.type
    run_async(
        context.bot.send_chat_action,
        chat_id=message.chat_id,
        action='typing'
    )
    subscribing_message = run_async(message.reply_text, f"订阅中，请稍候…").result()

    user = User.validate_user(update.effective_user)
    podcast = Podcast.validate_feed(feed=message.text.lower())
    user.subscribe(podcast)
    in_group = (chat_type == 'group') or (chat_type == 'supergroup')
    kwargs = {'mode': 'group'} if in_group else {}
    try:
        manage_page = ManagePage(
            podcasts=Podcast.of_subscriber(user, 'name'),
            text=f"`{podcast.name}` 订阅成功！"
        )
        run_async(subscribing_message.delete)
        run_async(
            message.reply_text,
            text=manage_page.text,
            reply_markup=ReplyKeyboardMarkup(
                manage_page.keyboard(),
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )

        podcast_page = PodcastPage(podcast, **kwargs)
        run_async(message.reply_text,
                  text=podcast_page.text(),
                  reply_markup=InlineKeyboardMarkup(podcast_page.keyboard())
                  )
        run_async(message.delete)
    except Exception as e:
        run_async(subscribing_message.edit_text, "订阅失败，可能是因为订阅源损坏 :(")
        raise e


def save_subscription(update, context):
    run_async = context.dispatcher.run_async
    message = update.message
    parsing_note = run_async(message.reply_text, "正在解析订阅文件…").result()
    user = User.validate_user(update.effective_user)
    try:
        feeds = run_async(
            parse_doc, context, user, message.document
        ).result()
        feeds_count = len(feeds)
        subscribing_note = run_async(
            parsing_note.edit_text, f"订阅中 (0/{feeds_count})").result()
        podcasts_count = 0
        failed_feeds = []
        for feed in feeds:
            podcast = None
            try:
                podcast = Podcast.validate_feed(feed['url'].lower())
                user.subscribe(podcast)
                podcasts_count += 1
            except Exception as e:
                podcast.delete()
                failed_feeds.append(feed['url'])
                continue
            run_async(
                subscribing_note.edit_text, f"订阅中 ({podcasts_count}/{feeds_count})"
            )

        if podcasts_count:
            newline = '\n'
            reply = f"成功订阅 {feeds_count} 部播客！" if not len(failed_feeds) else (
                f"成功订阅 {podcasts_count} 部播客，部分订阅源解析失败。"
                f"\n\n可能损坏的订阅源："
                # use Reduce ?
                f"\n{newline.join(['`'+feed+'`' for feed in failed_feeds])}"
            )
        else:
            reply = "订阅失败:( \n\n请检查订阅文件以及其中的订阅源是否受损"

        manage_page = ManagePage(
            podcasts=Podcast.of_subscriber(user, 'name'),
            text=reply
        )

        run_async(subscribing_note.delete)
        run_async(
            message.reply_text,
            text=manage_page.text,
            reply_markup=ReplyKeyboardMarkup(
                manage_page.keyboard(),
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )

    except Exception as e:
        run_async(parsing_note.delete)
        run_async(
            message.reply_text, (
                f"订阅失败 :(\n"
                f"请检查订阅文件是否完好无损；"
                f"若文件没有问题，请私信[开发者](tg://user?id={dev_user_id})。"
            )
        )
        raise e


def download_episode(update, context):
    bot = context.bot
    message = update.message
    chat_id = message.chat_id
    fetching_note = bot.send_message(chat_id, "获取节目中…")
    bot.send_chat_action(chat_id, ChatAction.RECORD_AUDIO)
    match = re.match(r'🎙️ (.+) #([0-9]+)', message.text)
    user = User.validate_user(update.effective_user)
    # podcast = Podcast.objects.get(name=match[1]) 
    podcast = Podcast.objects.get(
                Q(name=match[1]) & Q(subscribers=user))  # ⚠️ name改成id，且这一段代码与 handle_audio 重复
    context.user_data.update({'podcast': podcast.name, 'chat_id': chat_id})
    index = int(match[2])
    episode = podcast.episodes[-index]
    bot.send_chat_action(
        chat_id,
        ChatAction.UPLOAD_AUDIO
    )

    if episode.message_id:
        print('in!')
        fetching_note.delete()
        forwarded_message = bot.forward_message(
            chat_id=chat_id,
            from_chat_id=f"@{podcast_vault}",
            message_id=episode.message_id
        )
        forward_from_message = episode.message_id
    else:
        downloading_note = fetching_note.edit_text("下载中…")
        audio_file = local_download(episode, context)
        uploading_note = downloading_note.edit_text("正在上传，请稍候…")
        audio_message = None
        try:
            audio_message = bot.send_audio(
                chat_id=f'@{podcast_vault}',
                audio=audio_file,
                caption=(
                    f"🎙️ {podcast.name}\n"
                    f"总第 {index} 期"
                    f"\n\n[订阅](https://t.me/{manifest.bot_id}?start={podcast.id})"
                    f" | [相关链接]({episode.shownotes.url or episode.shownotes.set_url(episode.title, podcast.name)})"
                ),
                title=episode.title,
                performer=podcast.name,
                duration=episode.audio.duration,
                thumb=podcast.logo
            )
        except Exception as e:
            raise e
        finally:
            uploading_note.delete()
        forwarded_message = audio_message.forward(chat_id)
        forward_from_message = audio_message.message_id
        context.user_data.clear()
    forwarded_message.edit_caption(
        caption=(
            f"🎙️ <b>{podcast.name}</b>\n\n<a href='{episode.shownotes.url or podcast.website}'>相关链接</a>"
            f"\n\n{episode.shownotes.timeline or episode.shownotes.set_timeline()}"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                text="评论区",
                url=f"https://t.me/{podcast_vault}/{forward_from_message}")
        ], [
            InlineKeyboardButton(
                "订阅列表", switch_inline_query_current_chat=""),
            InlineKeyboardButton(
                "单集列表", switch_inline_query_current_chat=f"{podcast.name}")
        ]])
    )
    update.message.delete()


@delete_update_message
def exit_reply_keyboard(update, context):
    run_async = context.dispatcher.run_async
    run_async(
        update.message.reply_text(
            'OK', reply_markup=ReplyKeyboardRemove(selective=True)
        ).delete
    )
    run_async(delete_manage_starter, context)


def show_podcast(update, context):
    run_async = context.dispatcher.run_async
    message = update.message
    if message.reply_to_message and message.reply_to_message.from_user.username != manifest.bot_id:
        return
    user = User.validate_user(update.effective_user)
    chat_type = update.effective_chat.type
    in_group = (chat_type == 'group') or (chat_type == 'supergroup')
    kwargs = {'mode': 'group'} if in_group else {}
    # try:
    podcast = Podcast.objects.get(
                Q(name=message.text) & Q(subscribers=user))
    subscription = user.subscriptions.get(podcast=podcast)  # ⚠️ 待优化

    if subscription.is_fav:
        kwargs.update(
            {
                'fav_text': "⭐️",
                'fav_action': 'unfav_podcast'
            }
        )

    page = PodcastPage(podcast, **kwargs)
    update.message.reply_text(
        text=page.text(),
        reply_markup=InlineKeyboardMarkup(page.keyboard())
    )
    run_async(update.message.delete)
    # except Exception as e:
        # run_async(message.reply_text, '抱歉，没能理解您的指令。')


def handle_audio(update, context):
    message = update.message
    if not (message and (message.from_user.id == 777000)):
        return
    match = re.match(r'🎙️ (.+?)\n总第 ([0-9]+) 期', message.caption)
    name, index = match[1], int(match[2])  # ⚠️ name换成id
    podcast = Podcast.objects(name=name).only('episodes').first()
    episode = podcast.episodes[-index]
    episode.message_id = message.forward_from_message_id
    episode.file_id = message.audio.file_id
    kwargs = {f'set__episodes__{len(podcast.episodes)-index}':episode}
    podcast.update(**kwargs)
    # podcast.reload()
