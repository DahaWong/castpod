from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import utils.delete_message as del_msg
from utils.persistence import bot_persistence
from utils.date import get_today,is_today
import datetime

def start(update, context):
    USERNAME = 0
    END = -1
    if not context.user_data.__contains__('logged_in'):
        keyboard_lan = [
            [InlineKeyboardButton("注 册", url='https://www.instapaper.com/'),
            InlineKeyboardButton("登 入", callback_data='login_confirm')]
        ]
        markup = InlineKeyboardMarkup(keyboard_lan)
        message = update.message.reply_text(
            '欢迎使用 Instasaver！\n开始使用前，请先登录您的账号。', 
            reply_markup=markup
        )
        del_msg.later(update, context, message)
        return USERNAME
    else:
        message = update.message.reply_text(
            '您已登录成功，可以直接使用！'
        )
        del_msg.later(update, context, message)
        return END

def quit_(update, context):
    CONFIRM_QUIT = 0
    END = -1
    if context.user_data.__contains__('logged_in'):
        keyboard = [
            [InlineKeyboardButton("返 回", callback_data='cancel_quit'),
             InlineKeyboardButton("解 绑", callback_data='confirm_quit')
            ]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        message = update.message.reply_text(
                '确认解绑账号吗？', 
                reply_markup=markup
            )
        del_msg.later(update, context, message)
        return CONFIRM_QUIT
    else:
        message = update.message.reply_text("你还没有登入呢。\n前往：/start")
        del_msg.later(update, context, message)
        return END

def today(update, context):
    message = update.message
    today = datetime.date.today() + datetime.timedelta(hours=8)
    year, month, day = today.year, today.month, today.day
    if context.user_data.__contains__('logged_in'):
        if not is_today(context.user_data['today']['date']):
            context.user_data['today'].clear()
            context.user_data['today']['date'] = get_today()
            bot_persistence.flush()
        else:
            message_body = f'`{year}\-{month}\-{day}`\n\n'
            articles_today = filter(lambda x: not isinstance(x,datetime.date), context.user_data['today'].values())
            if list(articles_today):
                count = 0
                for article in articles_today:
                    count += 1
                    title, link = article['title'], article['link']
                    message_body += f"{count}\. [{title}]({link})\n\n"
                msg = context.bot.send_message(
                    chat_id=message.chat_id,
                    message_id=message.message_id,
                    text=message_body,
                    parse_mode="MarkdownV2",
                    disable_web_page_preview=True,
                    reply_to_message_id=message.message_id
                )
                del_msg.later(update, context, msg)
            else:
                msg = message.reply_text('今天还没有保存文章呢')
                del_msg.later(update, context, msg, timeup=2)     
    else:
        message = update.message.reply_text("你还没有登入呢。\n前往：/start")
        del_msg.later(update, context, message)

def about(update, context):
    keyboard = [[InlineKeyboardButton("源    代    码", url='https://github.com/dahawong/instasaver-bot')],
                [InlineKeyboardButton("工    作    室", url='https://office.daha.me/')]]
    markup = InlineKeyboardMarkup(keyboard)
    msg = update.message.reply_markdown('*Instasaver*  `2.0.4`', reply_markup=markup)
    del_msg.later(update, context, msg)
