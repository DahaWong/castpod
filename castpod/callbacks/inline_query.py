from castpod.utils import search_itunes
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
import re
from config import manifest
from castpod.models import User


def handle_inline_query(update, context):
    run_async = context.dispatcher.run_async
    query = update.inline_query
    query_text = query.query
    podcasts_match = re.match('^p$', query_text)
    episodes_match = re.match('^e$', query_text)
    results, kwargs = [], {"auto_pagination": True, "cache_time": 10}
    user = User.validate_user(query.from_user)
    if not query_text:
        results= run_async(show_subscription, user).result()
    elif podcasts_match:
        results = run_async(search_saved, 'podcasts', user).result()
    elif episodes_match:
        results = run_async(search_saved, 'episodes', user).result()
    else:
        try:
            podcast = user.subscriptions.get(podcast=query_text)
            results = run_async(show_episodes, podcast).result()
            kwargs.update({"cache_time": 40})
        except Exception as e:
            print(e)
            results = run_async(search_podcast, query_text).result()

    run_async(query.answer, list(results), **kwargs)


def show_subscription(user):
    subscriptions = user.subscriptions
    if not subscriptions:
        yield InlineQueryResultArticle(
            id=0,
            title='订阅列表还是空的 🥡',
            description=f'试着在 @{manifest.bot_id} 后面输入关键词，寻找喜欢的播客吧',
            input_message_content=InputTextMessageContent('🔍️'),
            reply_markup=InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    '搜索播客', switch_inline_query_current_chat='')
            )
        )
    else:
        for index, subscription in enumerate(subscriptions):
            podcast = subscription.podcast
            saved_flag = ''
            if subscription.is_saved:
                saved_flag = '  ⭐️'
            result = InlineQueryResultArticle(
                id=index,
                title=podcast.name + saved_flag,
                input_message_content=InputTextMessageContent(
                    podcast.name, parse_mode=None),
                description=podcast.host or podcast.name,
                thumb_url=podcast.logo,
                thumb_width=60,
                thumb_height=60
            )
            yield result


def search_saved(saved_type, user):
    pass
    # items = context.user_data[f'saved_{saved_type}'].items()
    # if not items:
    #     return [InlineQueryResultArticle(
    #         id=0,
    #         title="收藏夹还是空的",
    #         input_message_content=InputTextMessageContent('/manage 管理订阅的播客'),
    #         description='🥡',
    #     )]
    # return [InlineQueryResultArticle(
    #     id=uuid.uuid4(),
    #     title=item_name,
    #     input_message_content=InputTextMessageContent(
    #         item.name, parse_mode=None),
    #     description=item.host or item_name,
    #     thumb_url=item.logo,
    #     thumb_height=60,
    #     thumb_width=60
    # ) for item_name, item in items]


def show_episodes(podcast):
    episodes = podcast.episodes
    buttons = [
        InlineKeyboardButton("订阅列表", switch_inline_query_current_chat=""),
        InlineKeyboardButton(
            "单集列表", switch_inline_query_current_chat=f"{podcast.name}")
    ]
    for index, episode in enumerate(episodes):
        yield InlineQueryResultArticle(
            id=index,
            title=episode.title,
            input_message_content=InputTextMessageContent((
                f"[🎙️]({podcast.logo}) *{podcast.name}* #{len(episodes) - index}"
            )),
            reply_markup=InlineKeyboardMarkup.from_row(buttons),
            description=f"{episode.duration or podcast.name}\n{episode.subtitle}",
            thumb_url=podcast.logo,
            thumb_width=60,
            thumb_height=60
        )


def search_podcast(keyword):
    searched_results = search_itunes(keyword)
    if not searched_results:
        yield InlineQueryResultArticle(
            id='0',
            title="没有找到相关的播客呢 :(",
            description="换个关键词试试",
            input_message_content=InputTextMessageContent("🔍️"),
            reply_markup=InlineKeyboardMarkup.from_button(
                        InlineKeyboardButton(
                            '返回搜索', switch_inline_query_current_chat=keyword)
            )
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
