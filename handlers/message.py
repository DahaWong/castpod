from telegram.ext import MessageHandler, Filters
import callbacks.message as callback

subscription_handler = MessageHandler(
    Filters.document.mime_type('text/xml') | Filters.document.file_extension(
        "opml") | Filters.document.file_extension("opm"),
    callback.save_subscription
)

handlers = [
    MessageHandler(
        Filters.entity("url") & Filters.regex(r'^https?://'), callback.subscribe_feed),
    MessageHandler(
        Filters.regex(r'🎙️ (.+) #([0-9]+)'), callback.download_episode),
    MessageHandler(Filters.text, callback.show_feed),
    MessageHandler(Filters.regex(r'^╳$'), callback.exit_reply_keyboard, run_async=True),
    MessageHandler(Filters.audio, callback.handle_audio)
]
