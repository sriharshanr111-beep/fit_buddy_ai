from app import config
from google import genai

print("Key found:", bool(config.GOOGLE_API_KEY), "| length:", len(config.GOOGLE_API_KEY))
print("Pro model  :", config.GEMINI_PRO_MODEL)
print("Flash model:", config.GEMINI_FLASH_MODEL)

client = genai.Client(api_key=config.GOOGLE_API_KEY)

print("\nModels your key can use:")
names = []
try:
    for m in client.models.list():
        actions = getattr(m, "supported_actions", None) or []
        if not actions or "generateContent" in actions:
            n = m.name.replace("models/", "")
            if n.startswith("gemini") and "tts" not in n and "image" not in n and "live" not in n:
                names.append(n)
    for n in sorted(names):
        print("  ", n)
except Exception as e:
    print("Could not list models:", e)

for label, model in [("PRO", config.GEMINI_PRO_MODEL), ("FLASH", config.GEMINI_FLASH_MODEL)]:
    try:
        r = client.models.generate_content(model=model, contents="Say hi in 3 words")
        print(f"\n{label} model OK ->", r.text.strip())
    except Exception as e:
        print(f"\n{label} model FAILED ->", e)