# PoC（路徑 A）：用 ttyd 把 zerostack 包成桌面 agent console

這是可行性報告（`docs/zerostack-secondbrain-console-feasibility.md`）**路徑 A** 的最小可跑原型：
用本 repo 已驗證的 **ttyd + iframe** 手法，把 `zerostack` agent 包成一個桌面 console，
working dir 指到你既有的 Second Brain（S.2ndbrain）vault。

目的：先在這個 Terminal Widget 上把 pattern 跑通、確認體感，之後**原樣搬進
Commander Center 的 console 標籤頁**取代那個自寫命令/log 面板。

> 原本的 zsh 終端 widget（`bridge-tick.sh` + `index.jsx`）完全不動，這是**新增**的獨立一條路。

---

## 前置需求

```bash
brew install ttyd zerostack        # ttyd 已是本 repo 需求；zerostack 為新增
```

設定 zerostack 的 LLM provider（擇一，依 zerostack 官方文件）：

```bash
export OPENROUTER_API_KEY="..."    # 預設 provider
# 或用本機模型，敏感資料不出機器：
#   讓 zerostack 走 Ollama provider（見 zerostack config.yaml）
```

（可選）若要語意搜尋你的 vault，在 zerostack 的 `~/.local/share/zerostack/config.yaml`
註冊一個 Obsidian MCP server。純 Markdown 讀寫的話，zerostack 內建 file 工具就夠，不必 MCP。

---

## 1. 先在終端機直接驗證（不碰 widget）

```bash
# 語法：agent-bridge-tick.sh PORT [VAULT_DIR]
./agent-bridge-tick.sh 7690 "/Users/you/path/to/second-brain-vault"
```

它會：
1. 在 `127.0.0.1:7690` 起一個 ttyd，裡面 `cd` 進 vault 後跑 `zerostack`
2. 用 lockfile 防重複 spawn（沿用 `bridge-tick.sh` 的手法）
3. 印出 health code 與 `{"port":7690,"agent":"zerostack"}`

用瀏覽器開 <http://127.0.0.1:7690> 就能看到 zerostack 的 TUI，且它的工作目錄
就是你的 Second Brain。試著叫它「列出這個 vault 裡跟 X 有關的筆記並摘要」。

**首跑是唯讀的**（預設 `ZS_FLAGS=--read-only`），安全。要讓 agent 能寫回筆記：

```bash
ZS_FLAGS="" ./agent-bridge-tick.sh 7690 "/Users/you/path/to/vault"
```

停掉：

```bash
pkill -f 'ttyd -p 7690'
rm -rf /tmp/terminal-widget-agent-7690.*
```

---

## 2. 掛成一個桌面 widget instance（可選）

複製一份 widget 資料夾當「agent console」，把它的 `command` 指到本腳本即可。
在該複本的 `index.jsx` 頂部改兩行：

```js
const TTYD_PORT = 7690;   // 對到上面的 port
// 把原本呼叫 bridge-tick.sh 的那行 command 換成 agent-bridge-tick.sh：
//   export const command =
//     `'${WIDGET_DIR}/agent-bridge-tick.sh' ${TTYD_PORT} '/Users/you/path/to/vault'`;
```

Refresh All Widgets，桌面上就有一個常駐的 zerostack agent console，背後是你的 Second Brain。

---

## 3. 搬進 Commander Center 的 console 標籤頁

PoC 驗證的就是 console 標籤頁要的東西。移植時：

- **console 標籤頁 = 一個 xterm.js / webview 終端**（取代自寫的命令/log 面板），
  裡面跑 `agent-bridge-tick.sh` 起的 ttyd（或直接在 Commander Center 內嵌 xterm.js 連 ttyd）。
- **vault 路徑**、**port**、**ZS_FLAGS** 由 Commander Center 的設定帶入。
- 綁 `127.0.0.1`、沿用 lockfile guard —— 安全與生命週期管理都已在腳本裡。
- 之後若想要非終端、完全自訂的 UI，再依報告 **路徑 B** 改用 zerostack 的 ACP
  （`zerostack --acp --acp-host 127.0.0.1 --acp-port 7243`）當後端。

---

## 檔案

- `agent-bridge-tick.sh` — 本 PoC 的核心：ttyd → zerostack（cd 進 vault）。
- `bridge-tick.sh` — 原本的 zsh 版，未更動，供對照。
- `docs/zerostack-secondbrain-console-feasibility.md` — 完整可行性報告。

## 已知限制

- 腳本走 macOS 路徑（`/opt/homebrew/bin`、`/usr/sbin/lsof`），與本 repo 一致。
- zerostack 的確切旗標以官方為準；本 PoC 只用到已確認的 `--read-only`，其餘權限
  模式（`guarded` 等）依 zerostack 版本用 `ZS_FLAGS` 或其 `config.yaml` 設定。
- zerostack 為 GPL-3.0：以獨立 process 呼叫自用無虞；要打包散佈 Commander Center
  前請先確認 copyleft 義務（見報告 §5）。
