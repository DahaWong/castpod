from telegram.ext import InlineQueryHandler #, ChosenInlineResultHandler
import callbacks.inline_query as callback

inline_query_handler = InlineQueryHandler(callback.handle_inline_query)
# result_chosen_handler = ChosenInlineResultHandler(callback.handle_result_chosen)

handlers=[inline_query_handler]