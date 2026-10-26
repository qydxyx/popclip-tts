#!/usr/bin/env python3
"""
Unit tests for PopClip TTS Extension (tts.py)
"""

import base64
import io
import json
import os
import signal
import sys
import tempfile
import unittest
import urllib.error
import wave
from unittest.mock import MagicMock, patch

# Add TTS.popclipext to import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "TTS.popclipext")))
import tts


class TestTTSAudioConversion(unittest.TestCase):
    def test_convert_pcm_to_wav_default_rate(self):
        # 100 samples of 16-bit silence
        raw_pcm = b"\x00\x00" * 100
        wav_bytes = tts.convert_pcm_to_wav(raw_pcm, "audio/L16;codec=pcm;rate=24000")

        self.assertTrue(wav_bytes.startswith(b"RIFF"))
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)
            self.assertEqual(wf.getframerate(), 24000)
            self.assertEqual(wf.getnframes(), 100)

    def test_convert_pcm_to_wav_custom_rate(self):
        raw_pcm = b"\x12\x34" * 50
        wav_bytes = tts.convert_pcm_to_wav(raw_pcm, "audio/pcm;rate=16000")

        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)
            self.assertEqual(wf.getframerate(), 16000)
            self.assertEqual(wf.getnframes(), 50)

    def test_convert_pcm_to_wav_passthrough_riff(self):
        fake_riff = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
        result = tts.convert_pcm_to_wav(fake_riff, "audio/wav")
        self.assertEqual(result, fake_riff)


class TestTTSSynthesis(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_synthesize_gemini_pcm(self, mock_urlopen):
        raw_pcm = b"\x00\x00" * 100
        b64_audio = base64.b64encode(raw_pcm).decode("ascii")
        mock_response_body = json.dumps({
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/L16;codec=pcm;rate=24000",
                                    "data": b64_audio,
                                }
                            }
                        ]
                    }
                }
            ]
        }).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response_body
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        audio_bytes, ext = tts.synthesize_gemini(
            text="Hello world",
            api_key="test-gemini-key",
            model="gemini-2.5-flash-preview-tts",
            voice="Kore",
        )

        self.assertEqual(ext, ".wav")
        self.assertTrue(audio_bytes.startswith(b"RIFF"))

        # Verify request call args
        req = mock_urlopen.call_args[0][0]
        self.assertIn("gemini-2.5-flash-preview-tts:generateContent", req.full_url)
        self.assertEqual(req.headers["X-goog-api-key"], "test-gemini-key")
        self.assertEqual(req.headers["Content-type"], "application/json")

        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["contents"][0]["parts"][0]["text"], "Hello world")
        self.assertEqual(payload["generationConfig"]["responseModalities"], ["AUDIO"])
        self.assertEqual(
            payload["generationConfig"]["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"],
            "Kore",
        )

    @patch("urllib.request.urlopen")
    def test_synthesize_gemini_mp3(self, mock_urlopen):
        raw_mp3 = b"FAKE_MP3_STREAM_DATA"
        b64_audio = base64.b64encode(raw_mp3).decode("ascii")
        mock_response_body = json.dumps({
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/mpeg",
                                    "data": b64_audio,
                                }
                            }
                        ]
                    }
                }
            ]
        }).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response_body
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        audio_bytes, ext = tts.synthesize_gemini(
            text="Hello world",
            api_key="test-key",
            model="gemini-2.5-flash-preview-tts",
            voice="Kore",
        )

        self.assertEqual(ext, ".mp3")
        self.assertEqual(audio_bytes, raw_mp3)

    @patch("urllib.request.urlopen")
    def test_synthesize_elevenlabs(self, mock_urlopen):
        raw_mp3 = b"ELEVENLABS_MP3_BYTES"
        mock_resp = MagicMock()
        mock_resp.read.return_value = raw_mp3
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        audio_bytes, ext = tts.synthesize_elevenlabs(
            text="Testing ElevenLabs",
            api_key="test-eleven-key",
            model="eleven_flash_v2_5",
            voice="EXAVITQu4vr4xnSDxMaL",
        )

        self.assertEqual(ext, ".mp3")
        self.assertEqual(audio_bytes, raw_mp3)

        req = mock_urlopen.call_args[0][0]
        self.assertIn("/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL", req.full_url)
        self.assertIn("output_format=mp3_44100_128", req.full_url)
        self.assertEqual(req.headers["Xi-api-key"], "test-eleven-key")
        self.assertEqual(req.headers["Accept"], "audio/mpeg")

        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["text"], "Testing ElevenLabs")
        self.assertEqual(payload["model_id"], "eleven_flash_v2_5")


class TestHTTPErrorHandling(unittest.TestCase):
    def test_auth_errors_return_2(self):
        for code in (401, 403):
            err = urllib.error.HTTPError(
                url="http://example.com",
                code=code,
                msg="Forbidden",
                hdrs={},
                fp=io.BytesIO(b'{"error": "Unauthorized key"}'),
            )
            with patch("sys.stderr", new=io.StringIO()):
                self.assertEqual(tts.handle_http_error(err), 2)

    def test_400_invalid_api_key_returns_2(self):
        err = urllib.error.HTTPError(
            url="http://example.com",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=io.BytesIO(b'{"error": {"code": 400, "message": "API_KEY_INVALID", "status": "INVALID_ARGUMENT"}}'),
        )
        with patch("sys.stderr", new=io.StringIO()):
            self.assertEqual(tts.handle_http_error(err), 2)

    def test_400_other_returns_1(self):
        err = urllib.error.HTTPError(
            url="http://example.com",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=io.BytesIO(b'{"error": "Invalid voice"}'),
        )
        with patch("sys.stderr", new=io.StringIO()):
            self.assertEqual(tts.handle_http_error(err), 1)

    def test_server_or_rate_limit_returns_1(self):
        for code in (429, 500, 503):
            err = urllib.error.HTTPError(
                url="http://example.com",
                code=code,
                msg="Error",
                hdrs={},
                fp=io.BytesIO(b'{"error": "Rate limit exceeded"}'),
            )
            with patch("sys.stderr", new=io.StringIO()):
                self.assertEqual(tts.handle_http_error(err), 1)


class TestStateMachine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.state_file = os.path.join(self.test_dir.name, "state.json")
        self.dummy_audio = os.path.join(self.test_dir.name, "audio.wav")
        with open(self.dummy_audio, "wb") as f:
            f.write(b"AUDIO")

    def tearDown(self):
        self.test_dir.cleanup()

    @patch("tts.is_process_group_alive")
    @patch("os.killpg")
    def test_same_text_toggles_stop(self, mock_killpg, mock_alive):
        mock_alive.return_value = True
        state_data = {
            "pgid": 12345,
            "text_sha256": "hash_apple",
            "audio_path": self.dummy_audio,
        }
        with open(self.state_file, "w") as f:
            json.dump(state_data, f)

        # Same text clicked
        stopped = tts.check_and_stop_previous(self.state_file, "hash_apple")
        self.assertTrue(stopped)
        mock_killpg.assert_called_once_with(12345, signal.SIGTERM)
        self.assertFalse(os.path.exists(self.dummy_audio))
        self.assertFalse(os.path.exists(self.state_file))

    @patch("tts.is_process_group_alive")
    @patch("os.killpg")
    def test_different_text_interrupts(self, mock_killpg, mock_alive):
        mock_alive.return_value = True
        state_data = {
            "pgid": 12345,
            "text_sha256": "hash_apple",
            "audio_path": self.dummy_audio,
        }
        with open(self.state_file, "w") as f:
            json.dump(state_data, f)

        # Different text clicked
        stopped = tts.check_and_stop_previous(self.state_file, "hash_banana")
        self.assertFalse(stopped)
        mock_killpg.assert_called_once_with(12345, signal.SIGTERM)
        self.assertFalse(os.path.exists(self.dummy_audio))
        self.assertFalse(os.path.exists(self.state_file))

    @patch("tts.is_process_group_alive")
    @patch("os.killpg")
    def test_stale_dead_process_cleans_up(self, mock_killpg, mock_alive):
        mock_alive.return_value = False
        state_data = {
            "pgid": 99999,
            "text_sha256": "hash_apple",
            "audio_path": self.dummy_audio,
        }
        with open(self.state_file, "w") as f:
            json.dump(state_data, f)

        stopped = tts.check_and_stop_previous(self.state_file, "hash_apple")
        self.assertFalse(stopped)
        mock_killpg.assert_not_called()
        self.assertFalse(os.path.exists(self.state_file))

    def test_no_state_file(self):
        stopped = tts.check_and_stop_previous(self.state_file, "hash_apple")
        self.assertFalse(stopped)


class TestMainWorkflow(unittest.TestCase):
    def test_empty_text_exits_0(self):
        with patch("tts.get_input_text", return_value=""):
            self.assertEqual(tts.main(), 0)

    def test_too_long_text_exits_1(self):
        long_text = "a" * (tts.MAX_TEXT_LENGTH + 1)
        with patch("tts.get_input_text", return_value=long_text), patch("sys.stderr", new=io.StringIO()):
            self.assertEqual(tts.main(), 1)

    def test_missing_gemini_api_key_exits_2(self):
        env = {
            "POPCLIP_OPTION_PROVIDER": "gemini",
            "POPCLIP_OPTION_GEMINI_API_KEY": "",
        }
        with patch("tts.get_input_text", return_value="Hello"), \
             patch.dict(os.environ, env, clear=True), \
             patch("sys.stderr", new=io.StringIO()):
            self.assertEqual(tts.main(), 2)

    def test_missing_elevenlabs_api_key_exits_2(self):
        env = {
            "POPCLIP_OPTION_PROVIDER": "elevenlabs",
            "POPCLIP_OPTION_ELEVENLABS_API_KEY": "",
        }
        with patch("tts.get_input_text", return_value="Hello"), \
             patch.dict(os.environ, env, clear=True), \
             patch("sys.stderr", new=io.StringIO()):
            self.assertEqual(tts.main(), 2)

    @patch("tts.check_and_stop_previous", return_value=True)
    def test_toggle_stop_exits_0_without_calling_api(self, mock_stop):
        with patch("tts.get_input_text", return_value="Stop me"), \
             patch("tts.synthesize_gemini") as mock_synth:
            self.assertEqual(tts.main(), 0)
            mock_synth.assert_not_called()

    @patch("tts.start_playback")
    @patch("tts.synthesize_gemini", return_value=(b"RIFF_AUDIO", ".wav"))
    @patch("tts.check_and_stop_previous", return_value=False)
    def test_successful_gemini_play(self, mock_stop, mock_synth, mock_play):
        env = {
            "POPCLIP_OPTION_PROVIDER": "gemini",
            "POPCLIP_OPTION_GEMINI_API_KEY": "valid-key",
            "POPCLIP_OPTION_GEMINI_MODEL": "gemini-2.5-flash-preview-tts",
            "POPCLIP_OPTION_GEMINI_VOICE": "Kore",
        }
        with patch("tts.get_input_text", return_value="Read this text"), \
             patch.dict(os.environ, env, clear=True):
            self.assertEqual(tts.main(), 0)
            mock_synth.assert_called_once_with(
                "Read this text", "valid-key", "gemini-2.5-flash-preview-tts", "Kore"
            )
            mock_play.assert_called_once()


if __name__ == "__main__":
    unittest.main()
