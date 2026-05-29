import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, ConversationHandler, CommandHandler
from mutagen import File as MutagenFile
import tempfile
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CHANNEL_USERNAME = "AstralChords"

WAITING_FOR_INFO = 1


def get_music_metadata(file_path):
    try:
        audio = MutagenFile(file_path)
        if audio is None:
            return None, None
        tags = audio.tags
        if tags is None:
            return None, None

        artist = None
        title = None

        if hasattr(tags, 'get'):
            artist = str(tags.get('TPE1', tags.get('artist', tags.get('Author', '')))).strip() or None
            title = str(tags.get('TIT2', tags.get('title', tags.get('Title', '')))).strip() or None

        if not artist or not title:
            for key in tags.keys():
                k = key.lower()
                if 'artist' in k and not artist:
                    val = tags[key]
                    artist = str(val[0] if isinstance(val, list) else val).strip()
                if 'title' in k and not title:
                    val = tags[key]
                    title = str(val[0] if isinstance(val, list) else val).strip()

        return artist or None, title or None
    except Exception as e:
        logger.error(f"Metadata error: {e}")
        return None, None


def generate_hashtags(artist, title):
    prompt = f"""You are a music expert. Given the song "{title}" by "{artist}", identify 4-5 of the most accurate music genre hashtags.

Rules:
- Return ONLY the hashtags, one per line
- No explanations, no extra text
- Format: #GenreName (PascalCase, no spaces)
- Example output:
#AlternativeRock
#GrungeRock
#90sRock
#IndieRock

Now generate hashtags for "{title}" by "{artist}":"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    response = requests.post(url, json={
        "contents": [{"parts": [{"text": prompt}]}]
    })
    
    data = response.json()
   if "candidates" not in data:
        logger.error(f"Gemini error: {data}")
        raise Exception(f"Gemini API error: {data}")
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def build_caption(hashtags):
    lines = hashtags.strip().split('\n')
    linked_lines = []
    
    for line in lines:
        tag = line.strip()
        if tag.startswith('#'):
            linked_lines.append(f'<a href="https://t.me/{CHANNEL_USERNAME}">{tag}</a>')
    
    caption = '\n'.join(linked_lines)
    caption += f'\n\n<a href="https://t.me/{CHANNEL_USERNAME}">φ</a>'
    return caption


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    audio = message.audio or message.document
    
    if not audio:
        return
    
    file = await context.bot.get_file(audio.file_id)
    
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
        tmp_path = tmp.name
    
    await file.download_to_drive(tmp_path)
    artist, title = get_music_metadata(tmp_path)
    os.unlink(tmp_path)
    
    if artist and title:
        await process_song(update, context, artist, title)
    else:
        context.user_data['pending'] = True
        await message.reply_text(
            "❓ نتونستم اطلاعات آهنگ رو بخونم.\n\nلطفاً اسم آهنگ و خواننده رو بفرست:\n(مثال: Radiohead - Man of War)"
        )
        return WAITING_FOR_INFO


async def handle_manual_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if ' - ' in text:
        parts = text.split(' - ', 1)
        artist = parts[0].strip()
        title = parts[1].strip()
    else:
        await update.message.reply_text("❌ فرمت اشتباهه:\nRadiohead - Man of War")
        return WAITING_FOR_INFO
    
    await process_song(update, context, artist, title)
    return ConversationHandler.END


async def process_song(update: Update, context: ContextTypes.DEFAULT_TYPE, artist: str, title: str):
    msg = await update.message.reply_text(f"🎵 در حال پردازش: {title} - {artist}...")
    
    try:
        hashtags = generate_hashtags(artist, title)
        caption = build_caption(hashtags)
        
        await msg.edit_text(
            f"✅ کپشن آماده شد!\n\n{caption}\n\n<code>{caption}</code>",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error: {e}\n{traceback.format_exc()}")
        await msg.edit_text("❌ خطایی پیش اومد. دوباره امتحان کن.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎸 سلام! بات کانال Astral Chords\n\nیه فایل موزیک بفرست تا کپشن بسازم! 🤘"
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.AUDIO | filters.Document.AUDIO, handle_audio)],
        states={
            WAITING_FOR_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_info)],
        },
        fallbacks=[],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    
    logger.info("Bot started!")
    app.run_polling()


if __name__ == '__main__':
    main()
