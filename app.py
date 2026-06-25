import streamlit as st
import streamlit.components.v1 as _components
import uuid
import time
import hmac
import secrets as _secrets
import re
import requests as _req
import html as _html
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from urllib.parse import quote
from datetime import datetime, timezone, timedelta
from streamlit_autorefresh import st_autorefresh

_TAIWAN = timezone(timedelta(hours=8))

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="洞察易生的經歷",
    page_icon="☯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ─────────────────────────────────────────────────────────────────
_FALLBACK_PW = st.secrets.get("admin_password", "")  # 不再硬編碼預設密碼（原 kunze2024 寫在公開原始碼=任何人可登入後台）
_LIFF_ID = st.secrets.get("liff_id", "")  # LINE LIFF App ID; 空字串時整段 LIFF 功能停用
_APP_URL = st.secrets.get("app_url", "https://iching-insight.streamlit.app").rstrip("/")
def _email_enabled() -> bool:
    return bool(st.secrets.get("email_from", "") and st.secrets.get("gmail_app_password", ""))

def _google_enabled() -> bool:
    # 只有 [auth] 區塊「同時」有 redirect_uri 與 cookie_secret 才啟用 Google 登入。
    # 之前只檢查區塊存在 → 設定不全（缺 redirect_uri / cookie_secret）時按鈕照樣顯示，
    # 但 OAuth callback 階段才 500（特別是 Safari/Mac 對 cookie 較嚴時）。寧可不顯示按鈕。
    try:
        auth = st.secrets.get("auth", None)
        if not auth:
            return False
        return bool(auth.get("redirect_uri") and auth.get("cookie_secret"))
    except Exception:
        return False

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")

def _valid_email(s: str) -> bool:
    """嚴格驗證 email：擋掉引號/空白/角括號等可被注入 JS 字串或 HTML 的字元。
    email 之後會被插進 localStorage JS 字面量與通知信連結，必須先在源頭把關。"""
    return bool(_EMAIL_RE.match((s or "").strip()))

CATEGORIES = {
    "感情與人際": {
        "icon": "💕", "desc": "情感關係、人際緣分、婚姻家庭",
        "welcome": "此處為感情與人際分區。您可詢問情感困惑、人際關係、緣份時機、婚姻家庭等問題。靜心一念，易理自明。",
    },
    "事業與學業": {
        "icon": "📜", "desc": "職場發展、學習進修、創業方向",
        "welcome": "此處為事業與學業分區。您可詢問職涯方向、工作決策、創業規劃、學習進修等問題。靜心一念，易理自明。",
    },
    "財運與財務": {
        "icon": "💰", "desc": "財富運勢、投資理財、商業機遇",
        "welcome": "此處為財運與財務分區。您可詢問財富運勢、投資時機、商業決策、錢財去留等問題。靜心一念，易理自明。",
    },
    "健康與生活": {
        "icon": "🌿", "desc": "身心健康、生活品質、養生調息",
        "welcome": "此處為健康與生活分區。您可詢問身心狀態、生活調整、養生方向、居家環境等問題。靜心一念，易理自明。",
    },
    "時機與決策": {
        "icon": "⏳", "desc": "時機判斷、重要決策、方向抉擇",
        "welcome": "此處為時機與決策分區。您可詢問重要時機、關鍵決策、方向選擇、動靜取捨等問題。靜心一念，易理自明。",
    },
    "綜合命理": {
        "icon": "☯", "desc": "整體運勢、流年命盤、綜合解析",
        "welcome": "此處為綜合命理分區。您可詢問整體運勢、流年運程、命盤走向、綜合解析等問題。靜心一念，易理自明。",
    },
}

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Serif TC', 'Noto Serif', serif; }
.stApp { background-color: #FAF3E0; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1E2B1C 0%, #2D3B2A 100%);
    border-right: 1px solid #4A6040;
}
[data-testid="stSidebar"] * { color: #D4C4A0 !important; }
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] select {
    background: #2A3A28 !important;
    color: #E8D5A3 !important;
    border: 1px solid #4A6040 !important;
    border-radius: 6px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #2A3A28 !important;
    border: 1px solid #4A6040 !important;
}
.main-title {
    text-align: center; color: #3D2B1F;
    font-size: 2.6rem; font-weight: 700;
    letter-spacing: 0.3em; padding-top: 1rem;
    text-shadow: 1px 2px 6px rgba(139,105,20,0.18);
}
.main-subtitle {
    text-align: center; color: #9A7B50;
    font-size: 0.92rem; letter-spacing: 0.2em; margin-bottom: 1.8rem;
}
.g-div {
    border: none; height: 1px; margin: 1rem 0 1.5rem 0;
    background: linear-gradient(to right, transparent, #C4922A 25%, #C4922A 75%, transparent);
}
.info-box {
    background: linear-gradient(135deg, #FFFAF0, #FDF0D0);
    border: 1px solid #D4A843; border-left: 4px solid #C4922A;
    border-radius: 10px; padding: 18px 24px; margin-bottom: 24px;
    color: #4A3020; font-size: 0.95rem; line-height: 2.0;
}
.cat-card {
    background: linear-gradient(145deg, #FFF8E7, #F5E6C4);
    border: 1px solid #D4A843; border-radius: 14px;
    padding: 26px 18px 20px; text-align: center;
    box-shadow: 0 2px 10px rgba(139,105,20,0.12); margin-bottom: 4px;
}
.cat-icon { font-size: 2.4rem; margin-bottom: 6px; }
.cat-name { font-size: 1.05rem; font-weight: 700; color: #3D2B1F; margin-bottom: 4px; }
.cat-desc { font-size: 0.78rem; color: #7A5C3A; }
.badge {
    display: inline-block; color: #fff;
    font-size: 0.68rem; padding: 1px 7px; border-radius: 10px; margin-left: 6px;
}
.badge-red   { background: #C43A2A; }
.badge-green { background: #3A8A4A; }
.chat-hdr {
    background: linear-gradient(135deg, #2D3B2A, #3D5438);
    color: #E8D5A3; padding: 16px 24px; border-radius: 14px; margin-bottom: 16px;
    display: flex; align-items: center; gap: 12px;
}
.chat-hdr-title { font-size: 1.25rem; font-weight: 700; letter-spacing: 0.1em; }
.chat-hdr-sub   { font-size: 0.8rem; color: #B8A070; margin-top: 4px; }
.admin-hdr {
    background: linear-gradient(135deg, #1E2B1C, #2D3B2A);
    color: #E8D5A3; padding: 18px 28px; border-radius: 14px; margin-bottom: 20px;
    border: 1px solid #4A6040; display: flex; align-items: center; gap: 12px;
}
.stat-box {
    background: linear-gradient(135deg, #FFF8E7, #F5E6C4);
    border: 1px solid #D4A843; border-radius: 10px;
    padding: 16px; text-align: center; margin-bottom: 8px;
}
.stat-num   { font-size: 2rem; font-weight: 700; color: #C4922A; }
.stat-label { font-size: 0.78rem; color: #7A5C3A; }
.sess-card {
    background: #FFF8E7; border: 1px solid #D4A843;
    border-radius: 10px; padding: 14px 18px; margin-bottom: 10px;
}
.sess-card.pending { border-left: 4px solid #C43A2A; }
.sess-card.replied { border-left: 4px solid #3A8A4A; }
.sess-name    { font-weight: 700; color: #3D2B1F; font-size: 0.97rem; }
.sess-meta    { font-size: 0.78rem; color: #7A5C3A; margin-top: 3px; }
.sess-preview {
    font-size: 0.85rem; color: #5A4030; margin-top: 8px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.sid-box {
    background: #2D3B2A; color: #A0C870;
    font-family: monospace; font-size: 1.15rem; font-weight: 700;
    padding: 8px 16px; border-radius: 8px; letter-spacing: 0.2em;
    display: inline-block; margin: 4px 0;
}
.stButton > button {
    font-family: 'Noto Serif TC', serif !important; font-weight: 600;
    letter-spacing: 0.05em; border-radius: 8px !important; border: none !important;
    background: linear-gradient(135deg, #C4922A, #8B6914) !important;
    color: #fff !important; transition: all 0.25s ease !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #8B6914, #6B4F10) !important;
    box-shadow: 0 4px 14px rgba(139,105,20,0.38) !important;
}
</style>
""", unsafe_allow_html=True)

# ── Database (requests, no supabase-py) ───────────────────────────────────────
def _headers(extra=None):
    key = st.secrets.get("supabase_key", "")
    h = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    if extra:
        h.update(extra)
    return h

def _base():
    return st.secrets.get("supabase_url", "").rstrip("/") + "/rest/v1"

def _eqv(value: str) -> str:
    """安全的 PostgREST eq 過濾值（白名單清洗，不加雙引號）。
    合法業務值（session_id／token／email／line_uid）只含英數與 @ . _ + -，
    這些字元在 `col=eq.value` 不會被 PostgREST 當成過濾運算子。
    逗號／括號等「可竄改查詢語意」的字元一律剔除 → 杜絕注入
    （例：值若含 `,is_closed.eq.false` 會被去掉逗號而失效）。
    ⚠ 不可改回 eq."值"：本 PostgREST 不會剝掉雙引號，會把引號當值的一部分 → 比對不到
       （2026-06-25 線上實測：加引號讀回 ❌、不加引號 ✅）。"""
    return "eq." + re.sub(r'[^A-Za-z0-9@._+\-]', '', str(value))

def _get(table, params=None):
    r = _req.get(f"{_base()}/{table}", headers=_headers(), params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def _post(table, data, extra=None):
    r = _req.post(f"{_base()}/{table}", headers=_headers(extra), json=data, timeout=10)
    r.raise_for_status()
    return r.json()

def _patch(table, data, params=None):
    r = _req.patch(f"{_base()}/{table}", headers=_headers(), json=data, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def _delete(table, params=None):
    r = _req.delete(f"{_base()}/{table}", headers=_headers(), params=params, timeout=10)
    r.raise_for_status()

def fmt_time(ts):
    if not ts:
        return ""
    try:
        s = str(ts).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        tw = dt.astimezone(_TAIWAN)
        return tw.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)[:16].replace("T", " ")

def _plain(text: str) -> str:
    """把顧客自填內容（問題/姓名）當純文字安全渲染：HTML 跳脫＋不解析 markdown，保留換行。
    用法：st.markdown(_plain(x), unsafe_allow_html=True)。
    防顧客在問題塞 markdown 圖片 ![](http://attacker) 害小老師後台外連洩 IP，或用語法弄亂版面。"""
    return ("<div style='white-space:pre-wrap;word-break:break-word;'>"
            + _html.escape(text or "") + "</div>")

def _enrich(sessions):
    result = []
    for s in sessions:
        msgs = sorted(s.get("messages") or [], key=lambda m: m.get("created_at") or "")
        last = msgs[-1] if msgs else None
        result.append({
            **s,
            "msg_count": len(msgs),
            "last_role": last["role"] if last else None,
            "last_msg":  last["content"] if last else None,
        })
    return result

def _db_selftest():
    """?debug=1 用：定位「寫得進、讀不回」類問題。回報①金鑰類型(prefix，分得出 secret/publishable/JWT)
    ②目前可讀到幾筆 sessions ③寫入一筆探針後，用「加引號(_eqv) vs 不加引號」兩種方式讀回。
    - 不加引號讀得到、加引號讀不到 → 是 _eqv 雙引號害的（跟金鑰無關，要修 code）。
    - 兩種都讀不到 → 寫入沒持久化／RLS 擋（與金鑰/RLS 有關）。"""
    import json as _json, base64 as _b64
    out = []
    key = st.secrets.get("supabase_key", "")
    if key.startswith("sb_secret_"):
        ktype = "sb_secret_（service_role，繞過 RLS）✅"
    elif key.startswith("sb_publishable_"):
        ktype = "sb_publishable_（公開金鑰，受 RLS 管）⚠"
    elif key.startswith("eyJ"):
        try:
            pl = key.split(".")[1]; pl += "=" * (-len(pl) % 4)
            ktype = f"JWT role={_json.loads(_b64.urlsafe_b64decode(pl)).get('role','?')}"
        except Exception:
            ktype = "JWT(無法解析)"
    else:
        ktype = f"未知({key[:12]}…)" if key else "（空）"
    out.append(f"金鑰類型={ktype}")
    try:
        rows = _get("sessions", {"select": "session_id", "limit": "200"})
        out.append(f"可讀 sessions={len(rows)} 筆")
    except Exception as e:
        out.append(f"讀 sessions 失敗={type(e).__name__}")
    probe = "DBTEST" + _secrets.token_hex(2).upper()
    try:
        _post("sessions", {"session_id": probe, "customer_name": "_selftest",
                           "category": "_test", "preference": ""})
        q = _get("sessions", {"session_id": _eqv(probe), "limit": "1"})            # 加引號 eq."值"
        u = _get("sessions", {"session_id": f"eq.{probe}", "limit": "1"})          # 不加引號 eq.值
        out.append("寫入=OK、讀回[加引號]=" + ("✅" if q else "❌") +
                   "、讀回[不加引號]=" + ("✅" if u else "❌"))
        if u and not q:
            out.append("➜ 結論：_eqv 雙引號害的（跟金鑰無關）")
        elif not u and not q:
            out.append("➜ 結論：寫入沒持久化或 RLS 擋（查金鑰/RLS）")
        try:
            _delete("sessions", {"session_id": f"eq.{probe}"})
        except Exception:
            pass
    except Exception as e:
        out.append(f"寫入往返失敗={type(e).__name__}:{str(e)[:90]}")
    return " · ".join(out)

def create_session(name: str, category: str, line_uid: str = "", email: str = ""):
    """建立問卦，回傳 (session_id, token)。token 是猜不到的隨機字串，是日後回來查看的唯一鑰匙。
    失敗回 (None, None)；若 DB 欄位尚未建立則退而求其次仍送出，但 token 回空字串。"""
    sid = str(uuid.uuid4())[:8].upper()
    token = _secrets.token_urlsafe(32)
    name = (name or "").strip()[:40]  # 伺服器端長度上限（防超大 payload；前端 max_chars 之外的防線）
    payload = {
        "session_id": sid,
        "customer_name": name,
        "category": category,
        "preference": "",  # 查詢密碼功能已移除；此欄保留空字串相容舊資料表
        "token": token,
    }
    if line_uid:
        payload["line_uid"] = line_uid
    if email:
        payload["email"] = email.lower()
    try:
        _post("sessions", payload)
        return sid, token
    except Exception:
        # token / line_uid / email 欄位若尚未建立（migration 未跑），去掉選填欄位再試，確保問卦仍可送出
        minimal = {"session_id": sid, "customer_name": name, "category": category, "preference": ""}
        try:
            _post("sessions", minimal)
            return sid, ""  # 無 token：本次仍可問卦，只是這台裝置日後無法用 token 自動回登
        except Exception as e:
            st.error(f"建立諮詢失敗：{e}")
            return None, None

def get_session_by_token(token: str):
    """用 token（猜不到的隨機鑰匙）找未結案的問卦。這是唯一安全的「回來查看」入口。"""
    if not token:
        return None
    try:
        data = _get("sessions", {"token": _eqv(token), "is_closed": "eq.false", "limit": "1"})
        return data[0] if data else None
    except Exception:
        return _DB_ERROR

def _ensure_token(sess) -> str:
    """回傳此 session 的 token；舊資料若沒有就現補一個並寫回 DB。失敗回空字串。"""
    if not sess:
        return ""
    tok = (sess.get("token") or "").strip()
    if tok:
        return tok
    tok = _secrets.token_urlsafe(32)
    try:
        _patch("sessions", {"token": tok}, {"session_id": _eqv(sess["session_id"])})
        return tok
    except Exception:
        return ""

_DB_ERROR = object()  # sentinel: DB unreachable (distinct from "session not found")

def get_open_session_by_line_uid(uid: str):
    """LINE 用戶的免密碼自動登入：找此 LINE 帳號最新一筆未結案問卦。
    找不到回 None；DB 異常回 _DB_ERROR（呼叫端須區分，別把「DB 抖一下」當成「沒有問卦」→ 避免顧客重複建檔）。"""
    if not uid:
        return None
    try:
        data = _get("sessions", {
            "line_uid": _eqv(uid),
            "is_closed": "eq.false",
            "order": "updated_at.desc",
            "limit": "1",
        })
        return data[0] if data else None
    except Exception:
        return _DB_ERROR  # DB 異常：不可當成「沒有問卦」

def get_open_session_by_email(email: str):
    """Email 登入：找此 email 最新一筆未結案問卦。
    找不到回 None；DB 異常回 _DB_ERROR（呼叫端須區分，避免 DB 抖動時誤判成「沒問卦」害顧客重複建檔）。"""
    if not email:
        return None
    try:
        data = _get("sessions", {
            "email": _eqv(email.lower()),
            "is_closed": "eq.false",
            "order": "updated_at.desc",
            "limit": "1",
        })
        return data[0] if data else None
    except Exception:
        return _DB_ERROR  # DB 異常：不可當成「沒有問卦」

def find_my_open_session():
    """依目前登入身分（email / LINE）找此顧客最新一筆未結案問卦，找不到/DB 異常都回 None。
    （這只用於顯示『切換回進行中對話』便利按鈕，DB 抖動時不顯示即可，不影響正確性。）"""
    em = st.session_state.get("email", "")
    if em:
        s = get_open_session_by_email(em)
        if s and s is not _DB_ERROR:
            return s
    uid = st.session_state.get("line_uid", "")
    if uid:
        s = get_open_session_by_line_uid(uid)
        if s and s is not _DB_ERROR:
            return s
    return None

def get_session(sid: str):
    try:
        data = _get("sessions", {"session_id": _eqv(sid), "limit": "1"})
        return data[0] if data else None  # None = session genuinely not in DB
    except Exception:
        return _DB_ERROR  # connection/timeout error

def add_message(sid: str, role: str, content: str) -> bool:
    content = (content or "")[:8000]  # 伺服器端 sanity 上限（顧客前端 1000；小老師長文也夠用）
    try:
        _post("messages", {"session_id": sid, "role": role, "content": content})
        _patch("sessions", {"updated_at": datetime.now(timezone.utc).isoformat()},
               {"session_id": _eqv(sid)})
        return True
    except Exception as e:
        st.error(f"訊息儲存失敗：{e}")
        return False

def get_messages(sid: str):
    try:
        return _get("messages", {"session_id": _eqv(sid), "order": "created_at.asc"})
    except Exception as e:
        st.error(f"⚠️ 載入訊息失敗：{e}")
        return None  # None = DB error, [] = genuinely no messages

def get_all_sessions(cat_f=None, status_f=None):
    try:
        params = {
            "select": "*,messages(*)",
            "is_closed": "eq.false",
            "order": "updated_at.desc",
        }
        if cat_f and cat_f != "全部":
            params["category"] = f"eq.{cat_f}"
        rows = _enrich(_get("sessions", params))
        if status_f == "待回覆":
            rows = [s for s in rows if s["last_role"] == "customer" or s["msg_count"] == 0]
        elif status_f == "已解讀":
            rows = [s for s in rows if s["last_role"] == "consultant"]
        return rows
    except Exception as e:
        st.error(f"⚠️ 載入問卦記錄失敗：{e}")
        return None  # None = DB error, [] = genuinely empty

def get_archived_sessions():
    try:
        params = {
            "select": "*,messages(*)",
            "is_closed": "eq.true",
            "order": "updated_at.desc",
        }
        return _enrich(_get("sessions", params))
    except Exception as e:
        st.error(f"⚠️ 載入歸檔記錄失敗：{e}")
        return None  # None = DB error, [] = genuinely empty

def close_session(sid: str) -> bool:
    try:
        _patch("sessions", {
            "is_closed": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, {"session_id": _eqv(sid)})
        return True
    except Exception as e:
        st.error(f"結案失敗：{e}")
        return False

def delete_session(sid: str) -> bool:
    try:
        _delete("messages", {"session_id": _eqv(sid)})
        _delete("sessions", {"session_id": _eqv(sid)})
        return True
    except Exception as e:
        st.error(f"刪除失敗：{e}")
        return False

def get_admin_password():
    """回傳目前管理密碼。DB 連線異常時回 None（fail-closed），呼叫端須拒絕登入，
    避免攻擊者短暫干擾 DB 就讓密碼關卡降回硬編碼預設值。沒有 config 列（首次啟用）才用預設。"""
    try:
        data = _get("config", {"key": "eq.admin_password", "limit": "1"})
    except Exception:
        return None  # DB 錯誤 → fail-closed，不可登入
    return data[0]["value"] if data else _FALLBACK_PW

def set_admin_password(new_pw: str) -> bool:
    try:
        _post("config", {"key": "admin_password", "value": new_pw},
              {"Prefer": "resolution=merge-duplicates,return=representation"})
        return True
    except Exception as e:
        st.error(f"無法更新密碼：{e}")
        return False

def get_announcement() -> str:
    try:
        data = _get("settings", {"key": "eq.announcement", "select": "value", "limit": "1"})
        return (data[0].get("value") or "") if data else ""
    except Exception:
        return ""

def set_announcement(text: str) -> bool:
    try:
        r = _req.post(
            f"{_base()}/settings",
            headers=_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}),
            json={"key": "announcement", "value": text},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        st.error(f"儲存失敗：{e}")
        return False

def get_setting(key: str) -> str:
    try:
        data = _get("settings", {"key": _eqv(key), "select": "value", "limit": "1"})
        return (data[0].get("value") or "") if data else ""
    except Exception:
        return ""

def set_setting(key: str, value: str) -> bool:
    try:
        r = _req.post(
            f"{_base()}/settings",
            headers=_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}),
            json={"key": key, "value": value},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception:
        return False

# ── Email 驗證碼防濫發（跨 session，存 settings 表）──────────────────────────────
# session 冷卻只擋同一分頁重複點；攻擊者換分頁就能對受害者信箱連續寄信轟炸。
# 這裡用伺服器端「同信箱冷卻 + 每日上限」補上。DB 異常時 fail-open（不擋正常使用者）。
_EMAIL_COOLDOWN_S = 30   # 同一信箱兩封最少間隔（秒）
_EMAIL_DAILY_CAP  = 15   # 同一信箱每日驗證碼上限

def _email_rate_state(em: str) -> dict:
    import json as _json
    raw = get_setting(f"emailrate_{em}")
    if not raw:
        return {"last": 0.0, "count": 0, "day": 0.0}
    try:
        d = _json.loads(raw)
        return {"last": float(d.get("last", 0)), "count": int(d.get("count", 0)),
                "day": float(d.get("day", 0))}
    except Exception:
        return {"last": 0.0, "count": 0, "day": 0.0}

def email_send_allowed(em: str):
    """回 (是否可寄, 提示訊息)。跨 session 防濫發。"""
    now = time.time()
    s = _email_rate_state(em)
    gap = now - s["last"]
    if gap < _EMAIL_COOLDOWN_S:
        return False, f"這個信箱剛剛已寄出驗證碼，請於 {int(_EMAIL_COOLDOWN_S - gap) + 1} 秒後再試。"
    count = s["count"] if (now - s["day"] < 86400) else 0
    if count >= _EMAIL_DAILY_CAP:
        return False, "這個信箱今日的驗證碼次數已達上限，請改用上方 Google 登入，或明天再試。"
    return True, ""

def email_send_record(em: str) -> None:
    """寄送成功後記錄，供下次 email_send_allowed 判斷。"""
    import json as _json
    now = time.time()
    s = _email_rate_state(em)
    if now - s["day"] >= 86400:
        s["day"], s["count"] = now, 0
    s["last"], s["count"] = now, s["count"] + 1
    set_setting(f"emailrate_{em}", _json.dumps({"last": s["last"], "count": s["count"], "day": s["day"]}))

def get_stats():
    try:
        rows = _enrich(_get("sessions", {"select": "*,messages(*)", "is_closed": "eq.false"}))
        today = datetime.now(_TAIWAN).strftime("%Y-%m-%d")
        return {
            "total":   len(rows),
            "today":   sum(1 for s in rows if fmt_time(s.get("created_at", "")).startswith(today)),
            "pending": sum(1 for s in rows if s["last_role"] == "customer" or s["msg_count"] == 0),
            "replied": sum(1 for s in rows if s["last_role"] == "consultant"),
        }
    except Exception as e:
        st.warning(f"⚠️ 資料庫連線異常：{e}")
        return {"total": 0, "today": 0, "pending": 0, "replied": 0}

@st.cache_data(ttl=300)
def _check_line_token(token: str):
    try:
        r = _req.get("https://api.line.me/v2/bot/info",
                     headers={"Authorization": f"Bearer {token}"}, timeout=8)
        if r.status_code == 200:
            return True, r.json().get("displayName", "Bot")
        return False, f"{r.status_code}：{r.text}"
    except Exception as e:
        return None, str(e)

def send_notification(name: str, category: str, question: str, sid: str, is_followup: bool = False):
    """推播通知小老師。失敗時 retry 一次，並把原因寫進 settings，讓後台可見（不再靜默吞錯）。"""
    token   = st.secrets.get("line_token", "")
    user_id = st.secrets.get("line_user_id", "")
    if not token or not user_id:
        return False
    header = "【追加提問】" if is_followup else "【新問卦】"
    text = f"{header}\n姓名：{name}\n分區：{category}\n編號：{sid}\n\n問題：\n{question[:200]}"
    payload = {"to": user_id, "messages": [{"type": "text", "text": text}]}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    last_err = ""
    for attempt in range(2):  # 失敗時 retry 一次
        try:
            r = _req.post("https://api.line.me/v2/bot/message/push",
                          headers=headers, json=payload, timeout=8)
            if r.status_code == 200:
                return True
            last_err = f"{r.status_code}：{r.text[:120]}"
            print(f"[send_notification] LINE push failed {last_err}")
            if r.status_code != 429:  # 4xx（非額度問題）不必 retry
                break
        except Exception as e:
            last_err = str(e)[:120]
            print(f"[send_notification] LINE push exception: {last_err}")
    # 記錄失敗原因供後台顯示
    _ts = datetime.now(_TAIWAN).strftime("%m-%d %H:%M")
    _hint = "（疑似每月推播額度用盡）" if last_err.startswith("429") else ""
    set_setting("last_notify_error", f"{_ts} {('追加提問' if is_followup else '新問卦')} 推播失敗 {last_err}{_hint}")
    return False

def _gen_code() -> str:
    # 用 secrets（密碼學安全）而非 random，驗證碼才不可預測
    return f"{_secrets.randbelow(1000000):06d}"

def send_email(to_addr: str, subject: str, html: str) -> bool:
    """透過 Gmail SMTP 寄信（用寄件人自己的 Gmail + 應用程式密碼，免註冊第三方服務）。
    需 secrets: email_from（你的 Gmail）+ gmail_app_password（16 碼應用程式密碼）。
    未設定 / 寄送失敗時回 False，不丟例外、不影響呼叫端。"""
    sender = st.secrets.get("email_from", "")
    pw     = st.secrets.get("gmail_app_password", "")
    if not sender or not pw or not to_addr:
        return False
    try:
        msg = MIMEText(html, "html", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"]    = formataddr((str(Header("洞察易生的經歷", "utf-8")), sender))
        msg["To"]      = to_addr
        # 應用程式密碼 Google 顯示時帶空格（"abcd efgh ..."），去掉空格較不易出錯
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as s:
            s.login(sender, pw.replace(" ", ""))
            s.sendmail(sender, [to_addr], msg.as_string())
        return True
    except Exception as e:
        print(f"[send_email] Gmail SMTP failed: {e}")
        return False

def notify_customer_reply_email(sid: str) -> None:
    """小老師發送解讀後，若該問卦留有 email，寄信通知顧客回網頁查看。
    未設定寄信 / 無 email / 寄送失敗都靜默略過，絕不影響回覆流程。"""
    if not _email_enabled():
        return
    try:
        sess = get_session(sid)
    except Exception:
        return
    if not sess or sess is _DB_ERROR:
        return
    to_addr = (sess.get("email") or "").strip()
    if not to_addr:
        return
    name = _html.escape(sess.get("customer_name") or "您")
    # 用 token 當回登連結（猜不到、只開得了這一筆），取代舊的 ?email=（可被任何人偽造）
    tok = _ensure_token(sess)
    link = f"{_APP_URL}/?token={quote(tok)}" if tok else _APP_URL
    send_email(
        to_addr,
        "小老師回覆了您的問卦 · 洞察易生的經歷",
        f"<p>{name} 您好，</p>"
        f"<p>小老師已經為您的問卦寫下解讀，請點選下方連結回到網頁查看：</p>"
        f"<p><a href='{link}' style='display:inline-block;padding:10px 20px;"
        f"background:#8B6914;color:#fff;text-decoration:none;border-radius:6px;'>"
        f"查看小老師的解讀</a></p>"
        f"<p style='color:#999;font-size:0.85rem;'>此信由系統自動寄出，"
        f"開啟連結即可免密碼登入。洞察易生的經歷</p>",
    )

def notify_customer_reply_line(sess) -> None:
    """顧客若是透過 LINE 登入（留有 line_uid），小老師回覆後推播通知到他的 LINE。
    補上原本只寄 email、LINE 顧客收不到回覆通知的缺口。best-effort，失敗靜默、不影響回覆流程。"""
    token = st.secrets.get("line_token", "")
    uid = (sess.get("line_uid") or "").strip() if sess else ""
    if not token or not uid:
        return
    cat = sess.get("category", "")
    text = f"小老師回覆了您的問卦（{cat}），請回到網頁查看：\n{_APP_URL}"
    try:
        _req.post(
            "https://api.line.me/v2/bot/message/push",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"to": uid, "messages": [{"type": "text", "text": text}]},
            timeout=8,
        )
    except Exception as e:
        print(f"[notify_customer_reply_line] {e}")

# ── Session State Init ────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "page": "home",
        "admin_mode": False,
        "admin_reply_sid": None,
        "admin_cat_filter": "全部",
        "admin_status_filter": "全部",
        "customer_sid": None,
        "customer_name": "",
        "customer_category": "",
        "line_uid": "",                 # 透過 LIFF 取得的 LINE userId（免密碼登入用）
        "line_name": "",                # 透過 LIFF 取得的 LINE 顯示名稱（預填姓名用）
        "email": "",                    # 已驗證的顧客 email（登入與回覆通知用）
        "selected_cat": None,
        "reply_ver": 0,
        "admin_name_search": "",
        "admin_sort_mode": "最新時間",
        "_clear_storage": False,        # clear localStorage + show "session closed" notice
        "_clear_storage_quiet": False,  # clear localStorage silently (voluntary navigation)
        "_db_unreachable": False,       # suppress localStorage redirect when DB is down
        "_admin_reply_from": "admin",
        "_customer_self_closed": False, # customer clicked self-close → show custom success msg
        "_clear_reply_draft": None,     # sid whose sessionStorage draft should be wiped
        "arch_name_search": "",         # archive page search filter
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    params = st.query_params
    # OAuth 登入 callback 進行中（網址帶 code/state）時，不要動 query params，
    # 交給 Streamlit 內建 auth 完成交握，避免把 callback 參數清掉造成 500。
    if "code" in params or "state" in params:
        return

    # 自動回登只認 ?token=（猜不到的隨機鑰匙）。
    # 已移除 ?sid= / ?email= / ?line_uid=——那些可被任何人手打網址偽造成別人身分（帳號接管漏洞）。
    if "token" in params and st.session_state.customer_sid is None:
        sess = get_session_by_token(params["token"])
        if sess is _DB_ERROR:
            # DB 暫時不可用 — 清掉網址但保留 localStorage
            st.query_params.clear()
            st.session_state["_db_unreachable"] = True
        elif not sess:
            # token 無效／該問卦已結案或被刪 — 清掉一切
            st.query_params.clear()
            st.session_state["_clear_storage"] = True
        else:
            st.session_state.customer_sid = sess["session_id"]
            st.session_state.customer_name = sess["customer_name"] or ""
            st.session_state.customer_category = sess.get("category", "")
            # token 已證明此人擁有這筆問卦，綁定的 email 可安全記住（供回覆通知等用）
            if sess.get("email"):
                st.session_state.email = (sess.get("email") or "").lower()
            # 停在首頁、由「進行中諮詢」橫幅讓顧客自己選擇回去看回覆（不再強制跳進對話）
            st.session_state.page = "home"

init_state()

if not st.session_state.admin_mode:
    st.markdown("""<style>
#MainMenu { display: none !important; }
footer    { display: none !important; }
[data-testid="stToolbar"]         { display: none !important; }
[data-testid="stStatusWidget"]    { display: none !important; }
[data-testid="manage-app-button"] { display: none !important; }
.stDeployButton                   { display: none !important; }
</style>""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    if st.session_state.admin_mode:
        st.markdown("## 🔐 管理後台")
        st.markdown("---")
        st.markdown("**✅ 小老師模式啟動**")
        st.markdown("---")
        if st.button("← 回到後台首頁", use_container_width=True):
            _cur = st.session_state.admin_reply_sid
            if _cur:
                st.session_state.pop(f"_del_confirm_{_cur}", None)
            for _k in list(st.session_state.keys()):
                if _k.startswith("_del_arch_confirm_"):
                    st.session_state.pop(_k, None)
            st.session_state.page = "admin"
            st.session_state.admin_reply_sid = None
            st.rerun()
        if st.button("🚪 登出管理模式", use_container_width=True):
            _cur = st.session_state.admin_reply_sid
            if _cur:
                st.session_state.pop(f"_del_confirm_{_cur}", None)
            for _k in list(st.session_state.keys()):
                if _k.startswith("_del_arch_confirm_"):
                    st.session_state.pop(_k, None)
            st.session_state.pop("admin_pw", None)
            st.session_state.admin_mode = False
            st.session_state.page = "home"
            st.rerun()
        st.markdown("---")
        with st.expander("🔑 更改管理密碼"):
            old_pw  = st.text_input("目前密碼", type="password", key="chpw_old")
            new_pw  = st.text_input("新密碼",   type="password", key="chpw_new")
            new_pw2 = st.text_input("確認新密碼", type="password", key="chpw_new2")
            if st.button("確認更改", use_container_width=True, key="chpw_btn"):
                if not old_pw or not new_pw or not new_pw2:
                    st.error("請填寫所有欄位")
                elif len(new_pw) < 6:
                    st.error("新密碼至少 6 個字元")
                elif new_pw != new_pw2:
                    st.error("兩次新密碼不一致")
                elif (_cur_pw := get_admin_password()) is None:
                    st.error("⚠️ 資料庫暫時無法連線，請稍後再試。")
                elif not hmac.compare_digest(old_pw.encode("utf-8"), _cur_pw.encode("utf-8")):
                    st.error("目前密碼錯誤")
                else:
                    if set_admin_password(new_pw):
                        st.success("密碼已更新")

        with st.expander("📢 跑馬燈公告"):
            _cur_ann = get_announcement()
            _ann_input = st.text_area("公告內容", value=_cur_ann,
                                      placeholder="留空表示不顯示公告",
                                      height=80, key="ann_input",
                                      label_visibility="collapsed")
            _ac1, _ac2 = st.columns(2)
            with _ac1:
                if st.button("儲存", use_container_width=True, key="ann_save"):
                    if set_announcement(_ann_input.strip()):
                        st.success("已更新")
                        st.rerun()
            with _ac2:
                if st.button("清除", use_container_width=True, key="ann_clear"):
                    if set_announcement(""):
                        st.success("已清除")
                        st.rerun()

        with st.expander("💬 LINE 通知設定"):
            token = st.secrets.get("line_token", "")
            user_id = st.secrets.get("line_user_id", "")
            if not token:
                st.warning("尚未設定 line_token")
            else:
                ok, info = _check_line_token(token)
                if ok is True:
                    st.success(f"line_token ✅  Bot：{info}")
                elif ok is False:
                    st.error(f"line_token 無效 {info}")
                else:
                    st.error(f"token 驗證失敗：{info}")

            if not user_id:
                st.markdown("""**取得 LINE User ID（步驟）：**
1. 打開 [webhook.site](https://webhook.site) → 複製畫面上的網址（Your unique URL）
2. LINE Developers → 你的 Channel → Messaging API → Webhook settings
3. 貼上 webhook.site 的網址 → 點 **Update** → 開啟 **Use webhook**
4. 用手機 LINE 傳任一訊息給你的 Bot
5. 回到 webhook.site → 點剛收到的請求 → 在 JSON 裡找 `"userId": "Uxxxxxxx"`
6. 複製那串 ID，填進 Streamlit Secrets：`line_user_id = "Uxxxxxxx"`""")
            else:
                st.success("line_user_id ✅")
                if st.button("📤 發送測試訊息", use_container_width=True, disabled=not token):
                    try:
                        r = _req.post(
                            "https://api.line.me/v2/bot/message/push",
                            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                            json={"to": user_id, "messages": [{"type": "text", "text": "【測試】LINE 通知設定成功 ✅"}]},
                            timeout=10,
                        )
                        if r.status_code == 200:
                            st.success("已發送！檢查你的 LINE")
                        else:
                            st.error(f"LINE 錯誤 {r.status_code}：{r.text}")
                    except Exception as e:
                        st.error(f"發送失敗：{e}")

            _nerr = get_setting("last_notify_error")
            if _nerr:
                st.warning(f"⚠️ 最近一次自動通知失敗：\n\n{_nerr}\n\n"
                           "（顧客的問卦仍有存進系統，只是沒推播成功。若為 429 額度問題，"
                           "可至 LINE Official Account Manager 查看本月推播用量。）")
                if st.button("清除此提示", key="clr_notify_err", use_container_width=True):
                    set_setting("last_notify_error", "")
                    st.rerun()
    else:
        st.markdown("## ☯ 洞察易生的經歷")
        st.markdown("---")

        if st.session_state.page == "chat" and st.session_state.customer_sid:
            cat = st.session_state.get("customer_category", "")
            if cat:
                icon = CATEGORIES.get(cat, {}).get("icon", "☯")
                st.markdown(f"**目前分區：** {icon} {cat}")
            if st.button("← 回到首頁", use_container_width=True):
                st.session_state.page = "home"
                st.session_state.customer_sid = None
                st.session_state.customer_category = ""
                st.session_state["_clear_storage_quiet"] = True
                st.query_params.clear()
                st.rerun()
        elif st.session_state.page == "register":
            if st.button("← 返回", use_container_width=True):
                st.session_state.page = "home"
                st.session_state.selected_cat = None
                st.rerun()
        else:
            st.markdown("**目前位置：首頁**")

        st.markdown("---")
        st.markdown("""<div style="background:#2D3B2A;border:1px solid #5A7050;border-radius:8px;
padding:7px 10px;text-align:center;color:#A0C870;font-size:0.82rem;font-weight:700;
letter-spacing:0.05em;margin-bottom:10px;">🎁 目前為免費版</div>""", unsafe_allow_html=True)
        st.markdown("""<small>
<b>使用說明</b><br>
① 用 Google 或 Email 登入<br>
② 選擇分區、填寫姓名與問題<br>
③ 靜候小老師解讀回覆<br><br>
登入後小老師回覆會通知您，日後回來自動帶出您的紀錄。
</small>""", unsafe_allow_html=True)

        st.markdown("---")
        with st.expander("🔐 管理入口"):
            pw = st.text_input("管理密碼", type="password", key="admin_pw")
            if st.button("進入管理後台", use_container_width=True):
                _lock_until = st.session_state.get("_admin_lock_until", 0)
                _cur_pw = get_admin_password()
                if time.time() < _lock_until:
                    st.error(f"嘗試過多，請於 {int(_lock_until - time.time()) + 1} 秒後再試。")
                elif _cur_pw is None:
                    st.error("⚠️ 資料庫暫時無法連線，請稍後再試。")
                elif not _cur_pw:
                    st.error("尚未設定管理密碼，請於 Secrets 設定 admin_password。")
                elif pw and hmac.compare_digest(pw.encode("utf-8"), _cur_pw.encode("utf-8")):
                    st.session_state["_admin_fail"] = 0
                    st.session_state.admin_mode = True
                    st.session_state.page = "admin"
                    st.rerun()
                else:
                    # 連錯 5 次鎖 60 秒，拖慢暴力破解（伺服器級限流仍建議另做）
                    _fail = st.session_state.get("_admin_fail", 0) + 1
                    st.session_state["_admin_fail"] = _fail
                    if _fail >= 5:
                        st.session_state["_admin_lock_until"] = time.time() + 60
                        st.session_state["_admin_fail"] = 0
                        st.error("錯誤次數過多，已暫時鎖定 60 秒。")
                    else:
                        st.error(f"密碼錯誤（剩 {5 - _fail} 次）")

# ── Customer: Home ────────────────────────────────────────────────────────────
def show_home():
    _show_clear   = st.session_state.get("_clear_storage", False)
    _quiet_clear  = st.session_state.get("_clear_storage_quiet", False)
    _db_down      = st.session_state.get("_db_unreachable", False)
    _self_closed  = st.session_state.get("_customer_self_closed", False)
    if _show_clear or _quiet_clear:
        # 清掉所有 localStorage 鍵（含已淘汰、不安全的 iching_sid / iching_email）
        _components.html("""<script>
localStorage.removeItem('iching_token');
localStorage.removeItem('iching_sid');
localStorage.removeItem('iching_email');
</script>""", height=0)
        st.session_state["_clear_storage"] = False
        st.session_state["_clear_storage_quiet"] = False
        st.session_state["_db_unreachable"] = False
        st.session_state["_customer_self_closed"] = False
    elif not _db_down:
        # 自動回登：localStorage 若存有 token，就用 ?token= 重導回該問卦（token 猜不到，安全）。
        # 順手清掉舊版不安全的 iching_sid / iching_email（升級用戶用過一次就乾淨了）。
        _components.html("""<script>
(function(){
  const url = new URL(window.parent.location.href);
  if (url.searchParams.get('token')) return;
  if (url.searchParams.get('code') || url.searchParams.get('state')) return; // OAuth callback 進行中，勿覆蓋
  localStorage.removeItem('iching_sid');
  localStorage.removeItem('iching_email');
  const tok = localStorage.getItem('iching_token');
  if (tok) { url.searchParams.set('token', tok); window.parent.location.href = url.toString(); }
})();
</script>""", height=0)
    st.markdown('<div class="main-title">洞察易生的經歷</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="main-subtitle">靜心一問，易理自明 · 天地人和，坤澤長流</div>',
        unsafe_allow_html=True,
    )
    _ann = get_announcement()
    if _ann:
        _ann_esc = _html.escape(_ann)
        # 安全跑馬燈：用容器相對的 padding-left:100%（非視窗單位 100vw），
        # 外層 overflow:hidden + max-width:100% 把動畫完全框在容器內，不會撐寬文件、不卡捲動。
        st.markdown(f"""<div style="overflow:hidden;max-width:100%;background:linear-gradient(90deg,#2A1F0A,#3D2E0D,#2A1F0A);border:1px solid #7A5C3A;border-radius:8px;padding:10px 0;margin:10px 0;">
<div style="display:inline-block;white-space:nowrap;padding-left:100%;animation:marquee-scroll 22s linear infinite;color:#F0D080;font-size:0.95rem;">
📢 &nbsp;{_ann_esc}</div></div>
<style>@keyframes marquee-scroll{{
  from{{transform:translateX(0)}} to{{transform:translateX(-100%)}}}}</style>""",
        unsafe_allow_html=True)
    st.markdown('<hr class="g-div">', unsafe_allow_html=True)
    if _self_closed:
        st.success("🙏 感謝您的諮詢！若有新的問題，歡迎重新選擇分區問卦。")
    elif _show_clear and not _quiet_clear:
        st.info("您之前的諮詢已結案。如需繼續，請重新選擇分區問卦。")
    if _db_down:
        st.warning("⚠️ 資料庫暫時無法連線，您的查詢記錄已暫時保留。請稍後再試或點擊「重新整理」。")
        if st.button("🔄 重新整理", key="_home_db_retry"):
            st.session_state["_db_unreachable"] = False
            st.rerun()

    st.markdown("""<div class="info-box">
　《易經》六十四卦，象天地萬物之變化，述人事吉凶之道理。<br><br>
　<b>每次請提出一個問題，敘述越直觀越好。</b><br>
　例如：「我與某人的感情走向如何？」、「這份工作適合我嗎？」<br><br>
　選擇分區後填寫姓名與問題，靜候小老師為您解卦。
</div>""", unsafe_allow_html=True)

    if _google_enabled():
        if getattr(st.user, "is_logged_in", False):
            gem = (getattr(st.user, "email", "") or "").strip().lower()
            if gem and _valid_email(gem):
                st.session_state.email = gem
                gname = (getattr(st.user, "name", "") or "").strip()
                if gname:
                    st.session_state["name_prefill"] = gname
                # 只設定身分、不強制跳轉；若有進行中問卦，由下方「進行中諮詢」橫幅讓顧客自己選擇回去
                # （取代舊的「自動跳進對話」——顧客會被困在對話、到不了首頁、也不能問新問題）。
                st.success(f"✅ 已用 Google 登入（{gem}）")
                st.button("登出 Google", on_click=st.logout, key="g_logout")
            else:
                st.warning("Google 登入未取得 Email，請改用下方 Email 登入。")
                st.button("登出 Google", on_click=st.logout, key="g_logout_noemail")
        else:
            st.button("🔵 用 Google 帳號登入 / 註冊（最快，免記密碼）",
                      use_container_width=True, on_click=st.login, key="g_login")
            st.caption("用 Google 一鍵登入，免設密碼；登入後小老師回覆會寄信通知您，日後回來自動登入。")

    if _email_enabled():
        with st.expander("📧 用 Email 登入 / 查詢（免記密碼，推薦）", expanded=False):
            em_in = st.text_input("您的 Email", key="email_login_addr",
                                  placeholder="your@email.com", label_visibility="collapsed")
            ec1, ec2 = st.columns(2)
            with ec1:
                if st.button("寄送驗證碼", use_container_width=True, key="email_send_code"):
                    em = (em_in or "").strip().lower()
                    _now = time.time()
                    _wait = 10 - (_now - st.session_state.get("_email_last_send", 0))  # 兩封間隔至少 10 秒，擋網路延遲下的重複點擊
                    _srv_ok, _srv_msg = (email_send_allowed(em) if _valid_email(em) else (True, ""))
                    if not _valid_email(em):
                        st.error("請輸入正確的 Email")
                    elif _wait > 0:
                        st.warning(f"剛剛已寄出，請於 {int(_wait) + 1} 秒後再重新寄送，避免重複收信。")
                    elif not _srv_ok:
                        # L4：跨 session 防濫發（同信箱冷卻＋每日上限），擋換分頁轟炸別人信箱
                        st.warning(_srv_msg)
                    else:
                        code = _gen_code()
                        st.session_state["_email_code"] = code
                        st.session_state["_email_code_addr"] = em
                        st.session_state["_email_code_exp"] = time.time() + 600
                        st.session_state["_email_code_tries"] = 0
                        ok = send_email(
                            em, "您的登入驗證碼 · 洞察易生的經歷",
                            f"<p>您好，</p><p>您的登入驗證碼是：</p>"
                            f"<p style='font-size:1.8rem;font-weight:700;letter-spacing:0.2em;color:#8B6914;'>{code}</p>"
                            f"<p>請於 10 分鐘內回到網頁輸入。若非您本人操作，請忽略此信。</p>"
                            f"<p style='color:#999;font-size:0.85rem;'>洞察易生的經歷</p>",
                        )
                        if ok:
                            st.session_state["_email_last_send"] = _now  # 只在真的寄出後才起算冷卻；失敗可立即重試
                            email_send_record(em)  # L4：跨 session 記錄，供同信箱冷卻＋每日上限判斷
                            st.session_state["_email_code_sent"] = True
                            st.success("驗證碼已寄出，請查看信箱（含垃圾信匣）。")
                        else:
                            st.error("寄送失敗，請稍後再試，或改用上方 Google 登入。")
            with ec2:
                if st.session_state.get("_email_code_sent"):
                    if st.button("重新寄送", use_container_width=True, key="email_resend"):
                        st.session_state["_email_code_sent"] = False
                        st.rerun()
            if st.session_state.get("_email_code_sent"):
                code_in = st.text_input("輸入 6 位數驗證碼", key="email_code_in",
                                        max_chars=6, placeholder="000000")
                if st.button("驗證登入", use_container_width=True, key="email_verify"):
                    _real_code = st.session_state.get("_email_code", "")
                    if not _real_code or time.time() > st.session_state.get("_email_code_exp", 0):
                        st.error("驗證碼已過期，請重新寄送。")
                    elif not hmac.compare_digest((code_in or "").strip().encode("utf-8"), _real_code.encode("utf-8")):
                        # 限制嘗試次數，避免 6 位數驗證碼在有效期內被暴力試完
                        _tries = st.session_state.get("_email_code_tries", 0) + 1
                        st.session_state["_email_code_tries"] = _tries
                        if _tries >= 5:
                            for _k in ("_email_code", "_email_code_addr", "_email_code_exp",
                                       "_email_code_tries", "_email_code_sent"):
                                st.session_state.pop(_k, None)
                            st.error("錯誤次數過多，驗證碼已失效，請重新寄送。")
                        else:
                            st.error(f"驗證碼錯誤，請再確認。（剩 {5 - _tries} 次）")
                    else:
                        em = st.session_state.get("_email_code_addr", "")
                        st.session_state.email = em
                        for _k in ("_email_code", "_email_code_addr", "_email_code_exp",
                                   "_email_code_tries", "_email_code_sent"):
                            st.session_state.pop(_k, None)
                        # 只設定身分、不強制跳轉；有進行中問卦由下方橫幅讓顧客自己選擇回去
                        st.success("✅ 登入成功！")
                        st.rerun()
            st.caption("輸入 Email 收驗證碼即可登入；小老師回覆時會寄信通知您，點信中連結即可回來查看。")
    else:
        # 診斷行（新版才有）：看得到這行 = 新程式已上線；看不到 = 還在跑舊程式。
        _have_from = bool(st.secrets.get("email_from", ""))
        _have_pw   = bool(st.secrets.get("gmail_app_password", ""))
        st.caption(
            f"🔧 Email 功能未啟用 — email_from: {'✓' if _have_from else '✗ 缺'}、"
            f"gmail_app_password: {'✓' if _have_pw else '✗ 缺'}。兩個都要填好才會出現登入框。"
        )

    # LIFF 診斷（驗收用）：網址加 ?debug=1 才顯示，顧客平常看不到。
    # liff_id ✓ = 線上 Secrets 已吃到、LIFF 已啟用；在 LINE 內開啟若 line_uid 有值 = 免密碼自動登入成功。
    if st.query_params.get("debug") == "1":
        st.caption(
            f"🔧 LIFF 診斷 — liff_id: {'✓ 已設定（LIFF 啟用）' if _LIFF_ID else '✗ 缺（LIFF 停用）'}、"
            f"目前 line_uid: {st.session_state.line_uid or '（無 — 非 LINE 內開啟或尚未自動登入）'}。"
        )
        st.caption(
            f"🔧 Google 診斷 — [auth] 區塊: {'✓ 已讀到（按鈕應顯示）' if _google_enabled() else '✗ 沒讀到（Secrets 沒有 [auth]／格式錯／app 還沒重啟）'}、"
            f"redirect_uri: {st.secrets.get('auth', {}).get('redirect_uri', '（未設定）') if _google_enabled() else '—'}、"
            f"目前登入: {('✅ '+(getattr(st.user, 'email', '') or '')) if (_google_enabled() and getattr(st.user, 'is_logged_in', False)) else '未登入'}。"
        )
        st.caption("🔧 DB 自我測試 — " + _db_selftest())

    # 進行中諮詢橫幅：已登入／持 token 且有未結案問卦時，停在首頁讓顧客「自己選」回去看回覆，
    # 取代舊的「自動跳進對話」（會把顧客困在對話、到不了首頁、也不能問新問題）。
    # token 來的用 customer_sid 直接查；Google／Email 登入的用身分（email/line_uid）查。
    _resume = None
    _csid = st.session_state.get("customer_sid")
    if _csid:
        _cs = get_session(_csid)
        if _cs is not _DB_ERROR:
            if _cs and not _cs.get("is_closed"):
                _resume = _cs
            else:
                st.session_state.customer_sid = None  # 已結案／被刪 → 清掉失效指標
    if _resume is None:
        _f = find_my_open_session()
        if _f and _f is not _DB_ERROR:
            _resume = _f
    if _resume:
        _rcat = _resume.get("category", "")
        st.info(f"💬 您有一則進行中的諮詢（{_rcat}），小老師的回覆都在裡面。")
        if st.button("→ 回到對話查看回覆", key="_home_resume", use_container_width=True):
            st.session_state.customer_sid = _resume["session_id"]
            st.session_state.customer_name = _resume.get("customer_name") or ""
            st.session_state.customer_category = _rcat
            st.session_state.page = "chat"
            st.rerun()
        st.caption("想問一個全新的問題？也可以直接往下選分區開始。")

    # 須先登入（Email／Google／LINE）才能問卦——每筆問卦都綁定身分，安全且日後一定查得到。
    _logged_in = bool(st.session_state.email or st.session_state.line_uid)
    if not _logged_in:
        st.info("🔒 請先用上方的 **Google** 或 **Email** 登入，再選擇分區問卦。登入後小老師的回覆會通知您，日後回來自動帶出您的紀錄。")

    cats = list(CATEGORIES.items())
    col_a, col_b = st.columns(2, gap="large")
    for i, (cat_name, info) in enumerate(cats):
        col = col_a if i % 2 == 0 else col_b
        with col:
            st.markdown(f"""<div class="cat-card">
<div class="cat-icon">{info["icon"]}</div>
<div class="cat-name">{cat_name}</div>
<div class="cat-desc">{info["desc"]}</div>
</div>""", unsafe_allow_html=True)
            if st.button("進入諮詢", key=f"enter_{cat_name}", use_container_width=True,
                         disabled=not _logged_in):
                st.session_state.selected_cat = cat_name
                st.session_state.page = "register"
                st.rerun()

# ── Customer: Register ────────────────────────────────────────────────────────
def show_register():
    cat_name = st.session_state.selected_cat
    if not cat_name or cat_name not in CATEGORIES:
        st.session_state.page = "home"
        st.rerun()
        return

    info = CATEGORIES[cat_name]

    # 全新問問題頁也要能回首頁
    if st.button("← 返回首頁", key="reg_back_home"):
        st.session_state.page = "home"
        st.session_state.selected_cat = None
        st.rerun()

    # 強制先登入才能問卦：每筆問卦都綁定 Email／Google／LINE 身分，安全且日後一定查得到。
    if not (st.session_state.email or st.session_state.line_uid):
        st.warning("🔒 請先登入再問卦。")
        st.info("回到首頁，用 **Google** 或 **Email** 登入後即可開始問卦。")
        if st.button("← 回首頁登入", key="reg_need_login"):
            st.session_state.page = "home"
            st.session_state.selected_cat = None
            st.rerun()
        return

    st.markdown(f"""<div class="chat-hdr">
<span style="font-size:2rem;">{info["icon"]}</span>
<span>
<div class="chat-hdr-title">{cat_name}</div>
<div class="chat-hdr-sub">{info["desc"]}</div>
</span>
</div>""", unsafe_allow_html=True)

    st.markdown('<hr class="g-div">', unsafe_allow_html=True)
    st.markdown(f'<div class="info-box">{info["welcome"]}</div>', unsafe_allow_html=True)

    _via_line = bool(st.session_state.line_uid)
    _via_email = bool(st.session_state.email)
    if _via_line:
        st.caption("✅ 您已透過 LINE 登入，日後可直接從 LINE 選單回來查看回覆。")
    elif _via_email:
        st.caption(f"✅ 您已用 Email（{st.session_state.email}）登入，小老師回覆時會寄信通知您，日後回來免再輸入。")

    # 待修一：若此顧客已有一則進行中（未結案）的諮詢，提供入口直接切回該對話聊天室，
    # 避免登入後只看到「全新問問題」介面、找不到原本跟小老師的對話。
    _open = find_my_open_session()
    if _open and _open.get("session_id") != st.session_state.get("customer_sid"):
        _ocat = _open.get("category", "")
        st.info(f"💬 您有一則進行中的諮詢（{_ocat}），小老師的回覆都在那裡。")
        if st.button("→ 回到我進行中的諮詢、查看回覆", key="reg_resume_open",
                     use_container_width=True):
            st.session_state.customer_sid = _open["session_id"]
            st.session_state.customer_name = _open.get("customer_name") or ""
            st.session_state.customer_category = _ocat
            st.session_state.page = "chat"
            st.rerun()
        st.caption("若您是要問一個全新的問題，請繼續往下填寫；想看舊問題的回覆請點上方按鈕。")

    with st.form("register_form"):
        name = st.text_input("您的姓名",
                             value=st.session_state.line_name or st.session_state.get("name_prefill", "") or "",
                             placeholder="請輸入姓名", max_chars=40)
        question = st.text_area(
            "您的問題",
            placeholder="請輸入您想詢問的問題⋯⋯",
            height=140, max_chars=1000,
        )
        submitted = st.form_submit_button("提交問卦 →", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("請填寫姓名")
        elif not question.strip():
            st.error("請填寫問題")
        else:
            sid, token = create_session(name.strip(), cat_name,
                                        line_uid=st.session_state.line_uid,
                                        email=st.session_state.email)
            if not sid:
                return
            if not add_message(sid, "customer", question.strip()):
                delete_session(sid)  # remove orphaned session
                return
            st.session_state.pop("name_prefill", None)  # 用過即清，避免殘留預填到別人/別次
            st.session_state.customer_sid = sid
            st.session_state.customer_name = name.strip()
            st.session_state.customer_category = cat_name
            st.session_state.page = "chat"
            send_notification(name.strip(), cat_name, question.strip(), sid)
            if token:
                # 記 token 進這台裝置供日後自動回登；導向改走 Streamlit 原生 query param，
                # 可靠（不再依賴 JS 跳 parent，避免「正在跳轉…」卡住、要手動點返回才動）。
                _components.html(
                    f"<script>localStorage.setItem('iching_token','{token}');</script>",
                    height=0)
                st.query_params["token"] = token
            st.rerun()

# ── Customer: Chat ────────────────────────────────────────────────────────────
def show_chat():
    sid = st.session_state.customer_sid
    if not sid:
        st.session_state.page = "home"
        st.rerun()
        return

    sess = get_session(sid)
    if sess is _DB_ERROR:
        st.error("⚠️ 資料庫暫時無法連線，請稍後再試。")
        if st.button("🔄 重新整理", key="_chat_retry"):
            st.rerun()
        return
    if sess is None:
        st.error("找不到此諮詢記錄。")
        if st.button("← 返回首頁", key="_chat_back_notfound"):
            st.session_state.page = "home"
            st.session_state.customer_sid = None
            st.session_state.customer_category = ""
            st.session_state["_clear_storage_quiet"] = True
            st.query_params.clear()
            st.rerun()
        return

    category = sess["category"]
    info = CATEGORIES.get(category, {"icon": "☯", "desc": ""})

    st.markdown(f"""<div class="chat-hdr">
<span style="font-size:2rem;">{info["icon"]}</span>
<span>
<div class="chat-hdr-title">{category}</div>
<div class="chat-hdr-sub">{info["desc"]} · 編號：{sid}</div>
</span>
</div>""", unsafe_allow_html=True)

    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        if st.button("← 首頁"):
            st.session_state.page = "home"
            st.session_state.customer_sid = None
            st.session_state.customer_category = ""
            st.session_state["_clear_storage_quiet"] = True
            st.query_params.clear()
            st.rerun()
    with c2:
        if st.button("🔄 重新整理"):
            st.rerun()

    st.markdown('<hr class="g-div">', unsafe_allow_html=True)

    messages = get_messages(sid)
    if messages is None:
        if st.button("🔄 重新整理", key="_chat_msg_retry"):
            st.rerun()
        return

    for msg in messages:
        if msg["role"] == "customer":
            with st.chat_message("user", avatar="🙏"):
                st.markdown(_plain(msg["content"]), unsafe_allow_html=True)  # 顧客內容當純文字
                st.caption(fmt_time(msg["created_at"]))
        else:
            with st.chat_message("assistant", avatar="☯"):
                st.markdown(f"**【小老師解卦】**\n\n{msg['content']}")  # 小老師回覆保留 markdown
                st.caption(fmt_time(msg["created_at"]))

    if sess["is_closed"]:
        st.info("✅ 此諮詢已由小老師結案。如需繼續問卦，請回首頁重新提問。")
        return

    if messages and messages[-1]["role"] == "consultant":
        st.markdown("---")
        st.caption("解讀已收到？可主動結案：")
        if st.button("🙏 感謝小老師，結案", key="_customer_self_close"):
            if close_session(sid):
                st.session_state["_clear_storage"] = True
                st.session_state["_customer_self_closed"] = True
                st.session_state.customer_sid = None
                st.session_state.customer_name = ""
                st.session_state.customer_category = ""
                st.session_state.page = "home"
                st.query_params.clear()
                st.rerun()
            else:
                st.error("結案失敗，請稍後再試。")

    if messages and messages[-1]["role"] == "customer":
        st.info("⏳ 小老師正在為您研讀卦象，請稍候⋯⋯")
        st_autorefresh(interval=20000, key="chat_autorefresh")

    user_q = st.chat_input("繼續提問⋯⋯", max_chars=1000)
    if user_q:
        if add_message(sid, "customer", user_q):
            send_notification(sess["customer_name"] or "", sess["category"], user_q, sid, is_followup=True)
            st.rerun()
        # else: error shown by add_message(); user can retry without losing their text

# ── Admin: Dashboard ──────────────────────────────────────────────────────────
def show_admin():
    # 後台清單每 30 秒自動重抓，讓「小老師正開著後台、顧客剛問了新卦」也會浮上來。
    # （Streamlit 預設只在互動時重跑，否則會停在切過來之前的舊清單 → 看似「找不到」。）
    st_autorefresh(interval=30000, key="admin_dashboard_refresh")
    stats = get_stats()

    st.markdown("""<div class="admin-hdr">
<span style="font-size:2rem;">🔐</span>
<span>
<div style="font-size:1.3rem;font-weight:700;letter-spacing:0.1em;">洞察易生的經歷 · 管理後台</div>
<div style="font-size:0.82rem;color:#B8A070;margin-top:4px;">小老師專用後台 · 查閱與回覆所有來訪問卦</div>
</span>
</div>""", unsafe_allow_html=True)

    cs = st.columns(4)
    for col, (label, val, icon) in zip(cs, [
        ("今日新增",  stats["today"],   "📅"),
        ("進行中",    stats["total"],   "📂"),
        ("待回覆",    stats["pending"], "🔴"),
        ("已解讀",    stats["replied"], "✅"),
    ]):
        with col:
            st.markdown(f"""<div class="stat-box">
<div class="stat-num">{icon} {val}</div>
<div class="stat-label">{label}</div>
</div>""", unsafe_allow_html=True)

    st.markdown('<hr class="g-div">', unsafe_allow_html=True)

    fc1, fc2 = st.columns([2, 3])
    with fc1:
        status_opts = ["全部", "待回覆", "已解讀"]
        sf_val = st.session_state.admin_status_filter
        sf = st.radio(
            "狀態", status_opts, horizontal=True,
            index=status_opts.index(sf_val) if sf_val in status_opts else 0,
        )
        st.session_state.admin_status_filter = sf
    with fc2:
        cat_opts = ["全部"] + list(CATEGORIES.keys())
        cf_val = st.session_state.admin_cat_filter
        cf = st.selectbox(
            "分區", cat_opts,
            index=cat_opts.index(cf_val) if cf_val in cat_opts else 0,
        )
        st.session_state.admin_cat_filter = cf

    sessions = get_all_sessions(
        cat_f=st.session_state.admin_cat_filter,
        status_f=st.session_state.admin_status_filter,
    )

    # 搜尋 + 排序
    sa, sb, sc, sd = st.columns([3, 2, 1, 1])
    with sa:
        search = st.text_input("🔍 搜尋姓名", value=st.session_state.admin_name_search,
                               placeholder="輸入姓名或姓氏", label_visibility="collapsed")
        st.session_state.admin_name_search = search
    with sb:
        sort_opts = ["最新時間", "姓氏分組"]
        sm_val = st.session_state.admin_sort_mode
        sort_mode = st.radio("排列", sort_opts, horizontal=True,
                             index=sort_opts.index(sm_val) if sm_val in sort_opts else 0)
        st.session_state.admin_sort_mode = sort_mode
    with sc:
        if st.button("🔄 重新整理", use_container_width=True):
            st.rerun()
    with sd:
        if st.button("🗄️ 歸檔", use_container_width=True):
            st.session_state.page = "admin_archive"
            st.rerun()

    if sessions is None:
        if st.button("🔄 重新整理", key="_admin_sessions_retry"):
            st.rerun()
        return

    if search:
        sessions = [s for s in sessions if search.lower() in (s["customer_name"] or "").lower()]
    if sort_mode == "姓氏分組":
        sessions = sorted(sessions, key=lambda s: s["customer_name"] or "")

    st.markdown(f"**共 {len(sessions)} 筆問卦**")

    if not sessions:
        st.markdown('<div class="info-box">目前沒有符合條件的問卦記錄。</div>', unsafe_allow_html=True)
        return

    current_surname = None
    for s in sessions:
        if sort_mode == "姓氏分組":
            surname = s["customer_name"][0] if s["customer_name"] else "？"
            if surname != current_surname:
                current_surname = surname
                st.markdown(f"#### 　{surname} 姓")
        is_pending = s["last_role"] == "customer" or s["msg_count"] == 0
        css_cls = "pending" if is_pending else "replied"
        status_html = (
            '<span class="badge badge-red">🔴 待解讀</span>'
            if is_pending else
            '<span class="badge badge-green">✅ 已解讀</span>'
        )
        cat_icon = CATEGORIES.get(s["category"], {}).get("icon", "☯")
        preview = s["last_msg"] or "（尚未提問）"
        preview = preview[:60] + ("…" if len(preview) > 60 else "")
        name_esc = _html.escape(s["customer_name"] or "（未知）")
        preview_esc = _html.escape(preview)

        ci, cb = st.columns([4, 1])
        with ci:
            st.markdown(f"""<div class="sess-card {css_cls}">
<div>
  <span class="sess-name">{name_esc}</span>
  <span style="font-size:0.8rem;color:#7A5C3A;margin-left:8px;">{cat_icon} {s['category']}</span>
  {status_html}
</div>
<div class="sess-meta">
  編號：{s['session_id']} · {s['msg_count']} 則 · {fmt_time(s['updated_at'])}
</div>
<div class="sess-preview">💬 {preview_esc}</div>
</div>""", unsafe_allow_html=True)
        with cb:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("查看回覆 →", key=f"open_{s['session_id']}", use_container_width=True):
                st.session_state.admin_reply_sid = s["session_id"]
                st.session_state._admin_reply_from = "admin"
                st.session_state.page = "admin_reply"
                st.rerun()

# ── Admin: Reply ──────────────────────────────────────────────────────────────
def show_admin_reply():
    sid = st.session_state.admin_reply_sid
    if not sid:
        st.session_state.page = "admin"
        st.rerun()
        return

    sess = get_session(sid)
    if sess is _DB_ERROR:
        st.error("⚠️ 資料庫暫時無法連線，請稍後重試。")
        _ec1, _ec2 = st.columns(2)
        with _ec1:
            if st.button("🔄 重新整理", key="_admin_retry"):
                st.rerun()
        with _ec2:
            _back_pg = st.session_state.get("_admin_reply_from", "admin")
            if st.button("← 返回", key="_admin_retry_back"):
                st.session_state.page = _back_pg
                st.session_state.admin_reply_sid = None
                st.rerun()
        return
    if sess is None:
        st.error("找不到此問卦記錄。")
        if st.button("← 返回", key="_admin_reply_back_notfound"):
            st.session_state.page = st.session_state.get("_admin_reply_from", "admin")
            st.session_state.admin_reply_sid = None
            st.rerun()
        return

    # Clear sessionStorage draft if a send/clear just happened
    _draft_clear_sid = st.session_state.pop("_clear_reply_draft", None)
    if _draft_clear_sid:
        _components.html(f"""<script>
window.parent.sessionStorage.removeItem('iching_draft_{_draft_clear_sid}');
</script>""", height=0)

    category = sess["category"]
    info = CATEGORIES.get(category, {"icon": "☯", "desc": ""})

    back_page = st.session_state.get("_admin_reply_from", "admin")
    back_label = "← 歸檔" if back_page == "admin_archive" else "← 後台"
    if st.button(back_label):
        st.session_state.pop(f"_del_confirm_{sid}", None)
        st.session_state.pop(f"_close_confirm_{sid}", None)
        st.session_state.page = back_page
        st.session_state.admin_reply_sid = None
        st.rerun()

    cname_esc = _html.escape(sess["customer_name"] or "（未知）")
    email_val = (sess.get("email") or "").strip()
    email_esc = _html.escape(email_val)
    email_display = f'<span style="font-family:monospace;background:#2D3B2A;color:#A0C870;padding:2px 8px;border-radius:4px;">{email_esc}</span>' if email_val else '<span style="color:#B8A070;font-style:italic;">（非 Email 登入）</span>'
    line_display = '<span style="color:#A0C870;">✓ 是</span>' if (sess.get("line_uid") or "").strip() else '<span style="color:#B8A070;font-style:italic;">否</span>'
    st.markdown(f"""<div class="chat-hdr">
<span style="font-size:2rem;">{info["icon"]}</span>
<span>
<div class="chat-hdr-title">{cname_esc} · {category}</div>
<div class="chat-hdr-sub">編號：{sid} · 建立：{fmt_time(sess['created_at'])}</div>
<div class="chat-hdr-sub" style="margin-top:4px;">📧 Email：{email_display}　·　💬 LINE 登入：{line_display}</div>
</span>
</div>""", unsafe_allow_html=True)

    st.markdown('<hr class="g-div">', unsafe_allow_html=True)

    messages = get_messages(sid)
    if messages is None:
        if st.button("🔄 重新整理", key="_admin_msg_retry"):
            st.rerun()
        return
    if not messages:
        st.markdown('<div class="info-box">此來訪者尚未提問。</div>', unsafe_allow_html=True)
    else:
        for msg in messages:
            if msg["role"] == "customer":
                with st.chat_message("user", avatar="🙏"):
                    # 顧客姓名＋內容都當純文字（escape），防 markdown 圖片外連/版面注入
                    st.markdown(
                        f"<div style='white-space:pre-wrap;word-break:break-word;'>"
                        f"<b>{_html.escape(sess['customer_name'] or '（未知）')}</b>："
                        f"{_html.escape(msg['content'] or '')}</div>",
                        unsafe_allow_html=True)
                    st.caption(fmt_time(msg["created_at"]))
            else:
                with st.chat_message("assistant", avatar="☯"):
                    st.markdown(f"**【小老師解卦】**\n\n{msg['content']}")
                    st.caption(fmt_time(msg["created_at"]))

    st.markdown("---")

    if sess["is_closed"]:
        st.info("🗄️ 此問卦已歸檔。")
        if st.button("🗑️ 刪除此記錄", use_container_width=True, key="del_closed"):
            st.session_state[f"_del_confirm_{sid}"] = True
            st.rerun()
        if st.session_state.get(f"_del_confirm_{sid}"):
            st.error("⚠️ 確定要永久刪除此歸檔記錄？此操作無法復原。")
            cd1, cd2, _ = st.columns([1, 1, 2])
            with cd1:
                if st.button("✅ 確認刪除", key=f"_del_closed_yes_{sid}"):
                    if delete_session(sid):
                        st.session_state.pop(f"_del_confirm_{sid}", None)
                        st.session_state.page = "admin_archive"
                        st.session_state.admin_reply_sid = None
                        st.rerun()
            with cd2:
                if st.button("❌ 取消", key=f"_del_closed_no_{sid}"):
                    st.session_state.pop(f"_del_confirm_{sid}", None)
                    st.rerun()
        return

    st.markdown("### ✍ 卜卦解讀回覆")

    reply = st.text_area(
        "解讀內容",
        placeholder="在此輸入您的易經卜卦解讀⋯⋯",
        height=180,
        key=f"reply_txt_{sid}_{st.session_state.reply_ver}",
        label_visibility="collapsed",
    )
    _components.html(f"""<script>
(function(){{
  var ss = window.parent.sessionStorage;
  var K = 'iching_draft_{sid}';
  function findTA(){{
    var all = window.parent.document.querySelectorAll('textarea');
    for (var i=0;i<all.length;i++)
      if (all[i].placeholder && all[i].placeholder.indexOf('易經卜卦解讀') !== -1) return all[i];
    return null;
  }}
  var setup = false;
  var iv = setInterval(function(){{
    var t = findTA();
    if (!t) return;
    if (!setup){{
      setup = true;
      var saved = ss.getItem(K);
      if (saved && !t.value.trim()){{
        try{{
          var ns = Object.getOwnPropertyDescriptor(
            window.parent.HTMLTextAreaElement.prototype,'value').set;
          ns.call(t, saved);
          t.dispatchEvent(new Event('input',{{bubbles:true}}));
        }}catch(e){{ t.value = saved; }}
      }}
      t.addEventListener('input', function(){{
        t.value.trim() ? ss.setItem(K,t.value) : ss.removeItem(K);
      }});
    }}
  }}, 200);
  setTimeout(function(){{ clearInterval(iv); }}, 8000);
}})();
</script>""", height=0)
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        if st.button("📤 發送解讀", use_container_width=True):
            if reply.strip():
                if add_message(sid, "consultant", reply.strip()):
                    notify_customer_reply_email(sid)
                    notify_customer_reply_line(sess)
                    st.session_state["_clear_reply_draft"] = sid
                    st.session_state.reply_ver += 1
                    st.rerun()
                # else: error shown by add_message(), keep text so admin can retry
            else:
                st.error("請輸入解讀內容")
    with r2:
        if st.button("🗑 清除輸入", use_container_width=True):
            st.session_state["_clear_reply_draft"] = sid
            st.session_state.reply_ver += 1
            st.rerun()
    with r3:
        if st.button("✅ 結案歸檔", use_container_width=True):
            st.session_state[f"_close_confirm_{sid}"] = True
            st.rerun()
    with r4:
        if st.button("🗑️ 刪除問卦", use_container_width=True):
            st.session_state[f"_del_confirm_{sid}"] = True
            st.rerun()

    if st.session_state.get(f"_close_confirm_{sid}"):
        st.warning("確定要結案並歸檔此問卦？歸檔後顧客將無法再於此對話追問。")
        cc1, cc2, _ = st.columns([1, 1, 2])
        with cc1:
            if st.button("✅ 確認結案", key=f"_close_yes_{sid}"):
                if close_session(sid):
                    st.session_state.pop(f"_close_confirm_{sid}", None)
                    st.session_state.pop(f"_del_confirm_{sid}", None)
                    st.session_state.page = "admin"
                    st.session_state.admin_reply_sid = None
                    st.rerun()
                # else: error shown by close_session(), keep dialog open
        with cc2:
            if st.button("❌ 取消", key=f"_close_no_{sid}"):
                st.session_state.pop(f"_close_confirm_{sid}", None)
                st.rerun()

    if st.session_state.get(f"_del_confirm_{sid}"):
        st.error("⚠️ 確定要永久刪除此問卦及所有訊息？此操作無法復原。")
        cd1, cd2, _ = st.columns([1, 1, 2])
        with cd1:
            if st.button("✅ 確認刪除", key=f"_del_yes_{sid}"):
                if delete_session(sid):
                    st.session_state.pop(f"_del_confirm_{sid}", None)
                    st.session_state.page = "admin"
                    st.session_state.admin_reply_sid = None
                    st.rerun()
                # else: error shown by delete_session(), keep confirm dialog open
        with cd2:
            if st.button("❌ 取消", key=f"_del_no_{sid}"):
                st.session_state.pop(f"_del_confirm_{sid}", None)
                st.rerun()

# ── Admin: Archive ────────────────────────────────────────────────────────────
def show_admin_archive():
    if st.button("← 後台"):
        for k in list(st.session_state.keys()):
            if k.startswith("_del_arch_confirm_"):
                st.session_state.pop(k, None)
        st.session_state.page = "admin"
        st.rerun()

    st.markdown("""<div class="admin-hdr">
<span style="font-size:2rem;">🗄️</span>
<span>
<div style="font-size:1.3rem;font-weight:700;letter-spacing:0.1em;">歸檔記錄</div>
<div style="font-size:0.82rem;color:#B8A070;margin-top:4px;">已結案的問卦記錄</div>
</span>
</div>""", unsafe_allow_html=True)

    arch_search = st.text_input(
        "🔍 搜尋姓名", key="arch_name_search",
        placeholder="輸入姓名篩選", label_visibility="collapsed",
    )

    sessions = get_archived_sessions()
    if sessions is None:
        if st.button("🔄 重新整理", key="_arch_sessions_retry"):
            st.rerun()
        return

    if arch_search:
        sessions = [s for s in sessions if arch_search.lower() in (s["customer_name"] or "").lower()]

    st.markdown(f"**共 {len(sessions)} 筆歸檔**")

    if not sessions:
        st.markdown('<div class="info-box">目前沒有歸檔記錄。</div>', unsafe_allow_html=True)
        return

    for s in sessions:
        cat_icon = CATEGORIES.get(s["category"], {}).get("icon", "☯")
        preview = s["last_msg"] or "（無訊息）"
        preview = preview[:60] + ("…" if len(preview) > 60 else "")
        name_esc = _html.escape(s["customer_name"] or "（未知）")
        preview_esc = _html.escape(preview)

        ci, cb1, cb2 = st.columns([4, 1, 1])
        with ci:
            st.markdown(f"""<div class="sess-card replied">
<div>
  <span class="sess-name">{name_esc}</span>
  <span style="font-size:0.8rem;color:#7A5C3A;margin-left:8px;">{cat_icon} {s['category']}</span>
  <span class="badge badge-green">🗄️ 已歸檔</span>
</div>
<div class="sess-meta">
  編號：{s['session_id']} · {s['msg_count']} 則 · {fmt_time(s['updated_at'])}
</div>
<div class="sess-preview">💬 {preview_esc}</div>
</div>""", unsafe_allow_html=True)
        with cb1:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("查看", key=f"view_arch_{s['session_id']}", use_container_width=True):
                for _k in list(st.session_state.keys()):
                    if _k.startswith("_del_arch_confirm_"):
                        st.session_state.pop(_k, None)
                st.session_state.admin_reply_sid = s["session_id"]
                st.session_state._admin_reply_from = "admin_archive"
                st.session_state.page = "admin_reply"
                st.rerun()
        with cb2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ 刪除", key=f"del_arch_{s['session_id']}", use_container_width=True):
                for _k in list(st.session_state.keys()):
                    if _k.startswith("_del_arch_confirm_"):
                        st.session_state.pop(_k, None)
                st.session_state[f"_del_arch_confirm_{s['session_id']}"] = True
                st.rerun()

        arch_sid = s["session_id"]
        if st.session_state.get(f"_del_arch_confirm_{arch_sid}"):
            st.error(f"⚠️ 確定刪除「{_html.escape(s['customer_name'] or '（未知）')}」的歸檔記錄？此操作無法復原。")
            ca1, ca2, _ = st.columns([1, 1, 2])
            with ca1:
                if st.button("✅ 確認", key=f"_del_arch_yes_{arch_sid}"):
                    if delete_session(arch_sid):
                        st.session_state.pop(f"_del_arch_confirm_{arch_sid}", None)
                        st.rerun()
                    # else: error shown, keep dialog open so admin can retry
            with ca2:
                if st.button("❌ 取消", key=f"_del_arch_no_{arch_sid}"):
                    st.session_state.pop(f"_del_arch_confirm_{arch_sid}", None)
                    st.rerun()

# ── Router ────────────────────────────────────────────────────────────────────
page = st.session_state.page

if st.session_state.admin_mode:
    if page == "admin":
        show_admin()
    elif page == "admin_reply":
        show_admin_reply()
    elif page == "admin_archive":
        show_admin_archive()
    else:
        st.session_state.page = "admin"
        st.rerun()
else:
    if page == "home":
        show_home()
    elif page == "register":
        show_register()
    elif page == "chat":
        show_chat()
    else:
        st.session_state.page = "home"
        st.rerun()
