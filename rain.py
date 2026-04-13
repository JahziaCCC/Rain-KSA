import os
import requests

token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

print("TOKEN FOUND:", bool(token))
print("CHAT ID FOUND:", bool(chat_id))

if not token or not chat_id:
    print("ERROR: Missing secrets")
    raise SystemExit(1)

url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = {
    "chat_id": chat_id,
    "text": "✅ اختبار Telegram من Rain-KSA"
}

r = requests.post(url, data=payload, timeout=30)
print("STATUS:", r.status_code)
print("RESPONSE:", r.text)

r.raise_for_status()
print("DONE")
