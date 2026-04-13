def send_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("ERROR: Telegram secrets are missing.")
        print("TELEGRAM_BOT_TOKEN =", "FOUND" if token else "MISSING")
        print("TELEGRAM_CHAT_ID =", "FOUND" if chat_id else "MISSING")
        print(message)
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        response = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "text": message
            },
            timeout=30
        )

        print("Telegram status code:", response.status_code)
        print("Telegram response:", response.text)

        response.raise_for_status()
        print("Telegram message sent successfully.")

    except Exception as e:
        print("Telegram send failed:", str(e))
