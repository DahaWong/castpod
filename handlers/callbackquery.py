from telegram.ext import CallbackQueryHandler
import callbacks.callbackquery as callback

handlers=[]

for handler in vars(callback).values():
  if inspect.isfunction(handler):
      CallbackQueryHandler(handler, f"^{handler.__name__}$")
      handlers.append(handlers)
