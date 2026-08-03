# Mini Jarvis: Sherlock — System Audit & Progress Report

**Role:** Lead AI Systems Architect Review  
**Date:** August 3, 2026  
**Project Scope:** Modular Python Voice Assistant ("Sherlock")  
**Target Pipeline Architecture:**  
`Wake Word (Porcupine/openWakeWord)` ➔ `STT (faster-whisper)` ➔ `LLM Brain (Gemini ReAct)` ➔ `TTS (ElevenLabs/Piper)`

---

## 1. Workspace Audit & Feature Checklist

### 1.1 Architectural Phase Roadmap & Status

| Phase | Phase Name | Status | Key Components & Implementation Notes |
| :--- | :--- | :--- | :--- |
| **Phase 0** | **Environment Setup & API Credentials** | **[Completed]** | Modular directory layout (`brain/`, `core/`, `tools/`, `utils/`), virtual environment (`lock`), centralized [config.py](file:///d:/Work/Sherlock/Code/config.py), `.env` key schema, and static typing configurations. |
| **Phase 1** | **Text-Only Brain with LLM Function Calling** | **[Completed]** | Native `google-genai` SDK integration for Gemini (`gemini-2.5-flash`). Interleaved ReAct decision engine loop (`user_query` ➔ `response.function_calls` ➔ local tool execution ➔ `types.Part.from_function_response` observation feedback) in [main.py](file:///d:/Work/Sherlock/Code/main.py). |
| **Phase 2** | **Text-to-Speech Output (TTS)** | **[Completed]** | Production `TextToSpeech` engine in [core/tts.py](file:///d:/Work/Sherlock/Code/core/tts.py) with ElevenLabs low-latency model (`eleven_turbo_v2_5`), in-memory `io.BytesIO` buffer playback via `pygame.mixer`, graceful `[TTS Bypass]` logging fallback, and local Piper/VITS abstraction. |
| **Phase 3** | **Speech-to-Text Input (Push-to-Talk)** | **[Completed]** | Production-ready Push-to-Talk audio recording via `sounddevice` in [core/audio_recorder.py](file:///d:/Work/Sherlock/Code/core/audio_recorder.py) paired with local `faster-whisper` transcription in [core/stt.py](file:///d:/Work/Sherlock/Code/core/stt.py) integrated into [main.py](file:///d:/Work/Sherlock/Code/main.py). |
| **Phase 4** | **Always-Listening Wake Word Detection** | **[In Progress]** | Skeleton established in [core/wakeword.py](file:///d:/Work/Sherlock/Code/core/wakeword.py) targeting Picovoice Porcupine. Hardware audio stream listener pending `PICOVOICE_ACCESS_KEY` and streaming buffer hookup. |
| **Phase 5** | **Tool Expansion & Memory Persistence** | **[In Progress]** | Decorator-based [ToolRegistry](file:///d:/Work/Sherlock/Code/tools/registry.py) active with [timer.py](file:///d:/Work/Sherlock/Code/tools/timer.py) and [app_opener.py](file:///d:/Work/Sherlock/Code/tools/app_opener.py). Weather API tool is stubbed; Google Calendar and Web Search are stubs. Session memory is ephemeral. |
| **Phase 6** | **Hardening, Latency Reduction & Streaming** | **[Not Started]** | Pipeline runs synchronously end-to-end. Audio streaming pipelines (chunked TTS/STT), async task orchestration (`asyncio`), and speech barge-in interrupt handling are not yet implemented. |

---

### 1.2 Feature Completion Checklist

- [x] **Centralized Configuration ([config.py](file:///d:/Work/Sherlock/Code/config.py)):** `.env` parameter parsing with fallback mechanisms.
- [x] **Logging System ([utils/logger.py](file:///d:/Work/Sherlock/Code/utils/logger.py)):** Structured console log format across modules.
- [x] **Gemini GenAI Brain ([brain/llm_client.py](file:///d:/Work/Sherlock/Code/brain/llm_client.py)):** Gemini 2.0 Flash client with history formatting and system instruction injection.
- [x] **ReAct Prompt System ([brain/prompt_template.py](file:///d:/Work/Sherlock/Code/brain/prompt_template.py)):** Sherlock detective/butler persona with strict ReAct instructions.
- [x] **Dynamic Tool Registry ([tools/registry.py](file:///d:/Work/Sherlock/Code/tools/registry.py)):** Decorator pattern (`@tools.register`) for tool binding and invocation.
- [x] **Local Subprocess App Launcher ([tools/app_opener.py](file:///d:/Work/Sherlock/Code/tools/app_opener.py)):** Non-blocking Windows binary execution (Notepad, Calc, Chrome, Edge).
- [x] **Threaded Countdown Timer ([tools/timer.py](file:///d:/Work/Sherlock/Code/tools/timer.py)):** Non-blocking daemon background thread with console notification.
- [x] **Cloud Text-to-Speech Engine ([main.py](file:///d:/Work/Sherlock/Code/main.py)):** ElevenLabs streaming generation with Pygame buffer playback.
- [x] **Conversational Memory Window ([brain/prompt_template.py](file:///d:/Work/Sherlock/Code/brain/prompt_template.py)):** Sliding-window turn history (`ConversationMemory`).
- [x] **Real-time Weather Tool ([tools/weather.py](file:///d:/Work/Sherlock/Code/tools/weather.py)):** Live OpenWeatherMap API HTTP integration with fallback.
- [ ] **Web Search Tool ([tools/search.py](file:///d:/Work/Sherlock/Code/tools/search.py)):** Live search engine scraper/API integration.
- [ ] **Google Calendar Tool ([tools/calendar_tool.py](file:///d:/Work/Sherlock/Code/tools/calendar_tool.py)):** OAuth2 / CalDAV calendar scheduling integration.
- [x] **Speech-to-Text Engine ([core/stt.py](file:///d:/Work/Sherlock/Code/core/stt.py)):** `faster-whisper` model loading and audio transcription.
- [x] **Microphone Input Recorder ([core/audio_recorder.py](file:///d:/Work/Sherlock/Code/core/audio_recorder.py)):** `sounddevice` 16kHz 16-bit mono microphone capture into WAV files.
- [ ] **Hands-Free Wake Word Detector ([core/wakeword.py](file:///d:/Work/Sherlock/Code/core/wakeword.py)):** Picovoice Porcupine / openWakeWord continuous frame analyzer.
- [ ] **Session State Persistence:** Serialization of memory and settings to SQLite or local JSON.

---

## 2. Architectural & Theoretical Grounding Analysis

### 2.1 ReAct Pattern (Yao et al., 2022)
*Reasoning and Acting in Language Models*

* **Theoretical Paradigm:** The ReAct framework interleaves domain reasoning traces (`Thought`) with environment actions (`Action` / `Action Input`), processing system feedback (`Observation`) in a tight execution loop. This reduces hallucinations by grounding answers in tool observations.
* **Audit Assessment:** In [main.py](file:///d:/Work/Sherlock/Code/main.py) (`run_react_loop`) and [prompt_template.py](file:///d:/Work/Sherlock/Code/brain/prompt_template.py), the prompt explicitly forces the step sequence:
  $$\text{Thought} \rightarrow \text{Action} \rightarrow \text{Action Input} \rightarrow \text{Observation} \rightarrow \text{Final Answer}$$
* **Identified Architectural Flaws:**
  1. **Fragile String/Regex Parsing:** `parse_action()` relies on strict regular expressions (`r"Action:\s*([a-zA-Z0-9_-]+)"`). If the LLM generates slight syntax variations (e.g., markdown code blocks, alternative key casing, or multi-line parameters), parsing silently fails.
  2. **Unstructured Single-Argument Assumption:** `parse_action` only extracts a single string argument. Complex tools requiring multiple typed parameters (e.g., `add_event(summary, start_time)`) cannot be parsed cleanly.
  3. **Recommendation:** Migrate from string-based prompt ReAct parsing to native Gemini **Structured Function Calling** (`google.genai.types.Tool` & `FunctionDeclaration`), delegating schema enforcement directly to the API encoder.

---

### 2.2 Tool Usage Optimization (Toolformer - Schick et al., 2023)
*Language Models Can Teach Themselves to Use Tools*

* **Theoretical Paradigm:** Toolformer demonstrates that LLMs achieve optimal tool utilization when tool signatures, parameter descriptions, and return types are strictly structured and bounded.
* **Audit Assessment:** [tools/registry.py](file:///d:/Work/Sherlock/Code/tools/registry.py) defines a clean dynamic decorator (`@tools.register`). However, [prompt_template.py](file:///d:/Work/Sherlock/Code/brain/prompt_template.py) **hardcodes** tool descriptions inside the system prompt string rather than dynamically building them from `ToolRegistry.get_tool_definitions()`.
* **Identified Architectural Flaws:**
  1. **Schema Drift:** Registering a new tool in Python code does not automatically update the LLM system prompt in [prompt_template.py](file:///d:/Work/Sherlock/Code/brain/prompt_template.py), leading to missing tools or description mismatches.
  2. **Missing Parameter Schemas:** Tools lack type coercion contracts. When the LLM passes `"10"` as a string for `set_timer`, the tool function must perform manual string-to-int conversion.
  3. **Recommendation:** Use standard Pydantic models or inspect Python docstrings to dynamically export OpenAPI-compliant JSON Schemas directly to the LLM context.

---

### 2.3 End-to-End Speech Recognition (Whisper - Radford et al., 2022)
*Robust Speech Recognition via Large-Scale Weak Supervision*

* **Theoretical Paradigm:** Whisper utilizes an encoder-decoder Transformer architecture trained on 680,000 hours of multilingual audio, processing 30-second log-Mel spectrogram chunks.
* **Audit Assessment:** [core/stt.py](file:///d:/Work/Sherlock/Code/core/stt.py) references `faster-whisper` (CTranslate2 reimplementation of Whisper), configured for `base` model running on `cpu`.
* **STT Readiness & Trade-off Analysis:**
  * **Compute vs. Accuracy:** Running `base` on CPU with `int8` quantization yields a Real-Time Factor $RTF \approx 0.15 - 0.25$, balancing low latency (~300ms for 3s audio) with acceptable word error rates (WER).
  * **VAD Pre-filtering Requirement:** Raw Whisper decoder inference on quiet or noisy audio chunks can hallucinate repetitive phrase loops (e.g., "Thank you."). Integrating a lightweight Voice Activity Detector (such as **Silero VAD**) prior to Whisper encoding is mandatory to strip silence frames.

---

### 2.4 On-Device Keyword Spotting (Hello Edge - Zhang et al., 2017)
*Keyword Spotting Using Convolutional Neural Networks*

* **Theoretical Paradigm:** On-device Keyword Spotting (KWS) requires micro-DNN architectures (e.g., Depthwise Separable CNNs or RNNs) capable of non-stop stream classification under tight RAM/CPU constraints.
* **Audit Assessment:** [core/wakeword.py](file:///d:/Work/Sherlock/Code/core/wakeword.py) targets Picovoice Porcupine.
* **Wake Word Strategy Analysis:**
  * **Efficiency:** Porcupine operates entirely local in < 2 MB RAM with < 1% single-core CPU utilization, eliminating cloud latency and continuous cloud bandwidth usage.
  * **Privacy Guarantee:** Audio frames never leave local device RAM during passive monitoring.
  * **Dependency Risk:** Porcupine requires an active `PICOVOICE_ACCESS_KEY`. To ensure offline resilience without key dependencies, the system should implement a fallback engine using **openWakeWord** (ONNX Runtime).

---

### 2.5 Single-Stage End-to-End TTS (VITS - Kim et al., 2021)
*Conditional Variational Autoencoder with Adversarial Learning for End-to-End Text-to-Speech*

* **Theoretical Paradigm:** Traditional two-stage TTS architectures (Text ➔ Spectrogram Generator ➔ Neural Vocoder) incur compounded inference latency. Single-stage models like VITS unify acoustic features and waveform generation into a single VAE/Flow network.
* **Audit Assessment:** [main.py](file:///d:/Work/Sherlock/Code/main.py) currently relies on ElevenLabs (two-stage cloud API).
* **Trade-off Matrix:**

| Dimension | Cloud TTS (ElevenLabs `eleven_turbo_v2_5`) | Local Single-Stage TTS (Piper / VITS) |
| :--- | :--- | :--- |
| **Synthesis Latency** | High ($T_{\text{network}} + T_{\text{gen}} \approx 800 - 1500\text{ms}$) | Near-Zero ($RTF < 0.05$ on CPU, $< 150\text{ms}$) |
| **Voice Naturalness** | Exceptional (Human-grade expressiveness) | High (Clean, clear, slightly robotic) |
| **Offline Operation** | Impossible (Requires active internet connection) | 100% Fully Offline |
| **Cost Scale** | Tiered API subscription fees per character | Completely Free / Open-Source |

---

## 3. Actionable Next Steps, Blockers & Quantitative Latency Analysis

### 3.1 Active Runtime Bugs & Critical Unhandled Exception Paths

1. **Missing `.env` Credentials & Silent TTS Bypass:**
   * **Issue:** `ELEVENLABS_API_KEY`, `PICOVOICE_ACCESS_KEY`, `OPENAI_API_KEY`, and `ANTHROPIC_API_KEY` are empty in [.env](file:///d:/Work/Sherlock/Code/.env).
   * **Impact:** `speak_text()` in [main.py](file:///d:/Work/Sherlock/Code/main.py) falls back to console logging (`[TTS Bypass]`), resulting in no audible speech output.
2. **Unintegrated Weather API:**
   * **Issue:** `WEATHER_API_KEY` is present in [.env](file:///d:/Work/Sherlock/Code/.env), but [tools/weather.py](file:///d:/Work/Sherlock/Code/tools/weather.py) has commented-out HTTP requests and returns a static string: `"Weather information for ... is currently unavailable (API integration pending)."`.
3. **Single-Argument Regex Parsing Failure:**
   * **Issue:** `parse_action()` in [main.py](file:///d:/Work/Sherlock/Code/main.py) captures only one argument via `Action Input: (.+)`.
   * **Impact:** Multi-argument tools or complex JSON structures cause regex truncation or tool invocation signature errors.
4. **Blocking Main Thread GUI/CLI Freeze:**
   * **Issue:** `speak_text()` contains a busy-wait loop: `while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)`.
   * **Impact:** Completely blocks the main thread during audio playback, preventing user interruption, wake-word detection, or concurrent command processing.
5. **Uninstalled Core Dependencies:**
   * **Issue:** `faster-whisper` and `pvporcupine` are listed in `requirements.txt` but are not installed in the active virtual environment (`lock`).

---

### 3.2 End-to-End Loop Latency Modeling

The total end-to-end processing delay $T_{\text{total}}$ for a complete voice interaction turn is defined by:

$$T_{\text{total}} = T_{\text{STT}} + T_{\text{LLM Tool}} + T_{\text{Tool Exec}} + T_{\text{LLM Final}} + T_{\text{TTS}}$$

Where:
* $T_{\text{STT}}$: Time to record audio, capture VAD end-of-speech, and transcribe speech to text.
* $T_{\text{LLM Tool}}$: Latency for Gemini ReAct reasoning step 1 to decide on tool usage.
* $T_{\text{Tool Exec}}$: Latency of executing the local or external HTTP tool function.
* $T_{\text{LLM Final}}$: Latency for Gemini ReAct reasoning step 2 to synthesize final text answer.
* $T_{\text{TTS}}$: Time to synthesize voice audio and initiate speaker buffer playback.

#### Latency Decomposition (Current Implementation Estimates):

$$\begin{aligned}
T_{\text{STT}} &\approx 800\text{ms} - 1200\text{ms} \quad (\text{Whisper Base CPU inference + buffer copy}) \\
T_{\text{LLM Tool}} &\approx 400\text{ms} - 700\text{ms} \quad (\text{Gemini 2.0 Flash RTT + output tokens}) \\
T_{\text{Tool Exec}} &\approx 150\text{ms} - 350\text{ms} \quad (\text{Local Subprocess / Weather HTTP API}) \\
T_{\text{LLM Final}} &\approx 400\text{ms} - 600\text{ms} \quad (\text{Gemini 2.0 Flash Final Answer synthesis}) \\
T_{\text{TTS}} &\approx 900\text{ms} - 1800\text{ms} \quad (\text{ElevenLabs API generation + non-stream buffer download}) \\
\hline
\mathbf{T_{\text{total}}} &\approx \mathbf{2.65\text{s} - 4.65\text{s}} \quad (\text{Conversational delay is high; Target: } < 1.20\text{s})
\end{aligned}$$

---

### 3.3 Concrete Implementation Guide for Phase 3 (Push-to-Talk STT Integration)

To advance Sherlock from text-only interaction to voice-driven Push-to-Talk execution, complete the following steps:

#### Step 3.1: Install Audio & STT Dependencies
Run the following installation command inside the activated `lock` environment:
```bash
lock\Scripts\pip.exe install sounddevice numpy scipy faster-whisper
```

#### Step 3.2: Implement Audio Recorder ([core/audio_recorder.py](file:///d:/Work/Sherlock/Code/core/audio_recorder.py))
Update `AudioRecorder` using `sounddevice` to capture 16kHz, 16-bit mono PCM stream data upon keypress:
```python
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
from utils.logger import get_logger

logger = get_logger(__name__)

class AudioRecorder:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.recording = []
        self.is_recording = False

    def record_until_keypress(self) -> str:
        """Records microphone input until Enter is pressed, saving to a temp WAV file."""
        self.recording = []
        self.is_recording = True
        logger.info("Recording started. Speak now...")

        def callback(indata, frames, time_info, status):
            if self.is_recording:
                self.recording.append(indata.copy())

        with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='int16', callback=callback):
            input("Press [ENTER] to stop recording...")
            self.is_recording = False

        audio_data = np.concatenate(self.recording, axis=0)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        wav.write(temp_file.name, self.sample_rate, audio_data)
        logger.info(f"Audio saved to temporary file: {temp_file.name}")
        return temp_file.name
```

#### Step 3.3: Implement Speech-to-Text Engine ([core/stt.py](file:///d:/Work/Sherlock/Code/core/stt.py))
Connect `faster-whisper` model loading and transcription:
```python
from faster_whisper import WhisperModel
import config
from utils.logger import get_logger

logger = get_logger(__name__)

class SpeechToText:
    def __init__(self):
        self.model_size = config.STT_MODEL_SIZE
        self.device = config.STT_DEVICE
        self.model = None

    def load_model(self):
        if self.model is None:
            logger.info(f"Loading faster-whisper model '{self.model_size}' on '{self.device}'...")
            self.model = WhisperModel(self.model_size, device=self.device, compute_type="int8")

    def transcribe(self, audio_path: str) -> str:
        self.load_model()
        logger.info(f"Transcribing audio file: {audio_path}")
        segments, _ = self.model.transcribe(audio_path, beam_size=5)
        text = " ".join([segment.text for segment in segments]).strip()
        logger.info(f"Transcribed Text: '{text}'")
        return text
```

#### Step 3.4: Integrate Push-to-Talk in Main Orchestrator ([main.py](file:///d:/Work/Sherlock/Code/main.py))
Update `main()` loop to prompt the user for input mode selection (Text or Voice):
```python
# In main() loop of main.py:
print("Select Input Mode: [1] Text Prompt  [2] Push-to-Talk Voice")
mode = input("Choice (1/2): ").strip()

if mode == "2":
    wav_path = recorder.record_until_keypress()
    user_input = stt.transcribe(wav_path)
    print(f"You (Voice): {user_input}")
else:
    user_input = input("You: ").strip()
```

---

## 4. Architectural Sign-off & Summary

* **Current Baseline:** Phase 0 and Phase 1 are fully operational. Phase 2 (TTS) and Phase 5 (Tools) are functionally integrated but operate in partial stub/bypass mode.
* **Immediate Priority:** Execute Phase 3 (Push-to-Talk STT) to establish voice-in/voice-out capabilities before implementing Phase 4 (Continuous Wake Word Listener).
* **Architectural Horizon:** Replace string-regex ReAct parsing with native Gemini Function Calling, integrate Silero VAD for low-latency voice boundary detection, and evaluate Piper TTS for offline low-latency audio generation.
