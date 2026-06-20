import streamlit as st
import streamlit.components.v1 as _components
import uuid
import requests as _req
import html as _html
from datetime import datetime, timezone, timedelta

_TAIWAN = timezone(timedelta(hours=8))

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="洞察易生的經歷",
    page_icon="☯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ─────────────────────────────────────────────────────────────────
_FALLBACK_PW = st.secrets.get("admin_password", "kunze2024")

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

def _enrich(sessions):
    result = []
    for s in sessions:
        msgs = sorted(s.get("messages", []), key=lambda m: m.get("created_at") or "")
        last = msgs[-1] if msgs else None
        result.append({
            **s,
            "msg_count": len(msgs),
            "last_role": last["role"] if last else None,
            "last_msg":  last["content"] if last else None,
        })
    return result

def create_session(name: str, category: str, phone: str = ""):
    sid = str(uuid.uuid4())[:8].upper()
    try:
        _post("sessions", {
            "session_id": sid,
            "customer_name": name,
            "category": category,
            "preference": phone.lower(),
        })
        return sid
    except Exception as e:
        st.error(f"建立諮詢失敗：{e}")
        return None

def get_session_by_phone(phone: str):
    try:
        data = _get("sessions", {
            "preference": f"eq.{phone.lower()}",
            "is_closed": "eq.false",
            "order": "created_at.desc",
            "limit": "1",
        })
        return data[0] if data else None
    except Exception:
        return None

_DB_ERROR = object()  # sentinel: DB unreachable (distinct from "session not found")

def get_session(sid: str):
    try:
        data = _get("sessions", {"session_id": f"eq.{sid}", "limit": "1"})
        return data[0] if data else None  # None = session genuinely not in DB
    except Exception:
        return _DB_ERROR  # connection/timeout error

def add_message(sid: str, role: str, content: str) -> bool:
    try:
        _post("messages", {"session_id": sid, "role": role, "content": content})
        _patch("sessions", {"updated_at": datetime.now(timezone.utc).isoformat()},
               {"session_id": f"eq.{sid}"})
        return True
    except Exception as e:
        st.error(f"訊息儲存失敗：{e}")
        return False

def get_messages(sid: str):
    try:
        return _get("messages", {"session_id": f"eq.{sid}", "order": "created_at.asc"})
    except Exception as e:
        st.error(f"⚠️ 載入訊息失敗：{e}")
        return []

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
        return []

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
        return []

def close_session(sid: str):
    try:
        _patch("sessions", {"is_closed": True}, {"session_id": f"eq.{sid}"})
    except Exception as e:
        st.error(f"結案失敗：{e}")

def delete_session(sid: str):
    try:
        _delete("messages", {"session_id": f"eq.{sid}"})
        _delete("sessions", {"session_id": f"eq.{sid}"})
    except Exception as e:
        st.error(f"刪除失敗：{e}")

def get_admin_password() -> str:
    try:
        data = _get("config", {"key": "eq.admin_password", "limit": "1"})
        return data[0]["value"] if data else _FALLBACK_PW
    except Exception:
        return _FALLBACK_PW

def set_admin_password(new_pw: str):
    try:
        _post("config", {"key": "admin_password", "value": new_pw},
              {"Prefer": "resolution=merge-duplicates,return=representation"})
    except Exception as e:
        st.error(f"無法更新密碼：{e}")

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
    token   = st.secrets.get("line_token", "")
    user_id = st.secrets.get("line_user_id", "")
    if not token or not user_id:
        return
    try:
        header = "【追加提問】" if is_followup else "【新問卦】"
        text = f"{header}\n姓名：{name}\n分區：{category}\n編號：{sid}\n\n問題：\n{question[:200]}"
        _req.post(
            "https://api.line.me/v2/bot/message/push",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"to": user_id, "messages": [{"type": "text", "text": text}]},
            timeout=10,
        )
    except Exception:
        pass

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
        "selected_cat": None,
        "reply_ver": 0,
        "admin_name_search": "",
        "admin_sort_mode": "最新時間",
        "_clear_storage": False,
        "_admin_reply_from": "admin",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    params = st.query_params
    if "sid" in params and st.session_state.customer_sid is None:
        sid = params["sid"]
        sess = get_session(sid)
        if sess is _DB_ERROR:
            # DB temporarily unreachable — clear URL but keep localStorage intact
            st.query_params.clear()
        elif sess is None:
            # Session genuinely not found (deleted or never existed) — clear everything
            st.query_params.clear()
            st.session_state["_clear_storage"] = True
        elif sess["is_closed"]:
            st.query_params.clear()
            st.session_state["_clear_storage"] = True
        else:
            st.session_state.customer_sid = sid
            st.session_state.customer_name = sess["customer_name"]
            st.session_state.customer_category = sess.get("category", "")
            st.session_state.page = "chat"

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
            st.session_state.page = "admin"
            st.session_state.admin_reply_sid = None
            st.rerun()
        if st.button("🚪 登出管理模式", use_container_width=True):
            _cur = st.session_state.admin_reply_sid
            if _cur:
                st.session_state.pop(f"_del_confirm_{_cur}", None)
            st.session_state.admin_mode = False
            st.session_state.page = "home"
            st.rerun()
        st.markdown("---")
        with st.expander("🔑 更改管理密碼"):
            old_pw  = st.text_input("目前密碼", type="password", key="chpw_old")
            new_pw  = st.text_input("新密碼",   type="password", key="chpw_new")
            new_pw2 = st.text_input("確認新密碼", type="password", key="chpw_new2")
            if st.button("確認更改", use_container_width=True, key="chpw_btn"):
                if not old_pw or not new_pw:
                    st.error("請填寫所有欄位")
                elif old_pw != get_admin_password():
                    st.error("目前密碼錯誤")
                elif new_pw != new_pw2:
                    st.error("兩次新密碼不一致")
                elif len(new_pw) < 6:
                    st.error("新密碼至少 6 個字元")
                else:
                    set_admin_password(new_pw)
                    st.success("密碼已更新")

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
                if st.button("📤 發送測試訊息", use_container_width=True):
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
        st.markdown("""<small>
<b>使用說明</b><br>
① 選擇諮詢分區<br>
② 填寫姓名與問題<br>
③ 靜候小老師解讀回覆<br><br>
設定查詢密碼可隨時回來查閱記錄。
</small>""", unsafe_allow_html=True)

        st.markdown("---")
        with st.expander("🔐 管理入口"):
            pw = st.text_input("管理密碼", type="password", key="admin_pw")
            if st.button("進入管理後台", use_container_width=True):
                if pw == get_admin_password():
                    st.session_state.admin_mode = True
                    st.session_state.page = "admin"
                    st.rerun()
                else:
                    st.error("密碼錯誤")

# ── Customer: Home ────────────────────────────────────────────────────────────
def show_home():
    _show_clear = st.session_state.get("_clear_storage", False)
    if _show_clear:
        _components.html("""<script>
localStorage.removeItem('iching_sid');
</script>""", height=0)
        st.session_state["_clear_storage"] = False
    else:
        _components.html("""<script>
const sid = localStorage.getItem('iching_sid');
if (sid) {
    const url = new URL(window.parent.location.href);
    if (!url.searchParams.get('sid')) {
        url.searchParams.set('sid', sid);
        window.parent.location.href = url.toString();
    }
}
</script>""", height=0)
    st.markdown('<div class="main-title">洞察易生的經歷</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="main-subtitle">靜心一問，易理自明 · 天地人和，坤澤長流</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="g-div">', unsafe_allow_html=True)
    if _show_clear:
        st.info("您之前的諮詢已結案。如需繼續，請重新選擇分區問卦。")

    st.markdown("""<div class="info-box">
　《易經》六十四卦，象天地萬物之變化，述人事吉凶之道理。<br><br>
　<b>每次請提出一個問題，敘述越直觀越好。</b><br>
　例如：「我與某人的感情走向如何？」、「這份工作適合我嗎？」<br><br>
　選擇分區後填寫姓名與問題，靜候小老師為您解卦。
</div>""", unsafe_allow_html=True)

    with st.expander("📱 查詢我的諮詢記錄"):
        lookup_phone = st.text_input("輸入當時設定的查詢密碼", placeholder="您設定的查詢密碼", label_visibility="collapsed")
        if st.button("查詢記錄", use_container_width=True):
            phone_clean = lookup_phone.strip()
            if phone_clean:
                sess = get_session_by_phone(phone_clean)
                if sess:
                    found_sid = sess["session_id"]
                    st.session_state.customer_sid = found_sid
                    st.session_state.customer_name = sess["customer_name"]
                    st.session_state.customer_category = sess.get("category", "")
                    st.session_state.page = "chat"
                    _components.html(f"""<script>
localStorage.setItem('iching_sid', '{found_sid}');
window.parent.location.href = '?sid={found_sid}';
</script>""", height=0)
                    st.stop()
                else:
                    st.error("找不到記錄，或諮詢已結案。")

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
            if st.button("進入諮詢", key=f"enter_{cat_name}", use_container_width=True):
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

    st.markdown(f"""<div class="chat-hdr">
<span style="font-size:2rem;">{info["icon"]}</span>
<span>
<div class="chat-hdr-title">{cat_name}</div>
<div class="chat-hdr-sub">{info["desc"]}</div>
</span>
</div>""", unsafe_allow_html=True)

    st.markdown('<hr class="g-div">', unsafe_allow_html=True)
    st.markdown(f'<div class="info-box">{info["welcome"]}</div>', unsafe_allow_html=True)

    with st.form("register_form"):
        name = st.text_input("您的姓名", placeholder="請輸入姓名")
        phone = st.text_input("查詢密碼（選填，可用手機號、暱稱等任意文字）", placeholder="設定一個您記得住的查詢密碼")
        question = st.text_area(
            "您的問題",
            placeholder="請輸入您想詢問的問題⋯⋯",
            height=140,
        )
        submitted = st.form_submit_button("提交問卦 →", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("請填寫姓名")
        elif not question.strip():
            st.error("請填寫問題")
        else:
            sid = create_session(name.strip(), cat_name, phone.strip())
            if not sid:
                return
            if not add_message(sid, "customer", question.strip()):
                return
            send_notification(name.strip(), cat_name, question.strip(), sid)
            st.success("問卦已送出，正在跳轉⋯⋯")
            _components.html(f"""<script>
localStorage.setItem('iching_sid', '{sid}');
window.parent.location.href = '?sid={sid}';
</script>""", height=0)
            st.stop()

# ── Customer: Chat ────────────────────────────────────────────────────────────
def show_chat():
    sid = st.session_state.customer_sid
    if not sid:
        st.session_state.page = "home"
        st.rerun()
        return

    sess = get_session(sid)
    if sess is _DB_ERROR:
        st.error("⚠️ 資料庫暫時無法連線，請稍後重新整理。")
        return
    if sess is None:
        st.error("找不到此諮詢記錄。")
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
            st.query_params.clear()
            st.rerun()
    with c2:
        if st.button("🔄 重新整理"):
            st.rerun()

    st.markdown('<hr class="g-div">', unsafe_allow_html=True)

    messages = get_messages(sid)

    for msg in messages:
        if msg["role"] == "customer":
            with st.chat_message("user", avatar="🙏"):
                st.markdown(msg["content"])
                st.caption(fmt_time(msg["created_at"]))
        else:
            with st.chat_message("assistant", avatar="☯"):
                st.markdown(f"**【小老師解卦】**\n\n{msg['content']}")
                st.caption(fmt_time(msg["created_at"]))

    if sess["is_closed"]:
        st.info("✅ 此諮詢已由小老師結案。如需繼續問卦，請回首頁重新提問。")
        return

    if messages and messages[-1]["role"] == "customer":
        st.info("⏳ 小老師正在為您研讀卦象，請稍候⋯⋯")
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=20000, key="chat_autorefresh")

    user_q = st.chat_input("繼續提問⋯⋯")
    if user_q:
        add_message(sid, "customer", user_q)
        send_notification(sess["customer_name"], sess["category"], user_q, sid, is_followup=True)
        st.rerun()

# ── Admin: Dashboard ──────────────────────────────────────────────────────────
def show_admin():
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
    sa, sb, sc = st.columns([3, 2, 1])
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
        if st.button("🗄️ 歸檔", use_container_width=True):
            st.session_state.page = "admin_archive"
            st.rerun()

    if search:
        sessions = [s for s in sessions if search.lower() in s["customer_name"].lower()]
    if sort_mode == "姓氏分組":
        sessions = sorted(sessions, key=lambda s: s["customer_name"])

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
        name_esc = _html.escape(s["customer_name"])
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
        return
    if sess is None:
        st.error("找不到此問卦記錄。")
        return

    category = sess["category"]
    info = CATEGORIES.get(category, {"icon": "☯", "desc": ""})

    back_page = st.session_state.get("_admin_reply_from", "admin")
    back_label = "← 歸檔" if back_page == "admin_archive" else "← 後台"
    if st.button(back_label):
        st.session_state.pop(f"_del_confirm_{sid}", None)
        st.session_state.page = back_page
        st.session_state.admin_reply_sid = None
        st.rerun()

    cname_esc = _html.escape(sess["customer_name"])
    st.markdown(f"""<div class="chat-hdr">
<span style="font-size:2rem;">{info["icon"]}</span>
<span>
<div class="chat-hdr-title">{cname_esc} · {category}</div>
<div class="chat-hdr-sub">編號：{sid} · 建立：{fmt_time(sess['created_at'])}</div>
</span>
</div>""", unsafe_allow_html=True)

    st.markdown('<hr class="g-div">', unsafe_allow_html=True)

    messages = get_messages(sid)
    if not messages:
        st.markdown('<div class="info-box">此來訪者尚未提問。</div>', unsafe_allow_html=True)
    else:
        for msg in messages:
            if msg["role"] == "customer":
                with st.chat_message("user", avatar="🙏"):
                    st.markdown(f"**{sess['customer_name']}**：{msg['content']}")
                    st.caption(fmt_time(msg["created_at"]))
            else:
                with st.chat_message("assistant", avatar="☯"):
                    st.markdown(f"**【小老師解卦】**\n\n{msg['content']}")
                    st.caption(fmt_time(msg["created_at"]))

    st.markdown("---")

    if sess["is_closed"]:
        st.info("🗄️ 此問卦已歸檔。")
        if st.button("🗑️ 刪除此記錄", use_container_width=True, key="del_closed"):
            delete_session(sid)
            st.session_state.page = "admin_archive"
            st.session_state.admin_reply_sid = None
            st.rerun()
        return

    st.markdown("### ✍ 卜卦解讀回覆")

    reply = st.text_area(
        "解讀內容",
        placeholder="在此輸入您的易經卜卦解讀⋯⋯",
        height=180,
        key=f"reply_txt_{st.session_state.reply_ver}",
        label_visibility="collapsed",
    )
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        if st.button("📤 發送解讀", use_container_width=True):
            if reply.strip():
                add_message(sid, "consultant", reply.strip())
                st.session_state.reply_ver += 1
                st.rerun()
            else:
                st.error("請輸入解讀內容")
    with r2:
        if st.button("🗑 清除輸入", use_container_width=True):
            st.session_state.reply_ver += 1
            st.rerun()
    with r3:
        if st.button("✅ 結案歸檔", use_container_width=True):
            close_session(sid)
            st.session_state.pop(f"_del_confirm_{sid}", None)
            st.session_state.page = "admin"
            st.session_state.admin_reply_sid = None
            st.rerun()
    with r4:
        if st.button("🗑️ 刪除問卦", use_container_width=True):
            st.session_state[f"_del_confirm_{sid}"] = True
            st.rerun()

    if st.session_state.get(f"_del_confirm_{sid}"):
        st.error("⚠️ 確定要永久刪除此問卦及所有訊息？此操作無法復原。")
        cd1, cd2, _ = st.columns([1, 1, 2])
        with cd1:
            if st.button("✅ 確認刪除", key=f"_del_yes_{sid}"):
                delete_session(sid)
                st.session_state.pop(f"_del_confirm_{sid}", None)
                st.session_state.page = "admin"
                st.session_state.admin_reply_sid = None
                st.rerun()
        with cd2:
            if st.button("❌ 取消", key=f"_del_no_{sid}"):
                st.session_state.pop(f"_del_confirm_{sid}", None)
                st.rerun()

# ── Admin: Archive ────────────────────────────────────────────────────────────
def show_admin_archive():
    if st.button("← 後台"):
        st.session_state.page = "admin"
        st.rerun()

    st.markdown("""<div class="admin-hdr">
<span style="font-size:2rem;">🗄️</span>
<span>
<div style="font-size:1.3rem;font-weight:700;letter-spacing:0.1em;">歸檔記錄</div>
<div style="font-size:0.82rem;color:#B8A070;margin-top:4px;">已結案的問卦記錄</div>
</span>
</div>""", unsafe_allow_html=True)

    sessions = get_archived_sessions()
    st.markdown(f"**共 {len(sessions)} 筆歸檔**")

    if not sessions:
        st.markdown('<div class="info-box">目前沒有歸檔記錄。</div>', unsafe_allow_html=True)
        return

    for s in sessions:
        cat_icon = CATEGORIES.get(s["category"], {}).get("icon", "☯")
        preview = s["last_msg"] or "（無訊息）"
        preview = preview[:60] + ("…" if len(preview) > 60 else "")
        name_esc = _html.escape(s["customer_name"])
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
                st.session_state.admin_reply_sid = s["session_id"]
                st.session_state._admin_reply_from = "admin_archive"
                st.session_state.page = "admin_reply"
                st.rerun()
        with cb2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ 刪除", key=f"del_arch_{s['session_id']}", use_container_width=True):
                delete_session(s["session_id"])
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
