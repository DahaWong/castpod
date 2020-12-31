from telegram.ext import CommandHandler
import callbacks.command as callback
import inspect

handlers=[]
for value in vars(callback).values():
  if inspect.isfunction(value):
      handler = value
      handlers.append(CommandHandler(handler.__name__, handler, pass_args=True))


