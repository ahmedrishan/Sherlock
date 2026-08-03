# Mini Jarvis: Sherlock — System Audit & Development Roadmap

**Role:** Lead AI Systems Architect Review  
**Date:** August 2026  
**Project Scope:** Personal Voice Assistant ("Sherlock")  
**Target Pipeline Architecture:**  
`Wake Word (Porcupine)` ➔ `STT (faster-whisper)` ➔ `LLM Brain (Gemini ReAct)` ➔ `TTS (ElevenLabs/Pygame)`

---

## Part 1: Current Progress Audit Report

### 1. Architectural Phase Evaluation

| Phase | Phase Name | Status | Functionality & Notes |
| :--- | :--- | :--- | :--- |
| **Phase 0** | **Environment & Infrastructure** | **COMPLETE** | Modular directory structure, virtualenv setup (`lock`), centralized `config.py`, `.env` key management, and IDE type checking configuration (`pyrightconfig.json`, `.vscode/settings.json`). |
| **Phase 1** | **Cognitive Brain & ReAct Loop** | **COMPLETE** | Integrated `google-genai` SDK client for `gemini-1.5-flash`. Structured system prompt in `prompt_template.py` with multi-step reasoning (`Thought` ➔ `Action` ➔ `Action Input` ➔ `Observation` ➔ `Final Answer`). `ToolRegistry` router established. |
| **Phase 2** | **Text-to-Speech Output (TTS)** | **COMPLETE** | ElevenLabs SDK (`eleven_turbo_v2_5`) integrated with `pygame.mixer` for non-blocking stream buffer playback (`io.BytesIO`). Safely handles missing keys/audio devices with fallback logging. |
| **Phase 3** | **Push-to-Talk STT (Whisper)** | **PENDING** | `core/stt.py` is a stub. Microphone input payload needs connection to `faster-whisper`. |
| **Phase 4** | **Hands-Free Wake Word** | **PENDING** | `core/wakeword.py` is a stub. Requires `pvporcupine` or `openWakeWord` audio frame listener. |
| **Phase 5** | **Expanded Tools & Memory** | **PARTIAL** | Basic local tools (`get_weather`, `set_timer`, `open_app`) are live. Google Calendar and Web Search remain stubs. Ephemeral memory (`ConversationMemory`) works, but file persistence is pending. |
| **Phase 6** | **Streaming & Low Latency** | **PENDING** | Current pipeline runs synchronously end-to-end. Audio streaming pipeline to be built. |

---

### 2. Feature Completion Checklist

- [x] **Central Configuration (`config.py`):** Environment variable loading with fallback mechanisms.
- [x] **Logger Utility (`utils/logger.py`):** Standardized console stream logging.
- [x] **LLM Client (`brain/llm_client.py`):** Gemini 1.5 Flash client with chat history formatting.
- [x] **ReAct Prompt Engine (`brain/prompt_template.py`):** Strict ReAct pattern & Sherlock butler persona definition.
- [x] **Tool Router (`tools/registry.py`):** Decorator-based registration (`@tools.register`).
- [x] **Weather Tool (`tools/weather.py`):** City weather status query interface.
- [x] **Timer Tool (`tools/timer.py`):** Non-blocking background thread timer with console alerts.
- [x] **App Launcher (`tools/app_opener.py`):** Subprocess-based local Windows app opener (Notepad, Calc, Chrome, Edge).
- [x] **TTS Engine (`main.py` & `speak_text`):** ElevenLabs API output played via Pygame audio stream.
- [x] **Interactive CLI (`main.py`):** Multi-turn conversational prompt loop.
- [ ] **Speech-to-Text (`core/stt.py`):** Audio transcription using `faster-whisper`.
- [ ] **Microphone Recorder (`core/audio_recorder.py`):** PyAudio / SoundDevice capture loop.
- [ ] **Wake Word Engine (`core/wakeword.py`):** Porcupine keyword monitoring loop.
- [ ] **Persistent Memory Storage:** File/JSON session serialization across app restarts.

---

### 3. Technical & Performance Bottlenecks Analysis

1. **Full Audio Synthesis Delay (TTS Latency):**  
   In `speak_text()`, the audio stream generator (`eleven_client.generate(...)`) is fully consumed with `b"".join(...)` into a complete `io.BytesIO` buffer before Pygame starts playback. For long responses, this causes noticeable latency.
2. **Synchronous Busy-Wait Loop:**  
   The `while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)` loop blocks the main thread during speech playback. While appropriate for sequential CLI output, asynchronous non-blocking audio queues will be required for audio interruptions.
3. **Sequential ReAct Invocation:**  
   If the LLM triggers multiple tool actions in sequence, each action performs a separate round-trip HTTP request to the Gemini API, adding network overhead per step.
4. **Hardware Module Stubs:**  
   The classes in `core/` (`AudioRecorder`, `SpeechToText`, `WakeWordDetector`) remain skeleton interfaces and need full implementation.

---

## Part 2: Next Steps & Development Roadmap

```
           [ Phase 3: STT (Whisper) ]
                       │
                       ▼
         [ Phase 4: Wake Word Engine ]
                       │
                       ▼
       [ Phase 5: Tools & Persistent Memory ]
                       │
                       ▼
     [ Phase 6: Streaming & Latency Hardening ]
```

---

### Milestone 3: Push-to-Talk Speech-To-Text (Immediate Next Phase)

**Goal:** Allow users to record voice input by holding a key or pressing Enter, transcribe the speech using `faster-whisper`, and feed the transcribed prompt into the ReAct brain.

#### Implementation Steps:
1. **Audio Recording Core ([core/audio_recorder.py](file:///D:/Work/Sherlock/Code/core/audio_recorder.py)):**
   - Install `pyaudio` or `sounddevice` + `numpy`.
   - Implement `AudioRecorder` using `sounddevice.InputStream` to capture 16kHz, 16-bit mono PCM audio data into a temporary WAV file or memory buffer.
2. **Whisper Transcription Core ([core/stt.py](file:///D:/Work/Sherlock/Code/core/stt.py)):**
   - Install `faster-whisper`.
   - Initialize `WhisperModel(model_size="base", device="cpu", compute_type="int8")`.
   - Implement `transcribe(audio_file)` returning clean text strings.
3. **CLI Integration ([main.py](file:///D:/Work/Sherlock/Code/main.py)):**
   - Add a choice mode in `main.py`: Press Enter to start recording voice input, press Enter again to stop, transcribe audio, and pass text to `run_react_loop()`.

---

### Milestone 4: Hands-Free Wake Word Integration

**Goal:** Enable continuous background listening for the keyword **"Sherlock"** to activate the assistant without manual keypresses.

#### Implementation Steps:
1. **Porcupine Detector ([core/wakeword.py](file:///D:/Work/Sherlock/Code/core/wakeword.py)):**
   - Install `pvporcupine` and `pvrec` (or `openWakeWord`).
   - Read `PICOVOICE_ACCESS_KEY` from [.env](file:///D:/Work/Sherlock/Code/.env).
   - Initialize `pvporcupine.create(keywords=["sherlock"])` or custom keyword model.
2. **Continuous Audio Stream Loop:**
   - Run a dedicated background thread in `main.py` that continuously reads audio chunks from `AudioRecorder`.
   - Feed chunks into `WakeWordDetector.process_frame()`.
   - Upon detection (`True`), play a short activation chime sound, record user speech until silence is detected (VAD - Voice Activity Detection), and pass to STT.

---

### Milestone 5: Expanded Tools & Persistent Memory

**Goal:** Add real-world capabilities and conversation continuity across application restarts.

#### Implementation Steps:
1. **Google Calendar Integration ([tools/calendar_tool.py](file:///D:/Work/Sherlock/Code/tools/calendar_tool.py)):**
   - Implement Google Calendar API (`google-api-python-client`, `google-auth-oauthlib`) to fetch upcoming events and schedule new appointments.
2. **Web Search Grounding ([tools/search.py](file:///D:/Work/Sherlock/Code/tools/search.py)):**
   - Implement real-time web search queries using DuckDuckGo (`duckduckgo_search`) or Tavily API.
3. **Session Memory Persistence:**
   - Save `ConversationMemory` state to `memory.json` upon exit, reloading context on startup so Sherlock remembers past interactions.

---

### Milestone 6: Hardening, Latency Reduction & Stream Processing

**Goal:** Achieve near-instantaneous voice responses (< 1.5s end-to-end latency).

#### Implementation Steps:
1. **Chunked Audio Streaming (TTS):**
   - Modify `speak_text()` to stream audio bytes directly from ElevenLabs websocket/HTTP chunk streams into `mpv` or `miniaudio` for immediate playback without waiting for full clip downloads.
2. **Asynchronous Orchestration:**
   - Convert `main.py` to `asyncio`, running wake word detection, audio capture, LLM reasoning, and TTS in concurrent async tasks.
3. **Barge-In / Interruption Support:**
   - Allow user voice input or wake word detection during TTS playback to immediately stop `pygame.mixer.music` and listen to the new user input.
