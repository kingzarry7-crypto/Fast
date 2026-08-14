import os
import tempfile
import asyncio
import discord

# =========================================================
# KING ZARRY AI 👑
# DISCORD VOICE ENGINE
# =========================================================

async def create_audio_file(text: str) -> str:
    """
    Convert text to speech using Edge TTS.
    """
    try:
        import edge_tts
    except ImportError:
        raise RuntimeError(
            "edge-tts is not installed. "
            "Add edge-tts to requirements.txt."
        )

    # Create temporary file
    file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    file_path = file.name
    file.close()

    try:
        communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
        await communicate.save(file_path)
        return file_path
    except Exception:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        raise


async def speak(voice_client: discord.VoiceClient, text: str):
    """
    Make King Zarry AI speak in a Discord voice channel.
    """
    if not voice_client:
        raise RuntimeError("King Zarry AI is not connected to a voice channel.")

    if not voice_client.is_connected():
        raise RuntimeError("Voice connection is no longer active.")

    text = str(text).strip()
    if not text:
        raise RuntimeError("There is no text to speak.")

    # Stop anything currently playing
    if voice_client.is_playing():
        voice_client.stop()

    audio_file = await create_audio_file(text)

    finished = asyncio.Event()
    # Capture current loop to safely trigger Event from the audio thread
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

        # Safely notify the waiting asyncio task from a thread
        loop.call_soon_threadsafe(finished.set)

    try:
        source = discord.FFmpegOpusAudio(audio_file)
        voice_client.play(source, after=after_playback)
        await finished.wait()

    except Exception:
        if os.path.exists(audio_file):
            try:
                os.remove(audio_file)
            except OSError:
                pass
        raise
