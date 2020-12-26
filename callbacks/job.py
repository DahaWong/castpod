from config import podcast_vault

def update_podcasts(context):
    podcasts = context.bot_data['podcasts']
    for podcast in podcasts.values():
        latest_episode = podcast.update()
        if latest_episode:
            bot = context.bot
            audio_message = bot.send_audio(
                chat_id = podcast_vault,
                audio = latest_episode.url,
                caption = latest_episode.discription,
                title = latest_episode.title,
                performer = podcast.host,
                thumb = podcast.logo
            )
            latest_episode.vault_url = f"https://t.me/{podcast_vault}/{audio_message.message_id}"

# 自定义的更新周期应划分为几个档：30min, 1h, 6h, 1day ...?
def forward_to_user():
    pass

