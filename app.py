"""
Interview Copilot MVP: mic -> RealtimeSTT -> LLM talking points -> phone browser.
"""
import asyncio, json, os, time
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()
clients = set()
transcript_tail = []  # rolling last 8 turns

PROFILE_BRIEF = open(os.path.join(os.path.dirname(__file__), "profile_brief.txt")).read() if os.path.exists(os.path.join(os.path.dirname(__file__), "profile_brief.txt")) else "Yang Lu: 5y SWE, Java/Spring deep (Alaia 4y), Python/LLM current (RAG, LangGraph, MCP, evals, FastAPI)."

SYSTEM_PROMPT = """You are an interview copilot. Given the interviewer's last question and a rolling transcript, output 2-3 short bullet talking points (40 words max total) that Yang should say. Ground them in his profile. No preamble, just bullets."""

INDEX = """<!doctype html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<style>body{background:#111;color:#eee;font-family:-apple-system,sans-serif;padding:16px}
#tips{white-space:pre-wrap;font-size:18px;line-height:1.5} #q{color:#8ab4f8;margin-bottom:12px}</style></head>
<body><div id=q>waiting...</div><div id=tips></div>
<script>const ws=new WebSocket(`ws://${location.host}/ws`);ws.onmessage=e=>{const d=JSON.parse(e.data);
document.getElementById('q').textContent=d.question||'';document.getElementById('tips').textContent=d.tips||''};</script></body></html>"""

@app.get("/")
async def index():
    return HTMLResponse(INDEX)

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await asyncio.sleep(1)
    except Exception:
        clients.discard(ws)

async def broadcast(payload):
    dead = []
    for c in clients:
        try:
            await c.send_json(payload)
        except Exception:
            dead.append(c)
    for c in dead:
        clients.discard(c)

def ask_brain(question: str) -> str:
    # Brain = Ollama Cloud glm-5.3-flash (measured 2-3s/suggestion; zai same model ~5-10s).
    # Audio stays on-device; only the LLM call leaves the laptop.
    from openai import OpenAI
    messages = [{"role":"system","content":SYSTEM_PROMPT + "\n\nProfile:\n" + PROFILE_BRIEF},
                {"role":"user","content":f"Rolling transcript:\n" + "\n".join(transcript_tail[-8:]) + f"\n\nLatest interviewer line: {question}"}]
    okey = ""
    for line in open(os.path.expanduser("~/.hermes/.env")):
        if line.startswith("OLLAMA_API_KEY="):
            okey = line.split("=",1)[1].strip()
            break
    # Primary: Ollama Cloud (think:false is what makes it fast)
    if okey:
        try:
            client = OpenAI(api_key=okey, base_url="https://ollama.com/v1", timeout=15)
            r = client.chat.completions.create(
                model="glm-5.3-flash", messages=messages, max_tokens=500, temperature=0.4,
                extra_body={"think": False})
            text = (r.choices[0].message.content or "").strip()
            if text:
                return text
        except Exception:
            pass  # fall through to zai
    # Fallback: zai GLM (thinking disabled)
    key = base = ""
    for line in open(os.path.expanduser("~/.hermes/.env")):
        if line.startswith("GLM_API_KEY="):
            key = line.split("=",1)[1].strip()
        elif line.startswith("GLM_BASE_URL="):
            base = line.split("=",1)[1].strip()
    if not key:
        return "(no OLLAMA_API_KEY or GLM_API_KEY in ~/.hermes/.env)"
    client = OpenAI(api_key=key, base_url=base or "https://api.z.ai/api/paas/v4")
    r = client.chat.completions.create(
        model="glm-5.3-flash", messages=messages, max_tokens=300, timeout=20,
        extra_body={"thinking": {"type": "disabled"}})
    return r.choices[0].message.content or ""

def on_transcript(text: str):
    """Called by the STT thread for each finalized phrase."""
    transcript_tail.append(text)
    # crude question detection - refine later
    if "?" in text or any(w in text.lower() for w in ["tell me", "how do you", "describe", "walk me", "what is", "have you", "why"]):
        tips = ask_brain(text)
        payload = {"question": text, "tips": tips}
        asyncio.run(broadcast(payload))
        with open(os.path.join(os.path.dirname(__file__), "sessions", time.strftime("%Y%m%d") + ".jsonl"), "a") as f:
            f.write(json.dumps({"t": time.time(), "text": text, "tips": tips}) + "\n")

def stt_loop():
    """RealtimeSTT background thread. Requires: pip install RealtimeSTT"""
    from RealtimeSTT import AudioToTextRecorder
    recorder = AudioToTextRecorder(model="small", enable_realtime_transcription=True)
    def cb(text):
        if text.strip():
            on_transcript(text)
    while True:
        recorder.text(cb)

# ---- optional: screen capture + OCR (question text off shared screen) ----
SCREEN_ENABLED = os.environ.get("COPILOT_SCREEN", "1") == "1"
SCREEN_INTERVAL = float(os.environ.get("COPILOT_SCREEN_INTERVAL", "4"))  # seconds


def screen_loop():
    """Screenshot -> OCR -> feed candidate question lines into the same pipeline.

    Uses mss (fast screenshots) + pytesseract. Install: pip install mss pytesseract
    + the Tesseract binary (mac: brew install tesseract, win: installer, linux: apt).
    Only feeds lines that look like questions; dedupes repeats.
    """
    if not SCREEN_ENABLED:
        return
    try:
        import mss
        import pytesseract
        from PIL import Image
    except ImportError:
        print("[screen] mss/pytesseract not installed - screen reading disabled")
        return
    seen = set()
    while True:
        time.sleep(SCREEN_INTERVAL)
        try:
            with mss.mss() as sct:
                img = np.array(sct.grab(sct.monitors[1]))[:, :, :3]
            text = pytesseract.image_to_string(Image.fromarray(img))
            for line in text.splitlines():
                line = line.strip()
                if len(line) < 15 or line in seen:
                    continue
                low = line.lower()
                if "?" in line or any(w in low for w in ["tell me", "how do you", "describe", "walk me", "what is", "have you", "why do", "explain"]):
                    seen.add(line)
                    on_transcript(f"[screen] {line}")
        except Exception as e:
            print(f"[screen] {e}")
            return


# ---- dual-audio: mic (you) + system loopback (interviewer) ----
# macOS: install BlackHole (brew install blackhole-2ch), set macOS output to
#   BlackHole, then COPILOT_SYSTEM_DEVICE="BlackHole".
# Windows: enable Stereo Mix, or install VB-CABLE and route app output to it,
#   then COPILOT_SYSTEM_DEVICE="CABLE Output".
SYSTEM_DEVICE = os.environ.get("COPILOT_SYSTEM_DEVICE", "")


def system_audio_loop():
    """Second recorder for system/loopback audio (the interviewer's voice)."""
    if not SYSTEM_DEVICE:
        return
    from RealtimeSTT import AudioToTextRecorder
    recorder = AudioToTextRecorder(
        model="small", enable_realtime_transcription=True,
        device=SYSTEM_DEVICE)  # RealtimeSTT accepts a device name substring
    def cb(text):
        if text.strip():
            on_transcript(f"[caller] {text}")
    while True:
        recorder.text(cb)


def main():
    os.makedirs(os.path.join(os.path.dirname(__file__), "sessions"), exist_ok=True)
    import threading
    threading.Thread(target=stt_loop, daemon=True).start()          # your mic
    if SYSTEM_DEVICE:
        threading.Thread(target=system_audio_loop, daemon=True).start()  # interviewer (loopback)
    if SCREEN_ENABLED:
        threading.Thread(target=screen_loop, daemon=True).start()    # screen OCR
    uvicorn.run(app, host="0.0.0.0", port=8765)

if __name__ == "__main__":
    main()
