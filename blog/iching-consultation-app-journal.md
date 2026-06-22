# 研究日誌：洞察易生的經歷 — 易經諮詢平台建置全紀錄

> 作者：Thomas Chen  
> 技術協作：Claude Sonnet 4.6  
> 時間：2026 年 6 月  
> Repo：github.com/zchen114-vit/heng-yi-kunze

---

## 一、我想解決什麼問題

### 背景

我是一位提供易經卜卦諮詢的服務者（小老師），原本用 LINE 直接和顧客一對一溝通。隨著來訪人數增加，管理上出現幾個痛點：

- 顧客問題散落在各個 LINE 對話，難以追蹤
- 無法分類管理（感情、事業、健康等不同分區）
- 結案後的記錄無法統一歸檔
- 顧客找不到之前的對話記錄

**核心需求：**
1. 顧客可以在網頁自助提問，不需要先加 LINE
2. 我在後台手動回覆（不要 AI 自動回答）
3. 問卦依分區分類、可歸檔、可搜尋
4. 我能用 LINE 遠端管理，不用一直盯著網頁

---

## 二、用了哪些關鍵提示詞

### 架構決策類

```
"不用 supabase-py，改用 requests 直接打 PostgREST REST API"
→ 解決 Streamlit Cloud 上 async DNS 失敗的問題

"用 _DB_ERROR = object() sentinel 物件，區分『DB 斷線』和『找不到資料』"
→ 解決兩種空值情境的混淆

"localStorage 存 session ID，搭配 ?sid= URL 參數，讓顧客重開瀏覽器也能自動回到對話"
→ 無痛的顧客體驗，不需要帳號密碼
```

### Bug 修復類

```
"st.session_state 的 key 要包含 sid，不然切換不同問卦時 textarea 內容會殘留"
"_enrich() 的 messages 欄位若 Supabase 回傳 null 會 crash，改為 s.get('messages') or []"
"登出時要 pop('admin_pw') 否則密碼欄位會預填"
"關掉 Supabase Edge Function 的 JWT 驗證：--no-verify-jwt"
```

### 功能設計類

```
"顧客不要看到相對時間，避免給人壓力"
"管理員可以用 LINE 傳 [編號] [回覆內容] 直接回覆，顧客在網頁看得到"
"跑馬燈用 CSS animation 而不是 <marquee> 標籤（已廢棄）"
"sessionStorage 草稿：用 React 的 native setter + dispatchEvent 觸發 Streamlit 的 onChange"
```

---

## 三、怎麼做的、架構長怎樣

### 技術棧

| 層級 | 技術 | 原因 |
|------|------|------|
| 前端/後台 | Streamlit (Python) | 快速開發，純 Python，免費部署 |
| 資料庫 | Supabase (PostgreSQL) | 免費方案夠用，有 REST API |
| DB 客戶端 | requests（直接打 PostgREST） | supabase-py 在 Streamlit Cloud 有 async DNS bug |
| 部署 | Streamlit Cloud | 連接 GitHub，push 自動部署 |
| 通知 | LINE Messaging API | 新問卦時推播給管理員 |
| 遠端管理 | Supabase Edge Function (Deno/TypeScript) | LINE Webhook 接收管理員指令 |
| Session 持久化 | localStorage + URL ?sid= | 顧客關瀏覽器重開不會遺失 |

### 資料庫結構

```
sessions
  session_id    TEXT  PRIMARY KEY  (8碼大寫英數)
  customer_name TEXT
  category      TEXT  (感情/事業/健康/...)
  preference    TEXT  (查詢密碼，選填)
  is_closed     BOOLEAN  DEFAULT false
  created_at    TIMESTAMPTZ
  updated_at    TIMESTAMPTZ

messages
  id          BIGSERIAL  PRIMARY KEY
  session_id  TEXT  REFERENCES sessions
  role        TEXT  (customer / consultant)
  content     TEXT
  created_at  TIMESTAMPTZ

config
  key    TEXT  PRIMARY KEY  (admin_password)
  value  TEXT

settings
  key    TEXT  PRIMARY KEY  (announcement)
  value  TEXT
```

### 頁面路由（Streamlit session_state.page）

```
home       → 首頁（分區選擇、查詢記錄）
register   → 填寫姓名與問題
chat       → 顧客對話頁面
admin      → 管理後台儀表板
admin_reply → 查看/回覆特定問卦
admin_archive → 歸檔記錄列表
```

### LINE 系統架構

```
管理員 LINE App
    ↓ 傳訊息
LINE Platform
    ↓ Webhook POST
Supabase Edge Function (line-webhook/index.ts)
    ↓ 解析指令
Supabase DB（讀寫 sessions / messages）
    ↓ 回應
管理員 LINE App（push message）
```

---

## 四、踩到哪些坑、怎麼解決

### 坑 1：supabase-py 在 Streamlit Cloud 無法運作

**症狀：** 本機正常，部署到 Streamlit Cloud 後 DB 連線全部失敗  
**原因：** supabase-py 使用 async DNS 解析，Streamlit Cloud 的環境不支援  
**解法：** 完全放棄 supabase-py，改用 `requests` 直接打 PostgREST REST API

```python
# 舊做法（有問題）
from supabase import create_client
supabase.table("sessions").select("*").execute()

# 新做法（穩定）
import requests
requests.get(f"{url}/rest/v1/sessions", headers=headers)
```

---

### 坑 2：無法區分「DB 斷線」和「資料不存在」

**症狀：** DB 斷線時顯示「找不到記錄」，反而讓顧客以為資料遺失  
**解法：** 自訂 sentinel 物件

```python
_DB_ERROR = object()  # 唯一物件，不可能等於任何正常回傳值

def get_session(sid):
    try:
        data = _get("sessions", ...)
        return data[0] if data else None  # None = 真的找不到
    except Exception:
        return _DB_ERROR  # DB_ERROR = 連線失敗

# 呼叫端分三種情況處理
sess = get_session(sid)
if sess is _DB_ERROR:   st.error("DB 暫時無法連線")
elif sess is None:      st.error("找不到此問卦")
else:                   show_chat(sess)
```

---

### 坑 3：localStorage redirect 無窮迴圈

**症狀：** 問卦結案後顧客重訪 → localStorage 有舊 sid → redirect → DB 找不到 → 錯誤頁 → redirect 無窮迴圈  
**解法：** 加入三個 flag 分別處理不同情況

```python
"_clear_storage": False       # 清除 localStorage + 顯示提示
"_clear_storage_quiet": False  # 清除 localStorage 靜默（自願離開）
"_db_unreachable": False       # DB 斷線時不執行 redirect，保留 localStorage
```

---

### 坑 4：Supabase Edge Function 返回 401

**症狀：** LINE Verify 按鈕一直顯示 401  
**排查過程：**
1. 以為是 Channel Secret 填錯 → 改成遇到簽名錯誤也回 200 → 還是 401
2. 以為是 Secrets 沒生效 → 重新部署 → 還是 401
3. 才發現：Supabase Edge Function **預設要求 JWT 驗證**，LINE 的請求沒帶 JWT

**解法：**
```bash
supabase functions deploy line-webhook --no-verify-jwt
```

---

### 坑 5：LINE Admin User ID 格式錯誤

**症狀：** 所有訊息都被當成訪客，回覆「請到網址...」  
**原因：** 設定的是帳號顯示數字（`2005270278`），不是 API userId  
**LINE userId 正確格式：** `U` 開頭的 32 字元十六進位字串（`U761d59...`）  
**解法：** 去 LINE Developers Console → Basic settings → Your user ID 取得正確格式

---

### 坑 6：`return=minimal` 讓 `r.json()` 崩潰

**症狀：** `儲存失敗：Expecting value: line 1 column 1 (char 0)`  
**原因：** PostgREST 的 `return=minimal` 回傳 204 空 body，`r.json()` 無法解析  
**解法：** 對不需要回傳值的操作，直接用 `_req.post()` + `r.raise_for_status()`，不呼叫 `.json()`

---

### 坑 7：PIL 在 Windows 顯示中文需要指定字型

**症狀：** 產生的圖文選單圖片中文字變成方塊  
**解法：** 嘗試多個字型路徑，找到第一個存在的就用

```python
font_paths = [
    "C:/Windows/Fonts/msjhbd.ttc",  # 微軟正黑體 Bold
    "C:/Windows/Fonts/msjh.ttc",
    "/System/Library/Fonts/PingFang.ttc",  # macOS
]
```

---

### 坑 8：SessionStorage 跨 iframe 存取

**症狀：** `_components.html()` 的 JS 無法存取主頁面的 sessionStorage  
**原因：** `_components.html()` 在 iframe 中執行，需透過 `window.parent` 存取  
**解法：**
```javascript
// 錯誤
sessionStorage.setItem(K, v)

// 正確
window.parent.sessionStorage.setItem(K, v)
window.parent.document.querySelectorAll('textarea')
```

---

## 五、可以抽成 Skill 的做法

### Skill 1：DB Error Sentinel Pattern

適用於任何「需要區分 DB 錯誤 vs 空資料」的 Streamlit + Supabase 組合

```python
_DB_ERROR = object()

def safe_db_fetch(query_fn):
    try:
        result = query_fn()
        return result if result else None
    except Exception:
        return _DB_ERROR

# 呼叫端固定三分支
result = safe_db_fetch(...)
if result is _DB_ERROR:   handle_db_down()
elif result is None:      handle_not_found()
else:                     handle_success(result)
```

---

### Skill 2：Streamlit localStorage Session 持久化

讓使用者關掉瀏覽器後還能自動回到上次的頁面

```python
# 存入
_components.html(f"""<script>
localStorage.setItem('app_sid', '{sid}');
window.parent.location.href = '?sid={sid}';
</script>""", height=0)

# 首頁讀取（自動 redirect）
_components.html("""<script>
const sid = localStorage.getItem('app_sid');
if (sid) {
    const url = new URL(window.parent.location.href);
    if (!url.searchParams.get('sid')) {
        url.searchParams.set('sid', sid);
        window.parent.location.href = url.toString();
    }
}
</script>""", height=0)

# 清除（結案/登出時）
_components.html("""<script>
localStorage.removeItem('app_sid');
</script>""", height=0)
```

---

### Skill 3：Streamlit Textarea sessionStorage 草稿自動儲存

防止管理員重新整理後遺失正在打的回覆

```javascript
(function() {
  var ss = window.parent.sessionStorage;
  var K = 'draft_key';
  function findTA() {
    var all = window.parent.document.querySelectorAll('textarea');
    for (var i = 0; i < all.length; i++)
      if (all[i].placeholder.indexOf('識別關鍵字') !== -1) return all[i];
    return null;
  }
  var setup = false;
  var iv = setInterval(function() {
    var t = findTA();
    if (!t || setup) return;
    setup = true;
    var saved = ss.getItem(K);
    if (saved && !t.value.trim()) {
      // React-compatible setter
      var ns = Object.getOwnPropertyDescriptor(
        window.parent.HTMLTextAreaElement.prototype, 'value').set;
      ns.call(t, saved);
      t.dispatchEvent(new Event('input', {bubbles: true}));
    }
    t.addEventListener('input', function() {
      t.value.trim() ? ss.setItem(K, t.value) : ss.removeItem(K);
    });
  }, 200);
  setTimeout(function() { clearInterval(iv); }, 8000);
})();
```

---

### Skill 4：Supabase Edge Function 作為 LINE Webhook

完整的 LINE Bot 後端，不需要自己的伺服器

```typescript
// 關鍵：--no-verify-jwt 部署
// supabase functions deploy fn-name --no-verify-jwt

// HMAC-SHA256 簽名驗證
async function verifySignature(body, sig) {
  const key = await crypto.subtle.importKey("raw",
    new TextEncoder().encode(LINE_CHANNEL_SECRET),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const mac = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body));
  const expected = btoa(String.fromCharCode(...new Uint8Array(mac)));
  return expected === sig;
}

// 自動注入的 env：SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
// 手動設定的 Secrets：LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN, LINE_ADMIN_USER_ID
```

---

### Skill 5：LINE Rich Menu 自動建立腳本

一鍵建立圖文選單（含圖片生成），不需要進後台手動設定

核心步驟：
1. Pillow 生成背景圖（指定中文字型路徑）
2. POST `/v2/bot/richmenu` 建立結構
3. POST `/v2/bot/richmenu/{id}/content` 上傳圖片
4. POST `/v2/bot/user/all/richmenu/{id}` 設為預設

---

## 六、整體反思

### 做得好的地方
- **漸進式修復**：70+ bugs 分多輪修，每次 commit 後驗證，沒有一次大爆炸
- **防禦性設計**：所有 DB 函數都有錯誤處理，None/空值處理完整
- **顧客體驗優先**：localStorage 讓顧客幾乎不需要動腦，開網址就能繼續

### 如果重做會改什麼
- **DB 客戶端**：一開始就用 requests，不浪費時間在 supabase-py
- **Secrets 管理**：從一開始就告知所有敏感資料只能在終端輸入，不貼到聊天視窗
- **測試流程**：每個新功能應該先在本機 `streamlit run` 驗證再 push

### 這個專案的最大收穫

> 用 AI 協作開發的最大優勢不是「速度快」，  
> 而是「能夠同時照顧到功能、UX、安全、邊界情境」——  
> 這些在傳統一個人開發時很容易有一項被忽略。

---

*共修復 70+ bugs，新增 10+ 功能，歷時數週，合作愉快。*
