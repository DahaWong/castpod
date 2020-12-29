from telegram.ext import InlineQueryHandler
import callbacks.inline_query as callback

inline_query_handler = InlineQueryHandler(callback.handle_inline_query, run_async = True)

handlers=[inline_query_handler]