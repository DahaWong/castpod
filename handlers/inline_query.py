from telegram.ext import InlineQueryHandler
import callbacks.inline_query as callback
import re

inline_query_handler = InlineQueryHandler(callback.welcome)
"^podcast (\w+)",run_async = True)
"^podcast$",run_async = True)
"^\w*", run_async = True)

handlers=[inline_query_handler]