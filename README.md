# Interview Copilot

Real-time interview assistant: mic audio -> streaming transcription (on-device Whisper) -> LLM-generated talking points pushed to your phone's browser.

Audio never leaves the machine except the LLM API call. Nothing is overlaid on the shared screen, so it works with Zoom/Meet/Teams screenshares.

## Architecture

    Mic (local) -> RealtimeSTT (faster-whisper + VAD, local) -> rolling transcript
                                                                       |
    profile brief + transcript -> glm-5.3-flash (cloud) -> 2-3 talking points
                                                                       |
    FastAPI + WebSocket -> phone browser (same WiFi)

## Setup

    python3 -m venv venv && ./venv/bin/pip install -r requirements.txt

Environment (in `~/.hermes/.env` or export before running):

    OLLAMA_API_KEY=...   # primary brain (ollama.com, ~2-3s per suggestion)
    GLM_API_KEY=...      # optional fallback (api.z.ai)

Grant your terminal Microphone permission (macOS: System Settings > Privacy & Security > Microphone).

## Run

    ./venv/bin/python app.py
    # open http://<machine-ip>:8765 on your phone, same WiFi

## Notes

- Brain: glm-5.3-flash via Ollama Cloud with `think:false` (measured 2-3s per suggestion). Falls back to z.ai GLM.
- Whisper transcription runs locally (~1s on a modern laptop CPU).
- Session transcripts log to `sessions/` (gitignored) for post-call review.
- Latency budget end to end: ~4s from end of interviewer's sentence to suggestion on screen.

## Inputs

The copilot listens to three optional sources (all feed the same question pipeline):

1. **Your mic** (default on) - catches questions repeated aloud.
2. **System audio / interviewer's voice** - set `COPILOT_SYSTEM_DEVICE` to a loopback device name:
   - macOS: `brew install blackhole-2ch`, set system output to BlackHole, then `COPILOT_SYSTEM_DEVICE="BlackHole"`
   - Windows: enable Stereo Mix or install VB-CABLE, then `COPILOT_SYSTEM_DEVICE="CABLE Output"`
3. **Screen OCR** (on by default, `COPILOT_SCREEN=0` to disable) - screenshots every 4s and reads questions written on screen. Needs `pip install mss pytesseract` plus the Tesseract binary (mac: `brew install tesseract`, win: official installer). Tune interval with `COPILOT_SCREEN_INTERVAL`.

Transcript entries are tagged `[caller]` (system audio) and `[screen]` (OCR) so you can see where each suggestion came from.

## Honest-use

Built for interview prep drills and self-review. Use responsibly and in line with the rules of any assessment you take.
