#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# PoC（路徑 B）：把 widget 直接 iframe Pi 的官方 web UI（pi-web），跳過 ttyd
# ─────────────────────────────────────────────────────────────────────────────
# 與 bridge-tick.sh / agent-bridge-tick.sh 不同：這支「不 spawn 任何東西」，
# 只是純健康探測。因為 Pi 的 web UI 由 `pi-web install` 裝成 per-user service，
# 會自己常駐（預設 http://127.0.0.1:8504）。widget 只需知道它有沒有活著，
# 活著就 iframe 它 —— 這正是 Commander Center console 標籤頁的最終型態雛形：
# 一個原生 web UI，不必再包一層終端。
#
# 一次性設定（使用者手動跑一次；不要放進 widget poll）：
#   npm install -g @jmfederico/pi-web      # 需 Node.js 22+
#   pi-web install                          # 裝成 per-user service
#   pi-web doctor                           # 檢查環境
#   # vault / host / port 於 ~/.config/pi-web/config.json 設定，務必綁 127.0.0.1
#
# 把 widget 指過來（複製一份 widget 資料夾後，改 index.jsx 頂部兩處）：
#   const TTYD_PORT = 8504;                 // 對到 pi-web 的 port
#   export const command = `'${WIDGET_DIR}/pi-web-tick.sh' ${TTYD_PORT}`;
#   // index.jsx 其餘不動：它本來就 iframe http://127.0.0.1:${TTYD_PORT}
#
# 直接執行測試：
#   ./pi-web-tick.sh 8504
#
# 用法：pi-web-tick.sh [PORT]
#   PORT — pi-web 監聽的 port（預設 8504）
# ─────────────────────────────────────────────────────────────────────────────

set +e

PORT="${1:-8504}"
URL="http://127.0.0.1:${PORT}"

# 純健康探測，不 spawn。第一行＝HTTP code（widget 判斷 == 200 才 iframe）。
# 不用 -f：讓 curl 回真實碼（200/500…）；連不上時 %{http_code} 給 000。
HEALTH=$(/usr/bin/curl -s -o /dev/null -w '%{http_code}' "$URL/" 2>/dev/null)
[ -z "$HEALTH" ] && HEALTH=000
/bin/echo "$HEALTH"
/bin/echo "{\"port\":$PORT,\"agent\":\"pi-web\"}"
