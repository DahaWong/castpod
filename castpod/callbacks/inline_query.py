from ..utils import search_itunes, send_error_message
from telegram import (
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InputTextMessageContent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultCachedPhoto,
    Update,
)
from telegram.error import BadRequest, TimedOut
import re
from ..models_new import Episode, Shownotes, User, Podcast, UserSubscribePodcast
import datetime
from ..constants import SHORT_DOMAIN
from peewee import DoesNotExist
from uuid import uuid4


async def via_sender(update: Update, context):
    user = update.effective_user
    inline_query = update.inline_query
    keywords = inline_query.query
    subscribed_podcasts = (
        Podcast.select().join(UserSubscribePodcast).join(User).where(User.id == user.id)
    )
    if not keywords:
        if not subscribed_podcasts:
            results = [
                InlineQueryResultArticle(
                    id=uuid4(),
                    title="🔎 继续输入关键词，搜索并订阅新播客",
                    description="订阅后，这里将显示你的订阅列表。",
                    input_message_content=InputTextMessageContent("🔍"),
                    reply_markup=InlineKeyboardMarkup.from_button(
                        InlineKeyboardButton(
                            "返回搜索", switch_inline_query_current_chat=""
                        )
                    ),
                )
            ]
            await inline_query.answer(results, cache_time=5)
            return
        results = []
        for podcast in subscribed_podcasts:
            new_result = InlineQueryResultArticle(
                id=uuid4(),
                title=podcast.name,
                input_message_content=InputTextMessageContent(
                    podcast.name, parse_mode=None
                ),
                description=f"{podcast.host}",
                thumb_url=podcast.logo.url,
                thumb_height=60,
                thumb_width=60,
            )
            # new_result = InlineQueryResultPhoto(
            #     id=uuid4(),
            #     photo_url=podcast.logo.url,
            #     thumb_url=podcast.logo.thumbnail_url or podcast.logo.url,
            #     photo_width=80,
            #     photo_height=80,
            #     title=podcast.name,
            #     description=podcast.website or podcast.email or None,
            #     input_message_content=InputTextMessageContent(
            #         podcast.name, parse_mode=None
            #     ),
            # )
            results.append(new_result)
        await inline_query.answer(
            results,
            auto_pagination=True,
            cache_time=15,
            # switch_pm_text="订阅列表",
            # switch_pm_parameter="add_podcast",
        )
    else:
        match = re.search(r"(.*?)#(.*)$", keywords)
        try:
            if match:
                name, index = match[1], match[2]
                podcast = Podcast.get(Podcast.name == name)
                results = show_episodes(podcast, index)
                await inline_query.answer(
                    list(results),
                    auto_pagination=True,
                    cache_time=10,
                    # cache_time=3600,
                )
            else:
                results = await search_podcast(keywords)
                await inline_query.answer(
                    results,
                    auto_pagination=True,
                    cache_time=450,
                    # switch_pm_text=f"「{keywords}」的搜索结果",
                    # switch_pm_parameter="search_podcast",
                )
        except DoesNotExist:
            await send_error_message(user, "🫧 该播客不在订阅列表中")
        except TimedOut:
            # TODO
            await send_error_message(user, "该播客节目较多，暂时无法收听")


async def via_private(update, context):
    print("!!!")
    inline_query = update.inline_query
    user = User.validate_user(update.effective_user)
    if not inline_query.query:
        results = get_invitation(user)
    else:
        results = share_podcast(user, inline_query.query)
    await inline_query.answer(list(results), auto_pagination=True, cache_time=600)


# async def via_group(update, context):
#     via_private(update, context)


# async def via_channel(update, context):
#     via_private(update, context)


async def search_podcast(keywords):
    searched_results = await search_itunes(keyword=keywords)
    if not searched_results:
        return [
            InlineQueryResultArticle(
                id=uuid4(),
                title="没有找到相关的播客 :(",
                description="换个关键词试试",
                input_message_content=InputTextMessageContent(":("),
                reply_markup=InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton(
                        "返回搜索", switch_inline_query_current_chat=keywords
                    )
                ),
            )
        ]
    else:
        results = []
        for result in searched_results:
            name = re.sub(r"[_*`]", " ", result["collectionName"])
            host = re.sub(r"[_*`]", " ", result["artistName"])
            feed = result.get("feedUrl")
            if not feed:
                continue
            feed_short = re.match(SHORT_DOMAIN, feed.lower())[1]
            thumbtail_large = result.get("artworkUrl600")
            thumbnail_small = result.get("artworkUrl60")
            episode_count = f'共 {result["trackCount"]} 期'

            # 如果不在 机器人主页，则：
            # [InlineKeyboardButton('前往 bot', url = f"https://t.me/{manifest.bot_id}")],
            results.append(
                InlineQueryResultArticle(
                    id=result["collectionId"],
                    title=name,
                    input_message_content=InputTextMessageContent(
                        f"{feed}\n{thumbtail_large}\n{thumbnail_small}", parse_mode=None
                    ),
                    description=(
                        f"{host if len(host)<=31 else host[:31]+'...'}\n{episode_count} · {feed_short}"
                    ),
                    thumb_url=thumbnail_small or None,
                    thumb_height=60,
                    thumb_width=60,
                )
            )
        return results


# def show_subscription(user):
#     podcasts = Podcast.objects(subscribers=user).order_by("-updated_time")
#     if not podcasts:
#         yield InlineQueryResultArticle(
#             id=0,
#             title="搜索播客…",
#             description=f"在 @{manifest.bot_id} 后输入关键词，寻找喜欢的播客吧！",
#             input_message_content=InputTextMessageContent("🔍️"),
#             reply_markup=InlineKeyboardMarkup.from_button(
#                 InlineKeyboardButton("搜索播客", switch_inline_query_current_chat="")
#             ),
#         )
#     else:
#         for index, podcast in enumerate(podcasts):
#             if podcast.logo.file_id:
#                 yield InlineQueryResultCachedPhoto(
#                     id=str(index),
#                     photo_file_id=podcast.logo.file_id,
#                     title=str(podcast.name),
#                     description=podcast.host or podcast.name,
#                     # photo_url=podcast.logo.url,
#                     input_message_content=InputTextMessageContent(podcast.name),
#                     caption=podcast.name,
#                 )
#             else:
#                 yield InlineQueryResultPhoto(
#                     id=str(index),
#                     description=podcast.host or podcast.name,
#                     photo_url=podcast.logo.url,
#                     thumb_url=podcast.logo.url,
#                     photo_width=80,
#                     photo_height=80,
#                     title=str(podcast.name),
#                     caption=podcast.name,
#                     input_message_content=InputTextMessageContent(podcast.name),
#                 )


def show_episodes(podcast, index):
    buttons = [
        InlineKeyboardButton("订阅列表", switch_inline_query_current_chat=""),
        InlineKeyboardButton(
            "更多单集", switch_inline_query_current_chat=f"{podcast.name}#"
        ),
    ]
    episodes = podcast.episodes
    if index:
        if re.match(r"^-?[0-9]{1,4}$", index):
            index = int(index)
            if abs(index) <= len(podcast.episodes):
                if index >= 0:
                    index = -index
                    episodes = podcast.episodes[
                        max(index - 3, -len(podcast.episodes)) : min(index + 2, -1)
                    ]
                else:
                    index = abs(index + 1)
                    episodes = podcast.episodes[
                        max(index - 3, 0) : min(index + 2, len(podcast.episodes))
                    ]
            else:
                yield InlineQueryResultArticle(
                    id=uuid4(),
                    title="超出检索范围",
                    input_message_content=InputTextMessageContent(":("),
                    description="当前播客只有一期节目"
                    if podcast.episodes.count() == 1
                    else f"请输入 1 ～ {len(podcast.episodes)} 之间的数字",
                )
                return
        else:
            episodes = (
                Episode.select().where(
                    (Episode.from_podcast == podcast.id)
                    & (Episode.title.contains(index) | Episode.abbr.startswith(index))
                )
                # .join(Shownotes)
                # .where(Shownotes.content.contains(index))
            )
            if not episodes:
                yield InlineQueryResultArticle(
                    id=uuid4(),
                    title="🫧 没有找到相关的节目",
                    input_message_content=InputTextMessageContent(podcast.name),
                    description=f"换个关键词试试",
                )
    for i, episode in enumerate(episodes):
        yield InlineQueryResultArticle(
            id=uuid4(),
            title=episode.title,
            input_message_content=InputTextMessageContent(
                f"{podcast.name} #{len(episodes)-i}\n"
            ),
            reply_markup=InlineKeyboardMarkup.from_row(buttons),
            description=f"{datetime.timedelta(seconds=episode.duration) or podcast.name}\n{episode.subtitle}",
            thumb_url=episode.logo.url,
            thumb_width=60,
            thumb_height=60,
        )


def get_invitation():
    yield InlineQueryResultArticle(
        id=uuid4(),
        title="点击发送 Castpod 邀请函",
        description="或者继续输入关键词分享播客",
        input_message_content=InputTextMessageContent("来 Castpod 一起听播客！"),
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton("🏖️ 开启播客之旅", url=f"https://t.me/{manifest.bot_id}")
        ),
    )


# def share_podcast(user, keywords):
#     podcasts = Podcast.objects(Q(name__icontains=keywords) & Q(subscribers=user))
#     if not podcasts:
#         podcasts_of_user = Podcast.objects(subscribers=user).only("episodes")
#         episodes = Episode.objects(
#             Q(title__icontains=keywords) & Q(from_podcast__in=podcasts_of_user)
#         )
#         if not episodes:
#             yield InlineQueryResultArticle(
#                 id=0,
#                 title="没有找到相关的播客",
#                 description=f"换个关键词试试 :)",
#                 input_message_content=InputTextMessageContent(":)"),
#             )
#             return
#         else:
#             for index, episode in enumerate(episodes):
#                 podcast = episode.from_podcast
#                 email = f"\n✉️  {podcast.email}" if podcast.email else ""
#                 yield InlineQueryResultArticle(
#                     id=index,
#                     title=episode.title,
#                     description=podcast.name,
#                     thumb_url=episode.logo.url,
#                     thumb_width=60,
#                     thumb_height=60,
#                     input_message_content=InputTextMessageContent(
#                         message_text=(
#                             f"*{podcast.name}*"
#                             f"\n[{SPEAKER_MARK}]({podcast.logo.url}) {podcast.host or podcast.name}"
#                             f"{email}"
#                         )
#                     ),
#                     reply_markup=InlineKeyboardMarkup.from_button(
#                         InlineKeyboardButton(
#                             "订阅",
#                             url=f"https://t.me/{manifest.bot_id}?start=p{podcast.id}",
#                         )
#                     ),
#                 )
#     for index, podcast in enumerate(podcasts):
#         email = f"\n✉️  {podcast.email}" if podcast.email else ""
#         yield InlineQueryResultArticle(
#             id=index,
#             title=podcast.name,
#             description=podcast.host,
#             thumb_url=podcast.logo.url,
#             thumb_width=60,
#             thumb_height=60,
#             input_message_content=InputTextMessageContent(
#                 message_text=(
#                     f"*{podcast.name}*"
#                     f"\n[{SPEAKER_MARK}]({podcast.logo.url}) {podcast.host or podcast.name}"
#                     f"{email}"
#                 )
#             ),
#             reply_markup=InlineKeyboardMarkup.from_button(
#                 InlineKeyboardButton(
#                     "订阅", url=f"https://t.me/{manifest.bot_id}?start=p{podcast.id}"
#                 )
#             ),
#         )
