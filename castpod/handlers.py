from castpod.callbacks import *
from .constants import CLOSE_MARK, SPEAKER_MARK, STAR_MARK, DOC_MARK
from telegram.ext import (
    MessageHandler,
    filters,
    InlineQueryHandler,
    CommandHandler,
    CallbackQueryHandler,
)
from telegram import Chat
import inspect

RSS, CONFIRM, PHOTO = range(3)


def register_handlers(application):
    handlers = []

    for value in vars(callback_query).values():
        if inspect.isfunction(value):
            callback_query_handler = CallbackQueryHandler(
                value, pattern=f"^{value.__name__}"
            )
            handlers.append(callback_query_handler)

    handlers.extend(
        [
            CommandHandler("start", command.start, filters=filters.ChatType.PRIVATE),
            # CommandHandler('manage', command.manage),
            # CommandHandler('star', command.star),
            CommandHandler("search", command.search, block=False),
            # CommandHandler('favorite', command.favorite, block=False),
            # CommandHandler('share', command.share, block=False),
            CommandHandler("help", command.help_, block=False),
            CommandHandler("about", command.about, block=False),
            MessageHandler(
                filters.ChatType.PRIVATE & filters.Entity("url"),
                message.subscribe_feed,
            ),
            # MessageHandler(
            #     filters.Regex(f'{SPEAKER_MARK} (.+) #([0-9]+)'), message.download_episode, block=False),
            # MessageHandler(
            #     filters.Regex(f'^{CLOSE_MARK}$'),
            #     message.close_reply_keyboard,
            #     block=False
            # ),
            # MessageHandler(
            #     filters.Regex(f'^{STAR_MARK}$'),
            #     command.star,
            #     block=False
            # ),
            # MessageHandler(
            #     filters.Regex(f'^{DOC_MARK}$'),
            #     command.manage,
            #     block=False
            # ),
            # MessageHandler(
            #     filters.Regex(r'^探索播客世界$'),
            #     message.search_podcast,
            #     block=False
            # ),
            # MessageHandler(
            #     filters.ChatType.PRIVATE &
            #     (filters.Document.MimeType('text/xml') |
            #      filters.Document.FileExtension("opml") |
            #      filters.Document.FileExtension("opm")),
            #     message.save_subscription,
            #     block=False
            # ),
            # MessageHandler(
            #     (
            #         filters.REPLY |
            #         filters.ChatType.PRIVATE
            #     ) &
            #     filters.TEXT, message.show_podcast
            # ),
            # MessageHandler(filters.Chat(username="podcast_vault_chat")
            #                & filters.AUDIO, message.handle_audio),
            # MessageHandler(
            #     filters.StatusUpdate.PINNED_MESSAGE,
            #     message.delete_message
            # ),
            InlineQueryHandler(inline_query.via_sender, chat_types=[Chat.SENDER]),
            # InlineQueryHandler(inline_query.via_private,
            #                    chat_types=[Chat.PRIVATE]),
            # InlineQueryHandler(inline_query.via_group, chat_types=[
            #                    Chat.GROUP, Chat.SUPERGROUP]),
            # InlineQueryHandler(inline_query.via_channel,
            #                    chat_types=[Chat.CHANNEL]),
        ]
    )

    for handler in handlers:
        application.add_handler(handler)
    application.add_error_handler(error.handle_error)
