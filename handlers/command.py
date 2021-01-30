from telegram.ext import CommandHandler
import callbacks.command as callback

handlers=[
  CommandHandler('start', callback.start, pass_args=True),
  CommandHandler('about', callback.about),
  CommandHandler('home', callback.home),
  CommandHandler('manage', callback.manage),
  CommandHandler('settings', callback.settings, run_async=True),
  CommandHandler('help', callback.help, run_async=True),
  CommandHandler('logout', callback.logout, run_async=True)
]
  


