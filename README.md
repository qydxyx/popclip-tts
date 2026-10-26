# PopClip 在线 TTS 扩展（Gemini & ElevenLabs）

基于 macOS 原生能力（`/usr/bin/python3` 标准库 + `/usr/bin/afplay`）与 PopClip 扩展规范构建的零第三方依赖划词朗读扩展。

## 特性

- **双服务商支持**：内置 Google Gemini 与 ElevenLabs 在线语音合成。
- **单按钮智能交互**：PopClip 面板仅占一个按钮（`speaker.wave.2.fill` 图标），在设置中自由切换服务商。
- **后台异步播放与同文即停**：点击后后台无阻塞朗读；朗读途中再次点击相同选中文本立即停止播放；选中新文本点击自动打断上一段并播放新语音。
- **安全密钥存储**：API Key 采用 PopClip `secret` 类型，自动托管于 macOS 系统钥匙串（Keychain）。
- **配置错误自动引导**：初次使用未配置 API Key 或服务端提示密钥无效时，返回状态码 `2`，自动弹出 PopClip 扩展设置界面。
- **零外部依赖**：仅依赖 macOS 自带 Python 3 标准库，无需 `pip install` 任何额外库。

---

## 安装方法

### 方式一：终端命令安装
在本项目根目录下执行：
```bash
open TTS.popclipext
```

### 方式二：双击安装
在访达（Finder）中直接双击 `TTS.popclipext` 文件夹，PopClip 会自动识别并提示安装。

---

## 配置说明

安装后在 PopClip 偏好设置 -> 扩展列表 -> 点击「TTS / 朗读」右侧齿轮打开设置面板：

### 1. 服务商（Service Provider）
- **Gemini**（默认）：速度极快、自然度高，支持多语言。
- **ElevenLabs**：情感表达丰富，支持多语种及声音克隆。

### 2. Gemini 设置
- **API Key**（必填）：在 [Google AI Studio](https://aistudio.google.com/) 获取。
- **模型（Model）**：
  - `gemini-3.8-flash-lite-tts`（默认，高吞吐低延迟朗读模型）
  - `gemini-3.8-flash-tts`（旗舰级高表现力模型）
  - 支持手动输入其他 Gemini 模型名称。
- **音色（Voice）**：
  - 预设 30 种官方 Studio 预置音色：`Kore`（默认）、`Puck`、`Charon`、`Fenrir`、`Aoede`、`Zephyr`、`Achernar`、`Achird`、`Algenib`、`Algieba`、`Alnilam`、`Autonoe`、`Callirrhoe`、`Despina`、`Enceladus`、`Erinome`、`Gacrux`、`Iapetus`、`Laomedeia`、`Leda`、`Orus`、`Pulcherrima`、`Rasalgethi`、`Sadachbia`、`Sadaltager`、`Schedar`、`Sulafat`、`Umbriel`、`Vindemiatrix`、`Zubenelgenubi`。
  - 支持手动输入任意 Gemini 预置音色名。

### 3. ElevenLabs 设置
- **API Key**（必填）：在 [ElevenLabs 控制台](https://elevenlabs.io/) 获取。
- **模型（Model）**：
  - `eleven_flash_v2_5`（默认，低延迟支持 32 种语言）
  - `eleven_multilingual_v2`
  - `eleven_turbo_v2_5`
  - `eleven_v3`
  - 支持手动输入其他 ElevenLabs 模型 ID。
- **音色（Voice）**：
  - 预设通用音色：
    - `Sarah`（默认，ID: `EXAVITQu4vr4xnSDxMaL`）
    - `George`（ID: `JBFqnCBsd6RMkjVDRZzb`）
    - `Alice`（ID: `Xb7hH8MSUJpSbSDYk0k2`）
    - `Daniel`（ID: `onwK4e9ZLuTAKqWW03F9`）
    - `Lily`（ID: `pFZP5JQG7iQjIQuC4Bku`）
  - 支持粘贴任意自定义或克隆的 `voice_id`。

---

## 自动化测试

运行本地离线测试套件（覆盖 PCM 封装、网络载荷组装、HTTP 错误码映射及播放状态机）：
```bash
/usr/bin/python3 -m unittest discover -s tests
```

---

## 文件结构

```text
popclip-tts/
├── TTS.popclipext/
│   ├── Config.yaml      # PopClip 扩展声明与设置界面配置
│   └── tts.py           # TTS 核心调度、音频转换与后台播放脚本
├── tests/
│   └── test_tts.py      # 单元测试用例集
└── README.md            # 项目说明与配置指南
```
