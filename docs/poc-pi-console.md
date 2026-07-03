# PoC（路徑 A）：用 ttyd 把 Pi 包成桌面 agent console

這是可行性報告（`docs/pi-secondbrain-console-feasibility.md`）**路徑 A** 的最小可跑原型：
用本 repo 已驗證的 **ttyd + iframe** 手法，把 **Pi**（`@earendil-works/pi-coding-agent`）
包成一個桌面 console，working dir 指到你既有的 Second Brain（S.2ndbrain）vault。

目的：先在這個 Terminal Widget 上把 pattern 跑通、確認體感，之後**搬進 Commander
Center 的 console 標籤頁**取代自寫命令/log 面板。正式型態建議走**路徑 B**（Pi 的 web
UI 元件原生嵌入），見報告 §3。

> 原本的 zsh 終端 widget（`bridge-tick.sh` + `index.jsx`）完全不動，這是**新增**的獨立一條路。

---

## 前置需求

```bash
brew install ttyd                                              # 本 repo 既有需求
npm install -g --ignore-scripts @earendil-works/pi-coding-agent  # 安裝 Pi（或 curl -fsSL https://pi.dev/install.sh | sh）
export ANTHROPIC_API_KEY="..."                                # 或用 pi 內 /login、或 --provider/--model
```

- Second Brain 若是 Markdown vault，**不需要額外套件**：Pi 的 read/write/edit/bash 直接讀寫。
- 要語意搜尋再加 Pi 的 extension / package（Pi 的 MCP 非核心內建）。

---

## 1. 先在終端機直接驗證（不碰 widget）

```bash
# 語法：agent-bridge-tick.sh PORT [VAULT_DIR]
./agent-bridge-tick.sh 7690 "/Users/you/path/to/second-brain-vault"
```

它會：
1. 在 `127.0.0.1:7690` 起一個 ttyd，裡面 `cd` 進 vault 後跑 `pi`
2. 用 lockfile 防重複 spawn（沿用 `bridge-tick.sh` 手法）
3. 印出 health code 與 `{"port":7690,"agent":"pi"}`

用瀏覽器開 <http://127.0.0.1:7690> 就能看到 Pi 的 TUI，工作目錄即你的 Second Brain。
試著叫它「列出這個 vault 裡跟 X 有關的筆記並摘要」。

**首跑是唯讀的**（預設 `PI_FLAGS=--tools read,grep,find,ls`），安全。要讓 agent 能寫回筆記：

```bash
PI_FLAGS="" ./agent-bridge-tick.sh 7690 "/Users/you/path/to/vault"
```

停掉：

```bash
pkill -f 'ttyd -p 7690'
rm -rf /tmp/terminal-widget-agent-7690.*
```

---

## 2. 掛成一個桌面 widget instance（可選）

複製一份 widget 資料夾當「agent console」，把它的 `command` 指到本腳本。
在該複本的 `index.jsx` 頂部：

```js
const TTYD_PORT = 7690;   // 對到上面的 port
// 把原本呼叫 bridge-tick.sh 的 command 換成 agent-bridge-tick.sh：
//   export const command =
//     `'${WIDGET_DIR}/agent-bridge-tick.sh' ${TTYD_PORT} '/Users/you/path/to/vault'`;
```

Refresh All Widgets，桌面上就有一個常駐的 Pi agent console，背後是你的 Second Brain。

---

## 3. 搬進 Commander Center 的 console 標籤頁

- **快速版（路徑 A）**：console 標籤頁嵌一個 xterm.js/webview 終端，跑 `agent-bridge-tick.sh`
  起的 ttyd（或直接嵌 xterm.js 連該 ttyd）。vault/port/PI_FLAGS 由 Commander Center 設定帶入。
- **正式版（路徑 B，推薦）**：改用 Pi 的 **web UI 套件**原生嵌入——
  `@earendil-works/pi-web-ui`（web 元件）或 `@jmfederico/pi-web`（`pi-web install` → 服務於
  `127.0.0.1:8504`）。這樣就**不需要 ttyd**，UI 完全融入你的 app，且跨平台（含 Windows）。
- 兩者都務必綁 `127.0.0.1`。

---

## 檔案

- `agent-bridge-tick.sh` — 本 PoC 核心：ttyd → `pi`（cd 進 vault）。
- `bridge-tick.sh` — 原本的 zsh 版，未更動，供對照。
- `docs/pi-secondbrain-console-feasibility.md` — 完整可行性報告（含 zerostack vs Pi 選型）。

## 已知限制

- 這支腳本走 macOS 路徑（`/opt/homebrew/bin`、`/usr/sbin/lsof`），與本 repo 一致；
  **Windows 上請走路徑 B**（Pi 本身支援 Windows，但 ttyd 這層是 Unix）。
- Pi 旗標以官方 README 為準；本 PoC 只用到已驗證的 `--tools ...`。
- Pi 為 **MIT** 授權：打包散佈 Commander Center 無 copyleft 顧慮。
