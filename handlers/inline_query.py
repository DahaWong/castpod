from telegram.ext import InlineQueryHandler
import callbacks.inline_query as callback
import re

inline_query_handler = InlineQueryHandler(callback.handle_inline_query)

handlers=[inline_query_handler]