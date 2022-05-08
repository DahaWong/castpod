from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from .constants import QUIT_MARK, TICK_MARK, SPEAKER_MARK, STAR_MARK


class PodcastPage(object):
    def __init__(self, podcast, fav_text="收藏", fav_action="fav_podcast", mode="private"):
        self.podcast = podcast
        self.fav_text = fav_text
        self.fav_action = fav_action
        self.mode = mode

    def text(self):
        email = f'\n✉️  {self.podcast.email}' if self.podcast.email else ''
        return (
            f'<b>{self.podcast.name}</b>'
            f'\n{SPEAKER_MARK} {self.podcast.host or self.podcast.name}'
            f'{email}'
        )

    def keyboard(self):
        if self.mode == 'private':
            return [
                [InlineKeyboardButton("退订", callback_data=f"unsubscribe_podcast_{self.podcast.id}"),
                 InlineKeyboardButton(self.fav_text, callback_data=f"{self.fav_action}_{self.podcast.id}"),
                 InlineKeyboardButton("分享", switch_inline_query=f"{self.podcast.name}")],
                [InlineKeyboardButton("订阅列表", switch_inline_query_current_chat=f""),
                 InlineKeyboardButton("分集列表", switch_inline_query_current_chat=f"{self.podcast.name}#")]
            ]
        elif self.mode == 'group':
            return [
                [InlineKeyboardButton("订阅列表", switch_inline_query_current_chat=f""),
                 InlineKeyboardButton("分集列表", switch_inline_query_current_chat=f"{self.podcast.name}#")]
            ]


class ManagePage(object):
    def __init__(self, podcasts, text="已启动管理面板"):
        self.podcasts = podcasts
        self.text = text

    def row(self, i):
        row = [podcast.name for index, podcast in enumerate(
            self.podcasts) if index // 3 == i]
        return row

    def keyboard(self, null_text='探索播客世界', jump_to=STAR_MARK):
        podcasts_count = self.podcasts.count()
        if not podcasts_count:
            return [[QUIT_MARK, jump_to],[null_text]]
        rows_count = podcasts_count // 3 + bool(podcasts_count % 3)
        return [[QUIT_MARK, jump_to]]+[self.row(i) for i in range(rows_count)]


class Tips(object):
    def __init__(self, from_command, text):
        self.command = from_command
        self.text = text

    def keyboard(self):
        return InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                TICK_MARK, callback_data=f'close_tips_{self.command}')
        )

    async def send(self, update, context):
        if self.command not in context.user_data.get('tips'):
            return
        await update.message.reply_text(
            text=self.text,
            reply_markup=self.keyboard())
