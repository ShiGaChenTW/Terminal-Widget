#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# PoC — 路徑 A：用 ttyd 把 zerostack agent 包成桌面 console
# ─────────────────────────────────────────────────────────────────────────────
# 這是 bridge-tick.sh 的「agent 版」：一模一樣的 ttyd + lockfile + health 手法，
# 差別只在把跑的東西從 `zsh` 換成 `zerostack`，並把 working dir 指到你的
# Second Brain vault（S.2ndbrain）。用來驗證「用 zerostack 取代自寫命令/log
# 面板」這條路，之後可直接搬進 Commander Center 的 console 標籤頁。
#
# 原本的 zsh 終端 widget 完全不受影響（那條路仍走 bridge-tick.sh）。
#
# 直接執行測試：
#   ./agent-bridge-tick.sh 7690 "/Users/me/vault"
#
# 用法：agent-bridge-tick.sh PORT [VAULT_DIR]
#   PORT      — ttyd 監聽的 port（PoC 建議用 7690 之類，避開 7681 的 zsh 版）
#   VAULT_DIR —（可選）Second Brain vault 路徑；有給就 cd 進去再跑 zerostack
#
# 可調環境變數：
#   ZS_BIN    — zerostack 執行檔路徑（預設找 /opt/homebrew/bin 或 PATH）
#   ZS_FLAGS  — 傳給 zerostack 的旗標（預設 "--read-only" 當安全首跑；
#               想讓 agent 能寫回 vault，改成 "" 或你要的權限旗標）
# ─────────────────────────────────────────────────────────────────────────────

set +e

PORT="${1:-7690}"
VAULT_DIR="${2:-}"
SCRIPT_DIR="$(cd "$(/usr/bin/dirname "$0")" && pwd)"
LOCK="/tmp/terminal-widget-agent-${PORT}.lock"
LOG="/tmp/terminal-widget-agent-${PORT}.log"
URL="http://127.0.0.1:${PORT}"
TTYD="/opt/homebrew/bin/ttyd"

# zerostack 執行檔：優先 Homebrew，再退回 PATH。
ZS_BIN="${ZS_BIN:-}"
if [ -z "$ZS_BIN" ]; then
  if [ -x "/opt/homebrew/bin/zerostack" ]; then
    ZS_BIN="/opt/homebrew/bin/zerostack"
  else
    ZS_BIN="$(command -v zerostack 2>/dev/null)"
  fi
fi

# 安全首跑預設唯讀；要讓 agent 寫回 Second Brain 時把它設成 ""。
ZS_FLAGS="${ZS_FLAGS---read-only}"

if ! /usr/sbin/lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  if /bin/mkdir "$LOCK" 2>/dev/null; then
    trap '/bin/rmdir "$LOCK" 2>/dev/null' EXIT

    # 組出要在 ttyd 裡跑的命令：（可選）先 cd 進 vault，再 exec zerostack。
    # 用 /bin/sh -c 當單一 argv 傳進去，vault 路徑含空白也安全。
    INNER="exec \"$ZS_BIN\" $ZS_FLAGS"
    if [ -n "$VAULT_DIR" ] && [ -d "$VAULT_DIR" ]; then
      INNER="cd \"$VAULT_DIR\" && $INNER"
    fi

    (
      exec /usr/bin/nohup "$TTYD" \
        -p "$PORT" \
        -i 127.0.0.1 \
        -W \
        -t 'fontFamily=JetBrainsMono Nerd Font, JetBrains Mono, Menlo, monospace' \
        -t 'fontSize=13' \
        -t 'theme={"background":"#141418","foreground":"#d4d4d4","cursor":"#5fd7af"}' \
        -t 'cursorStyle=bar' \
        -t 'rendererType=webgl' \
        /bin/sh -c "$INNER" \
        >"$LOG" 2>&1
    ) &
    /bin/sleep 0.6
  fi
fi

HEALTH=$(/usr/bin/curl -sf -o /dev/null -w '%{http_code}' "$URL/" 2>/dev/null || /bin/echo 000)
/bin/echo "$HEALTH"
/bin/echo "{\"port\":$PORT,\"agent\":\"zerostack\"}"
