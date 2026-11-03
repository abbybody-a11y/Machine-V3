import json, os

CONFIG_FILE = "config.json"

# 預設帳密（容器重啟 / 重新部署時 config.json 若被清空，會自動補回這些值）
DEFAULT_PROVIDER_CREDENTIALS = {
    "textedge": {"account": "jvddemoadmin", "password": "Qwert1234!"},
    "acestar":  {"account": "swn2.sms@email.com", "password": "cYn$wNSMS2@sLm"},
    "cyy":      {"account": "xndSUC", "password": "u4apcH"},
}

class Config:
    @staticmethod
    def load() -> dict:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
        else:
            data = {}

        providers = data.get("providers", {})
        for pid, creds in DEFAULT_PROVIDER_CREDENTIALS.items():
            pcfg = providers.get(pid, {})
            if not pcfg.get("account"):
                pcfg["account"] = creds["account"]
                pcfg["password"] = creds["password"]
                providers[pid] = pcfg
        data["providers"] = providers

        return data

    @staticmethod
    def save(data: dict):
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
