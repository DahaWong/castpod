from telegram.ext import MessageHandler, Filters
import callbacks.message as callback

handlers = [
    MessageHandler(
        Filters.entity("url") & Filters.regex(r'^https?://'), callback.subscribe_feed),
    MessageHandler(
        Filters.regex(r'🎙️ (.+) #([0-9]+)'), callback.download_episode),
    MessageHandler(
        Filters.regex(r'^╳$') |
        Filters.regex(r'^订阅列表是空的～$'), callback.exit_reply_keyboard, run_async=True),
    MessageHandler(
        Filters.document.mime_type('text/xml') |
        Filters.document.file_extension("opml") |
        Filters.document.file_extension("opm"),
        callback.save_subscription
    ),
    MessageHandler(Filters.text, callback.show_feed),
    MessageHandler(Filters.audio, callback.handle_audio)
]
