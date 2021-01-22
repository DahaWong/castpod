from telegram.ext import MessageHandler, Filters
import callbacks.message as callback

subscription_handler = MessageHandler(
    Filters.document.mime_type('text/xml') | Filters.document.file_extension("opml") | Filters.document.file_extension("opm"), 
    callback.save_subscription
)

feed_handler = MessageHandler(Filters.entity("url") & Filters.regex(r'^https?://'), callback.subscribe_feed)
exit_handler = MessageHandler(Filters.regex(r'^╳$'), callback.exit_reply_keyboard)
show_feed = MessageHandler(Filters.text, callback.show_feed)

handlers=[feed_handler, subscription_handler, exit_handler, show_feed]