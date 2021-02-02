from telegram import InlineKeyboardMarkup, InlineKeyboardButton


class PodcastPage(object):
    def __init__(self, podcast, save_text="收藏", save_action="save_podcast"):
        self.podcast = podcast
        self.save_text = save_text
        self.save_action = save_action

    def text(self):
        email_info = f'\n✉️  {self.podcast.email}' if self.podcast.email else ''
        return (
            f'*{self.podcast.name}*'
            f'\n[🎙️]({self.podcast.logo})  {self.podcast.host or self.podcast.name}'
            f'{email_info}'
        )

    def keyboard(self):
        return [
            [InlineKeyboardButton("退订", callback_data=f"unsubscribe_podcast_{self.podcast.name}"),
             InlineKeyboardButton("关于", url=self.podcast.website),
             InlineKeyboardButton(self.save_text, callback_data=f"{self.save_action}_{self.podcast.name}")],
            [InlineKeyboardButton("订阅列表", switch_inline_query_current_chat=f""),
             InlineKeyboardButton("分集列表", switch_inline_query_current_chat=f"{self.podcast.name}")]
        ]


class ManagePage(object):
    def __init__(self, podcast_names, text="已启动管理面板"):
        self.podcast_names = podcast_names
        self.text = text

    def row(self, i):
        row = [name[:32] for index, name in enumerate(
            self.podcast_names) if index // 3 == i]
        return row

    def keyboard(self):
        podcasts_count = len(self.podcast_names)
        if not podcasts_count:
            return [['订阅列表是空的～']]
        rows_count = podcasts_count // 3 + bool(podcasts_count % 3)
        return [['╳']]+[self.row(i) for i in range(rows_count)]


class Tips(object):
    def __init__(self, from_command, text):
        self.command = from_command
        self.text = text

    def keyboard(self):
        return InlineKeyboardMarkup.from_button(
            InlineKeyboardButton(
                "✓", callback_data=f'close_tips_{self.command}')
        )

    def send(self, update, context):
        if self.command not in context.user_data.get('tips'):
            return
        update.message.reply_text(
            text=self.text,
            reply_markup=self.keyboard())
