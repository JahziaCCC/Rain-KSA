import os
import requests

def send_telegram():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    print("TOKEN FOUND:", bool(token))
    print("CHAT ID FOUND:", bool(chat_id))

    if not token or not chat_id:
        print("ERROR: Missing Telegram secrets")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "✅ اختبار من Rain-KSA عبر GitHub Actions"
    }

    r = requests.post(url, data=payload, timeout=30)
    print("STATUS:", r.status_code)
    print("RESPONSE:", r.text)

send_telegram()
