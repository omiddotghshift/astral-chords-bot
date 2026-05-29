import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, ConversationHandler, CommandHandler
from mutagen import File as MutagenFile
import tempfile
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = "AstralChords"

WAITING_FOR_INFO = 1

# Genre database
ARTIST_GENRES = {
    # Metal
    "metallica": ["#HeavyMetal", "#ThrashMetal", "#HardRock", "#MetalClassics"],
    "black sabbath": ["#HeavyMetal", "#DoomMetal", "#ClassicRock", "#MetalOrigins"],
    "iron maiden": ["#HeavyMetal", "#BritishMetal", "#PowerMetal", "#ClassicMetal"],
    "slayer": ["#ThrashMetal", "#HeavyMetal", "#SpeedMetal", "#DeathmMetal"],
    "megadeth": ["#ThrashMetal", "#HeavyMetal", "#SpeedMetal", "#MetalClassics"],
    "pantera": ["#GrooveMetal", "#HeavyMetal", "#ThrashMetal", "#HardRock"],
    "tool": ["#ProgressiveMetal", "#AlternativeMetal", "#HeavyMetal", "#ArtRock"],
    "system of a down": ["#AlternativeMetal", "#HeavyMetal", "#NuMetal", "#ProgressiveRock"],
    "rammstein": ["#IndustrialMetal", "#HeavyMetal", "#GermanMetal", "#NeueDeutscheHärte"],
    "marilyn manson": ["#IndustrialMetal", "#GothicRock", "#ShockRock", "#AlternativeMetal"],
    "nine inch nails": ["#IndustrialRock", "#AlternativeRock", "#ElectronicRock", "#DarkWave"],
    "korn": ["#NuMetal", "#AlternativeMetal", "#HeavyMetal", "#GrooveMetal"],
    "linkin park": ["#NuMetal", "#AlternativeRock", "#RapRock", "#PopRock"],
    "slipknot": ["#NuMetal", "#HeavyMetal", "#AlternativeMetal", "#GrooveMetal"],
    "disturbed": ["#NuMetal", "#HeavyMetal", "#AlternativeMetal", "#HardRock"],
    "a7x": ["#HeavyMetal", "#MetalCore", "#HardRock", "#ProgressiveMetal"],
    "avenged sevenfold": ["#HeavyMetal", "#MetalCore", "#HardRock", "#ProgressiveMetal"],
    "falling in reverse": ["#PostHardcore", "#MetalCore", "#AlternativeMetal", "#HardRock"],
    # Rock
    "radiohead": ["#AlternativeRock", "#ArtRock", "#ExperimentalRock", "#PostRock"],
    "pink floyd": ["#ProgressiveRock", "#PsychedelicRock", "#ArtRock", "#ClassicRock"],
    "led zeppelin": ["#HardRock", "#ClassicRock", "#BluesRock", "#HeavyMetal"],
    "the doors": ["#PsychedelicRock", "#ClassicRock", "#BluesRock", "#ArtRock"],
    "nirvana": ["#Grunge", "#AlternativeRock", "#IndieRock", "#HardRock"],
    "pearl jam": ["#Grunge", "#AlternativeRock", "#HardRock", "#ClassicRock"],
    "soundgarden": ["#Grunge", "#AlternativeRock", "#HardRock", "#PsychedelicRock"],
    "alice in chains": ["#Grunge", "#HeavyMetal", "#AlternativeRock", "#DoomMetal"],
    "the smashing pumpkins": ["#AlternativeRock", "#Grunge", "#IndieRock", "#GothicRock"],
    "david bowie": ["#GlamRock", "#ArtRock", "#NewWave", "#ClassicRock"],
    "queen": ["#ClassicRock", "#GlamRock", "#HardRock", "#ArtRock"],
    "the rolling stones": ["#ClassicRock", "#BluesRock", "#HardRock", "#BritishRock"],
    "the beatles": ["#ClassicRock", "#BritishRock", "#PsychedelicRock", "#PopRock"],
    "u2": ["#AlternativeRock", "#PostPunk", "#NewWave", "#PopRock"],
    "coldplay": ["#AlternativeRock", "#BritPop", "#PostBritPop", "#IndieRock"],
    "muse": ["#AlternativeRock", "#ProgressiveRock", "#SpaceRock", "#ArtRock"],
    "oscar and the wolf": ["#DreamPop", "#ElectroPop", "#AlternativeMusic", "#EmotionalElectronic"],
    "the white buffalo": ["#DarkFolk", "#SouthernGothic", "#FolkRock", "#DarkAtmosphere"],
    "white buffalo": ["#DarkFolk", "#SouthernGothic", "#FolkRock", "#DarkAtmosphere"],
}

KEYWORD_GENRES = {
    "metal": ["#HeavyMetal", "#Metal", "#HardRock", "#MetalCore"],
    "rock": ["#Rock", "#AlternativeRock", "#HardRock", "#ClassicRock"],
    "punk": ["#PunkRock", "#HardcorePunk", "#PostPunk", "#AlternativeRock"],
    "grunge": ["#Grunge", "#AlternativeRock", "#HardRock", "#IndieRock"],
    "indie": ["#IndieRock", "#AlternativeRock", "#IndiePop", "#DreamPop"],
    "dark": ["#DarkRock", "#GothicRock", "#DarkWave", "#PostPunk"],
    "death": ["#DeathMetal", "#HeavyMetal", "#BrutalMetal", "#ExtremeMetal"],
    "black": ["#BlackMetal", "#HeavyMetal", "#ExtremeMetal", "#AtmosphericMetal"],
    "doom": ["#DoomMetal", "#SlowMetal", "#HeavyMetal", "#DarkMetal"],
    "progressive": ["#ProgressiveRock", "#ProgressiveMetal", "#ArtRock", "#ExperimentalRock"],
    "psychedelic": ["#PsychedelicRock", "#ExperimentalRock", "#ArtRock", "#SpaceRock"],
    "folk": ["#FolkRock", "#AcousticRock", "#AlternativeFolk", "#Americana"],
    "blues": ["#BluesRock", "#ClassicBlues", "#HardRock", "#SouthernRock"],
    "industrial": ["#IndustrialRock", "#IndustrialMetal", "#ElectronicRock", "#DarkWave"],
    "gothic": ["#GothicRock", "#DarkWave", "#PostPunk", "#DarkRock"],
    "classic": ["#ClassicRock", "#HardRock", "#VintageRock", "#RockNRoll"],
    "alternative": ["#AlternativeRock", "#IndieRock", "#PostRock", "#ModernRock"],
    "hardcore": ["#Hardcore", "#PostHardcore", "#MetalCore", "#PunkRock"],
    "thrash": ["#ThrashMetal", "#HeavyMetal", "#SpeedMetal", "#AggressiveMetal"],
    "power": ["#PowerMetal", "#HeavyMetal", "#EpicMetal", "#SpeedMetal"],
}

DEFAULT_GENRES = ["#AlternativeRock", "#IndieRock", "#HardRock", "#ModernRock"]


def get_genres(artist, title):
    artist_lower = artist.lower().strip()
    title_lower = title.lower().strip()

    # Check artist database
    for key, genres in ARTIST_GENRES.items():
        if key in artist_lower or artist_lower in key:
            return genres

    # Check keywords in artist and title
    combined = f"{artist_lower} {title_lower}"
    for keyword, genres in KEYWORD_GENRES.items():
        if keyword in combined:
            return genres

    return DEFAULT_GENRES


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


def build_caption(genres):
    linked_lines = []
    for tag in genres:
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
        genres = get_genres(artist, title)
        caption = build_caption(genres)

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
