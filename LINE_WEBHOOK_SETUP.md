# LINE 遠端回覆功能設定指南

管理員可透過 LINE 傳送指令，直接回覆顧客、查看統計、結案歸檔。

---

## 可用指令

| 傳送內容 | 功能 |
|---------|------|
| `統計` | 查看今日新增、進行中、已歸檔筆數 |
| `待辦` | 列出最新 10 筆進行中問卦（含狀態） |
| `說明` | 顯示指令說明 |
| `[編號] 查詢` | 查看該問卦內容（最近 6 則對話） |
| `[編號] 結案` | 歸檔該問卦 |
| `[編號] [回覆內容]` | 儲存解讀回覆（顧客在網頁上即可看到） |

**範例：**
```
統計
AB12CD34 查詢
AB12CD34 這是您的解讀：坤卦第二爻…
AB12CD34 結案
```

---

## 設定步驟（共 4 步）

### 步驟一：確認 Supabase 資料表

`messages` 表需有以下欄位（應已存在）：
- `session_id` (text)
- `role` (text)
- `content` (text)
- `created_at` (timestamptz)

### 步驟二：部署 Supabase Edge Function

1. 安裝 Supabase CLI：[supabase.com/docs/guides/cli](https://supabase.com/docs/guides/cli)

2. 登入並連結專案：
   ```bash
   supabase login
   supabase link --project-ref YOUR_PROJECT_REF
   ```

3. 部署 Edge Function：
   ```bash
   supabase functions deploy line-webhook
   ```

4. 設定 Secrets（在 Supabase Dashboard → Edge Functions → Secrets，或用 CLI）：
   ```bash
   supabase secrets set LINE_CHANNEL_SECRET=你的LINE頻道密鑰
   supabase secrets set LINE_CHANNEL_ACCESS_TOKEN=你的LINE存取金鑰
   supabase secrets set LINE_ADMIN_USER_ID=你的LINE用戶ID
   ```

   > `SUPABASE_URL` 和 `SUPABASE_SERVICE_ROLE_KEY` 由 Supabase 自動注入，不需手動設定。

5. 記下 Edge Function 的 URL（格式如下）：
   ```
   https://YOUR_PROJECT_REF.supabase.co/functions/v1/line-webhook
   ```

### 步驟三：設定 LINE Messaging API Webhook

1. 進入 [LINE Developers Console](https://developers.line.biz/)
2. 選擇您的 Messaging API 頻道
3. 在「Messaging API」→「Webhook settings」中：
   - 填入 Webhook URL（步驟二取得的 Edge Function URL）
   - 點擊「Verify」確認連線成功
   - 開啟「Use webhook」

### 步驟四：取得您的 LINE User ID

在 LINE Developers Console → 「Messaging API」→「Bot information」頁面，
或傳送任意訊息給 Bot，在 Supabase Edge Function 的 Logs 中找到 `userId`。

將取得的 userId 填入 `LINE_ADMIN_USER_ID` Secret。

---

## 安全說明

- 僅接受來自 `LINE_ADMIN_USER_ID` 的指令，其他人的訊息一律忽略
- 所有請求均驗證 LINE HMAC-SHA256 簽名
- 使用 `SUPABASE_SERVICE_ROLE_KEY`（只在 Edge Function 後端使用，不對外暴露）

---

## 故障排除

- **收不到回覆**：確認 `LINE_ADMIN_USER_ID` 正確（不是 `@id`，是純數字 userId）
- **Webhook 驗證失敗**：確認 `LINE_CHANNEL_SECRET` 正確
- **「找不到問卦」**：問卦編號區分大小寫，請使用全大寫（Edge Function 已自動轉大寫）
- **Edge Function Logs**：Supabase Dashboard → Edge Functions → line-webhook → Logs
