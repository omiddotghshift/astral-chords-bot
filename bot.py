import os
import logging
import anthropic
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, ConversationHandler, CommandHandler
from mutagen import File as MutagenFile
from mutagen.id3 import ID3NoHeaderError
import tempfile

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CHANNEL_USERNAME = "AstralChords"

# States
WAITING_FOR_INFO = 1

# Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, http_client=None)

def get_music_metadata(file_path):
    """Extract artist and title from audio file metadata."""
    try:
        audio = MutagenFile(file_path)
        if audio is None:
            return None, None
        
        tags = audio.tags
        if tags is None:
            return None, None

        # Try common tag formats
        artist = None
        title = None

        # ID3 (MP3)
        if hasattr(tags, 'get'):
            artist = str(tags.get('TPE1', tags.get('artist', tags.get('Author', '')))).strip() or None
            title = str(tags.get('TIT2', tags.get('title', tags.get('Title', '')))).strip() or None
        
        # Try as dict
        if not artist and not title:
            for key in tags.keys():
                k = key.lower()
                if 'artist' in k and not artist:
                    artist = str(tags[key][0] if isinstance(tags[key], list) else tags[key]).strip()
                if 'title' in k and not title:
                    title = str(tags[key][0] if isinstance(tags[key], list) else tags[key]).strip()

        return artist or None, title or None
    except Exception as e:
        logger.error(f"Metadata error: {e}")
        return None, None


def generate_hashtags(artist, title):
    """Use Claude to generate genre hashtags."""
    prompt = f"""You are a music expert. Given the song "{title}" by "{artist}", identify 4-5 of the most accurate music genre hashtags.

Rules:
- Return ONLY the hashtags, one per line
- No explanations, no extra text
- Format: #GenreName (PascalCase, no spaces)
- Focus on the most specific and accurate genres
- Example output:
#AlternativeRock
#GrungeRock
#90sRock
#IndieRock

Now generate hashtags for "{title}" by "{artist}":"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text.strip()


def build_caption(hashtags):
    """Build the final caption with linked hashtags and phi symbol."""
    lines = hashtags.strip().split('\n')
    linked_lines = []
    
    for line in lines:
        tag = line.strip()
        if tag.startswith('#'):
            # Make hashtag link to channel
            linked_lines.append(f'<a href="https://t.me/{CHANNEL_USERNAME}">{tag}</a>')
    
    caption = '\n'.join(linked_lines)
    caption += f'\n\n<a href="https://t.me/{CHANNEL_USERNAME}">φ</a>'
    
    return caption


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming audio files."""
    message = update.message
    audio = message.audio or message.document
    
    if not audio:
        return
    
    # Download the file
    file = await context.bot.get_file(audio.file_id)
    
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
        tmp_path = tmp.name
    
    await file.download_to_drive(tmp_path)
    
    # Extract metadata
    artist, title = get_music_metadata(tmp_path)
    os.unlink(tmp_path)
    
    if artist and title:
        # We have the info, generate caption
        await process_song(update, context, artist, title)
    else:
        # Ask user for info
        context.user_data['pending_audio_id'] = audio.file_id
        await message.reply_text(
            "❓ نتونستم اطلاعات آهنگ رو از فایل بخونم.\n\nلطفاً اسم آهنگ و خواننده رو بفرست:\n(مثال: Radiohead - Man of War)"
        )
        return WAITING_FOR_INFO


async def handle_manual_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle manually entered song info."""
    text = update.message.text.strip()
    
    if ' - ' in text:
        parts = text.split(' - ', 1)
        artist = parts[0].strip()
        title = parts[1].strip()
    else:
        await update.message.reply_text("❌ فرمت اشتباهه. لطفاً اینطوری بنویس:\nRadiohead - Man of War")
        return WAITING_FOR_INFO
    
    await process_song(update, context, artist, title)
    return ConversationHandler.END


async def process_song(update: Update, context: ContextTypes.DEFAULT_TYPE, artist: str, title: str):
    """Generate and send caption for a song."""
    msg = await update.message.reply_text(f"🎵 در حال پردازش: {title} - {artist}...")
    
    try:
        hashtags = generate_hashtags(artist, title)
        caption = build_caption(hashtags)
        
        await msg.edit_text(
            f"✅ کپشن آماده شد!\n\n{caption}\n\n<code>{caption}</code>",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error: {e}")
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
