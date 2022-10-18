# from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
# from telegram.constants import ChatAction, ParseMode
# from ..models import User, Podcast
# from ..components import PodcastPage, ManagePage
# from ..utils import download, parse_doc
# from config import podcast_vault, manifest, dev
# from ..constants import RIGHT_SEARCH_MARK, SPEAKER_MARK, STAR_MARK
# from mongoengine.queryset.visitor import Q
# from mongoengine.errors import DoesNotExist
# import re


# async def delete_message(update, context):
#     await update.message.delete()


# async def subscribe_feed(update, context):
#     message = update.message
#     chat_type = update.effective_chat.type
#     await context.bot.send_chat_action(
#         chat_id=message.chat_id,
#         action='typing'
#     )
#     subscribing_message = await message.reply_text(f"订阅中，请稍候…")

#     user = User.validate_user(update.effective_user)
#     podcast = Podcast.validate_feed(feed=message.text.lower())
#     user.subscribe(podcast)
#     in_group = (chat_type == 'group') or (chat_type == 'supergroup')
#     kwargs = {'mode': 'group'} if in_group else {}
#     try:
#         manage_page = ManagePage(
#             podcasts=Podcast.subscribe_by(user, 'name'),
#             text=f"`{podcast.name}` 订阅成功！"
#         )
#         await subscribing_message.delete()
#         await message.reply_text(
#             text=manage_page.text,
#             reply_markup=ReplyKeyboardMarkup(
#                 manage_page.keyboard(),
#                 resize_keyboard=True,
#                 one_time_keyboard=True
#             )
#         )

#         podcast_page = PodcastPage(podcast, **kwargs)
#         photo = podcast.logo.file_id or podcast.logo.url
#         msg = await message.reply_photo(
#             photo=photo,
#             caption=podcast_page.text(),
#             reply_markup=InlineKeyboardMarkup(
#                 podcast_page.keyboard()),
#             parse_mode="HTML"
#         )
#         podcast.logo.file_id = msg.photo[0].file_id
#         podcast.save()
#         await message.delete()
#     except Exception as e:
#         await subscribing_message.edit_text("订阅失败 :(")
#         raise e


# async def save_subscription(update, context):
#     message = update.message
#     parsing_note = await message.reply_text("正在解析订阅文件…")
#     user = User.validate_user(update.effective_user)
#     try:
#         feeds = await parse_doc(context, user, message.document)
#         feeds_count = len(feeds)
#         subscribing_note = await parsing_note.edit_text(f"订阅中 (0/{feeds_count})")
#         podcasts_count = 0
#         failed_feeds = []
#         for feed in feeds:
#             podcast = None
#             try:
#                 podcast = Podcast.validate_feed(feed['url'].lower())
#                 user.subscribe(podcast)
#                 podcasts_count += 1
#             except Exception as e:
#                 podcast.delete()
#                 failed_feeds.append(feed['url'])
#                 continue
#             await subscribing_note.edit_text(
#                 f"订阅中 ({podcasts_count}/{feeds_count})"
#             )

#         if podcasts_count:
#             newline = '\n'
#             reply = f"成功订阅 {feeds_count} 部播客！" if not len(failed_feeds) else (
#                 f"成功订阅 {podcasts_count} 部播客，部分订阅源解析失败。"
#                 f"\n\n可能损坏的订阅源："
#                 # use Reduce ?
#                 f"\n{newline.join(['`'+feed+'`' for feed in failed_feeds])}"
#             )
#         else:
#             reply = "订阅失败:( \n\n请检查订阅文件以及其中的订阅源是否受损"

#         manage_page = ManagePage(
#             podcasts=Podcast.subscribe_by(user, 'name'),
#             text=reply
#         )

#         await subscribing_note.delete()
#         await message.reply_text(
#             text=manage_page.text,
#             reply_markup=ReplyKeyboardMarkup(
#                 manage_page.keyboard(),
#                 resize_keyboard=True,
#                 one_time_keyboard=True
#             )
#         )

#     except Exception as e:
#         await parsing_note.delete()
#         await message.reply_text(
#             f"订阅失败 :(\n"
#             f"请检查订阅文件是否完好无损；"
#             f"若文件没有问题，请私信[开发者](tg://user?id={dev})。"
#         )
#         raise e


# async def download_episode(update, context):
#     bot = context.bot
#     message = update.message
#     chat_id = message.chat_id
#     fetching_note = await bot.send_message(chat_id, "获取节目中…")
#     await bot.send_chat_action(chat_id, ChatAction.RECORD_VOICE)
#     match = re.match(f'{SPEAKER_MARK} (.+) #([0-9]+)', message.text)
#     user = User.validate_user(update.effective_user)
#     # podcast = Podcast.objects.get(name=match[1])
#     podcast = Podcast.objects.get(
#         Q(name=match[1]) & Q(subscribers=user))  # ⚠️ name改成id，且这一段代码与 handle_audio 重复
#     context.user_data.update({'podcast': podcast.name, 'chat_id': chat_id})
#     index = int(match[2])
#     episode = podcast.episodes[-index]
#     await bot.send_chat_action(
#         chat_id,
#         ChatAction.UPLOAD_VOICE
#     )

#     if episode.message_id:
#         await fetching_note.delete()
#         forwarded_message = await bot.forward_message(
#             chat_id=chat_id,
#             from_chat_id=f"@{podcast_vault}",
#             message_id=episode.message_id
#         )
#         forward_from_message = episode.message_id
#     else:
#         downloading_note = await fetching_note.edit_text("下载中…")
#         audio_file, progress_message_id = download(episode, context)
#         await context.bot.delete_message(update.effective_chat.id, progress_message_id)
#         uploading_note = await downloading_note.edit_text("发送中，请稍候…")
#         audio_message = None
#         try:
#             audio_message = await bot.send_audio(
#                 chat_id=f'@{podcast_vault}',
#                 audio=audio_file,
#                 caption=(
#                     f"{SPEAKER_MARK} *{podcast.name}*\n"
#                     f"总第 {index} 期\n\n"
#                     f"#{podcast.id}"
#                 ),
#                 reply_markup=InlineKeyboardMarkup.from_row(
#                     [InlineKeyboardButton('订阅', url=f'https://t.me/{manifest.bot_id}?start=p{podcast.id}'),
#                      InlineKeyboardButton('相关链接', url=episode.shownotes_url)]
#                 ),
#                 title=episode.title,
#                 performer=podcast.name,
#                 duration=episode.duration,
#                 thumb=episode.logo.path
#             )
#         except Exception as e:
#             raise e
#         finally:
#             await uploading_note.delete()
#         forwarded_message = await audio_message.forward(chat_id)
#         forward_from_message = audio_message.message_id
#         episode.update(set__message_id=audio_message.message_id)
#         episode.update(set__file_id=audio_message.audio.file_id)
#         context.user_data.clear()  # !!!
#     await forwarded_message.edit_caption(
#         caption=(f"{episode.timeline}"),
#         parse_mode=ParseMode.HTML,
#         reply_markup=InlineKeyboardMarkup([
#             [
#                 InlineKeyboardButton(
#                     '简介', url=episode.shownotes_url or podcast.website),
#                 InlineKeyboardButton(
#                     '收藏', callback_data=f'fav_ep_{episode.id}'),
#                 InlineKeyboardButton(
#                     '分享', switch_inline_query=f'{podcast.name}#{episode.id}')
#             ],
#             [
#                 InlineKeyboardButton(
#                     "订阅列表", switch_inline_query_current_chat=""),
#                 InlineKeyboardButton(
#                     "单集列表", switch_inline_query_current_chat=f"{podcast.name}#")
#             ]])
#     )
#     await update.message.delete()


# async def close_reply_keyboard(update, context):
#     if context.chat_data.get('reply_keyboard'):
#         await context.chat_data['reply_keyboard'].delete()
#     msg = await update.message.reply_text(
#         'OK', reply_markup=ReplyKeyboardRemove(selective=True)
#     )
#     await msg.delete()
#     await update.message.delete()
#     context.chat_data.pop('reply_keyboard', None)


# async def show_podcast(update, context):
#     message = update.message
#     if message.reply_to_message and message.reply_to_message.from_user.username != manifest.bot_id:
#         return
#     user = User.validate_user(update.effective_user)
#     chat_type = update.effective_chat.type
#     in_group = (chat_type == 'group') or (chat_type == 'supergroup')
#     kwargs = {'mode': 'group'} if in_group else {}
#     podcast = None
#     try:
#         podcast = Podcast.objects.get(
#             Q(name=message.text) & Q(subscribers=user))
#     except Exception as e:
#         podcast = Podcast.objects(
#             subscribers=user).search_text(message.text).first()
#     finally:
#         if not podcast:
#             await message.reply_text('抱歉，没能理解这条指令。')
#             return

#         if user in podcast.starrers:
#             kwargs.update(
#                 {
#                     'fav_text': STAR_MARK,
#                     'fav_action': 'unfav_podcast'
#                 }
#             )

#         page = PodcastPage(podcast, **kwargs)
#         photo = podcast.logo.file_id or podcast.logo.url
#         msg = await message.reply_photo(
#             photo=photo,
#             caption=page.text(),
#             reply_markup=InlineKeyboardMarkup(page.keyboard()),
#             parse_mode="HTML"
#         )
#         podcast.logo.file_id = msg.photo[0].file_id
#         podcast.save()
#         await message.delete()


# async def handle_audio(update, context):
#     message = update.message
#     if not (message and (message.from_user.id == 777000)):
#         return
#     match = re.match(f'{SPEAKER_MARK} .+?\n总第 ([0-9]+) 期', message.caption)
#     index = int(match[1])
#     podcast_id = list(message.parse_caption_entities().values()
#                       )[-1].replace('#', '')
#     podcast = Podcast.objects(id=podcast_id).only('episodes').first()
#     episodes = podcast.episodes
#     episodes[-index].update(set__message_id=message.forward_from_message_id)
#     episodes[-index].update(set__file_id=message.audio.file_id)
#     podcast.update(set__episodes=episodes)
#     episodes[-index].reload()
#     podcast.reload()


# async def search_podcast(update, context):
#     await update.message.reply_text(
#         text=RIGHT_SEARCH_MARK,
#         reply_markup=InlineKeyboardMarkup.from_button(
#             InlineKeyboardButton(
#                 '搜索播客', switch_inline_query_current_chat='')
#         )
#     )
