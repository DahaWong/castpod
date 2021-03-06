from config import dev, manifest
import sys
import html
import traceback
from telegram import ParseMode
import json

# def handle_error(update, context):
#     if not update:
#         return
#     if update.effective_message:
#         text = f"刚刚的操作触发了一个错误，报告已抄送给[开发者](https://t.me/{manifest.author_id})。"
#         update.effective_message.reply_text(text)
#     payload = ""
#     if update.effective_user:
#         payload += f"有[用户](tg://user?id={update.effective_user.id})"
#     if update.effective_chat and update.effective_chat.title:
#         payload += f"在{update.effective_chat.title}"
#         if update.effective_chat.username:
#             payload += f'(@{update.effective_chat.username})'
#     if update.poll:
#         payload += f'在发起投票 {update.poll.id} 时'
#     trace = "".join(traceback.format_tb(sys.exc_info()[2]))
#     text = f"{payload}触发了一个错误：`{context.error}`。\n\n"
#     text += f"错误路径如下:\n`{trace}`" if trace else ''
#     context.bot.send_message(dev, text)
#     raise context.error

import logging
logger = logging.getLogger(__name__)


def handle_error(update, context):
    if not update:
        return
    if update.effective_message:
        text = f"刚刚的操作触发了一个错误，报告已抄送给[开发者](https://t.me/{manifest.author_id})。"
        update.effective_message.reply_text(text)
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error(msg="Exception while handling an update:",
                 exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    message = (
        f'发生错误：\n'
        f'<pre>update = {html.escape(json.dumps(update.to_dict(), indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )

    # Finally, send the message
    context.bot.send_message(chat_id=dev,
                             text=message, parse_mode=ParseMode.HTML)
