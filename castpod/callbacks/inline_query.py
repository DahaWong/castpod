from mongoengine.queryset.visitor import Q
from mongoengine.errors import DoesNotExist
from ..utils import search_itunes
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultCachedPhoto, InlineQueryResultPhoto, InlineQueryResultCachedAudio
import re
from config import manifest
from ..models import User, Podcast, Episode
import datetime
from ..constants import SPEAKER_MARK


def via_sender(update, context):
    query = update.inline_query
    user = User.validate_user(update.effective_user)
    keywords = query.query
    if not keywords:
        results = show_subscription(user)
        query.answer(
            list(results),
            auto_pagination=True,
            cache_time=30
        )
        return
    match = re.match(r'(.*?)#(.*)$', keywords)
    name, index = match[1], match[2]
    if match:
        try:
            podcast = Podcast.objects.get(
                Q(name=name) & Q(subscribers=user))
            results = show_episodes(podcast, index)
        except:
            results = search_podcast(user, keywords)
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
    via_private(update, context)


def via_channel(update, context):
    via_private(update, context)


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
        subscribers=user).order_by('-updated_time')
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


def show_episodes(podcast, index):
    buttons = [
        InlineKeyboardButton("订阅列表", switch_inline_query_current_chat=""),
        InlineKeyboardButton(
            "单集列表", switch_inline_query_current_chat=f"{podcast.name}#")
    ]
    if index:
        if re.match(r'^-?[0-9]*$', index):
            index = int(index)
            if abs(index) <= len(podcast.episodes):
                if index >= 0:
                    index = -index
                    episodes = podcast.episodes[max(
                        index-3, -len(podcast.episodes)): min(index+2, -1)]
                else:
                    index = abs(index + 1)
                    episodes = podcast.episodes[max(
                        index-3, 0): min(index+2, len(podcast.episodes))]
            else:
                yield InlineQueryResultArticle(
                    id=0,
                    title='超出检索范围',
                    input_message_content=InputTextMessageContent(':('),
                    # !!如果 podcast.episodes.count() == 1
                    description=f"请输入 1 ～ {len(podcast.episodes)} 之间的数字",
                )
                return
        else:
            episodes = Episode.objects(
                Q(from_podcast=podcast) & Q(title__icontains=index)
            ).order_by('-published_time') or Episode.objects(
                Q(from_podcast=podcast) & Q(summary__icontains=index)
            ).order_by('-published_time')
            if not episodes:
                yield InlineQueryResultArticle(
                    id=0,
                    title='没有找到相关的节目',
                    input_message_content=InputTextMessageContent(':('),
                    description=f"换个关键词试试",
                )
                return
    else:
        episodes = podcast.episodes
    for index, episode in enumerate(episodes):
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
        podcasts_of_user = Podcast.objects(subscribers=user).only('episodes')
        episodes = Episode.objects(
            Q(title__icontains=keywords) & Q(from_podcast__in=podcasts_of_user)
        )
        if not episodes:
            yield InlineQueryResultArticle(
                id=0,
                title='没有找到相关的播客',
                description=f'换个关键词试试 :)',
                input_message_content=InputTextMessageContent(':)')
            )
            return
        else:
            for index, episode in enumerate(episodes):
                podcast = episode.from_podcast
                email = f'\n✉️  {podcast.email}' if podcast.email else ''
                yield InlineQueryResultArticle(
                    id=index,
                    title=episode.title,
                    description=podcast.name,
                    thumb_url=episode.logo.url,
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
