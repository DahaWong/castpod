from telegram import (
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
)
from telegram.ext import Application, ApplicationBuilder, JobQueue
from castpod.callbacks.jobs import update_episodes

import config
from castpod.handlers import register_handlers
from castpod.models import db_init


async def post_init(app: Application) -> None:
    bot = app.bot
    # Use this method to logout your bot from official telegram api:
    # await bot.log_out()
    # await bot.delete_webhook()
    # await bot.close()
    await bot.set_my_commands(
        commands=config.private_commands, scope=BotCommandScopeAllPrivateChats()
    )
    await bot.set_my_commands(
        commands=config.group_commands, scope=BotCommandScopeAllChatAdministrators()
    )
    await bot.set_my_commands(
        commands=config.dev_commands, scope=BotCommandScopeChat(config.dev)
    )


app = (
    ApplicationBuilder()
    .token(config.bot_token)
    .defaults(config.defaults)
    .base_url(config.bot_api)
    .post_init(post_init)
    .write_timeout(180)
    .read_timeout(30)
    .concurrent_updates(True)
    .build()
)

register_handlers(app)
db_init()
job_queue: JobQueue = app.job_queue
job_queue.run_repeating(update_episodes, 900)
# job_queue.run_repeating(update_episodes, interval=900, first=5)
# Webhook:
app.run_webhook(
    listen="127.0.0.1",
    port=8443,
    url_path=config.bot_token,
    webhook_url=f"http://127.0.0.1:8443/{config.bot_token}",
    max_connections=80,
    drop_pending_updates=True,
)

# Polling:
# app.run_polling()
