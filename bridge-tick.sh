#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Übersicht Terminal Widget — 每次 widget poll 時呼叫的啟動腳本
# ─────────────────────────────────────────────────────────────────────────────
# 它做的事：
#   1. 檢查 ttyd 是否已經在指定 port 跑了，如果還沒就啟動它
#   2. 用 lockfile 防止多個 poll 同時 spawn（避免重複啟動）
#   3. 回傳 health code + JSON 給 widget，讓畫面知道 ttyd 是否就緒
#
# 一般情況下不用動這個檔案，只要在 install.py 或 zsh/.zshrc 裡調整即可。
#
# 直接執行測試：
#   ./bridge-tick.sh 7681
#   ./bridge-tick.sh 7682 /Users/me/.config/another-zsh
#
# 用法：bridge-tick.sh PORT [ZDOTDIR]
#   PORT     — ttyd 監聽的 port（如 7681）
#   ZDOTDIR  — （可選）替代 .zshrc 所在的資料夾。空字串時自動使用同層的 zsh/。

set +e

PORT="${1:-7681}"
ZDOTDIR_OVERRIDE="${2:-}"
SCRIPT_DIR="$(cd "$(/usr/bin/dirname "$0")" && pwd)"
LOCK="/tmp/terminal-widget-ttyd-${PORT}.lock"
LOG="/tmp/terminal-widget-ttyd-${PORT}.log"
URL="http://127.0.0.1:${PORT}"
TTYD="/opt/homebrew/bin/ttyd"
SHELL_BIN="/bin/zsh"

# When no ZDOTDIR is passed in, fall back to the bundled minimal config in
# this widget's `zsh/` folder (clean greeting + simple two-level prompt).
if [ -z "$ZDOTDIR_OVERRIDE" ] && [ -d "$SCRIPT_DIR/zsh" ]; then
  ZDOTDIR_OVERRIDE="$SCRIPT_DIR/zsh"
fi

if ! /usr/sbin/lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  if /bin/mkdir "$LOCK" 2>/dev/null; then
    trap '/bin/rmdir "$LOCK" 2>/dev/null' EXIT

    # Export ZDOTDIR in a subshell so the path is passed cleanly even when it
    # contains spaces (the widgets directory is `Application Support/…`).
    (
      if [ -n "$ZDOTDIR_OVERRIDE" ] && [ -d "$ZDOTDIR_OVERRIDE" ]; then
        export ZDOTDIR="$ZDOTDIR_OVERRIDE"
      fi
      exec /usr/bin/nohup "$TTYD" \
        -p "$PORT" \
        -i 127.0.0.1 \
        -W \
        -t 'fontFamily=JetBrainsMono Nerd Font, JetBrains Mono, Menlo, monospace' \
        -t 'fontSize=13' \
        -t 'theme={"background":"#141418","foreground":"#d4d4d4","cursor":"#5fd7af"}' \
        -t 'cursorStyle=bar' \
        -t 'rendererType=webgl' \
        "$SHELL_BIN" -i \
        >"$LOG" 2>&1
    ) &
    /bin/sleep 0.6
  fi
fi

HEALTH=$(/usr/bin/curl -sf -o /dev/null -w '%{http_code}' "$URL/" 2>/dev/null || /bin/echo 000)
/bin/echo "$HEALTH"
/bin/echo "{\"port\":$PORT}"
