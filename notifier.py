import requests

def send_telegram(cfg: dict, message: str) -> bool:
    token   = cfg.get("tg_token", "")
    chat_id = cfg.get("tg_chat", "")
    if not token or not chat_id:
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=10)
        return r.status_code == 200
    except:
        return False

def send_slack(cfg: dict, message: str, has_warning: bool = False) -> bool:
    webhook = cfg.get("slack_webhook", "")
    if not webhook:
        return False
    try:
        r = requests.post(webhook, json={"text": message, "has_warning": has_warning}, timeout=10)
        return r.status_code == 200
    except:
        return False
