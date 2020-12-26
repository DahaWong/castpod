from config import podcast_vault

def update_podcasts(context):
    podcasts = context.bot_data['podcasts']
    for podcast in podcasts.values():
        need_update = podcast.update()
        if need_update:
            bot = context.bot
            episode = podcast.latest_episode # :Episode class
            audio_message = bot.send_audio(
                chat_id = podcast_vault,
                audio = episode.url,
                caption = episode.discription,
                title = episode.title,
                performer = podcast.host,
                thumb = podcast.logo
            )

# 自定义的更新周期应划分为几个档：30min, 1h, 6h, 1day ...?
def forward_to_user():
    pass

