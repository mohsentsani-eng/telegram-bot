import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

ROOT = Path(__file__).resolve().parent
env_file = ROOT / ".env"

if load_dotenv:
    load_dotenv(env_file, override=False)

enabled = os.getenv("AI_ENABLED", "").strip().lower() in {"1","true","yes","on"}
key = os.getenv("GEMINI_API_KEY", "").strip()
model = os.getenv("GEMINI_MODEL", "").strip() or "gemini-3.8-flash"

print("=== Taranom Hamdeli Gemini check ===")
print("Project:", ROOT)
print(".env exists:", env_file.exists())
print("AI_ENABLED:", enabled)
print("GEMINI_API_KEY:", "present" if key else "missing")
print("GEMINI_MODEL:", model)

if not enabled:
    print("FIX: set AI_ENABLED=true in .env")
elif not key:
    print("FIX: set GEMINI_API_KEY=... in .env")
else:
    try:
        from google import genai
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=model,
            contents="Reply with exactly: OK"
        )
        print("Gemini connection: OK")
        print("Response:", getattr(response, "text", "") or "(empty)")
    except Exception as e:
        print("Gemini connection: FAILED")
        print(type(e).__name__ + ":", str(e))
