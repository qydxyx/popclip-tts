#!/usr/bin/env python3
"""
PopClip TTS Extension - Gemini & ElevenLabs
Plays text-to-speech audio in the background using macOS afplay.
Toggle behavior: clicking again while reading the same text stops playback.
"""

import base64
import hashlib
import io
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import wave

MAX_TEXT_LENGTH = 5000
HTTP_TIMEOUT = 25.0


def get_input_text(stdin_stream=None, env=None) -> str:
    """Read input text from stdin (preferred for long text) or POPCLIP_TEXT env."""
    text = ""
    stream = stdin_stream if stdin_stream is not None else sys.stdin
    try:
        text = stream.read()
    except Exception:
        text = ""

    if not text:
        environ = env if env is not None else os.environ
        text = environ.get("POPCLIP_TEXT", "")

    return text.strip()


def get_state_file_path(env=None) -> str:
    """Return path to user-scoped state tracking file."""
    environ = env if env is not None else os.environ
    tmpdir = environ.get("TMPDIR") or tempfile.gettempdir()
    uid = os.getuid() if hasattr(os, "getuid") else 1000
    return os.path.join(tmpdir, f"popclip-tts-{uid}-state.json")


def is_process_group_alive(pgid: int) -> bool:
    """Check if process group is alive via signal 0."""
    try:
        os.killpg(pgid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def check_and_stop_previous(state_file: str, current_hash: str) -> bool:
    """
    Check if previous playback is still running.
    If running: terminate process group and clean up audio file.
    If same text was clicked: return True to stop playback and exit immediately.
    If different text: clean up previous and return False to continue with new text.
    """
    if not os.path.exists(state_file):
        return False

    is_running = False
    same_text = False
    pgid = None
    audio_path = None

    try:
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        pgid = data.get("pgid")
        text_hash = data.get("text_sha256")
        audio_path = data.get("audio_path")

        if pgid and isinstance(pgid, int) and is_process_group_alive(pgid):
            is_running = True
            if text_hash == current_hash:
                same_text = True
    except Exception:
        pass

    if is_running and pgid:
        try:
            os.killpg(pgid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass

    if audio_path and os.path.exists(audio_path):
        try:
            os.remove(audio_path)
        except OSError:
            pass

    try:
        os.remove(state_file)
    except OSError:
        pass

    return is_running and same_text


def convert_pcm_to_wav(raw_bytes: bytes, mime_type: str = "") -> bytes:
    """Convert raw 16-bit mono PCM into standard RIFF WAV, or pass through existing RIFF."""
    if raw_bytes.startswith(b"RIFF"):
        return raw_bytes

    sample_rate = 24000
    if mime_type:
        match = re.search(r"rate=(\d+)", mime_type)
        if match:
            sample_rate = int(match.group(1))

    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)      # mono
        wf.setsampwidth(2)      # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(raw_bytes)

    return bio.getvalue()


def handle_http_error(err: urllib.error.HTTPError) -> int:
    """
    Classify HTTP errors:
    Return 2 for authentication/api-key errors (triggers PopClip settings UI).
    Return 1 for transient/other errors.
    """
    body = ""
    try:
        body = err.read().decode("utf-8", errors="replace")
    except Exception:
        pass

    if err.code in (401, 403):
        sys.stderr.write(f"Authentication failed ({err.code}): {body or err.reason}\n")
        return 2

    if err.code == 400:
        body_lower = body.lower()
        if "api_key_invalid" in body_lower or "api key not valid" in body_lower or "invalid api key" in body_lower:
            sys.stderr.write(f"Invalid API key: {body}\n")
            return 2
        sys.stderr.write(f"Bad request (400): {body or err.reason}\n")
        return 1

    sys.stderr.write(f"TTS service error ({err.code}): {body or err.reason}\n")
    return 1


def synthesize_gemini(
    text: str, api_key: str, model: str, voice: str, timeout: float = HTTP_TIMEOUT
) -> tuple[bytes, str]:
    """Call Google Gemini generateContent API with AUDIO response modality."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice
                    }
                }
            },
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        resp_data = json.loads(resp.read().decode("utf-8"))

    try:
        candidate = resp_data["candidates"][0]
        part = candidate["content"]["parts"][0]
        inline_data = part["inlineData"]
        mime_type = inline_data.get("mimeType", "audio/L16;codec=pcm;rate=24000")
        raw_audio = base64.b64decode(inline_data["data"])
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"Malformed Gemini audio response: {exc}") from exc

    if "mpeg" in mime_type or "mp3" in mime_type:
        return raw_audio, ".mp3"

    wav_data = convert_pcm_to_wav(raw_audio, mime_type)
    return wav_data, ".wav"


def synthesize_elevenlabs(
    text: str, api_key: str, model: str, voice: str, timeout: float = HTTP_TIMEOUT
) -> tuple[bytes, str]:
    """Call ElevenLabs text-to-speech API returning MP3 audio."""
    encoded_voice = urllib.parse.quote(voice.strip(), safe="")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{encoded_voice}?output_format=mp3_44100_128"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": model,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        audio_data = resp.read()

    return audio_data, ".mp3"


def start_playback(audio_bytes: bytes, suffix: str, text_hash: str, state_file: str) -> None:
    """Save audio to temp file and launch afplay in detached background process group."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        audio_path = f.name

    # Background runner script: removes temp audio file on completion or termination
    runner_cmd = [
        "/bin/sh",
        "-c",
        'trap \'rm -f "$1"\' EXIT INT TERM; /usr/bin/afplay "$1"',
        "_",
        audio_path,
    ]

    proc = subprocess.Popen(
        runner_cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )

    # Save state atomically for stop toggle
    state_data = {
        "pgid": proc.pid,
        "text_sha256": text_hash,
        "audio_path": audio_path,
    }
    tmp_state = f"{state_file}.{os.getpid()}.tmp"
    with open(tmp_state, "w", encoding="utf-8") as f:
        json.dump(state_data, f)
    os.replace(tmp_state, state_file)


def main() -> int:
    text = get_input_text()
    if not text:
        return 0

    if len(text) > MAX_TEXT_LENGTH:
        sys.stderr.write(f"Text too long: {len(text)} characters (maximum {MAX_TEXT_LENGTH})\n")
        return 1

    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    state_file = get_state_file_path()

    # Toggle stop if clicked while playing same text
    if check_and_stop_previous(state_file, text_hash):
        return 0

    provider = os.environ.get("POPCLIP_OPTION_PROVIDER", "gemini").strip().lower()

    try:
        if provider == "gemini":
            api_key = os.environ.get("POPCLIP_OPTION_GEMINI_API_KEY", "").strip()
            if not api_key:
                sys.stderr.write("Gemini API Key is required\n")
                return 2

            model = (
                os.environ.get("POPCLIP_OPTION_GEMINI_MODEL", "").strip()
                or "gemini-3.8-flash-lite-tts"
            )
            voice = os.environ.get("POPCLIP_OPTION_GEMINI_VOICE", "").strip() or "Kore"

            audio_bytes, suffix = synthesize_gemini(text, api_key, model, voice)

        elif provider == "elevenlabs":
            api_key = os.environ.get("POPCLIP_OPTION_ELEVENLABS_API_KEY", "").strip()
            if not api_key:
                sys.stderr.write("ElevenLabs API Key is required\n")
                return 2

            model = (
                os.environ.get("POPCLIP_OPTION_ELEVENLABS_MODEL", "").strip()
                or "eleven_flash_v2_5"
            )
            voice = (
                os.environ.get("POPCLIP_OPTION_ELEVENLABS_VOICE", "").strip()
                or "EXAVITQu4vr4xnSDxMaL"
            )

            audio_bytes, suffix = synthesize_elevenlabs(text, api_key, model, voice)

        else:
            sys.stderr.write(f"Unsupported provider: {provider}\n")
            return 1

    except urllib.error.HTTPError as err:
        return handle_http_error(err)
    except urllib.error.URLError as err:
        sys.stderr.write(f"Network error: {err.reason}\n")
        return 1
    except TimeoutError:
        sys.stderr.write("TTS request timed out\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"TTS error: {exc}\n")
        return 1

    if not audio_bytes:
        sys.stderr.write("Empty audio received from TTS service\n")
        return 1

    start_playback(audio_bytes, suffix, text_hash, state_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
