import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const LINE_SECRET = Deno.env.get("LINE_CHANNEL_SECRET")!;
const LINE_TOKEN = Deno.env.get("LINE_CHANNEL_ACCESS_TOKEN")!;
const ADMIN_USER_ID = Deno.env.get("LINE_ADMIN_USER_ID")!;
const APP_URL = Deno.env.get("APP_URL") ?? "https://heng-yi-kunze.streamlit.app";

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

// ── Helpers ──────────────────────────────────────────────────────────────────

async function verifySignature(body: string, sig: string): Promise<boolean> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(LINE_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const mac = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body));
  const expected = btoa(String.fromCharCode(...new Uint8Array(mac)));
  return expected === sig;
}

async function pushLine(text: string) {
  await fetch("https://api.line.me/v2/bot/message/push", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${LINE_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      to: ADMIN_USER_ID,
      messages: [{ type: "text", text }],
    }),
  });
}

async function replyLine(replyToken: string, text: string) {
  await fetch("https://api.line.me/v2/bot/message/reply", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${LINE_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      replyToken,
      messages: [{ type: "text", text }],
    }),
  });
}

const VISITOR_REPLY = `您好！歡迎來到洞察易生的經歷 🌿

請點選下方選單的「☯ 開始問卦」，
即可直接在 LINE 裡填寫問題、查看小老師的解卦回覆，免註冊免密碼。

（若沒看到選單，請點輸入框旁的選單圖示展開）`;

function fmtTime(iso: string): string {
  const d = new Date(iso);
  const tw = new Date(d.getTime() + 8 * 3600_000);
  return tw.toISOString().replace("T", " ").slice(0, 16);
}

// ── Commands ─────────────────────────────────────────────────────────────────

async function cmdStats(): Promise<string> {
  const { data, error } = await supabase
    .from("sessions")
    .select("is_closed, created_at");
  if (error) return "❌ 無法取得統計資料";

  const now = new Date();
  const todayUtc8 = new Date(now.getTime() + 8 * 3600_000).toISOString().slice(0, 10);
  const total = data.filter((s: any) => !s.is_closed).length;
  const today = data.filter((s: any) =>
    !s.is_closed && s.created_at.slice(0, 10) === todayUtc8
  ).length;
  const archived = data.filter((s: any) => s.is_closed).length;

  return `📊 統計\n今日新增：${today}\n進行中：${total}\n已歸檔：${archived}`;
}

async function cmdPending(): Promise<string> {
  const { data, error } = await supabase
    .from("sessions")
    .select("session_id, customer_name, category, messages(role, created_at)")
    .eq("is_closed", false)
    .order("updated_at", { ascending: false })
    .limit(10);
  if (error) return "❌ 無法取得待辦清單";
  if (!data || data.length === 0) return "✅ 目前沒有進行中的問卦";

  const lines = data.map((s: any) => {
    const msgs: any[] = s.messages ?? [];
    const lastRole = msgs.length > 0 ? msgs[msgs.length - 1].role : null;
    const status = lastRole === "customer" || msgs.length === 0 ? "🔴待回" : "✅已回";
    return `${status} ${s.customer_name ?? "？"} [${s.session_id}]\n　${s.category}`;
  });
  return `📋 待辦（最新10筆）\n${lines.join("\n")}`;
}

async function cmdView(sid: string): Promise<string> {
  const { data: sess, error: e1 } = await supabase
    .from("sessions")
    .select("customer_name, category, preference, is_closed")
    .eq("session_id", sid)
    .single();
  if (e1 || !sess) return `❌ 找不到問卦 ${sid}`;

  const { data: msgs, error: e2 } = await supabase
    .from("messages")
    .select("role, content, created_at")
    .eq("session_id", sid)
    .order("created_at", { ascending: true })
    .limit(6);
  if (e2) return `❌ 無法讀取訊息`;

  const status = sess.is_closed ? "🗄️歸檔" : "🟢進行中";
  const lines = (msgs ?? []).map((m: any) => {
    const who = m.role === "customer" ? "問" : "答";
    return `[${who}] ${m.content.slice(0, 60)}${m.content.length > 60 ? "…" : ""}`;
  });
  return `📖 ${sess.customer_name ?? "？"} · ${sess.category} · ${status}\n密碼：${sess.preference ?? "未設定"}\n\n${lines.join("\n\n")}`;
}

async function cmdClose(sid: string): Promise<string> {
  const { error } = await supabase
    .from("sessions")
    .update({ is_closed: true, updated_at: new Date().toISOString() })
    .eq("session_id", sid)
    .eq("is_closed", false);
  if (error) return `❌ 結案失敗：${error.message}`;
  return `✅ ${sid} 已結案歸檔`;
}

async function cmdReply(sid: string, content: string): Promise<string> {
  const { data: sess, error: e1 } = await supabase
    .from("sessions")
    .select("session_id, is_closed, customer_name")
    .eq("session_id", sid)
    .single();
  if (e1 || !sess) return `❌ 找不到問卦 ${sid}`;
  if (sess.is_closed) return `❌ ${sid} 已歸檔，無法回覆`;

  const { error: e2 } = await supabase.from("messages").insert({
    session_id: sid,
    role: "consultant",
    content: content,
    created_at: new Date().toISOString(),
  });
  if (e2) return `❌ 儲存失敗：${e2.message}`;

  await supabase
    .from("sessions")
    .update({ updated_at: new Date().toISOString() })
    .eq("session_id", sid);

  return `✅ 已回覆給 ${sess.customer_name ?? sid}`;
}

const HELP = `📖 可用指令：
統計 → 查看各類統計
待辦 → 待回覆列表
[編號] 查詢 → 查看問卦內容
[編號] 結案 → 歸檔此問卦
[編號] [回覆內容] → 送出解讀

範例：
  統計
  AB12CD34 查詢
  AB12CD34 感情的走向是...`;

// ── Main handler ─────────────────────────────────────────────────────────────

serve(async (req) => {
  if (req.method !== "POST") return new Response("OK", { status: 200 });

  const sig = req.headers.get("x-line-signature") ?? "";
  const body = await req.text();

  if (!(await verifySignature(body, sig))) {
    return new Response("Unauthorized", { status: 401 });
  }

  const payload = JSON.parse(body);
  const events = payload.events ?? [];

  for (const evt of events) {
    if (evt.type !== "message" || evt.message?.type !== "text") continue;

    // Non-admin visitor → 若此 LINE 帳號有進行中問卦，把留言存進去並通知小老師
    if (evt.source?.userId !== ADMIN_USER_ID) {
      const uid = evt.source?.userId;
      let handled = false;
      if (uid) {
        const { data: sess } = await supabase
          .from("sessions")
          .select("session_id, customer_name, category")
          .eq("line_uid", uid)
          .eq("is_closed", false)
          .order("updated_at", { ascending: false })
          .limit(1)
          .maybeSingle();
        if (sess) {
          const text = (evt.message.text as string).trim();
          await supabase.from("messages").insert({
            session_id: sess.session_id,
            role: "customer",
            content: text,
            created_at: new Date().toISOString(),
          });
          await supabase
            .from("sessions")
            .update({ updated_at: new Date().toISOString() })
            .eq("session_id", sess.session_id);
          await pushLine(
            `【追加提問】\n姓名：${sess.customer_name ?? "？"}\n分區：${sess.category}\n編號：${sess.session_id}\n\n問題：\n${text.slice(0, 200)}`,
          );
          if (evt.replyToken) {
            await replyLine(
              evt.replyToken,
              "已收到您的提問 🌿 小老師會盡快為您解卦，可點下方選單「📖 我的回覆」查看進度。",
            );
          }
          handled = true;
        }
      }
      if (!handled && evt.replyToken) await replyLine(evt.replyToken, VISITOR_REPLY);
      continue;
    }

    const text = (evt.message.text as string).trim();
    let reply = "";

    if (text === "統計") {
      reply = await cmdStats();
    } else if (text === "待辦") {
      reply = await cmdPending();
    } else if (text === "說明" || text === "help" || text === "？" || text === "?") {
      reply = HELP;
    } else {
      // Expect: "{SID} {command or reply}"
      const spaceIdx = text.indexOf(" ");
      if (spaceIdx === -1) {
        reply = HELP;
      } else {
        const sid = text.slice(0, spaceIdx).toUpperCase();
        const rest = text.slice(spaceIdx + 1).trim();
        if (rest === "查詢") {
          reply = await cmdView(sid);
        } else if (rest === "結案") {
          reply = await cmdClose(sid);
        } else if (rest.length > 0) {
          reply = await cmdReply(sid, rest);
        } else {
          reply = HELP;
        }
      }
    }

    if (reply) await pushLine(reply);
  }

  return new Response("OK", { status: 200 });
});
