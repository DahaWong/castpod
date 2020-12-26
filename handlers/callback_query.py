from telegram.ext import CallbackQueryHandler
import callbacks.callback_query as callback
import inspect

handlers=[]

for handler in vars(callback).values():
  if inspect.isfunction(handler):
      callback_query_handler = CallbackQueryHandler(handler, pattern=f"^{handler.__name__}")
      handlers.append(callback_query_handler)
