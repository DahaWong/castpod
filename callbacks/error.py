from config import dev_user_id
from manifest import manifest
from telegram import ParseMode
from telegram.utils.helpers import mention_html
import sys
import traceback
import logging 

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def handle_error(update, context):
    if update.effective_message:
        text = f"刚刚的操作触发了一个错误，报告已抄送给[开发者](https://t.me/{manifest.author_id})。"
        update.effective_message.reply_text(text)
    trace = "".join(traceback.format_tb(sys.exc_info()[2]))
    payload = ""
    if update.effective_user:
        payload += f'{mention_html(update.effective_user.id, update.effective_user.first_name)}'
    if update.effective_chat:
        payload += f'<i>{update.effective_chat.title}</i>'
        if update.effective_chat.username:
            payload += f'(@{update.effective_chat.username})'
    if update.poll:
        payload += f'投票 {update.poll.id}'
    text = f"{payload} 触发了一个错误：<code>{context.error}</code>。错误路径如下:\n\n<code>{trace}" \
           f"</code>"
    context.bot.send_message(dev_user_id, text, parse_mode=ParseMode.HTML)
    logger.error(msg="发生异常：\n", exc_info=context.error)
