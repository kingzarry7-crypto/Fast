import os
import re
import tempfile
import asyncio
import discord

# =========================================================
# 👑 KING ZARRY AI
# ELEVENLABS VOICE ENGINE
# TELEGRAM + DISCORD
# =========================================================

# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

ELEVENLABS_API_KEY = os.environ.get(
    "ELEVENLABS_API_KEY",
    ""
).strip()

# Put your ElevenLabs Voice ID here in Render/Railway/etc.
ELEVENLABS_VOICE_ID = os.environ.get(
    "ELEVENLABS_VOICE_ID",
    ""
).strip()

# Fast, low-latency ElevenLabs model.
# Can also use:
# eleven_multilingual_v2
# eleven_v3
ELEVENLABS_MODEL = os.environ.get(
    "ELEVENLABS_MODEL",
    "eleven_flash_v2_5"
).strip()

# MP3 is ideal for Discord + Telegram.
ELEVENLABS_OUTPUT_FORMAT = os.environ.get(
    "ELEVENLABS_OUTPUT_FORMAT",
    "mp3_44100_128"
).strip()

# =========================================================
# 🎙️ VOICE SETTINGS
# =========================================================

# These are ElevenLabs voice settings.
#
# Stability:
#   0.0 - more expressive
#   1.0 - more consistent
#
# Similarity:
#   0.0 - less constrained
#   1.0 - stronger similarity to selected voice
#
# Style:
#   0.0 - neutral
#   1.0 - more stylistic
#
# Speaker boost:
#   True = enhanced speaker clarity
#
# Speed:
#   1.0 = normal
#   1.1 = slightly faster
#   0.9 = slightly slower

try:
    ELEVENLABS_STABILITY = float(
        os.environ.get(
            "ELEVENLABS_STABILITY",
            "0.5"
        )
    )
except ValueError:
    ELEVENLABS_STABILITY = 0.5


try:
    ELEVENLABS_SIMILARITY = float(
        os.environ.get(
            "ELEVENLABS_SIMILARITY",
            "0.75"
        )
    )
except ValueError:
    ELEVENLABS_SIMILARITY = 0.75


try:
    ELEVENLABS_STYLE = float(
        os.environ.get(
            "ELEVENLABS_STYLE",
            "0.0"
        )
    )
except ValueError:
    ELEVENLABS_STYLE = 0.0


try:
    ELEVENLABS_SPEED = float(
        os.environ.get(
            "ELEVENLABS_SPEED",
            "1.0"
        )
    )
except ValueError:
    ELEVENLABS_SPEED = 1.0


ELEVENLABS_SPEAKER_BOOST = (
    os.environ.get(
        "ELEVENLABS_SPEAKER_BOOST",
        "true"
    ).lower()
    in ("1", "true", "yes", "on")
)


# =========================================================
# 🧹 TEXT CLEANING
# =========================================================

def clean_text_for_speech(text: str) -> str:
    """
    Clean AI/Markdown/HTML text before sending it
    to ElevenLabs.
    """

    if not text:
        return ""

    # Remove URLs
    text = re.sub(
        r"https?://\S+|www\.\S+",
        "",
        text
    )

    # Remove HTML tags
    text = re.sub(
        r"<[^>]+>",
        "",
        text
    )

    # Remove <think> blocks
    text = re.sub(
        r"<think>[\s\S]*?</think>",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove code blocks
    text = re.sub(
        r"```[\s\S]*?```",
        "",
        text
    )

    # Remove inline code markers
    text = re.sub(
        r"`([^`]+)`",
        r"\1",
        text
    )

    # Remove Markdown formatting
    text = re.sub(
        r"[*_~#>]",
        "",
        text
    )

    # Remove control tokens
    text = re.sub(
        r"<\|.*?\|>",
        "",
        text
    )

    # Clean excessive whitespace
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# 🔐 VALIDATE ELEVENLABS
# =========================================================

def validate_elevenlabs():
    """
    Check that ElevenLabs configuration exists.
    """

    if not ELEVENLABS_API_KEY:

        raise RuntimeError(
            "ELEVENLABS_API_KEY is missing. "
            "Add your ElevenLabs API key to the environment variables."
        )

    if not ELEVENLABS_VOICE_ID:

        raise RuntimeError(
            "ELEVENLABS_VOICE_ID is missing. "
            "Add the Voice ID of your selected ElevenLabs voice."
        )


# =========================================================
# 🎙️ ELEVENLABS GENERATOR
# =========================================================

def generate_elevenlabs_audio(
    text: str,
    output_file: str
):
    """
    Generate audio using the official ElevenLabs
    Python SDK.
    """

    try:

        from elevenlabs.client import ElevenLabs
        from elevenlabs import VoiceSettings

    except ImportError:

        raise RuntimeError(
            "ElevenLabs SDK is not installed.\n\n"
            "Add this to requirements.txt:\n"
            "elevenlabs"
        )

    validate_elevenlabs()

    client = ElevenLabs(
        api_key=ELEVENLABS_API_KEY
    )

    print(
        "🎙️ ElevenLabs TTS starting..."
    )

    print(
        f"🎤 Voice ID: {ELEVENLABS_VOICE_ID}"
    )

    print(
        f"🧠 Model: {ELEVENLABS_MODEL}"
    )

    audio = client.text_to_speech.convert(
        text=text,
        voice_id=ELEVENLABS_VOICE_ID,
        model_id=ELEVENLABS_MODEL,
        output_format=ELEVENLABS_OUTPUT_FORMAT,
        voice_settings=VoiceSettings(
            stability=ELEVENLABS_STABILITY,
            similarity_boost=ELEVENLABS_SIMILARITY,
            style=ELEVENLABS_STYLE,
            use_speaker_boost=ELEVENLABS_SPEAKER_BOOST,
            speed=ELEVENLABS_SPEED,
        ),
    )

    with open(
        output_file,
        "wb"
    ) as audio_file:

        for chunk in audio:

            if chunk:

                audio_file.write(chunk)

    if not os.path.exists(output_file):

        raise RuntimeError(
            "ElevenLabs did not create an audio file."
        )

    file_size = os.path.getsize(
        output_file
    )

    if file_size <= 0:

        raise RuntimeError(
            "ElevenLabs returned an empty audio file."
        )

    print(
        f"✅ ElevenLabs audio created: "
        f"{file_size:,} bytes"
    )

    return output_file


# =========================================================
# 🎙️ TELEGRAM VOICE NOTE
# =========================================================

async def create_voice_note(
    text: str,
    suffix: str = ".mp3"
) -> str:
    """
    Convert text into an ElevenLabs MP3.

    Telegram bot.py already calls:

        create_voice_note(text)

    so no Telegram handler changes are required.
    """

    cleaned_text = clean_text_for_speech(
        text
    )

    if not cleaned_text:

        raise ValueError(
            "Text is empty after cleaning for speech."
        )

    # Telegram voice messages can accept audio files.
    # MP3 keeps the implementation simple and reliable.
    file = tempfile.NamedTemporaryFile(
        suffix=suffix,
        delete=False
    )

    file_path = file.name

    file.close()

    try:

        await asyncio.to_thread(
            generate_elevenlabs_audio,
            cleaned_text,
            file_path
        )

        return file_path

    except Exception:

        if os.path.exists(file_path):

            try:
                os.remove(file_path)

            except OSError:
                pass

        raise


# =========================================================
# 🔊 DISCORD AUDIO FILE
# =========================================================

async def create_audio_file(
    text: str
) -> str:
    """
    Generate an MP3 for Discord voice playback.
    """

    return await create_voice_note(
        text,
        suffix=".mp3"
    )


# =========================================================
# 🎧 DISCORD VOICE CHANNEL
# =========================================================

async def speak(
    voice_client: discord.VoiceClient,
    text: str
):
    """
    Make King Zarry AI speak in a Discord
    voice channel using ElevenLabs.
    """

    if not voice_client:

        raise RuntimeError(
            "King Zarry AI is not connected "
            "to a voice channel."
        )

    if not voice_client.is_connected():

        raise RuntimeError(
            "Discord voice connection is "
            "no longer active."
        )

    cleaned_text = clean_text_for_speech(
        text
    )

    if not cleaned_text:

        raise RuntimeError(
            "There is no valid text to speak."
        )

    # Stop existing playback
    if voice_client.is_playing():

        voice_client.stop()

    audio_file = None

    try:

        # Generate ElevenLabs audio
        audio_file = await create_audio_file(
            cleaned_text
        )

        finished = asyncio.Event()

        loop = asyncio.get_running_loop()

        def after_playback(error):

            if error:

                print(
                    "❌ Discord voice playback error:",
                    repr(error)
                )

            try:

                if (
                    audio_file
                    and os.path.exists(audio_file)
                ):

                    os.remove(audio_file)

            except OSError:

                pass

            loop.call_soon_threadsafe(
                finished.set
            )

        # FFmpeg reads the MP3 generated by ElevenLabs
        source = discord.FFmpegPCMAudio(
            audio_file
        )

        voice_client.play(
            source,
            after=after_playback
        )

        await finished.wait()

    except Exception:

        if (
            audio_file
            and os.path.exists(audio_file)
        ):

            try:

                os.remove(audio_file)

            except OSError:

                pass

        raise


# =========================================================
# 🧪 SIMPLE TEST
# =========================================================

async def test_voice():

    """
    Optional local test.

    Run only if you want to test voice.py directly.
    """

    print(
        "👑 Testing King Zarry AI ElevenLabs..."
    )

    test_file = None

    try:

        test_file = await create_voice_note(
            "Hello! This is King Zarry AI powered by ElevenLabs."
        )

        print(
            "✅ Voice test successful:"
        )

        print(
            test_file
        )

    except Exception as e:

        print(
            "❌ Voice test failed:"
        )

        print(
            e
        )

    finally:

        if (
            test_file
            and os.path.exists(test_file)
        ):

            try:

                os.remove(test_file)

            except OSError:

                pass


# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":

    asyncio.run(
        test_voice()
    )
