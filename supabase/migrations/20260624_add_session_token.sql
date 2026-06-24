-- 為每筆 session 加一個猜不到的隨機 token，當作「回來查看」的唯一鑰匙。
-- 取代原本用 ?sid= / ?email= / ?line_uid= 帶身分（那些可被任何人手打網址偽造）。
alter table sessions add column if not exists token text;
create index if not exists idx_sessions_token on sessions(token);
