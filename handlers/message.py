from telegram.ext import MessageHandler, Filters
import callbacks.message as callback

subscription_handler = MessageHandler(
    Filters.document.mime_type('text/xml') | Filters.document.mime_type('application/octet-stream'), 
    callback.save_subscription
)

feed_handler = MessageHandler(Filters.entity("url") & Filters.regex(r'^https?://'), callback.subscribe_via_add)
subscribe_handler = MessageHandler(Filters.regex(r'订阅源：'), callback.subscribe_via_search)
text_handler = MessageHandler(Filters.regex(r'^退出'), callback.handle_exit)

handlers=[feed_handler, subscription_handler, text_handler, subscribe_handler]