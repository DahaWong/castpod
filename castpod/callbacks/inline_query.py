from castpod.callbacks.command import share
from mongoengine.queryset.visitor import Q
from mongoengine.errors import DoesNotExist
from castpod.utils import search_itunes
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultCachedPhoto, InlineQueryResultPhoto, InlineQueryResultCachedAudio
import re
from config import manifest
from castpod.models import User, Podcast
import datetime
from ..constants import SPEAKER_MARK, STAR_MARK


def via_sender(update, context):
    query = update.inline_query
    user = User.validate_user(update.effective_user)
    if not query.query:
        results = show_subscription(user)
        query.answer(
            list(results),
            auto_pagination=True,
            cache_time=30
        )
    else:
        try:
            podcast = Podcast.objects.get(
                Q(name=query.query) & Q(subscribers=user))
            results = show_episodes(podcast)
        except:
            results = search_podcast(user, query.query)
        query.answer(
            list(results),
            auto_pagination=True,
            cache_time=10
        )


def via_private(update, context):
    query = update.inline_query
    user = User.validate_user(update.effective_user)
    if not query.query:
        results = get_invitation(user)
    else:
        results = share_podcast(user, query.query)
    query.answer(list(results), auto_pagination=True, cache_time=600)


def via_group(update, context):
    pass


def via_channel(update, context):
    pass


def search_podcast(user, keywords):
    searched_results = search_itunes(keywords)
    if not searched_results:
        podcasts = Podcast.objects(
            Q(name__icontains=keywords) & Q(subscribers=user))
        if not podcasts:
            yield InlineQueryResultArticle(
                id='0',
                title="没有找到相关的播客 :(",
                description="换个关键词试试",
                input_message_content=InputTextMessageContent(":("),
                reply_markup=InlineKeyboardMarkup.from_button(
                            InlineKeyboardButton(
                                '返回搜索', switch_inline_query_current_chat=keywords)
                )
            )
        else:
            yield InlineQueryResultArticle(
                id='0',
                title="没有找到相关的播客 :(",
                description="以下是在订阅列表中搜索到的结果：",
                input_message_content=InputTextMessageContent(":("),
                reply_markup=InlineKeyboardMarkup.from_button(
                            InlineKeyboardButton(
                                '返回搜索', switch_inline_query_current_chat=keywords)
                )
            )
            for index, podcast in enumerate(podcasts):
                if podcast.logo.file_id:
                    yield InlineQueryResultCachedPhoto(
                        id=index,
                        photo_file_id=podcast.logo.file_id,
                        title=str(podcast.name),
                        description=podcast.host or podcast.name,
                        # photo_url=podcast.logo.url,
                        input_message_content=InputTextMessageContent(
                            podcast.name),
                        caption=podcast.name
                    )
                else:
                    yield InlineQueryResultPhoto(
                        id=index,
                        description=podcast.host or podcast.name,
                        photo_url=podcast.logo.url,
                        thumb_url=podcast.logo.url,
                        photo_width=80,
                        photo_height=80,
                        title=str(podcast.name),
                        caption=podcast.name,
                        input_message_content=InputTextMessageContent(
                            podcast.name)
                    )
    else:
        for result in searched_results:
            name = re.sub(r"[_*`]", ' ', result['collectionName'])
            host = re.sub(r"[_*`]", ' ', result['artistName'])
            feed = result.get('feedUrl') or '（此播客没有提供订阅源）'
            thumbnail_small = result.get('artworkUrl60')

            # 如果不在 机器人主页，则：
            # [InlineKeyboardButton('前  往  B O T', url = f"https://t.me/{manifest.bot_id}")],

            yield InlineQueryResultArticle(
                id=result['collectionId'],
                title=name,
                input_message_content=InputTextMessageContent(
                    feed, parse_mode=None),
                description=host,
                thumb_url=thumbnail_small or None,
                thumb_height=60,
                thumb_width=60
            )


def show_subscription(user):
    podcasts = Podcast.objects(
        subscribers__in=[user]).order_by('-updated_time')
    if not podcasts:
        yield InlineQueryResultArticle(
            id=0,
            title='请输入关键词…',
            description=f'在 @{manifest.bot_id} 后输入关键词，寻找喜欢的播客吧！',
            input_message_content=InputTextMessageContent('🔍️'),
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    '搜索播客', switch_inline_query_current_chat='')
            )
        )
    else:
        for index, podcast in enumerate(podcasts):
            if podcast.logo.file_id:
                yield InlineQueryResultCachedPhoto(
                    id=str(index),
                    photo_file_id=podcast.logo.file_id,
                    title=str(podcast.name),
                    description=podcast.host or podcast.name,
                    # photo_url=podcast.logo.url,
                    input_message_content=InputTextMessageContent(
                        podcast.name),
                    caption=podcast.name
                )
            else:
                yield InlineQueryResultPhoto(
                    id=str(index),
                    description=podcast.host or podcast.name,
                    photo_url=podcast.logo.url,
                    thumb_url=podcast.logo.url,
                    photo_width=80,
                    photo_height=80,
                    title=str(podcast.name),
                    caption=podcast.name,
                    input_message_content=InputTextMessageContent(podcast.name)
                )


def show_episodes(podcast):
    buttons = [
        InlineKeyboardButton("订阅列表", switch_inline_query_current_chat=""),
        InlineKeyboardButton(
            "单集列表", switch_inline_query_current_chat=f"{podcast.name}")
    ]
    for index, episode in enumerate(podcast.episodes):
        if episode.file_id:
            yield InlineQueryResultCachedAudio(
                id=index,
                audio_file_id=episode.file_id,
                reply_markup=InlineKeyboardMarkup.from_row(buttons),
                input_message_content=InputTextMessageContent((
                    f"[{SPEAKER_MARK}]({podcast.logo.url}) *{podcast.name}* #{len(podcast.episodes)-index}"
                )),
            )
        else:
            yield InlineQueryResultArticle(
                id=index,
                title=episode.title,
                input_message_content=InputTextMessageContent((
                    f"[{SPEAKER_MARK}]({podcast.logo.url}) *{podcast.name}* #{len(podcast.episodes)-index}"
                )),
                reply_markup=InlineKeyboardMarkup.from_row(buttons),
                description=f"{datetime.timedelta(seconds=episode.duration) or podcast.name}\n{episode.subtitle}",
                thumb_url=episode.logo.url,
                thumb_width=80,
                thumb_height=80
            )


def get_invitation(user):
    yield InlineQueryResultArticle(
        id='0',
        title="点击发送 Castpod 邀请函",
        description="或者继续输入关键词同好友分享播客",
        input_message_content=InputTextMessageContent("一起用 Castpod 听播客吧！"),
        reply_markup=InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton(
                        '开启旅程', url=f"https://t.me/{manifest.bot_id}/start=via_{user.id}"))
    )


def share_podcast(user, keywords):
    podcasts = Podcast.objects(
        Q(name__icontains=keywords) & Q(subscribers=user))
    if not podcasts:
        yield InlineQueryResultArticle(
            id=0,
            title='没有找到相关的播客',
            description=f'换个关键词试试 :)',
            input_message_content=InputTextMessageContent(':)')
        )
        return
    for index, podcast in enumerate(podcasts):
        email = f'\n✉️  {podcast.email}' if podcast.email else ''
        yield InlineQueryResultArticle(
            id=index,
            title=podcast.name,
            description=podcast.host,
            thumb_url=podcast.logo.url,
            thumb_width=60,
            thumb_height=60,
            input_message_content=InputTextMessageContent(
                message_text=(
                    f'*{podcast.name}*'
                    f'\n[{SPEAKER_MARK}]({podcast.logo.url}) {podcast.host or podcast.name}'
                    f'{email}'
                )
            ),
            reply_markup=InlineKeyboardMarkup.from_button(InlineKeyboardButton(
                '订阅', url=f"https://t.me/{manifest.bot_id}/start={podcast.id}"))
        )
