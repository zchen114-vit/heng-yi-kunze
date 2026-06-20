import streamlit as st
import sqlite3
import uuid
from datetime import datetime
import os

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="洞察易經的人生",
    page_icon="☯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ─────────────────────────────────────────────────────────────────
ADMIN_PASSWORD = st.secrets.get("admin_password", "kunze2024")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "consultations.db")

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
        "icon": "🪙", "desc": "財富運勢、投資理財、商業機遇",
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

PREFERENCES = ["偏好傳統解讀", "現代化解讀", "中西合璧解讀", "直覺式解讀"]

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
    font-size: 2.8rem; font-weight: 700;
    letter-spacing: 0.4em; padding-top: 1rem;
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
.badge-gold  { background: #C4922A; }

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

# ── Database ──────────────────────────────────────────────────────────────────
def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = _conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id    TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            category      TEXT NOT NULL,
            preference    TEXT,
            created_at    TEXT NOT NULL,
            updated_at    TEXT NOT NULL,
            is_closed     INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role       TEXT NOT NULL,
            content    TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
    """)
    c.commit()
    c.close()

init_db()

def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def create_session(name: str, category: str, pref: str) -> str:
    sid = str(uuid.uuid4())[:8].upper()
    now = _now()
    c = _conn()
    c.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?,0)", (sid, name, category, pref, now, now))
    c.commit()
    c.close()
    return sid

def get_session(sid: str):
    c = _conn()
    r = c.execute("SELECT * FROM sessions WHERE session_id=?", (sid,)).fetchone()
    c.close()
    return r

def add_message(sid: str, role: str, content: str):
    now = _now()
    c = _conn()
    c.execute(
        "INSERT INTO messages (session_id,role,content,created_at) VALUES (?,?,?,?)",
        (sid, role, content, now)
    )
    c.execute("UPDATE sessions SET updated_at=? WHERE session_id=?", (now, sid))
    c.commit()
    c.close()

def get_messages(sid: str):
    c = _conn()
    r = c.execute(
        "SELECT * FROM messages WHERE session_id=? ORDER BY created_at", (sid,)
    ).fetchall()
    c.close()
    return r

def get_all_sessions(cat_f=None, status_f=None):
    c = _conn()
    q = """
        SELECT s.*,
            (SELECT COUNT(*) FROM messages m WHERE m.session_id=s.session_id) AS msg_count,
            (SELECT role    FROM messages m WHERE m.session_id=s.session_id ORDER BY created_at DESC LIMIT 1) AS last_role,
            (SELECT content FROM messages m WHERE m.session_id=s.session_id ORDER BY created_at DESC LIMIT 1) AS last_msg
        FROM sessions s WHERE s.is_closed=0
    """
    params = []
    if cat_f and cat_f != "全部":
        q += " AND s.category=?"
        params.append(cat_f)
    q += " ORDER BY s.updated_at DESC"
    rows = c.execute(q, params).fetchall()
    c.close()
    if status_f == "待回覆":
        rows = [r for r in rows if r["last_role"] == "customer" or r["msg_count"] == 0]
    elif status_f == "已解讀":
        rows = [r for r in rows if r["last_role"] == "consultant"]
    return rows

def close_session(sid: str):
    c = _conn()
    c.execute("UPDATE sessions SET is_closed=1 WHERE session_id=?", (sid,))
    c.commit()
    c.close()

def get_stats():
    today = datetime.now().strftime("%Y-%m-%d")
    c = _conn()
    total   = c.execute("SELECT COUNT(*) FROM sessions WHERE is_closed=0").fetchone()[0]
    today_n = c.execute("SELECT COUNT(*) FROM sessions WHERE date(created_at)=?", (today,)).fetchone()[0]
    pending = c.execute("""
        SELECT COUNT(*) FROM sessions s WHERE s.is_closed=0
        AND (SELECT role FROM messages m WHERE m.session_id=s.session_id
             ORDER BY created_at DESC LIMIT 1) = 'customer'
    """).fetchone()[0]
    replied = c.execute("""
        SELECT COUNT(*) FROM sessions s WHERE s.is_closed=0
        AND (SELECT role FROM messages m WHERE m.session_id=s.session_id
             ORDER BY created_at DESC LIMIT 1) = 'consultant'
    """).fetchone()[0]
    c.close()
    return {"total": total, "today": today_n, "pending": pending, "replied": replied}

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
        "customer_pref": PREFERENCES[0],
        "reply_ver": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Restore session from URL query param
    params = st.query_params
    if "sid" in params and st.session_state.customer_sid is None:
        sid = params["sid"]
        sess = get_session(sid)
        if sess and not sess["is_closed"]:
            st.session_state.customer_sid = sid
            st.session_state.customer_name = sess["customer_name"]
            st.session_state.customer_pref = sess["preference"] or PREFERENCES[0]
            st.session_state.page = "chat"

init_state()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    if st.session_state.admin_mode:
        st.markdown("## 🔐 管理後台")
        st.markdown("---")
        st.markdown("**✅ 顧問模式啟動**")
        st.markdown("---")
        if st.button("← 回到後台首頁", use_container_width=True):
            st.session_state.page = "admin"
            st.session_state.admin_reply_sid = None
            st.rerun()
        if st.button("🚪 登出管理模式", use_container_width=True):
            st.session_state.admin_mode = False
            st.session_state.page = "home"
            st.rerun()
    else:
        st.markdown("## ☯ 洞察易經的人生")
        st.markdown("---")
        st.markdown("**📋 個人檔案**")

        new_name = st.text_input(
            "您的姓名", value=st.session_state.customer_name, placeholder="請輸入姓名"
        )
        st.session_state.customer_name = new_name

        new_pref = st.selectbox(
            "解讀偏好", PREFERENCES,
            index=PREFERENCES.index(st.session_state.customer_pref)
        )
        st.session_state.customer_pref = new_pref

        st.markdown("---")

        if st.session_state.page == "chat" and st.session_state.customer_sid:
            sid = st.session_state.customer_sid
            sess = get_session(sid)
            if sess:
                icon = CATEGORIES[sess["category"]]["icon"]
                st.markdown(f"**目前分區：** {icon} {sess['category']}")
                st.markdown("**您的諮詢編號：**")
                st.markdown(f'<div class="sid-box">{sid}</div>', unsafe_allow_html=True)
                st.caption("請保存此編號，可隨時返回查閱")
            if st.button("← 回到首頁", use_container_width=True):
                st.session_state.page = "home"
                st.session_state.customer_sid = None
                st.query_params.clear()
                st.rerun()
        else:
            st.markdown("**目前位置：首頁**")

        st.markdown("---")
        st.markdown("""<small>
<b>使用說明</b><br>
① 填寫姓名與解讀偏好<br>
② 選擇諮詢分區<br>
③ 輸入您的問題<br>
④ 靜候顧問解讀回覆<br><br>
請保存諮詢編號以便日後查閱。
</small>""", unsafe_allow_html=True)

        st.markdown("---")
        with st.expander("🔐 顧問入口"):
            pw = st.text_input("管理密碼", type="password", key="admin_pw")
            if st.button("進入管理後台", use_container_width=True):
                if pw == ADMIN_PASSWORD:
                    st.session_state.admin_mode = True
                    st.session_state.page = "admin"
                    st.rerun()
                else:
                    st.error("密碼錯誤")

# ── Customer: Home ────────────────────────────────────────────────────────────
def show_home():
    st.markdown('<div class="main-title">洞察易經的人生</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="main-subtitle">靜心一問，易理自明 · 天地人和，坤澤長流</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="g-div">', unsafe_allow_html=True)

    name = st.session_state.customer_name or "訪客"
    pref = st.session_state.customer_pref
    st.markdown(f"""<div class="info-box">
　歡迎，<b>{name}</b>。<br><br>
　《易經》六十四卦，象天地萬物之變化，述人事吉凶之道理。<br>
　本館採「<b>{pref}</b>」為您解讀，問題無需複雜，一心一念即可。<br><br>
　請選擇下方分區，進入後輸入您的問題，顧問將為您逐一解析。
</div>""", unsafe_allow_html=True)

    if not st.session_state.customer_name:
        st.warning("請先在左側欄填入您的姓名，再進入諮詢分區。")

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
            disabled = not st.session_state.customer_name
            if st.button("進入諮詢", key=f"enter_{cat_name}", use_container_width=True, disabled=disabled):
                sid = create_session(
                    st.session_state.customer_name,
                    cat_name,
                    st.session_state.customer_pref,
                )
                st.session_state.customer_sid = sid
                st.session_state.page = "chat"
                st.query_params["sid"] = sid
                st.rerun()

# ── Customer: Chat ────────────────────────────────────────────────────────────
def show_chat():
    sid = st.session_state.customer_sid
    if not sid:
        st.session_state.page = "home"
        st.rerun()
        return

    sess = get_session(sid)
    if not sess:
        st.error("找不到此諮詢記錄。")
        return

    category = sess["category"]
    info = CATEGORIES[category]

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
            st.query_params.clear()
            st.rerun()
    with c2:
        if st.button("🔄 重新整理"):
            st.rerun()

    st.markdown('<hr class="g-div">', unsafe_allow_html=True)

    messages = get_messages(sid)

    if not messages:
        st.markdown(
            f'<div class="info-box">{info["welcome"]}<br><br>'
            f'靜心一念，易理自明。請在下方輸入您想詢問的問題。</div>',
            unsafe_allow_html=True,
        )

    for msg in messages:
        if msg["role"] == "customer":
            with st.chat_message("user", avatar="🙏"):
                st.markdown(msg["content"])
                st.caption(msg["created_at"])
        else:
            with st.chat_message("assistant", avatar="☯"):
                st.markdown(f"**【易經顧問解讀】**\n\n{msg['content']}")
                st.caption(msg["created_at"])

    if messages and messages[-1]["role"] == "customer":
        st.info("⏳ 顧問正在為您研讀卦象，請稍候。可按「重新整理」查看最新回覆。")

    user_q = st.chat_input("請輸入您的問題⋯⋯")
    if user_q:
        add_message(sid, "customer", user_q)
        st.rerun()

# ── Admin: Dashboard ──────────────────────────────────────────────────────────
def show_admin():
    stats = get_stats()

    st.markdown("""<div class="admin-hdr">
<span style="font-size:2rem;">🔐</span>
<span>
<div style="font-size:1.3rem;font-weight:700;letter-spacing:0.1em;">洞察易經的人生 · 管理後台</div>
<div style="font-size:0.82rem;color:#B8A070;margin-top:4px;">易經顧問專用 · 查閱與回覆所有諮詢</div>
</span>
</div>""", unsafe_allow_html=True)

    cs = st.columns(4)
    for col, (label, val, icon) in zip(cs, [
        ("今日新增", stats["today"], "📅"),
        ("進行中",  stats["total"],  "📂"),
        ("待回覆",  stats["pending"], "🔴"),
        ("已解讀",  stats["replied"], "✅"),
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
        sf = st.radio(
            "狀態", status_opts, horizontal=True,
            index=status_opts.index(st.session_state.admin_status_filter),
        )
        st.session_state.admin_status_filter = sf
    with fc2:
        cat_opts = ["全部"] + list(CATEGORIES.keys())
        cf = st.selectbox(
            "分區",
            cat_opts,
            index=cat_opts.index(st.session_state.admin_cat_filter),
        )
        st.session_state.admin_cat_filter = cf

    sessions = get_all_sessions(
        cat_f=st.session_state.admin_cat_filter,
        status_f=st.session_state.admin_status_filter,
    )

    st.markdown(f"**共 {len(sessions)} 筆諮詢**")

    if not sessions:
        st.markdown('<div class="info-box">目前沒有符合條件的諮詢記錄。</div>', unsafe_allow_html=True)
        return

    for s in sessions:
        is_pending = s["last_role"] == "customer" or s["msg_count"] == 0
        css_cls = "pending" if is_pending else "replied"
        status_html = (
            '<span class="badge badge-red">🔴 待回覆</span>'
            if is_pending else
            '<span class="badge badge-green">✅ 已解讀</span>'
        )
        cat_icon = CATEGORIES.get(s["category"], {}).get("icon", "☯")
        preview = (s["last_msg"] or "（尚未提問）")
        preview = preview[:60] + ("…" if len(preview) > 60 else "")

        ci, cb = st.columns([4, 1])
        with ci:
            st.markdown(f"""<div class="sess-card {css_cls}">
<div>
  <span class="sess-name">{s['customer_name']}</span>
  <span style="font-size:0.8rem;color:#7A5C3A;margin-left:8px;">{cat_icon} {s['category']}</span>
  {status_html}
</div>
<div class="sess-meta">
  編號：{s['session_id']} · {s['preference'] or '未設定'} · {s['msg_count']} 則 · {s['updated_at']}
</div>
<div class="sess-preview">💬 {preview}</div>
</div>""", unsafe_allow_html=True)
        with cb:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("查看回覆 →", key=f"open_{s['session_id']}", use_container_width=True):
                st.session_state.admin_reply_sid = s["session_id"]
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
    if not sess:
        st.error("找不到此諮詢記錄。")
        return

    category = sess["category"]
    info = CATEGORIES[category]

    _, cb = st.columns([1, 6])
    with _:
        if st.button("← 後台"):
            st.session_state.page = "admin"
            st.session_state.admin_reply_sid = None
            st.rerun()

    st.markdown(f"""<div class="chat-hdr">
<span style="font-size:2rem;">{info["icon"]}</span>
<span>
<div class="chat-hdr-title">{sess['customer_name']} · {category}</div>
<div class="chat-hdr-sub">編號：{sid} · {sess['preference']} · 建立：{sess['created_at']}</div>
</span>
</div>""", unsafe_allow_html=True)

    st.markdown('<hr class="g-div">', unsafe_allow_html=True)

    messages = get_messages(sid)
    if not messages:
        st.markdown('<div class="info-box">此顧客尚未提問。</div>', unsafe_allow_html=True)
    else:
        for msg in messages:
            if msg["role"] == "customer":
                with st.chat_message("user", avatar="🙏"):
                    st.markdown(f"**{sess['customer_name']}**：{msg['content']}")
                    st.caption(msg["created_at"])
            else:
                with st.chat_message("assistant", avatar="☯"):
                    st.markdown(f"**【顧問解讀】**\n\n{msg['content']}")
                    st.caption(msg["created_at"])

    st.markdown("---")
    st.markdown("### ✍ 輸入解讀回覆")

    reply = st.text_area(
        "解讀內容",
        placeholder="在此輸入您的易經解讀⋯⋯",
        height=180,
        key=f"admin_reply_txt_{st.session_state.reply_ver}",
        label_visibility="collapsed",
    )
    r1, r2, r3 = st.columns(3)
    with r1:
        if st.button("📤 發送解讀", use_container_width=True):
            if reply.strip():
                add_message(sid, "consultant", reply.strip())
                st.session_state.reply_ver += 1
                st.rerun()
    with r2:
        if st.button("🗑 清除輸入", use_container_width=True):
            st.session_state.reply_ver += 1
            st.rerun()
    with r3:
        if st.button("✅ 結案歸檔", use_container_width=True):
            close_session(sid)
            st.session_state.page = "admin"
            st.session_state.admin_reply_sid = None
            st.rerun()

# ── Router ────────────────────────────────────────────────────────────────────
page = st.session_state.page

if st.session_state.admin_mode:
    if page == "admin":
        show_admin()
    elif page == "admin_reply":
        show_admin_reply()
    else:
        st.session_state.page = "admin"
        st.rerun()
else:
    if page == "home":
        show_home()
    elif page == "chat":
        show_chat()
    else:
        st.session_state.page = "home"
        st.rerun()
