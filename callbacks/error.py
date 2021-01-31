from config import dev_user_id, manifest
import sys
import traceback

def handle_error(update, context):
    if not update:
        return
    if update.effective_message:
        text = f"刚刚的操作触发了一个错误，报告已抄送给[开发者](https://t.me/{manifest.author_id})。"
        update.effective_message.reply_text(text)
    payload = ""
    if update.effective_user:
        payload += f"有[用户](tg://user?id={update.effective_user.id})在使用中"
    if update.effective_chat.title:
        payload += update.effective_chat.title
        if update.effective_chat.username:
            payload += f'(@{update.effective_chat.username})'
    if update.poll:
        payload += f'投票 {update.poll.id} '
    trace = "".join(traceback.format_tb(sys.exc_info()[2]))
    text = f"{payload}触发了一个错误：`{context.error}`。\n\n错误路径如下:\n\n`{trace}`"
    context.bot.send_message(dev_user_id, text)
    