from castpod.models import Podcast
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ChatAction, ParseMode, ReplyKeyboardRemove
from castpod.components import PodcastPage, ManagePage
from config import podcast_vault
from castpod.utils import check_login, local_download, parse_doc
from base64 import urlsafe_b64encode as encode
from manifest import manifest
import re


@check_login
def save_subscription(update, context):
    run_async = context.dispatcher.run_async
    message = update.message
    parsing_note = run_async(message.reply_text, "正在解析订阅文件…").result()
    user = context.user_data['user']
    cached_podcasts = context.bot_data['podcasts']
    try:
        feeds = run_async(parse_doc, context, user,
                          message.document).result()
    except Exception as e:
        print(e)
        run_async(parsing_note.delete)
        run_async(message.reply_text, "订阅失败 :(\n请检查订阅文件是否格式正确/完好无损")
        return

    subscribing_note = run_async(
        parsing_note.edit_text, f"订阅中 (0/{len(feeds)})").result()
    podcasts = []
    failed_feeds = []
    for feed in feeds:
        if feed['name'] not in cached_podcasts.keys():
            try:
                podcast = Podcast(feed['url'])
                podcasts.append(podcast)
                podcast.subscribers.add(user.user_id)
                cached_podcasts.update({podcast.name: podcast})
            except Exception as e:
                print(e)
                failed_feeds.append(feed['url'])
                continue
        else:
            podcast = cached_podcasts[feed['name']]
            podcasts.append(podcast)
            podcast.subscribers.add(user.user_id)
        run_async(subscribing_note.edit_text,
                  f"订阅中 ({len(podcasts)}/{len(feeds)})")

    if podcasts:
        user.import_feeds(podcasts)
        newline = '\n'
        reply = f"成功订阅 {len(feeds)} 部播客！" if not len(failed_feeds) else (
            f"成功订阅 {len(podcasts)} 部播客，部分订阅源解析失败。"
            f"\n\n可能损坏的订阅源："
            f"\n{newline.join(['`'+feed+'`' for feed in failed_feeds])}"
        )
    else:
        reply = "订阅失败:( \n\n请检查订阅文件以及其中的订阅源是否受损"

    manage_page = ManagePage([podcast.name[:32]
                              for podcast in podcasts], text=reply)
    run_async(subscribing_note.delete)
    run_async(message.reply_text,
              text=manage_page.text,
              reply_markup=ReplyKeyboardMarkup(
                  manage_page.keyboard(),
                  resize_keyboard=True,
                  one_time_keyboard=True
              )
              )


@check_login
def subscribe_feed(update, context):
    run_async = context.dispatcher.run_async
    message = update.message
    run_async(context.bot.send_chat_action,
              chat_id=message.chat_id, action='typing')
    subscribing_message = run_async(message.reply_text, f"订阅中，请稍候…").result()

    user = context.user_data['user']
    podcasts = context.bot_data['podcasts']
    podcast = Podcast(feed_url=message.text)  # 判断是否存在于音乐库中！
    user.add_feed(podcast)
    try:
        manage_page = ManagePage(
            podcast_names=user.subscription.keys(),
            text=f"`{podcast.name}` 订阅成功！"
        )
        run_async(subscribing_message.delete)
        run_async(message.reply_text,
                  text=manage_page.text,
                  reply_markup=ReplyKeyboardMarkup(
                      manage_page.keyboard(),
                      resize_keyboard=True,
                      one_time_keyboard=True
                  )
                  )
        podcast_page = PodcastPage(podcast)
        run_async(message.reply_text,
                  text=podcast_page.text(),
                  reply_markup=InlineKeyboardMarkup(podcast_page.keyboard())
                  )
        run_async(message.delete)
        podcast.subscribers.add(user.user_id)
        if podcast.name not in podcasts.keys():
            podcasts.update({podcast.name: podcast})
    except Exception as e:
        print(e)
        run_async(subscribing_message.edit_text, "订阅失败，可能是因为订阅源损坏 :(")


@check_login
def download_episode(update, context):
    run_async = context.dispatcher.run_async
    bot = context.bot
    message = update.message
    fetching_note = run_async(
        bot.send_message, message.chat_id, "获取节目中…").result()
    run_async(bot.send_chat_action, message.chat_id, ChatAction.RECORD_AUDIO)
    match = re.match(r'🎙️ (.+) #([0-9]+)', message.text)
    podcast_name, index = match[1], int(match[2])
    podcast = context.bot_data['podcasts'].get(podcast_name)
    episode = podcast.episodes[-index]
    run_async(bot.send_chat_action, update.message.chat_id,
              ChatAction.UPLOAD_AUDIO)
    if episode.message_id:
        run_async(fetching_note.delete)
        forwarded_message = run_async(bot.forward_message,
                                      chat_id=context.user_data['user'].user_id,
                                      from_chat_id=f"@{podcast_vault}",
                                      message_id=episode.message_id
                                      ).result()
        forward_from_message = episode.message_id
    else:
        encoded_podcast_name = encode(
            bytes(podcast.name, 'utf-8')).decode("utf-8")
        downloading_note = run_async(fetching_note.edit_text, "下载中…").result()
        audio_file = run_async(local_download, episode, context).result()
        uploading_note = run_async(
            downloading_note.edit_text, "正在上传，请稍候…").result()
        audio_message = None
        try:
            audio_message = run_async(bot.send_audio,
                                      chat_id=f'@{podcast_vault}',
                                      audio=audio_file,
                                      caption=(
                                          f"🎙️ {podcast.name}\n"
                                          f"总第 {index} 期"
                                          f"\n\n[订阅](https://t.me/{manifest.bot_id}?start={encoded_podcast_name})"
                                          f" | [相关链接]({episode.get_shownotes_url()})"
                                      ),
                                      title=episode.title,
                                      performer=f"{podcast.name} | {episode.host or podcast.host}" if podcast.host else podcast.name,
                                      duration=episode.duration.seconds,
                                      thumb=podcast.logo_url
                                      ).result()
        except Exception as e:
            pass  # ⚠️
        finally:
            run_async(uploading_note.delete)
        forwarded_message = run_async(audio_message.forward,
                                      context.user_data['user'].user_id).result()
        forward_from_message = audio_message.message_id
    run_async(update.message.delete)

    run_async(forwarded_message.edit_caption,
              caption=(
                  f"🎙️ <b>{podcast.name}</b>\n\n<a href='{episode.get_shownotes_url() or podcast.website}'>相关链接</a>"
                  f"\n\n{episode.timeline}"
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


@check_login
def exit_reply_keyboard(update, context):
    message = update.message
    message.reply_text(
        '已退出管理面板',
        reply_markup=ReplyKeyboardRemove()
    ).delete()
    message.delete()

@check_login
def show_feed(update, context):
    run_async = context.dispatcher.run_async
    message = update.message
    feed_name = message.text
    user = context.user_data['user']
    if feed_name in user.subscription.keys():
        feed = context.user_data['user'].subscription[feed_name]
        podcast = feed.podcast
        if podcast.name in context.user_data['saved_podcasts']:
            page = PodcastPage(podcast, save_text="❤️",
                               save_action='unsave_podcast')
        else:
            page = PodcastPage(podcast)
        run_async(update.message.reply_text,
                  text=page.text(),
                  reply_markup=InlineKeyboardMarkup(page.keyboard())
                  )
        run_async(update.message.delete)
    else:
        run_async(message.reply_text, '抱歉，没能理解您想要做什么。')


def handle_audio(update, context):
    message = update.message
    if not message:
        return
    if not message.from_user.id == 777000:
        return
    match = re.match(r'🎙️ (.+?)\n总第 ([0-9]+) 期', message.caption)
    podcast_name, index = match[1], int(match[2])
    podcast = context.bot_data['podcasts'][podcast_name]
    episode = podcast.episodes[-index]
    episode.message_id = message.forward_from_message_id
    # episode.file_id = message.audio.file_id
