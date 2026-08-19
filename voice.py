import os
import re
import asyncio
import tempfile
import discord

# =========================================================
# 👑 KING ZARRY AI
# ELEVENLABS VOICE ENGINE
# TELEGRAM + DISCORD
# =========================================================

# =========================================================
# ENVIRONMENT
# =========================================================

ELEVENLABS_API_KEY = os.getenv(
    "ELEVENLABS_API_KEY",
    ""
).strip()

ELEVENLABS_VOICE_ID = os.getenv(
    "ELEVENLABS_VOICE_ID",
    ""
).strip()

ELEVENLABS_MODEL = os.getenv(
    "ELEVENLABS_MODEL",
    "eleven_flash_v2_5"
).strip()

ELEVENLABS_OUTPUT_FORMAT = os.getenv(
    "ELEVENLABS_OUTPUT_FORMAT",
    "mp3_44100_128"
).strip()


# =========================================================
# 🎙️ VOICE SETTINGS
# =========================================================

def get_float_env(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
        return max(0.0, min(1.0, value))
    except (TypeError, ValueError):
        return default


ELEVENLABS_STABILITY = get_float_env(
    "ELEVENLABS_STABILITY",
    0.5
)

ELEVENLABS_SIMILARITY = get_float_env(
    "ELEVENLABS_SIMILARITY",
    0.75
)

ELEVENLABS_STYLE = get_float_env(
    "ELEVENLABS_STYLE",
    0.0
)


try:
    ELEVENLABS_SPEED = float(
        os.getenv(
            "ELEVENLABS_SPEED",
            "1.0"
        )
    )
except (TypeError, ValueError):
    ELEVENLABS_SPEED = 1.0

ELEVENLABS_SPEED = max(
    0.7,
    min(1.2, ELEVENLABS_SPEED)
)


ELEVENLABS_SPEAKER_BOOST = (
    os.getenv(
        "ELEVENLABS_SPEAKER_BOOST",
        "true"
    ).lower()
    in {
        "1",
        "true",
        "yes",
        "on",
    }
)


# =========================================================
# 🧹 TEXT CLEANING
# =========================================================

def clean_text_for_speech(text: str) -> str:

    if not text:
        return ""

    text = str(text)

    # Remove hidden reasoning
    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    # Remove unfinished think block
    text = re.sub(
        r"<think>.*$",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    # Remove URLs
    text = re.sub(
        r"https?://\S+",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"www\.\S+",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove HTML tags
    text = re.sub(
        r"<[^>]+>",
        "",
        text
    )

    # Remove code blocks
    text = re.sub(
        r"```.*?```",
        "",
        text,
        flags=re.DOTALL
    )

    # Remove inline code markers
    text = re.sub(
        r"`([^`]*)`",
        r"\1",
        text
    )

    # Markdown emphasis
    text = re.sub(
        r"[*_~#]",
        "",
        text
    )

    # Remove AI control tokens
    text = re.sub(
        r"<\|.*?\|>",
        "",
        text
    )

    # Remove excessive whitespace
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# 🔐 VALIDATION
# =========================================================

def validate_elevenlabs():

    if not ELEVENLABS_API_KEY:

        raise RuntimeError(
            "❌ ELEVENLABS_API_KEY is missing.\n\n"
            "Add ELEVENLABS_API_KEY to your "
            "Render/Railway environment variables."
        )

    if not ELEVENLABS_VOICE_ID:

        raise RuntimeError(
            "❌ ELEVENLABS_VOICE_ID is missing.\n\n"
            "Add the Voice ID of your ElevenLabs voice "
            "to your environment variables."
        )


# =========================================================
# 📦 LOAD ELEVENLABS SDK
# =========================================================

def get_elevenlabs_client():

    try:
        from elevenlabs.client import ElevenLabs
    except ImportError as exc:

        raise RuntimeError(
            "❌ ElevenLabs package is not installed.\n\n"
            "Add this to requirements.txt:\n"
            "elevenlabs>=1.0.0"
        ) from exc

    validate_elevenlabs()

    return ElevenLabs(
        api_key=ELEVENLABS_API_KEY
    )


# =========================================================
# 🎙️ GENERATE ELEVENLABS AUDIO
# =========================================================

def generate_elevenlabs_audio(
    text: str,
    output_file: str
):

    client = get_elevenlabs_client()

    print(
        "🎙️ ======================================="
    )

    print(
        "🎙️ KING ZARRY AI VOICE ENGINE"
    )

    print(
        "🎤 ElevenLabs generating audio..."
    )

    print(
        f"🎤 Voice ID: {ELEVENLABS_VOICE_ID}"
    )

    print(
        f"🧠 Model: {ELEVENLABS_MODEL}"
    )

    print(
        f"🎵 Format: {ELEVENLABS_OUTPUT_FORMAT}"
    )

    try:

        from elevenlabs import VoiceSettings

        voice_settings = VoiceSettings(
            stability=ELEVENLABS_STABILITY,
            similarity_boost=ELEVENLABS_SIMILARITY,
            style=ELEVENLABS_STYLE,
            use_speaker_boost=ELEVENLABS_SPEAKER_BOOST,
            speed=ELEVENLABS_SPEED,
        )

    except ImportError:

        voice_settings = None


    # =====================================================
    # ELEVENLABS REQUEST
    # =====================================================

    kwargs = {
        "text": text,
        "voice_id": ELEVENLABS_VOICE_ID,
        "model_id": ELEVENLABS_MODEL,
        "output_format": ELEVENLABS_OUTPUT_FORMAT,
    }

    if voice_settings is not None:
        kwargs["voice_settings"] = voice_settings


    try:

        audio = client.text_to_speech.convert(
            **kwargs
        )

    except Exception as first_error:

        print(
            "⚠️ ElevenLabs SDK request failed."
        )

        print(
            repr(first_error)
        )

        raise RuntimeError(
            f"ElevenLabs generation failed: {first_error}"
        ) from first_error


    # =====================================================
    # WRITE AUDIO
    # =====================================================

    try:

        with open(
            output_file,
            "wb"
        ) as audio_file:

            if isinstance(audio, bytes):

                audio_file.write(audio)

            else:

                for chunk in audio:

                    if chunk:
                        audio_file.write(chunk)

    except Exception as error:

        raise RuntimeError(
            f"Could not save ElevenLabs audio: {error}"
        ) from error


    # =====================================================
    # VERIFY FILE
    # =====================================================

    if not os.path.isfile(output_file):

        raise RuntimeError(
            "ElevenLabs returned audio but "
            "the output file was not created."
        )


    file_size = os.path.getsize(
        output_file
    )

    if file_size <= 0:

        raise RuntimeError(
            "ElevenLabs returned an empty audio file."
        )


    print(
        f"✅ Audio generated successfully: "
        f"{file_size:,} bytes"
    )

    print(
        "🎙️ ======================================="
    )

    return output_file


# =========================================================
# 📱 TELEGRAM VOICE
# =========================================================

async def create_voice_note(
    text: str,
    suffix: str = ".mp3"
) -> str:

    cleaned_text = clean_text_for_speech(
        text
    )

    if not cleaned_text:

        raise ValueError(
            "❌ Text is empty after cleaning."
        )


    # Telegram's voice upload works best with
    # an actual audio file.
    temporary_file = tempfile.NamedTemporaryFile(
        prefix="king_zarry_voice_",
        suffix=suffix,
        delete=False
    )

    file_path = temporary_file.name

    temporary_file.close()


    try:

        await asyncio.to_thread(
            generate_elevenlabs_audio,
            cleaned_text,
            file_path
        )

        return file_path

    except Exception:

        try:

            if os.path.exists(file_path):
                os.remove(file_path)

        except OSError:
            pass

        raise


# =========================================================
# 🔊 GENERIC AUDIO FILE
# =========================================================

async def create_audio_file(
    text: str
) -> str:

    return await create_voice_note(
        text,
        ".mp3"
    )


# =========================================================
# 🎧 DISCORD VOICE
# =========================================================

async def speak(
    voice_client: discord.VoiceClient,
    text: str
):

    if voice_client is None:

        raise RuntimeError(
            "❌ Discord voice client is not available."
        )


    if not voice_client.is_connected():

        raise RuntimeError(
            "❌ Discord is not connected to a voice channel."
        )


    cleaned_text = clean_text_for_speech(
        text
    )

    if not cleaned_text:

        raise RuntimeError(
            "❌ There is no valid text to speak."
        )


    # Stop existing playback
    if voice_client.is_playing():

        voice_client.stop()


    audio_file = None
    source = None


    try:

        audio_file = await create_audio_file(
            cleaned_text
        )


        # =================================================
        # FFmpeg
        # =================================================

        source = discord.FFmpegPCMAudio(
            audio_file
        )


        finished = asyncio.Event()

        loop = asyncio.get_running_loop()


        def playback_finished(error):

            if error:

                print(
                    "❌ Discord playback error:",
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


        voice_client.play(
            source,
            after=playback_finished
        )


        await finished.wait()


    except Exception:

        try:

            if (
                audio_file
                and os.path.exists(audio_file)
            ):

                os.remove(audio_file)

        except OSError:
            pass


        raise


# =========================================================
# 🧪 TEST
# =========================================================

async def test_voice():

    print(
        "👑 KING ZARRY AI"
    )

    print(
        "🧪 Testing ElevenLabs voice..."
    )


    test_file = None


    try:

        test_file = await create_voice_note(
            "Hello! This is King Zarry AI powered by ElevenLabs."
        )


        print(
            "✅ VOICE TEST SUCCESSFUL"
        )

        print(
            f"📁 File: {test_file}"
        )

        print(
            f"📦 Size: {os.path.getsize(test_file):,} bytes"
        )


    except Exception as error:

        print(
            "❌ VOICE TEST FAILED"
        )

        print(
            repr(error)
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
# 🚀 ENTRY POINT
# =========================================================

if __name__ == "__main__":

    asyncio.run(
        test_voice()
    )
