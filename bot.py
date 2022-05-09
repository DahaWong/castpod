from telegram import BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats, BotCommandScopeAllChatAdministrators, BotCommandScopeChat
from telegram.ext import ApplicationBuilder
from castpod.handlers import register_handlers
from castpod.models import Podcast
import config
from mongoengine import connect
application = ApplicationBuilder().token(
    config.bot_token).defaults(config.defaults).base_url(config.bot_api).build()

# Use this method to logout your bot from official telegram api:
# application.bot.log_out()
# application.bot.delete_webhook()
# application.bot.close()

# Webhook:
# application.run_webhook(**config.webhook_info)

# Database:
connect(db=config.Mongo.db)
# username=Mongo.user, # for auth
# password=Mongo.pwd # for auth
# host=Mongo.remote_host # for remote test)


register_handlers(application)


async def update_podcasts(context):
    for podcast in Podcast.objects:
        message = podcast.check_update(context)
        if message:
            for subscriber in podcast.subscribers:
                await message.copy(subscriber.user_id)


# application.job_queue.run_repeating(
#     update_podcasts, 1200)  # runs every 1200 s (20 min)

# Set commands scope:
bot = application.bot
bot.set_my_commands(
    commands=config.private_commands, scope=BotCommandScopeAllPrivateChats())
bot.set_my_commands(
    commands=config.group_commands, scope=BotCommandScopeAllChatAdministrators())
bot.set_my_commands(
    commands=config.dev_commands, scope=BotCommandScopeChat(config.dev))

# Polling:
application.run_polling()
