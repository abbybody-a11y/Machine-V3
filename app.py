from flask import Flask, jsonify, render_template_string, request
from scraper import check_textedge, check_acestar, check_yun_cloud, check_yun_cloud_ca, check_cyy, check_movider, check_movider_regional, check_laaffic, check_laaffic_co
from notifier import send_telegram, send_slack
from config import Config
import json, os
from datetime import datetime, timezone, timedelta

TZ_TAIPEI = timezone(timedelta(hours=8))
def now_tw(): return datetime.now(TZ_TAIPEI).strftime("%Y-%m-%d %H:%M:%S")

app = Flask(__name__)
HISTORY_FILE = "history.json"

PROVIDERS = [
    {"id": "textedge",        "name": "TextEdge",          "threshold": 300},
    {"id": "acestar",         "name": "Acestar",           "threshold": 200},
    {"id": "yun_cloud",       "name": "雲 Cloud",          "threshold": 1000},
    {"id": "cyy",             "name": "CYY",               "threshold": 500},
    {"id": "yun_cloud_ca",    "name": "雲 Cloud 加拿大",   "threshold": 1000},
    {"id": "movider",         "name": "Movider",           "threshold": 300},
    {"id": "movider_regional","name": "Movider 區域簡訊",  "threshold": 100000},
    {"id": "laaffic",         "name": "Laaffic",           "threshold": 300},
    {"id": "laaffic_co",      "name": "Laaffic 哥倫比亞",  "threshold": 300},
]

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except Exception:
            os.remove(HISTORY_FILE)
    return []

def save_history(entry):
    history = load_history()
    history.append(entry)
    history = history[-200:]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, ensure_ascii=False)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>簡訊商餘額監控</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:-apple-system,sans-serif;background:#f5f5f5;color:#1a1a1a;}
.header{background:#fff;border-bottom:1px solid #e5e5e5;padding:16px 24px;display:flex;align-items:center;justify-content:space-between;}
.header h1{font-size:18px;font-weight:600;}
.container{max-width:900px;margin:24px auto;padding:0 16px;}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px;}
.stat{background:#fff;border-radius:10px;padding:16px;border:1px solid #e5e5e5;}
.stat label{font-size:12px;color:#888;display:block;margin-bottom:6px;}
.stat .val{font-size:24px;font-weight:600;}
.panel{background:#fff;border-radius:10px;padding:20px;border:1px solid #e5e5e5;margin-bottom:16px;}
.panel h2{font-size:14px;font-weight:600;color:#444;margin-bottom:16px;}
.prow{border:0.5px solid #e5e5e5;border-radius:10px;padding:14px 16px;margin-bottom:10px;transition:border-color .2s;}
.prow.active{border-color:#6366f1;}
.prow.warn{border-color:#f59e0b;}
.prow.error{border-color:#ef4444;}
.prow-header{display:flex;align-items:center;justify-content:space-between;gap:12px;}
.prow-title{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.badge{font-size:11px;padding:2px 8px;border-radius:99px;display:inline-flex;align-items:center;}
.badge-active{background:#eef2ff;color:#6366f1;}
.badge-ok{background:#dcfce7;color:#16a34a;}
.badge-warn{background:#fef9c3;color:#b45309;}
.badge-err{background:#fee2e2;color:#dc2626;}
.badge-off{background:#f0f0f0;color:#888;}
.dot{width:7px;height:7px;border-radius:50%;background:#6366f1;display:inline-block;margin-right:5px;animation:pulse 2s ease-in-out infinite;}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:.4;}}
.tk{position:relative;width:36px;height:20px;background:#ccc;border-radius:10px;cursor:pointer;transition:background .2s;display:inline-flex;align-items:center;flex-shrink:0;}
.tk.on{background:#6366f1;}
.kn{position:absolute;left:2px;width:16px;height:16px;background:#fff;border-radius:50%;transition:transform .2s;pointer-events:none;}
.tk.on .kn{transform:translateX(16px);}
.prow-fields{margin-top:12px;padding-top:12px;border-top:0.5px solid #eee;display:grid;grid-template-columns:1fr 1fr 130px auto auto;gap:8px;align-items:center;}
.prow-error{margin-top:10px;padding:8px 12px;background:#fee2e2;color:#991b1b;border-radius:6px;font-size:12px;display:none;}
input[type=text],input[type=password],input[type=number]{border:1px solid #ddd;border-radius:6px;padding:7px 10px;font-size:13px;width:100%;}
input:focus{outline:none;border-color:#6366f1;}
input:read-only{background:#f9f9f9;color:#888;cursor:default;}
button{border:none;border-radius:6px;padding:8px 14px;font-size:13px;cursor:pointer;font-weight:500;}
.btn-primary{background:#6366f1;color:#fff;}
.btn-primary:hover{background:#4f46e5;}
.btn-secondary{background:#f0f0f0;color:#333;}
.btn-secondary:hover{background:#e0e0e0;}
.btn-save{background:#10b981;color:#fff;}
.btn-save:hover{background:#059669;}
.btn-edit{background:#f0f0f0;color:#555;}
button:disabled{opacity:.5;cursor:not-allowed;}
table{width:100%;border-collapse:collapse;font-size:13px;}
th{text-align:left;padding:8px 10px;color:#888;font-weight:500;border-bottom:1px solid #eee;}
td{padding:10px;border-bottom:1px solid #f5f5f5;}
.result-table td.num{text-align:right;font-weight:500;}
.result-table td.th-num{text-align:right;color:#888;}
.result-table tr.warn-row{background:#fffbeb;}
.result-table tr.err-row{background:#fff1f1;}
#global-status{font-size:13px;padding:10px 14px;border-radius:6px;margin-bottom:16px;display:none;}
#global-status.ok{background:#dcfce7;color:#166534;display:block;}
#global-status.err{background:#fee2e2;color:#991b1b;display:block;}
#global-status.loading{background:#eff6ff;color:#1d4ed8;display:block;}
</style>
</head>
<body>
<div class="header">
  <h1>簡訊商餘額監控</h1>
  <span id="last-update" style="font-size:13px;color:#888;">尚未查詢</span>
</div>
<div class="container">

  <div class="stats">
    <div class="stat">
      <label>啟用廠商</label>
      <div class="val" id="stat-on" style="color:#16a34a;">— / —</div>
    </div>
    <div class="stat">
      <label>查詢成功</label>
      <div class="val" id="stat-ok">—</div>
    </div>
    <div class="stat">
      <label>低餘額警告</label>
      <div class="val" id="stat-warn" style="color:#b45309;">—</div>
    </div>
  </div>

  <div id="global-status"></div>

  <div class="panel" id="result-panel" style="display:none;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h2 style="margin:0;">查詢結果匯總</h2>
      <button class="btn-secondary" onclick="sendToSlack()" style="font-size:12px;padding:6px 12px;">發送到 Slack</button>
      <button class="btn-secondary" onclick="copySlack()" style="font-size:12px;padding:6px 12px;margin-left:6px;">📋 複製 Slack 格式</button>
    </div>
    <table class="result-table">
      <thead><tr><th>廠商</th><th style="text-align:right;">餘額</th><th style="text-align:right;">警示閾值</th><th style="text-align:center;">狀態</th></tr></thead>
      <tbody id="result-tbody"></tbody>
    </table>
  </div>

  <div class="panel">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h2 style="margin:0;">廠商設定</h2>
      <div style="display:flex;gap:8px;">
        <button class="btn-primary" id="btn-all" onclick="fetchAll()">全部查詢</button>

      </div>
    </div>
    <div id="provider-list"></div>
  </div>

  <div class="panel">
    <h2>通知設定</h2>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;">
      <div>
        <label style="font-size:12px;color:#888;display:block;margin-bottom:4px;">Slack Webhook URL</label>
        <input type="text" id="cfg-slack" placeholder="https://hooks.slack.com/...">
      </div>
      <div>
        <label style="font-size:12px;color:#888;display:block;margin-bottom:4px;">Telegram Bot Token</label>
        <input type="text" id="cfg-tg-token" placeholder="Bot Token">
      </div>
      <div>
        <label style="font-size:12px;color:#888;display:block;margin-bottom:4px;">Telegram Chat ID</label>
        <input type="text" id="cfg-tg-chat" placeholder="Chat ID">
      </div>
    </div>
    <button class="btn-save" onclick="saveNotifyConfig()">儲存通知設定</button>
    <span id="notify-saved" style="font-size:12px;color:#10b981;margin-left:8px;display:none;">已儲存</span>
  </div>

</div>

<script>
let PROVIDERS = [];
let results = {};

function showStatus(msg, type) {
  const el = document.getElementById('global-status');
  el.textContent = msg;
  el.className = type;
}

function renderProviders() {
  const cfg = JSON.parse(localStorage.getItem('provider_cfg') || '{}');
  const enabled = JSON.parse(localStorage.getItem('provider_enabled') || '{}');
  const list = document.getElementById('provider-list');

  list.innerHTML = PROVIDERS.map(p => {
    const pcfg = cfg[p.id] || {};
    const isOn = enabled[p.id] !== false;
    const saved = pcfg.saved;
    return `
    <div class="prow ${isOn ? 'active' : ''}" id="row-${p.id}">
      <div class="prow-header">
        <div class="prow-title">
          <span style="font-size:14px;font-weight:500;" id="name-${p.id}">${p.name}</span>
          <span class="badge ${isOn ? 'badge-active' : 'badge-off'}" id="status-badge-${p.id}">
            ${isOn ? '<span class="dot"></span>啟用中' : '停用'}
          </span>
          <span class="badge badge-ok" id="bal-badge-${p.id}" style="display:none;"></span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          <button class="btn-secondary" style="font-size:12px;padding:5px 10px;" onclick="fetchOne('${p.id}')" id="btn-${p.id}">查詢</button>
          <div class="tk ${isOn ? 'on' : ''}" id="tk-${p.id}" onclick="toggleProvider('${p.id}')"><div class="kn"></div></div>
        </div>
      </div>
      <div class="prow-fields" id="fields-${p.id}" ${isOn ? '' : 'style="display:none;"'}>
        <input type="text" placeholder="帳號" id="acc-${p.id}" value="${saved ? '●●●●●●●●' : (pcfg.account||'')}" ${saved ? 'readonly' : ''}>
        <input type="password" placeholder="密碼" id="pw-${p.id}" value="${saved ? '●●●●●●●●' : (pcfg.password||'')}" ${saved ? 'readonly' : ''}>
        <div style="display:flex;align-items:center;gap:4px;">
          <span style="font-size:11px;color:#888;white-space:nowrap;">警示 <</span>
          <input type="number" id="thr-${p.id}" value="${pcfg.threshold || p.threshold}" style="width:80px;">
        </div>
        ${saved
          ? `<button class="btn-edit" onclick="editCreds('${p.id}')">編輯</button>`
          : `<button class="btn-save" onclick="saveCreds('${p.id}')">儲存</button>`
        }
      </div>
      <div class="prow-error" id="err-${p.id}"></div>
    </div>`;
  }).join('');

  updateStats();
}

function saveCreds(id) {
  const acc = document.getElementById('acc-'+id).value;
  const pw = document.getElementById('pw-'+id).value;
  const thr = document.getElementById('thr-'+id).value;
  const cfg = JSON.parse(localStorage.getItem('provider_cfg') || '{}');
  cfg[id] = { account: acc, password: pw, threshold: thr, saved: true };
  localStorage.setItem('provider_cfg', JSON.stringify(cfg));
  fetch('/api/provider-config', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ id, account: acc, password: pw, threshold: thr })
  });
  renderProviders();
}

function editCreds(id) {
  const cfg = JSON.parse(localStorage.getItem('provider_cfg') || '{}');
  if (cfg[id]) cfg[id].saved = false;
  localStorage.setItem('provider_cfg', JSON.stringify(cfg));
  fetch('/api/provider-config', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ id, saved: false })
  });
  renderProviders();
  document.getElementById('acc-'+id).value = '';
  document.getElementById('pw-'+id).value = '';
}

function toggleProvider(id) {
  const tk = document.getElementById('tk-'+id);
  tk.classList.toggle('on');
  const isOn = tk.classList.contains('on');
  const enabled = JSON.parse(localStorage.getItem('provider_enabled') || '{}');
  enabled[id] = isOn;
  localStorage.setItem('provider_enabled', JSON.stringify(enabled));
  const row = document.getElementById('row-'+id);
  const badge = document.getElementById('status-badge-'+id);
  const fields = document.getElementById('fields-'+id);
  row.classList.toggle('active', isOn);
  badge.className = 'badge ' + (isOn ? 'badge-active' : 'badge-off');
  badge.innerHTML = isOn ? '<span class="dot"></span>啟用中' : '停用';
  fields.style.display = isOn ? '' : 'none';
  updateStats();
}

function updateStats() {
  const enabled = JSON.parse(localStorage.getItem('provider_enabled') || '{}');
  const on = PROVIDERS.filter(p => enabled[p.id] !== false).length;
  document.getElementById('stat-on').textContent = on + ' / ' + PROVIDERS.length;
}

async function fetchOne(id) {
  const btn = document.getElementById('btn-'+id);
  const errEl = document.getElementById('err-'+id);
  const balBadge = document.getElementById('bal-badge-'+id);
  const row = document.getElementById('row-'+id);
  btn.disabled = true;
  btn.textContent = '查詢中...';
  errEl.style.display = 'none';
  try {
    const res = await fetch('/api/fetch-one', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ id })
    });
    const data = await res.json();
    if (data.ok) {
      balBadge.textContent = data.balance;
      balBadge.style.display = '';
      balBadge.className = 'badge ' + (data.warning ? 'badge-warn' : 'badge-ok');
      row.classList.remove('warn','error');
      if (data.warning) row.classList.add('warn');
      results[id] = data;
    } else {
      errEl.textContent = '查詢失敗：' + (data.error || '未知錯誤');
      errEl.style.display = 'block';
      row.classList.add('error');
      results[id] = data;
    }
  } catch(e) {
    errEl.textContent = '連線錯誤：' + e.message;
    errEl.style.display = 'block';
  }
  btn.disabled = false;
  btn.textContent = '查詢';
}

async function fetchAll() {
  const btn = document.getElementById('btn-all');
  btn.disabled = true;
  btn.textContent = '查詢中...';
  showStatus('正在查詢所有啟用廠商，請稍候...', 'loading');
  results = {};

  const enabled = JSON.parse(localStorage.getItem('provider_enabled') || '{}');
  const active = PROVIDERS.filter(p => enabled[p.id] !== false);

  for (const p of active) {
    await fetchOne(p.id);
  }

  renderResultTable();
  const now = new Date().toLocaleString('zh-TW', {timeZone:'Asia/Taipei'});
  document.getElementById('last-update').textContent = '上次更新：' + now;

  const okCount = Object.values(results).filter(r => r.ok).length;
  const warnCount = Object.values(results).filter(r => r.ok ? r.warning : false).length;
  document.getElementById('stat-ok').textContent = okCount + ' 家';
  document.getElementById('stat-warn').textContent = warnCount + ' 家';
  showStatus('查詢完成！成功 ' + okCount + ' 家，警告 ' + warnCount + ' 家', 'ok');

  btn.disabled = false;
  btn.textContent = '全部查詢';
}

function renderResultTable() {
  const tbody = document.getElementById('result-tbody');
  const panel = document.getElementById('result-panel');
  const rows = PROVIDERS.map(p => {
    const r = results[p.id];
    if (!r) return '';
    if (!r.ok) {
      return `<tr class="err-row">
        <td>${p.name}</td>
        <td class="num" style="color:#dc2626;">查詢失敗</td>
        <td class="th-num">—</td>
        <td style="text-align:center;"><span class="badge badge-err">錯誤：${r.error||''}</span></td>
      </tr>`;
    }
    const cls = r.warning ? 'warn-row' : '';
    const badgeCls = r.warning ? 'badge-warn' : 'badge-ok';
    const badgeText = r.warning ? '警告' : '正常';
    return `<tr class="${cls}">
      <td>${p.name}</td>
      <td class="num" ${r.warning ? 'style="color:#b45309;"' : ''}>${r.balance}</td>
      <td class="th-num">${r.threshold?.toLocaleString() || '—'}</td>
      <td style="text-align:center;"><span class="badge ${badgeCls}">${badgeText}</span></td>
    </tr>`;
  }).join('');
  tbody.innerHTML = rows || '<tr><td colspan="4" style="text-align:center;color:#aaa;">尚無資料</td></tr>';
  panel.style.display = rows ? '' : 'none';
}

async function sendToSlack() {
  const res = await fetch('/api/send-slack', { method: 'POST' });
  const data = await res.json();
  alert(data.ok ? 'Slack 發送成功！' : '發送失敗：' + data.error);
}

async function saveNotifyConfig() {
  const data = {
    slack_webhook: document.getElementById('cfg-slack').value,
    tg_token: document.getElementById('cfg-tg-token').value,
    tg_chat: document.getElementById('cfg-tg-chat').value,
  };
  await fetch('/api/notify-config', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(data)
  });
  const s = document.getElementById('notify-saved');
  s.style.display = 'inline';
  setTimeout(() => s.style.display = 'none', 2000);
}

async function loadNotifyConfig() {
  const res = await fetch('/api/notify-config');
  const cfg = await res.json();
  if (cfg.slack_webhook) document.getElementById('cfg-slack').value = cfg.slack_webhook;
  if (cfg.tg_token) document.getElementById('cfg-tg-token').value = cfg.tg_token;
  if (cfg.tg_chat) document.getElementById('cfg-tg-chat').value = cfg.tg_chat;
}

fetch('/api/providers').then(r=>r.json()).then(data=>{PROVIDERS=data;renderProviders();});
loadNotifyConfig();

function copySlack() {
  var NL = String.fromCharCode(10);
  var now = new Date();
  var ts = now.toLocaleDateString("zh-TW") + " " + now.toLocaleTimeString("zh-TW", {hour:"2-digit",minute:"2-digit"});
  var lines = [":bar_chart: *" + ts + " 簡訊商餘額報告*", ""];
  var hasData = false;
  PROVIDERS.forEach(function(p) {
    var tk = document.getElementById("tk-" + p.id);
    if (!tk || !tk.classList.contains("on")) return;
    var el = document.getElementById("bal-badge-" + p.id);
    var bal = el ? el.textContent.trim() : "";
    if (!bal || bal === "" || bal === "-") return;
    var isWarn = el && el.classList.contains("warn");
    lines.push((isWarn ? ":warning: *" : ":white_check_mark: *") + p.name + "*：" + bal);
    hasData = true;
  });
  if (!hasData) { alert("請先執行全部查詢再複製！"); return; }
  navigator.clipboard.writeText(lines.join(NL)).then(function() {
    var btn = document.querySelector('[onclick="copySlack()"]');
    var orig = btn.textContent;
    btn.textContent = "Copied!";
    setTimeout(function(){ btn.textContent = orig; }, 2000);
  });
}
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route("/api/provider-config", methods=["POST"])
def provider_config():
    data = request.json
    cfg = Config.load()
    providers = cfg.get("providers", {})
    pid = data.get("id")
    if pid not in providers:
        providers[pid] = {}
    for k in ["account", "password", "threshold", "saved"]:
        if k in data:
            providers[pid][k] = data[k]
    cfg["providers"] = providers
    Config.save(cfg)
    return jsonify({"ok": True})

@app.route("/api/fetch-one", methods=["POST"])
def fetch_one():
    data = request.json
    pid = data.get("id")
    cfg = Config.load()
    providers = cfg.get("providers", {})
    pcfg = providers.get(pid, {})

    provider_info = next((p for p in PROVIDERS if p["id"] == pid), None)
    threshold = float(pcfg.get("threshold") or (provider_info["threshold"] if provider_info else 0))

    if pid == "textedge":
        result = check_textedge(pcfg)
    elif pid == "acestar":
        result = check_acestar(pcfg)
    elif pid == "yun_cloud":
        result = check_yun_cloud(pcfg)
    elif pid == "yun_cloud_ca":
        result = check_yun_cloud_ca(pcfg)
    elif pid == "cyy":
        result = check_cyy(pcfg)
    elif pid == "movider":
        result = check_movider(pcfg)
    elif pid == "movider_regional":
        result = check_movider_regional(pcfg)
    elif pid == "laaffic":
        result = check_laaffic(pcfg)
    elif pid == "laaffic_co":
        result = check_laaffic_co(pcfg)
    else:
        result = {
            "status": "error",
            "error": f"{pid} 尚未串接，請用 F12 查詢 API 端點後設定",
            "fetched_at": now_tw()
        }

    result["ok"] = (result["status"] == "ok")
    result["threshold"] = threshold

    if result["ok"]:
        bal_str = ''.join(c for c in result["balance"] if c.isdigit() or c == '.')
        bal_val = float(bal_str) if bal_str else 0
        result["warning"] = bal_val < threshold
        if result["warning"]:
            notify_cfg = cfg.get("notify", {})
            msg = f"⚠️ {provider_info['name'] if provider_info else pid} 餘額不足\n目前：{result['balance']}\n閾值：{threshold}"
            send_slack(notify_cfg, msg)
            send_telegram(notify_cfg, msg)

    save_history({**result, "provider": pid})
    return jsonify(result)


@app.route("/api/fetch-all", methods=["POST"])
def api_fetch_all():
    """N8N 用：查詢所有啟用的廠商"""
    cfg = Config.load()
    providers_cfg = cfg.get("providers", {})
    enabled = cfg.get("enabled", {})
    results = {}
    for p in PROVIDERS:
        pid = p["id"]
        if enabled.get(pid) == False:
            continue
        pcfg = providers_cfg.get(pid, {})
        if not pcfg.get("account"):
            continue
        threshold = float(pcfg.get("threshold") or p.get("threshold", 0))
        if pid == "textedge":
            result = check_textedge(pcfg)
        elif pid == "acestar":
            result = check_acestar(pcfg)
        elif pid == "yun_cloud":
            result = check_yun_cloud(pcfg)
        elif pid == "yun_cloud_ca":
            result = check_yun_cloud_ca(pcfg)
        elif pid == "cyy":
            result = check_cyy(pcfg)
        elif pid == "movider":
            result = check_movider(pcfg)
        elif pid == "movider_regional":
            result = check_movider_regional(pcfg)
        elif pid == "laaffic":
            result = check_laaffic(pcfg)
        elif pid == "laaffic_co":
            result = check_laaffic_co(pcfg)
        else:
            continue
        result["ok"] = (result["status"] == "ok")
        result["threshold"] = threshold
        if result["ok"]:
            try:
                bal_num = float(''.join(c for c in result["balance"] if c.isdigit() or c == '.'))
                result["warning"] = bal_num < threshold
            except:
                result["warning"] = False
        save_history({**result, "provider": pid})
        results[pid] = result
    return jsonify({"ok": True, "results": results})

@app.route("/api/send-slack", methods=["POST"])
def api_send_slack():
    cfg = Config.load()
    notify_cfg = cfg.get("notify", {})
    history = load_history()

    latest = {}
    for h in reversed(history):
        pid = h.get("provider")
        if pid and pid not in latest:
            latest[pid] = h

    now = datetime.now(TZ_TAIPEI).strftime("%Y/%m/%d %H:%M")
    lines = [f"📊 簡訊商餘額報告 {now}", "─────────────────────"]
    warnings = []

    for p in PROVIDERS:
        r = latest.get(p["id"])
        if not r:
            continue
        if r.get("ok"):
            icon = "⚠️" if r.get("warning") else "✅"
            lines.append(f"{icon} {p['name'].ljust(12)} {r['balance']}")
            if r.get("warning"):
                warnings.append(p["name"])
        else:
            pass  # 跟總開關の不顯示查詢失敗

    lines.append("─────────────────────")
    if warnings:
        lines.append(f"⚠️ 低餘額警告：{'、'.join(warnings)}")

    msg = "\n".join(lines)
    ok = send_slack(notify_cfg, msg)
    return jsonify({"ok": ok})

@app.route("/api/notify-config", methods=["GET", "POST"])
def notify_config():
    cfg = Config.load()
    if request.method == "POST":
        cfg["notify"] = request.json
        Config.save(cfg)
        return jsonify({"ok": True})
    return jsonify(cfg.get("notify", {}))

@app.route("/api/balance", methods=["GET"])
def api_balance():
    history = load_history()
    last = next((h for h in reversed(history) if h.get("status") == "ok" and h.get("provider") == "textedge"), None)
    if last:
        return jsonify({"ok": True, "balance": last["balance"], "fetched_at": last["fetched_at"]})
    return jsonify({"ok": False, "error": "尚無資料"}), 404

@app.route("/api/history", methods=["GET"])
def api_history():
    return jsonify(load_history())

@app.route("/api/providers", methods=["GET"])
def api_providers():
    return jsonify(PROVIDERS)

if __name__ == "__main__":
    print("後台已啟動：http://localhost:5000")
    app.run(debug=True, port=5000)
