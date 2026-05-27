import requests
import pyotp
from datetime import datetime

# ── TextEdge ──────────────────────────────────────────────
TEXTEDGE_SIGN_IN = "https://auth.stacktech.org/backend/auth/v1/user/sign-in"
TEXTEDGE_BALANCE = "https://payment.stacktech.org/backend/topup/v1/balance"

def check_textedge(cfg: dict) -> dict:
    account  = cfg.get("account", "")
    password = cfg.get("password", "")
    headers = {
        "Content-Type": "application/json",
        "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Origin":       "https://crm.textedge.net",
        "Referer":      "https://crm.textedge.net/",
        "X-Company-Id": "834",
    }
    try:
        login_resp = requests.post(TEXTEDGE_SIGN_IN, json={
            "account": account, "password": password
        }, headers=headers, timeout=15)
        login_data = login_resp.json()
        token = (login_data.get("data") or {}).get("ac_token")
        if not token:
            return {"status": "error", "error": f"登入失敗：{login_data}",
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        headers["Authorization"] = f"Bearer {token}"
        bal_resp = requests.get(TEXTEDGE_BALANCE, headers=headers, timeout=15)
        bal_data = bal_resp.json()
        amount = (bal_data.get("data") or {}).get("amount")
        if amount is None:
            return {"status": "error", "error": f"找不到餘額：{bal_data}",
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        return {"status": "ok", "balance": f"{float(amount):.3f} USDT",
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    except Exception as e:
        return {"status": "error", "error": str(e),
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


# ── Acestar ───────────────────────────────────────────────
ACESTAR_BASE     = "https://digibox.acestartelecoms.net"
ACESTAR_LOGIN    = f"{ACESTAR_BASE}/Home/CheckLogin"
ACESTAR_2FA_PAGE = f"{ACESTAR_BASE}/GAAuthentication"
ACESTAR_2FA      = f"{ACESTAR_BASE}/GAAuthentication/TwoFactorAuthenticate"
ACESTAR_DATA     = f"{ACESTAR_BASE}/Common/GetCustomerData"
ACESTAR_TOTP_SECRET = "HE2EWUDSIJUXOQRTGJ4HU2TNMNCGC4DXKI4WSY3SOJ3GC3LMN5XTSZI"
ACESTAR_USER_ID     = "94"

def get_csrf_token(session, url):
    resp = session.get(url, timeout=15)
    from html.parser import HTMLParser
    class TokenParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.token = None
        def handle_starttag(self, tag, attrs):
            if tag == "input":
                attrs = dict(attrs)
                if attrs.get("name") == "__RequestVerificationToken":
                    self.token = attrs.get("value")
    parser = TokenParser()
    parser.feed(resp.text)
    return parser.token

def check_acestar(cfg: dict) -> dict:
    account  = cfg.get("account", "")
    password = cfg.get("password", "")
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": ACESTAR_BASE,
    })
    try:
        # Step 1: 取得登入頁 CSRF token
        csrf1 = get_csrf_token(session, ACESTAR_BASE)
        if not csrf1:
            return {"status": "error", "error": "無法取得 CSRF token",
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        # Step 2: 登入帳號密碼
        login_resp = session.post(ACESTAR_LOGIN, data={
            "__RequestVerificationToken": csrf1,
            "Username": account,
            "Password": password,
        }, timeout=15)

        # Step 3: 取得 2FA 頁面 CSRF token
        csrf2 = get_csrf_token(session, ACESTAR_2FA_PAGE)
        if not csrf2:
            return {"status": "error", "error": "無法取得 2FA CSRF token",
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        # Step 4: 自動產生 TOTP 驗證碼
        totp = pyotp.TOTP(ACESTAR_TOTP_SECRET)
        code = totp.now()

        # Step 5: 送出 2FA
        auth_resp = session.post(ACESTAR_2FA, data={
            "__RequestVerificationToken": csrf2,
            "UserID": ACESTAR_USER_ID,
            "RememberMe": "False",
            "VerificationCode": code,
        }, timeout=15)

        # Step 6: 取得餘額
        data_resp = session.post(ACESTAR_DATA, timeout=15)
        data = data_resp.json()
        amount = (data.get("customer") or {}).get("BalanceAmount")

        if amount is None:
            return {"status": "error", "error": f"找不到餘額：{data}",
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        return {"status": "ok", "balance": f"{float(amount):.3f} USD",
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    except Exception as e:
        return {"status": "error", "error": str(e),
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


# ── 雲 Cloud ──────────────────────────────────────────────
YUN_CLOUD_BASE     = "http://47.242.85.7:9358/sms-service-api"
YUN_CLOUD_LOGIN    = f"{YUN_CLOUD_BASE}/user/login"
YUN_CLOUD_USERINFO = f"{YUN_CLOUD_BASE}/user/getUserInfo"

def check_yun_cloud(cfg: dict) -> dict:
    account  = cfg.get("account", "")
    password = cfg.get("password", "")
    headers = {
        "Content-Type":   "application/json;charset=UTF-8",
        "Accept":         "application/json, text/plain, */*",
        "Accept-Language":"zh",
        "Origin":         "http://47.242.85.7:9356",
        "Referer":        "http://47.242.85.7:9356/",
        "User-Agent":     "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    try:
        import base64
        password_b64 = base64.b64encode(password.encode()).decode()

        # Step 1: 登入取得 token（密碼需 Base64，code/redomStr 後端不驗證）
        login_resp = requests.post(YUN_CLOUD_LOGIN, json={
            "username": account,
            "password": password_b64,
            "code":     "1234",
            "redomStr": "123456789",
        }, headers=headers, timeout=15)
        login_data = login_resp.json()

        if login_data.get("type") != 0:
            return {"status": "error", "error": f"登入失敗：{login_data.get('message')}",
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        token = login_data.get("data")
        if not token:
            return {"status": "error", "error": "未取得 token",
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        # Step 2: 取得餘額
        headers["Authorization"] = f"Bearer {token}"
        headers["Cookie"]        = f"Authorization={token}"

        info_resp = requests.post(YUN_CLOUD_USERINFO, headers=headers, timeout=15)
        info_data = info_resp.json()

        auth_user = (info_data.get("data") or {}).get("userInfo", {}).get("authUser", {})
        balance   = auth_user.get("balance")

        if balance is None:
            return {"status": "error", "error": f"找不到餘額：{info_data}",
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        return {"status": "ok", "balance": f"{float(balance):.2f} ¥",
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    except Exception as e:
        return {"status": "error", "error": str(e),
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


# ── 雲 Cloud 加拿大 ───────────────────────────────────────
def check_yun_cloud_ca(cfg: dict) -> dict:
    return check_yun_cloud(cfg)  # 同一套 API，帳號密碼不同


# ── CYY ──────────────────────────────────────────────────
CYY_BASE     = "http://101.44.162.101:9358/sms-service-api"
CYY_LOGIN    = f"{CYY_BASE}/user/login"
CYY_USERINFO = f"{CYY_BASE}/user/getUserInfo"

def check_cyy(cfg: dict) -> dict:
    account  = cfg.get("account", "")
    password = cfg.get("password", "")
    headers = {
        "Content-Type":    "application/json;charset=UTF-8",
        "Accept":          "application/json, text/plain, */*",
        "Accept-Language": "zh",
        "Origin":          "http://101.44.162.101:9356",
        "Referer":         "http://101.44.162.101:9356/",
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    try:
        import base64
        password_b64 = base64.b64encode(password.encode()).decode()

        login_resp = requests.post(CYY_LOGIN, json={
            "username": account,
            "password": password_b64,
            "code":     "1234",
            "redomStr": "123456789",
        }, headers=headers, timeout=15)
        login_data = login_resp.json()

        if login_data.get("type") != 0:
            return {"status": "error", "error": f"登入失敗：{login_data.get('message')}",
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        token = login_data.get("data")
        if not token:
            return {"status": "error", "error": "未取得 token",
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        headers["Authorization"] = f"Bearer {token}"
        headers["Cookie"]        = f"Authorization={token}"

        info_resp = requests.post(CYY_USERINFO, headers=headers, timeout=15)
        info_data = info_resp.json()

        auth_user = (info_data.get("data") or {}).get("userInfo", {}).get("authUser", {})
        balance   = auth_user.get("balance")

        if balance is None:
            return {"status": "error", "error": f"找不到餘額：{info_data}",
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        return {"status": "ok", "balance": f"{float(balance):.2f} ¥",
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    except Exception as e:
        return {"status": "error", "error": str(e),
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


# ── Movider ───────────────────────────────────────────────
MOVIDER_BALANCE_URL  = "https://api.movider.co/v1/balance"
MOVIDER_MEMBER_URL   = "https://member.movider.co/v1/member"

def _movider_member(api_key, api_secret):
    """用 API Key 取得 member 資料（含 wallet）"""
    import hashlib, time as _time
    ts   = str(int(_time.time()))
    sign = hashlib.md5(f"{api_key}{api_secret}{ts}".encode()).hexdigest()
    # 先試官方 balance API
    resp = requests.get(MOVIDER_BALANCE_URL, params={
        "api_key": api_key, "api_secret": api_secret
    }, timeout=15)
    return resp.json()

def check_movider(cfg: dict) -> dict:
    api_key    = cfg.get("account", "")
    api_secret = cfg.get("password", "")
    try:
        data = requests.post(MOVIDER_BALANCE_URL, data={
            "api_key": api_key, "api_secret": api_secret
        }, timeout=15).json()
        amount = data.get("amount")
        if amount is None:
            return {"status": "error", "error": f"找不到餘額：{data}",
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        return {"status": "ok", "balance": f"{float(amount):.4f} USD",
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    except Exception as e:
        return {"status": "error", "error": str(e),
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# ── Movider 區域簡訊（PH wallet）─────────────────────────
MOVIDER_AUTH_URL = "https://member.movider.co/v1/auth"

def _movider_get_token(email, password):
    """嘗試自動登入取得 JWT token"""
    resp = requests.post(MOVIDER_AUTH_URL, json={
        "email":    email,
        "password": password,
        "r":        "",
        "fp":       "",
        "cf_turnstile_token": ""
    }, headers={
        "Content-Type": "application/json",
        "Origin":  "https://movider.co",
        "Referer": "https://movider.co/",
    }, timeout=15)
    data = resp.json()
    return data.get("data", {}).get("token") or data.get("token")

def check_movider_regional(cfg: dict) -> dict:
    email    = cfg.get("account", "")
    password = cfg.get("password", "")
    try:
        token = _movider_get_token(email, password)
        if not token:
            return {"status": "error", "error": "無法取得登入 token，請確認帳密",
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        resp = requests.get(MOVIDER_MEMBER_URL, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }, timeout=15)
        data   = resp.json()
        wallet = (data.get("data") or {}).get("wallet", {})
        ph     = wallet.get("PH", [])
        amount = ph[0].get("credit_available") if ph else None
        if amount is None:
            return {"status": "error", "error": f"找不到 PH 區域餘額：{wallet}",
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        return {"status": "ok", "balance": f"{int(amount):,} 則",
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    except Exception as e:
        return {"status": "error", "error": str(e),
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


# ── Laaffic ───────────────────────────────────────────────
import hashlib

LAAFFIC_BALANCE_URL = "https://api.laaffic.com/v3/getBalance"

def check_laaffic(cfg: dict) -> dict:
    api_key = cfg.get("account", "")
    api_pwd = cfg.get("password", "")
    try:
        ts  = str(int(__import__("time").time()))
        sign = hashlib.md5(f"{api_key}{api_pwd}{ts}".encode()).hexdigest()
        headers = {
            "Content-Type": "application/json;charset=utf-8",
            "Sign":      sign,
            "Timestamp": ts,
            "Api-Key":   api_key,
        }
        resp = requests.get(LAAFFIC_BALANCE_URL, headers=headers, timeout=15)
        data = resp.json()
        if str(data.get("status")) != "0":
            return {"status": "error", "error": f"API錯誤：{data.get('reason')}",
                    "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        balance = data.get("balance", "0")
        return {"status": "ok", "balance": f"{float(balance):.2f} USD",
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    except Exception as e:
        return {"status": "error", "error": str(e),
                "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
