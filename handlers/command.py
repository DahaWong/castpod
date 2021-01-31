from telegram.ext import CommandHandler
import callbacks.command as callback

handlers = [
    CommandHandler('start', callback.start, pass_args=True),
    CommandHandler('about', callback.about),
    CommandHandler('favourites', callback.favourites),
    CommandHandler('manage', callback.manage),
    CommandHandler('export', callback.export, run_async=True),
    CommandHandler('setting', callback.setting, run_async=True),
    CommandHandler('help', callback.help, run_async=True),
    CommandHandler('logout', callback.logout, run_async=True)
]
