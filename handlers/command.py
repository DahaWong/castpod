from telegram.ext import CommandHandler
import callbacks.command as callback

start_handler = CommandHandler('start', callback.start)
today_handler = CommandHandler('today', callback.today)
quit_handler = CommandHandler('quit', callback.quit_)
about_handler = CommandHandler('about', callback.about)