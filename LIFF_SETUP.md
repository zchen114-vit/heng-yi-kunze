# LINE 顧客版（LIFF）設定指南

讓顧客直接在 LINE 裡開啟網頁問卦、用 LINE 身分**免密碼自動登入**，
並支援顧客在 LINE 對話框追問時自動通知小老師。

整體流程：顧客加好友 → 點底部圖文選單 → 在 LINE 內開啟網頁 → 自動帶出本人的問卦記錄。

---

## 一次性設定（共 5 步）

### 步驟一：建立 LINE Login 頻道 + LIFF App

> LIFF 需要的是「LINE Login 頻道」，跟你現有的「Messaging API 頻道」是不同類型，
> 但請建立在**同一個 Provider 底下**，這樣才能共用同一個官方帳號。

1. 進入 [LINE Developers Console](https://developers.line.biz/)
2. 選擇你現有的 Provider（跟 Messaging API 同一個）
3. 點 **Create a new channel** → 選 **LINE Login**
   - App name：洞察易生的經歷（或任意）
   - 其餘照預設填完建立
4. 進入剛建立的 LINE Login 頻道 → **LIFF** 分頁 → **Add**
   - **LIFF app name**：問卦
   - **Size**：**Full**（全螢幕）
   - **Endpoint URL**：你的網站網址，例如
     `https://heng-yi-kunze.streamlit.app`
   - **Scope**：勾選 **profile**（必須，才能取得 userId 與名稱）
   - **Bot link feature**：On（建議，加 LIFF 時順便加官方帳號好友）
5. 建立後會得到一個 **LIFF ID**，格式像 `1234567890-abcdEFGH`，複製起來。

### 步驟二：把 LIFF ID 加進網站 Secrets

在 Streamlit Cloud → 你的 App → **Settings → Secrets**，新增一行：

```toml
liff_id = "1234567890-abcdEFGH"
```

> 本機測試的話，加到 `.streamlit/secrets.toml`（此檔已被 gitignore，不會上傳）。
> **沒有設定 `liff_id` 時，LIFF 功能整段停用，網站行為跟原本完全一樣**，不會影響現有顧客。

### 步驟三：資料庫加一個欄位（重要，務必執行）

到 Supabase → **SQL Editor**，貼上並執行：

```sql
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS line_uid text;
CREATE INDEX IF NOT EXISTS idx_sessions_line_uid ON sessions (line_uid);
```

這個欄位用來記錄「這筆問卦是哪個 LINE 帳號送的」，是免密碼自動登入與
LINE 追問通知的關鍵。

> 沒跑這步也不會壞（程式會自動略過），但自動登入與 LINE 追問通知會失效。

### 步驟四：建立顧客版圖文選單

在本機（裝有 Python）執行：

```bash
pip install Pillow requests
python setup_customer_menu.py
```

依提示輸入：
- **LINE Channel Access Token**（Messaging API 頻道取得）
- **LIFF ID**（步驟一取得）
- **小老師自己的 LINE userId**（選填）—— 有填的話，腳本會把原本的管理選單
  重新綁定給你個人，這樣**顧客看到顧客選單、你自己仍保留管理按鈕**。

執行成功後，用手機 LINE 重新打開與 Bot 的對話，底部就會出現
「☯ 開始問卦 / 📖 我的回覆」選單。

### 步驟五（選填）：重新部署 webhook

LINE 追問通知的邏輯在 Edge Function 裡，若你想啟用「顧客在 LINE 對話框
直接打字追問 → 自動存進對話並通知小老師」，重新部署一次：

```bash
supabase functions deploy line-webhook
```

> 此功能依賴步驟三的 `line_uid` 欄位。

---

## 完成後的顧客體驗

1. 顧客加官方帳號好友 → 看到底部選單。
2. 點「☯ 開始問卦」→ 在 LINE 內開啟網頁，**自動以 LINE 身分登入**：
   - 有進行中的問卦 → 直接進入該對話看回覆。
   - 沒有 → 進首頁選分區提問，**姓名自動帶入 LINE 名稱、免設密碼**。
3. 小老師回覆後，顧客點「📖 我的回覆」即可看到，不必記任何密碼。
4. 顧客若直接在 LINE 對話框打字追問 → 自動存入該問卦並推播通知小老師。

---

## 故障排除

- **點選單沒反應 / 開啟空白**：確認 LIFF 的 Endpoint URL 與網站網址完全一致
  （含 https、結尾不要多斜線差異）。
- **沒有自動登入、仍要求輸入密碼**：多半是步驟三的 `line_uid` 欄位沒建立，
  或步驟二的 `liff_id` 沒設定。
- **顧客在 LINE 打字追問沒通知**：確認步驟五已重新部署，且步驟三欄位已建立。
- **顧客看到的是管理選單（統計/待辦）**：重跑 `setup_customer_menu.py`，
  它會把顧客選單設為預設；若要保留自己的管理選單，記得輸入你的 userId。
- **一般瀏覽器（非 LINE）打開網站**：完全照舊，不會被要求 LINE 登入。
