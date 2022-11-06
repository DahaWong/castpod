from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from config import manifest


class PodcastPage(object):
    def __init__(self, podcast, mode="private"):
        self.podcast = podcast
        self.mode = mode

    def text(self):
        host = f"主播：{self.podcast.host}" if self.podcast.host else ""
        email = f"\n信箱： {self.podcast.email}" if self.podcast.email else ""
        line_break = "\n\n" if host or email else ""
        return f"#<b>{self.podcast.name}</b>{line_break}{host}{email}"

    def keyboard(self):
        if self.mode == "private":
            return [
                [
                    InlineKeyboardButton(
                        "退订", callback_data=f"unsubscribe_podcast_{self.podcast.id}"
                    ),
                    InlineKeyboardButton("我的订阅", switch_inline_query_current_chat=""),
                    InlineKeyboardButton(
                        "分享", switch_inline_query=f"{self.podcast.name}"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "查看单集", switch_inline_query_current_chat=f"{self.podcast.name}#"
                    )
                ],
            ]
        elif self.mode == "group":
            return [
                [
                    InlineKeyboardButton(
                        "订阅", url=f"https://t.me/{manifest.bot_id}?start={podcast.id}"
                    ),
                ]
            ]
