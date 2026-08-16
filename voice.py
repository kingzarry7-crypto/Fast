import os
import re
import tempfile
import asyncio
import discord

# =========================================================
# KING ZARRY AI 👑
# UNIFIED VOICE ENGINE (DISCORD + TELEGRAM)
# =========================================================

# Primary and fallback neural voices for TTS
PREFERRED_VOICES = [
    "en-US-AriaNeural",
    "en-US-GuyNeural",
    "en-US-ChristopherNeural",
    "en-GB-SoniaNeural",
]

# Configure Voice Speed and Volume via Environment Variables
# Rate examples: "+0%", "+10%", "-15%", "+25%"
# Volume examples: "+0%", "+20%", "-10%", "+50%"
TTS_RATE = os.environ.get("TTS_RATE", "+0%").strip()
TTS_VOLUME = os.environ.get("TTS_VOLUME", "+0%").strip()


def clean_text_for_speech(text: str) -> str:
    """
    Clean raw text/markdown/HTML into clean prose for TTS generation.
    """
    if not text:
        return ""

    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", "", text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Remove code blocks and inline code
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Remove Markdown formatting (*, _, ~, #, >)
    text = re.sub(r"[*_~#>]", "", text)

    # Clean excessive whitespace/newlines
    text = re.sub(r"\s+", " ", text)

    return text.strip()


async def create_voice_note(text: str, suffix: str = ".ogg") -> str:
    """
    Convert text to an audio file for Telegram voice notes or audio responses.
    Applies configurable rate/volume settings and multi-voice fallback.
    """
    try:
        import edge_tts
    except ImportError:
        raise RuntimeError(
            "edge-tts is not installed. Add 'edge-tts' to requirements.txt."
        )

    cleaned_text = clean_text_for_speech(text)
    if not cleaned_text:
        raise ValueError("Text is empty after cleaning for speech.")

    # Create temporary file
    file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    file_path = file.name
    file.close()

    last_error = None

    # Try preferred voice first, then fall back to alternate voices
    for voice in PREFERRED_VOICES:
        try:
            communicate = edge_tts.Communicate(
                text=cleaned_text,
                voice=voice,
                rate=TTS_RATE,
                volume=TTS_VOLUME,
            )
            await communicate.save(file_path)

            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                return file_path

        except Exception as e:
            last_error = e
            continue

    # Clean up file on total failure
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    raise RuntimeError(
        f"Failed to generate voice note with all TTS voices. Last error: {last_error}"
    )


async def create_audio_file(text: str) -> str:
    """
    Legacy helper alias for Discord voice generation (returns .mp3).
    """
    return await create_voice_note(text, suffix=".mp3")


async def speak(voice_client: discord.VoiceClient, text: str):
    """
    Make King Zarry AI speak in a Discord voice channel.
    """
    if not voice_client:
        raise RuntimeError("King Zarry AI is not connected to a voice channel.")

    if not voice_client.is_connected():
        raise RuntimeError("Voice connection is no longer active.")

    cleaned_text = clean_text_for_speech(text)
    if not cleaned_text:
        raise RuntimeError("There is no valid text to speak.")

    # Stop anything currently playing
    if voice_client.is_playing():
        voice_client.stop()

    audio_file = await create_audio_file(cleaned_text)

    finished = asyncio.Event()
    loop = asyncio.get_running_loop()

    def after_playback(error):
        if error:
            print("❌ Voice playback error:", repr(error))

        # Safe asynchronous cleanup of the audio file
        try:
            if os.path.exists(audio_file):
                os.remove(audio_file)
        except OSError:
            pass

        loop.call_soon_threadsafe(finished.set)

    try:
        source = discord.FFmpegPCMAudio(audio_file)
        voice_client.play(source, after=after_playback)
        await finished.wait()

    except Exception as e:
        if os.path.exists(audio_file):
            try:
                os.remove(audio_file)
            except OSError:
                pass
        raise e
