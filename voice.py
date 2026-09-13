import os
import re
import asyncio
import tempfile
from pathlib import Path

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
    "21m00Tcm4TlvDq8ikWAM"
).strip()

ELEVENLABS_MODEL = os.getenv(
    "ELEVENLABS_MODEL",
    "eleven_multilingual_v2"
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
    0.35
)

ELEVENLABS_SIMILARITY = get_float_env(
    "ELEVENLABS_SIMILARITY",
    0.85
)

ELEVENLABS_STYLE = get_float_env(
    "ELEVENLABS_STYLE",
    0.20
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
    """
    Prepare AI text for natural ElevenLabs speech.

    Removes:
    - Hidden reasoning
    - URLs
    - HTML
    - Code blocks
    - Markdown formatting
    - AI control tokens

    Preserves:
    - Normal punctuation
    - Sentence boundaries
    - Paragraph spacing
    """

    if not text:
        return ""

    text = str(text)

    # -----------------------------------------------------
    # Remove hidden reasoning
    # -----------------------------------------------------

    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    # Remove unfinished reasoning blocks
    text = re.sub(
        r"<think>.*$",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    # -----------------------------------------------------
    # Remove URLs
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Remove code blocks
    # -----------------------------------------------------

    text = re.sub(
        r"```.*?```",
        "",
        text,
        flags=re.DOTALL
    )

    # Remove inline code markers while preserving content
    text = re.sub(
        r"`([^`]*)`",
        r"\1",
        text
    )

    # -----------------------------------------------------
    # Remove HTML tags
    # -----------------------------------------------------

    text = re.sub(
        r"<[^>]+>",
        "",
        text
    )

    # -----------------------------------------------------
    # Remove AI control tokens
    # -----------------------------------------------------

    text = re.sub(
        r"<\|.*?\|>",
        "",
        text
    )

    # -----------------------------------------------------
    # Remove Markdown formatting characters
    # -----------------------------------------------------

    text = re.sub(
        r"[*_~#]",
        "",
        text
    )

    # -----------------------------------------------------
    # Normalize spaces while preserving paragraphs
    # -----------------------------------------------------

    text = re.sub(
        r"[ \t\f\v]+",
        " ",
        text
    )

    text = re.sub(
        r"\n[ \t]+",
        "\n",
        text
    )

    # Keep paragraph breaks useful for natural pauses
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    # Remove spaces immediately before line breaks
    text = re.sub(
        r"[ \t]+\n",
        "\n",
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
            "Add ELEVENLABS_API_KEY to the deployment "
            "environment variables."
        )

    if not ELEVENLABS_VOICE_ID:

        raise RuntimeError(
            "❌ ELEVENLABS_VOICE_ID is missing.\n\n"
            "Add the Voice ID of your ElevenLabs voice "
            "to the environment variables."
        )

    if not ELEVENLABS_MODEL:

        raise RuntimeError(
            "❌ ELEVENLABS_MODEL is missing."
        )

    if not ELEVENLABS_OUTPUT_FORMAT.startswith("mp3_"):

        raise RuntimeError(
            "❌ ELEVENLABS_OUTPUT_FORMAT must be "
            "an MP3 format for this voice engine."
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
# 🎵 BASIC MP3 VALIDATION
# =========================================================

def _looks_like_mp3(path: str) -> bool:
    """
    Perform a lightweight MP3 signature check.

    This is intentionally dependency-free so the voice
    engine does not require another audio package.
    """

    try:

        with open(
            path,
            "rb"
        ) as audio_file:

            header = audio_file.read(4096)

    except OSError:

        return False

    if len(header) < 4:
        return False

    # ID3 metadata header
    if header[:3] == b"ID3":
        return True

    # Search for an MPEG audio frame sync
    for index in range(len(header) - 1):

        first_byte = header[index]
        second_byte = header[index + 1]

        if (
            first_byte == 0xFF
            and (second_byte & 0xE0) == 0xE0
        ):
            return True

    return False


# =========================================================
# 💾 WRITE ELEVENLABS AUDIO
# =========================================================

def _write_audio_chunks(
    audio,
    path: str
) -> None:

    wrote_data = False

    with open(
        path,
        "wb"
    ) as audio_file:

        if isinstance(audio, bytes):

            if audio:

                audio_file.write(audio)
                wrote_data = True

        else:

            for chunk in audio:

                if chunk:

                    audio_file.write(chunk)
                    wrote_data = True

    if not wrote_data:

        raise RuntimeError(
            "ElevenLabs returned an empty audio response."
        )


# =========================================================
# 🎙️ GENERATE ELEVENLABS AUDIO
# =========================================================

def generate_elevenlabs_audio(
    text: str,
    output_file: str
):

    client = get_elevenlabs_client()

    output_path = Path(output_file)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # -----------------------------------------------------
    # Logging
    # -----------------------------------------------------

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
        f"🧠 Model: {ELEVENLABS_MODEL}"
    )

    print(
        f"🎵 Format: {ELEVENLABS_OUTPUT_FORMAT}"
    )

    # -----------------------------------------------------
    # Voice settings
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # ElevenLabs request
    # -----------------------------------------------------

    kwargs = {
        "text": text,
        "voice_id": ELEVENLABS_VOICE_ID,
        "model_id": ELEVENLABS_MODEL,
        "output_format": ELEVENLABS_OUTPUT_FORMAT,
    }

    if voice_settings is not None:

        kwargs["voice_settings"] = voice_settings

    # -----------------------------------------------------
    # Generate audio
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Stage audio safely
    # -----------------------------------------------------

    staging_path = None

    try:

        with tempfile.NamedTemporaryFile(
            prefix="king_zarry_audio_",
            suffix=".mp3",
            dir=str(output_path.parent),
            delete=False
        ) as staging_file:

            staging_path = staging_file.name

        _write_audio_chunks(
            audio,
            staging_path
        )

        # -------------------------------------------------
        # Validate staged file
        # -------------------------------------------------

        if not os.path.isfile(staging_path):

            raise RuntimeError(
                "ElevenLabs returned audio but "
                "the staging file was not created."
            )

        staged_size = os.path.getsize(
            staging_path
        )

        if staged_size <= 0:

            raise RuntimeError(
                "ElevenLabs returned an empty audio file."
            )

        if not _looks_like_mp3(
            staging_path
        ):

            raise RuntimeError(
                "ElevenLabs returned invalid or "
                "corrupted MP3 audio."
            )

        # -------------------------------------------------
        # Atomically replace destination
        # -------------------------------------------------

        os.replace(
            staging_path,
            output_path
        )

        staging_path = None

        # -------------------------------------------------
        # Final validation
        # -------------------------------------------------

        if not output_path.is_file():

            raise RuntimeError(
                "Generated MP3 file was not created."
            )

        final_size = output_path.stat().st_size

        if final_size <= 0:

            raise RuntimeError(
                "Generated MP3 file is empty."
            )

        if not _looks_like_mp3(
            str(output_path)
        ):

            raise RuntimeError(
                "Generated MP3 failed audio validation."
            )

        print(
            f"✅ Audio generated successfully: "
            f"{final_size:,} bytes"
        )

        print(
            "🎙️ ======================================="
        )

        return str(output_path)

    except Exception as error:

        if isinstance(error, RuntimeError):
            raise

        raise RuntimeError(
            f"Could not save ElevenLabs audio: {error}"
        ) from error

    finally:

        if staging_path:

            try:

                if os.path.exists(staging_path):
                    os.remove(staging_path)

            except OSError:
                pass


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

    # -----------------------------------------------------
    # This engine currently produces MP3 only.
    # -----------------------------------------------------

    if suffix.lower() != ".mp3":

        raise ValueError(
            "❌ ElevenLabs voice output must use "
            "the .mp3 suffix."
        )

    temporary_file = tempfile.NamedTemporaryFile(
        prefix="king_zarry_voice_",
        suffix=".mp3",
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

        # Final safety check before returning
        if not os.path.isfile(file_path):

            raise RuntimeError(
                "Voice file was not created."
            )

        if os.path.getsize(file_path) <= 0:

            raise RuntimeError(
                "Voice file is empty."
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

        # -------------------------------------------------
        # FFmpeg
        # -------------------------------------------------

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

        file_size = os.path.getsize(
            test_file
        )

        print(
            "✅ VOICE TEST SUCCESSFUL"
        )

        print(
            f"📁 File: {test_file}"
        )

        print(
            f"📦 Size: {file_size:,} bytes"
        )

        print(
            "🎵 MP3 validation: PASSED"
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
