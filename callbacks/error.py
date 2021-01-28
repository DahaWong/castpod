import html
import json
import logging
import traceback

from telegram.parsemode import ParseMode
from config import dev_user_id
from telegraph import Telegraph
from manifest import manifest

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def handle_error(update, context):
    logger.error(msg="发生错误：\n", exc_info=context.error)

    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)

    message = (
        f'⚠️ 发生错误：\n'
        f'<pre>update = {html.escape(json.dumps(update.to_dict(), indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )

    context.bot.send_message(
        chat_id=int(dev_user_id),
        text=message,
        parse_mode=ParseMode.HTML
    )

    # telegraph = Telegraph()
    # telegraph.create_account(
    #     short_name=manifest.name,
    #     author_name=manifest.name,
    #     author_url=f'https://t.me/{manifest.bot_id}'
    # )

    # res = telegraph.create_page(
    #     title=f"Castpod 错误日志",
    #     html_content=message,
    #     author_name=manifest.name
    # )

    # context.bot.send_message(
    #     chat_id=int(dev_user_id),
    #     text=f"[错误日志](https://telegra.ph/{res['path']}) #{datetime.date.today()}"
    # )
