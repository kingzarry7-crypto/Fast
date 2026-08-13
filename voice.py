import os
import tempfile
import asyncio

import discord


# =========================================================
# KING ZARRY AI 👑
# DISCORD VOICE ENGINE
# =========================================================


async def create_audio_file(text):
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

    file = tempfile.NamedTemporaryFile(
        suffix=".mp3",
        delete=False
    )

    file.close()

    try:

        communicate = edge_tts.Communicate(
            text,
            "en-US-AriaNeural"
        )

        await communicate.save(
            file.name
        )

        return file.name

    except Exception:

        if os.path.exists(file.name):
            os.remove(file.name)

        raise


async def speak(
    voice_client,
    text
):
    """
    Make King Zarry AI speak in a Discord
    voice channel.
    """

    if not voice_client:

        raise RuntimeError(
            "King Zarry AI is not connected "
            "to a voice channel."
        )

    if not voice_client.is_connected():

        raise RuntimeError(
            "Voice connection is no longer active."
        )

    text = str(text).strip()

    if not text:

        raise RuntimeError(
            "There is no text to speak."
        )

    # Stop anything currently playing
    if voice_client.is_playing():

        voice_client.stop()

    audio_file = await create_audio_file(
        text
    )

    finished = asyncio.Event()

    def after_playback(error):

        if error:

            print(
                "❌ Voice playback error:",
                repr(error)
            )

        try:

            os.remove(
                audio_file
            )

        except FileNotFoundError:
            pass

        finished_loop = asyncio.get_event_loop()

        finished_loop.call_soon_threadsafe(
            finished.set
        )

    try:

        source = discord.FFmpegOpusAudio(
            audio_file
        )

        voice_client.play(
            source,
            after=after_playback
        )

        await finished.wait()

    except Exception:

        try:

            if os.path.exists(audio_file):
                os.remove(audio_file)

        except Exception:
            pass

        raise
