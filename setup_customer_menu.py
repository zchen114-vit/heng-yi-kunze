"""
顧客版圖文選單（LIFF）一鍵設定

這支腳本會：
  1. 產生一張顧客版選單底圖（兩格：開始問卦 / 我的回覆）
  2. 建立圖文選單，按鈕動作＝開啟你的 LIFF 網址（在 LINE 內直接開網頁、免密碼登入）
  3. 設為「所有好友的預設選單」
  4. （選填）若你輸入小老師自己的 LINE userId，會自動把原本的管理選單
     （名稱 "Admin Quick Menu"）重新綁定給你個人，這樣顧客看到顧客選單、
     你自己仍保留管理按鈕。

執行方式：
  pip install Pillow requests
  python setup_customer_menu.py

需要準備：
  - LINE Channel Access Token（Messaging API 頻道 → 取得）
  - LIFF ID（LINE Login 頻道 → LIFF → 建立後取得，格式如 1234567890-abcdEFGH）
  - （選填）小老師自己的 LINE userId（Uxxxxxxxx…）
"""
import os, sys
import requests

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("請先安裝 Pillow：pip install Pillow")
    sys.exit(1)

# ── 輸入 ──────────────────────────────────────────────────────────────────────
TOKEN = input("請貼上 LINE Channel Access Token：").strip()
LIFF_ID = input("請貼上 LIFF ID（例 1234567890-abcdEFGH）：").strip()
ADMIN_USER_ID = input("（選填）小老師自己的 LINE userId，沒有就直接按 Enter：").strip()

if not TOKEN or not LIFF_ID:
    print("❌ Token 與 LIFF ID 為必填")
    sys.exit(1)

LIFF_URL = f"https://liff.line.me/{LIFF_ID}"

CELLS = [
    ("開始問卦", "☯", "選分區・提出問題"),
    ("我的回覆", "📖", "查看小老師解卦"),
]

W, H = 2500, 843
BG   = (250, 243, 224)      # 米色（與網站同色系）
DIV  = (196, 146, 42)       # 金線
TEXT = (61, 43, 31)         # 深棕字
SUB  = (122, 92, 58)        # 副標題色
ICON_BG = (245, 230, 196)   # 圖示圓底

# ── 產生底圖 ──────────────────────────────────────────────────────────────────
img  = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

# 中央分隔線
draw.rectangle([W // 2 - 2, 80, W // 2 + 2, H - 80], fill=DIV)

font_paths = [
    "C:/Windows/Fonts/msjhbd.ttc",
    "C:/Windows/Fonts/msjh.ttc",
    "C:/Windows/Fonts/kaiu.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
]
font_big = font_mid = font_small = None
for fp in font_paths:
    if os.path.exists(fp):
        try:
            font_big   = ImageFont.truetype(fp, 130)
            font_mid   = ImageFont.truetype(fp, 90)
            font_small = ImageFont.truetype(fp, 52)
            print(f"使用字型：{fp}")
            break
        except Exception:
            pass
if font_big is None:
    print("⚠ 找不到中文字型，使用預設字型（文字可能不完整）")
    font_big = font_mid = font_small = ImageFont.load_default()

cell_w = W // 2
for i, (label, icon, sub) in enumerate(CELLS):
    cx = cell_w * i + cell_w // 2
    r = 105
    draw.ellipse([cx - r, H//2 - 170 - r, cx + r, H//2 - 170 + r], fill=ICON_BG)
    draw.text((cx, H//2 - 170), icon, fill=DIV, font=font_mid, anchor="mm")
    draw.text((cx, H//2 + 25),  label, fill=TEXT, font=font_big, anchor="mm")
    draw.text((cx, H//2 + 180), sub, fill=SUB, font=font_small, anchor="mm")

out_path = "customer_menu_bg.png"
img.save(out_path, "PNG")
print(f"圖片已建立：{out_path}")

# ── 建立顧客圖文選單 ──────────────────────────────────────────────────────────
hjson = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

menu_body = {
    "size": {"width": 2500, "height": 843},
    "selected": True,
    "name": "Customer LIFF Menu",
    "chatBarText": "☯ 點此問卦",
    "areas": [
        {"bounds": {"x": 0,    "y": 0, "width": 1250, "height": 843},
         "action": {"type": "uri", "uri": LIFF_URL}},
        {"bounds": {"x": 1250, "y": 0, "width": 1250, "height": 843},
         "action": {"type": "uri", "uri": LIFF_URL}},
    ],
}

r1 = requests.post("https://api.line.me/v2/bot/richmenu", json=menu_body, headers=hjson)
if r1.status_code != 200:
    print(f"❌ 建立選單失敗：{r1.text}")
    sys.exit(1)
menu_id = r1.json()["richMenuId"]
print(f"✅ 顧客選單建立：{menu_id}")

with open(out_path, "rb") as f:
    r2 = requests.post(
        f"https://api-data.line.me/v2/bot/richmenu/{menu_id}/content",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "image/png"},
        data=f.read(),
    )
if r2.status_code != 200:
    print(f"❌ 上傳圖片失敗：{r2.text}")
    sys.exit(1)
print("✅ 圖片上傳完成")

# 設為所有好友的預設選單
r3 = requests.post(
    f"https://api.line.me/v2/bot/user/all/richmenu/{menu_id}",
    headers={"Authorization": f"Bearer {TOKEN}"},
)
if r3.status_code != 200:
    print(f"❌ 設定預設失敗：{r3.text}")
    sys.exit(1)
print("✅ 已設為所有好友的預設圖文選單（顧客版）")

# ── 選填：把管理選單綁回小老師個人 ────────────────────────────────────────────
if ADMIN_USER_ID:
    lr = requests.get("https://api.line.me/v2/bot/richmenu/list", headers=hjson)
    admin_menu_id = None
    if lr.status_code == 200:
        for m in lr.json().get("richmenus", []):
            if m.get("name") == "Admin Quick Menu":
                admin_menu_id = m["richMenuId"]
                break
    if admin_menu_id:
        lk = requests.post(
            f"https://api.line.me/v2/bot/user/{ADMIN_USER_ID}/richmenu/{admin_menu_id}",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        if lk.status_code == 200:
            print(f"✅ 已將管理選單綁定給你個人（{ADMIN_USER_ID[:8]}…），顧客不受影響")
        else:
            print(f"⚠ 管理選單綁定失敗：{lk.text}")
    else:
        print("⚠ 找不到名為 'Admin Quick Menu' 的管理選單。")
        print("  你可以重新跑一次 setup_rich_menu.py 建立管理選單，")
        print("  再回來執行本腳本（輸入 userId）把它綁回你個人。")

print(f"\n顧客選單 ID（備用）：{menu_id}")
print(f"LIFF 網址：{LIFF_URL}")
print("\n完成！用手機 LINE 重新打開與 Bot 的對話，底部就會出現新的選單。")
