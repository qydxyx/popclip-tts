# PopClip TTS Extension (Gemini & ElevenLabs)

A lightweight, zero-dependency [PopClip](https://popclip.app/) extension for macOS that reads selected text aloud using Google Gemini, ElevenLabs, and Alibaba Cloud Bailian (DashScope) text-to-speech APIs.

---

## Features

- **Multi-Provider Support**: Seamlessly switch between Google Gemini, ElevenLabs, and Alibaba Cloud Bailian (百炼) in preferences.
- **Smart Single-Button Action**: Adds a single speaker button (`speaker.wave.2.fill`) to the PopClip bar.
- **Background Playback & Toggle Stop**: Plays audio asynchronously in the background via macOS `/usr/bin/afplay`. Clicking again on the same text stops playback immediately; clicking on new text interrupts the previous speech and starts the new one.
- **Secure Keychain Storage**: API keys are securely managed by PopClip and stored directly in the macOS Keychain.
- **Automatic Configuration Guide**: Exits with status code `2` on missing or invalid API keys, automatically prompting the PopClip settings interface.
- **Zero Third-Party Dependencies**: Runs on macOS built-in `/usr/bin/python3` standard library. No `pip install` or external runtimes required.

---

## Installation

### Method 1: Download from Releases (Recommended)
1. Download `TTS.popclipextz` from the latest [GitHub Release](https://github.com/qydxyx/popclip-tts/releases).
2. Double-click the downloaded file to install it into PopClip.

### Method 2: From Source
Clone the repository and open the package:
```bash
git clone https://github.com/qydxyx/popclip-tts.git
cd popclip-tts
open TTS.popclipext
```

---

## Configuration

In PopClip Preferences -> **Extensions** -> click the gear icon next to **TTS / 朗读**:

### 1. Service Provider
- **Gemini** (Default): High throughput, ultra-low latency, and natural inflection across 100+ languages.
- **ElevenLabs**: Expressive, highly nuanced vocal acting with rich voice cloning capabilities across 32+ languages.
- **Alibaba Bailian (阿里云百炼)**: High-fidelity Chinese, English, dialect, and cross-lingual speech synthesis powered by Qwen-Audio 3.1 TTS.

### 2. Gemini Settings
- **API Key** (Required): Obtain your key from [Google AI Studio](https://aistudio.google.com/).
- **Model**:
  - `gemini-3.8-flash-lite-tts` (Default: fast, cost-effective read-aloud model)
  - `gemini-3.8-flash-tts` (Flagship studio-grade model)
  - Supports typing any custom Gemini model ID via `Other...`.
- **Voice**:
  - 30 prebuilt Google Studio voices: `Kore` (Default), `Puck`, `Charon`, `Fenrir`, `Aoede`, `Zephyr`, `Achernar`, `Achird`, `Algenib`, `Algieba`, `Alnilam`, `Autonoe`, `Callirrhoe`, `Despina`, `Enceladus`, `Erinome`, `Gacrux`, `Iapetus`, `Laomedeia`, `Leda`, `Orus`, `Pulcherrima`, `Rasalgethi`, `Sadachbia`, `Sadaltager`, `Schedar`, `Sulafat`, `Umbriel`, `Vindemiatrix`, `Zubenelgenubi`.
  - Supports typing any custom voice name via `Other...`.

### 3. ElevenLabs Settings
- **API Key** (Required): Obtain your key from the [ElevenLabs Console](https://elevenlabs.io/).
- **Model**:
  - `eleven_flash_v2_5` (Default: fast, low-latency multilingual model)
  - `eleven_multilingual_v2`
  - `eleven_turbo_v2_5`
  - `eleven_v3`
  - Supports typing custom model IDs via `Other...`.
- **Voice**:
  - Curated American English & Multilingual voices:
    - `Rachel` (Default: American female, calm)
    - `Adam` (American male, deep narration)
    - `Sarah` (American female, soft)
    - `Antoni` (American male, well-rounded)
    - `Aria` (American female, expressive)
    - `Josh` (American male, warm)
    - `Domi` (American female, strong)
    - `Elli` (American female, emotional)
    - `Sam` (American male, dynamic)
    - `Michael` (American male, natural)
    - `Jessica` (American female, playful)
    - `Eric` (American male, conversational)
    - `Will` (American male, relaxed)
    - `Drew` (American male, confident)
    - `Roger` (American male, grounded)
    - `Charlotte` (Multilingual female, character)
    - `Callum` (Multilingual male, dramatic)
    - `Freya` (Multilingual female, expressive)
  - Supports pasting any custom or cloned `voice_id` via `Other...`.

### 4. Alibaba Cloud Bailian (阿里云百炼) Settings
- **API Key** (Required): Obtain your DashScope API key from [Alibaba Cloud Model Studio (百炼控制台)](https://bailian.console.aliyun.com/).
- **Model**:
  - `qwen-audio-3.1-tts-flash` (Default: ultra-low latency, real-time interactive model)
  - `qwen-audio-3.1-tts-plus` (Flagship studio-grade model for maximum fidelity)
  - Supports typing any custom Qwen/DashScope TTS model ID via `Other...`.
- **Voice**:
  - **Chinese & Multilingual / Dialects**:
    - `longanlingxin_v3.1` (Default: 龙安灵心, female, gentle & supports French/Yunnan/Shaanxi/Shanghainese)
    - `longanhuan_v3.1` (龙安环, female, lively)
    - `longanfengyue_v3.1` (龙安风悦, female, intellectual & calm)
    - `xunanchuan_v3.1` (许南川, male, professional broadcast)
    - `longanqian_v3.1` (龙安谦, male, gentle & refined)
  - **English (American Accents)**:
    - Female: `Annie_v3.1`, `Ava_v3.1`, `Beth_v3.1`, `Betty_v3.1`, `Cally_v3.1`, `Cindy_v3.1`, `Donna_v3.1`
    - Male: `Andy_v3.1`, `Brian_v3.1`, `David_v3.1`
  - Supports entering any custom or fine-tuned voice ID via `Other...`.

---

## Offline Tests

Run the complete test suite (covers PCM to WAV conversion, HTTP payloads, error code mapping, and process state machine):
```bash
/usr/bin/python3 -m unittest discover -s tests -v
```

---

## Project Structure

```text
popclip-tts/
├── TTS.popclipext/
│   ├── Config.yaml      # Extension manifest and options schema
│   └── tts.py           # Core TTS driver, audio packaging, and process manager
├── tests/
│   └── test_tts.py      # Offline unit tests
└── README.md            # Documentation
```

---

## License

MIT License
