from telegram.ext import CallbackQueryHandler, MessageHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
RSS, CONFIRM, PHOTO = range(3)


def request_host(update, context):
    update.callback_query.edit_message_text(
        text="请输入您主持的播客的订阅源，也就是 RSS 地址：",
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton('什么是 RSS？', callback_data='explain_rss')
        )
    )
    return RSS


def explain_rss(update, context):
    update.callback_query.edit_message_text(
        text="我们将播客节目托管给第三方平台后，听众只需知道 RSS 地址即可在泛用型播客客户端订阅。因此您应当可以在托管平台找到它。",
        reply_markup=InlineKeyboardMarkup.from_button(
            '返回', callback_data=request_host)
    )
    return RSS


def parse_rss(update, context):
    rss = update.message.text
    return CONFIRM


def confirm_podcast(update, context):
    update.message.reply_text(
        text=(
            f"播客名称：",
            f"订阅地址：",
            f"联系方式：",
            f"请确认这是否是您主持的播客："
        ),
        reply_markup=InlineKeyboardMarkup.from_row(
            [InlineKeyboardButton('这不是我的播客'),
             InlineKeyboardButton('确认')]
        )
    )
    return PHOTO


def verify_info(update, context):
    update.callback_query.edit_message_text(
        text="请发送一张截图，用来证明您的主播身份。\n\n（比如，播客音频的后台管理界面、第三方平台的官方认证主页等等）",
        reply_markup="直接用我在官方渠道留下的联系方式沟通吧"
    )
    return -1


def fallback(update, context):
    update.message.reply_text(
        text='抱歉，没有理解您的指令。请重新申请主播认证。',
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton('申请主播认证', callback_data='request_host')
        )
    )
    return -1


request_host_handler = CallbackQueryHandler(
    request_host, pattern='^request_host$')
explain_rss_handler = CallbackQueryHandler(
    explain_rss, pattern='^explain_rss$')
parse_rss_handler = MessageHandler(Filters.text, parse_rss)
verify_info_handler = CallbackQueryHandler(Filters.photo, verify_info)
fallback_handler = MessageHandler(Filters.all, fallback)
