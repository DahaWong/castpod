from castpod.constants import TICK_MARK
from telegram.ext import CallbackQueryHandler, MessageHandler, filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from ..models import Podcast
from config import dev, dev_name
RSS, CONFIRM, PHOTO = range(3)

async def request_host(update, context):
    await update.callback_query.edit_message_text(
        text="请输入您主持的播客的订阅源，也就是 RSS 地址：",
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton('什么是 RSS ？', callback_data='explain_rss')
        )
    )
    return RSS


async def explain_rss(update, context):
    await update.callback_query.edit_message_text(
        text="播客被托管给第三方平台后，听众只需知道 RSS 地址即可在泛用型播客客户端订阅。因此您应当可以在托管平台中找到它。",
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton('返回', callback_data='request_host')
        )
    )
    return -1


async def handle_rss(update, context):
    podcast = None
    # try:
    #     # 需要先处理 text 的格式，比如没带 https\大小写统一等问题
    #     podcast = Podcast.objects(feed=update.message.text).first()
    # except:
    #     pass  # 用 feedparser 处理 feed
    await update.message.reply_text(
        text=(
            f"播客名称："
            f"订阅地址："
            f"联系方式："
            f"请确认这是否是您主持的播客："
        ),
        reply_markup=InlineKeyboardMarkup.from_row(
            [InlineKeyboardButton('这不是我的播客', callback_data='deny_podcast'),
             InlineKeyboardButton('确认', callback_data=f'confirm_podcast_{podcast}')]
        )
    )
    return CONFIRM


async def handle_confirm(update, context):
    # re.match...
    podcast = None
    await update.callback_query.edit_message_text(
        text="接下来请发送一张截图，用来证明您的主播身份。\n\n（如：播客音频的后台管理界面、第三方平台的官方认证主页等等）",
        reply_markup=InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                "直接通过其他官方渠道联系我", callback_data=f'direct_contact_{podcast}')
        )
    )
    return PHOTO


async def deny_confirm(update, context):
    await update.callback_query.edit_message_text(
        text=f"如果没有找到您主持的播客，请联系我们",
        reply_markup=InlineKeyboardMarkup.from_row(([
            InlineKeyboardButton('重新申请认证', callback_data='request_host'),
            InlineKeyboardButton('联系客服', url=f'https://t.me/{dev_name}')
        ]))
    )
    return -1


async def verify_photo(update, context):
    user = update.effective_user
    await context.bot.send_photo(
        chat_id=dev,
        photo=update.message.photo[0],
        caption=f"{user.first_name} 想要成为 XX 播客的认证主播",
        reply_markup=InlineKeyboardMarkup.from_row(
            [
                InlineKeyboardButton(
                    '拒绝', callback_data=f"deny_host_{update.effective_user.id}"),
                InlineKeyboardButton(
                    '通过', callback_data=f"pass_host_{update.effective_user.id}"),
            ]
        )
    ).pin()
    await update.message.reply_text(
        text=f"图片上传成功，请耐心等待审核。\n\n审核通常会在一个工作日内完成，如果长时间没有收到回复，可直接联系我们",
        reply_markup=InlineKeyboardMarkup.from_button(
             InlineKeyboardButton('联系客服', url=f'https://t.me/{dev_name}')
        )
    )
    return -1


async def direct_contact(update, context):
    # 提醒用户是否为主播本人，否则将封号处理。这里需要进一步确认
    await context.bot.send_message(
        chat_id=dev,
        text=(
            f'{update.effective_user.first_name} 希望直接通过邮箱认证他的主播身份，邮件模板如下:\n\n'
            f'主题： `Castpod 主播认证`'
            f'正文：`XX 主播 XX 您好！我们收到了您（telegram 账号：XXX）在 Castpod 的认证申请。如果这是您本人发起的申请，请回复这封邮件以确认。（如：「确认申请 Castpod 认证主播。」） 若申请非您本人发起，请忽视本则邮件，原谅我们的无端叨扰。`'
        )
    ).pin()
    return -1


async def fallback(update, context):
    await update.message.reply_text(
        text='抱歉，没有理解您发来的消息。'
    )


request_host_handler = CallbackQueryHandler(
    request_host, pattern='^request_host$')
explain_rss_handler = CallbackQueryHandler(
    explain_rss, pattern='^explain_rss$')
rss_handler = MessageHandler(filters.TEXT, handle_rss)
confirm_podcast_handler = CallbackQueryHandler(
    handle_confirm, pattern='^confirm_podcast')
deny_confirm_handler = CallbackQueryHandler(
    deny_confirm, pattern='^deny_podcast')
photo_handler = MessageHandler(filters.PHOTO, verify_photo)
fallback_handler = MessageHandler(filters.ALL, fallback)
