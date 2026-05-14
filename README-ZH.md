# Terminal Widget for Übersicht（繁體中文版）

把真正的終端機嵌進 macOS 桌面的 Übersicht widget。**vim、htop、ssh、tmux、fzf** 都能用，因為底層接的是 [ttyd](https://github.com/tsl0922/ttyd) + xterm.js。

> English version: [`README.md`](./README.md)

---

## 為什麼要這樣做

Übersicht widget 本質是一個 WebKit 頁面 — 它沒有內建終端機模擬器。直接把 PTY 輸出當文字流貼到畫面上，所有 ANSI 控制碼、游標移動、p10k 的繽紛 prompt 都會變成亂碼。

這個 widget 把終端機渲染交給 **ttyd**（內含 xterm.js 的小巧本地 web 終端伺服器），自己只負責提供「拖移／縮放／鎖定」的桌面外殼。終端模擬全部由業界標準工具處理。

```
┌─────────────────────────────────────────┐
│  Übersicht widget (index.jsx)           │
│  ┌──────────────────────────────────┐   │
│  │  <iframe src=localhost:7681>     │   │  ← xterm.js 前端
│  └───┬──────────────────────────────┘   │
└──────┼──────────────────────────────────┘
       │  WebSocket
       ▼
   ttyd ── 啟動 ──► /bin/zsh -i  ← 你真正的 shell
```

---

## 功能

- ✅ 完整互動式 shell — `vim`、`htop`、`ssh`、`tmux`、`fzf`、`less`、`watch` 全部正常
- ✅ Powerlevel10k / oh-my-zsh / Nerd Font 圖示正確顯示
- ✅ 上方 8 px 區拖移、右下角拖縮放
- ✅ **位置／大小／鎖定狀態自動記憶**（重開機也記得）
- ✅ **鎖定按鈕**：左下小鎖頭，鎖上後拖移／縮放／鍵盤輸入全部停用
- ✅ **多份獨立實例**（各自 port、各自 `.zshrc`、各自記憶）
- ✅ **內建簡潔 prompt + 招呼語 + 啟動自動執行指令**
- ✅ 隱藏 xterm scrollbar，桌面上看起來乾淨
- ✅ 只綁 `127.0.0.1`，外網絕對打不到

---

## 系統需求

| 軟體 | 安裝方式 |
|---|---|
| macOS | 內建 |
| [Übersicht](https://tracesof.net/uebersicht/) | App Store 或 `brew install --cask ubersicht` |
| [ttyd](https://github.com/tsl0922/ttyd) ≥ 1.7 | `brew install ttyd` |
| zsh（macOS 預設）| 已內建 |
| Nerd Font（選用，prompt 圖示用）| `brew install font-jetbrains-mono-nerd-font` |

---

## 安裝

### 方法 A — 互動安裝程式（推薦）

```bash
cd "/Users/<你>/Library/Application Support/Übersicht/widgets/terminal-widget.widget"
python3 install.py
```

互動流程會帶你完成：

1. 檢查 ttyd / Übersicht 是否就位
2. 詢問要建立幾個獨立的 widget 實例
3. 自動分配未被佔用的 port
4. 每份可選擇是否使用獨立的 `.zshrc`（ZDOTDIR）
5. 每份可自訂**招呼語**
6. 每份可設定**啟動自動執行的指令**（例：`tmux attach -t main`、`claude`）
7. 自動 patch 各份的 `index.jsx` + `zsh/.zshrc`，並通知 Übersicht refresh

### 方法 B — 手動

把整個 `terminal-widget.widget` 資料夾放到 `~/Library/Application Support/Übersicht/widgets/`，然後 Übersicht 選單列 → **Refresh All Widgets** 即可。

---

## 多實例設定

每份實例需要：(a) 獨立的 widget 資料夾、(b) 獨特的 port、(c) 可選的獨立 `.zshrc`。

`install.py` 會自動處理。手動的話：

```bash
# 1. 複製資料夾
cp -R terminal-widget.widget terminal-widget-work.widget

# 2. （選用）準備獨立 zsh 設定
mkdir -p ~/.config/widget-zsh-work
cp ~/.zshrc ~/.config/widget-zsh-work/.zshrc
# … 改成工作模式的設定

# 3. 編輯新複本的 index.jsx，最上方兩個常數改一下：
#       const TTYD_PORT = 7682;
#       const ZDOTDIR   = "/Users/scottchen/.config/widget-zsh-work";
```

Refresh Übersicht，桌面上就有第二個完全獨立的 zsh session。

---

## 鎖定功能

每個 widget 左下角有一個淡色小鎖頭按鈕：

- **平常半透明**，滑鼠移到 widget 上才浮現
- **點擊鎖上**：拖移條、縮放角隱藏，iframe 上鋪一層透明 veil 擋住所有滑鼠／鍵盤事件 → 整個視窗完全凍結
- **再點一次解鎖**：拖移／縮放／輸入全部恢復
- 鎖定狀態跟位置、大小一起寫進 localStorage，重開機後仍維持鎖定

---

## 檔案結構

```
terminal-widget.widget/
├── index.jsx              ← Übersicht widget：iframe + 拖縮 + 鎖定 + 持久化
├── bridge-tick.sh         ← 每個 poll 跑一次：確保 ttyd 在線
├── install.py             ← 互動安裝／實例克隆器
├── widget.json            ← Übersicht metadata
├── zsh/
│   ├── .zshenv            ← 阻擋 macOS 系統層 zsh rc 噪音
│   └── .zshrc             ← 內建簡潔 prompt + 招呼語 + AUTORUN（含中文註解）
├── README.md              ← English
└── README-ZH.md           ← 本檔
```

執行階段檔案：

- `/tmp/terminal-widget-ttyd-<port>.log` — 每個實例的 ttyd 標準錯誤
- `/tmp/terminal-widget-ttyd-<port>.lock` — 防 race 用的 lock 資料夾

---

## 可調整的設定點

### 1. `index.jsx`（widget 外殼）

```js
const TTYD_PORT = 7681;        // 此 widget 的 port，多開時要不同
const ZDOTDIR   = "";          // 留空 → 用內建 zsh/；填路徑 → 用該資料夾
```

最小尺寸：

```js
const MIN_W = 320;
const MIN_H = 180;
```

### 2. `zsh/.zshrc`（終端機體驗）

檔案內三個區塊都有中文註解，可直接編輯：

```bash
# 1. PROMPT — 提示字元樣式
PROMPT='%F{green}%2~%f %F{cyan}[zsh]%f %F{magenta}❯%f '

# 2. 招呼語 — 開啟時的歡迎文字
print -P "%F{cyan}Hi Scott — terminal ready.%f"

# 3. AUTORUN — 啟動自動執行的指令
WIDGET_AUTORUN=""
# 範例：
#   WIDGET_AUTORUN="cd ~/Documents/Coding-Project && ls"
#   WIDGET_AUTORUN="tmux attach -t main || tmux new -s main"
#   WIDGET_AUTORUN="claude"
```

改完後執行 `pkill -f 'ttyd -p 7681'`，下次 widget poll 會自動拉起新的 ttyd 套用新設定。

### 3. `bridge-tick.sh`（ttyd 啟動參數）

ttyd 的 xterm.js 樣式都用 `-t key=value` 帶入：

```bash
-t 'fontFamily=JetBrainsMono Nerd Font, JetBrains Mono, Menlo, monospace'
-t 'fontSize=13'
-t 'theme={"background":"#141418","foreground":"#d4d4d4","cursor":"#5fd7af"}'
-t 'cursorStyle=bar'
```

完整 xterm.js 選項：<https://xtermjs.org/docs/api/terminal/interfaces/iterminaloptions/>

---

## Troubleshooting（常見問題）

| 症狀 | 解法 |
|---|---|
| 一直停在 "starting ttyd…" | `cat /tmp/terminal-widget-ttyd-7681.log` 看錯誤；通常是 port 被佔用或 ttyd 沒裝 |
| widget 載入但 iframe 空白 | 再 refresh 一次；首次啟動 ttyd 約需 0.5 秒綁定 |
| Nerd Font 圖示變方框 | 安裝 Nerd Font 並修改 `bridge-tick.sh` 裡的 `fontFamily` |
| 兩個 widget 互相搶 shell | 它們用了同一個 port — 各自設不同 `TTYD_PORT` |
| Powerlevel10k 抱怨 instant prompt | 自帶 `.zshrc` 裡加 `POWERLEVEL9K_INSTANT_PROMPT=quiet` |
| 改了 zshrc 沒反應 | `pkill -f 'ttyd -p <port>'` 強制 ttyd 重啟，下次 widget poll 會自動拉起 |
| 想完全重置 widget 位置／大小 | Web Inspector Console 跑 `localStorage.removeItem('terminal-widget:7681')` 然後 refresh |

### 全部砍掉重來

```bash
pkill -f 'ttyd -p 768'                  # 殺掉 7680~7689 範圍所有 widget ttyd
rm -f /tmp/terminal-widget-ttyd-*       # 清 log 與 lock
```

---

## 安全考量

- ttyd 只綁 `127.0.0.1`（`-i 127.0.0.1`）— 區網其他機器絕對連不到
- localhost 不需要驗證 — 能在你 Mac 上開瀏覽器的人本來就能用你的帳號開 shell
- 如果你的 Mac 有多人共用，要再加一層保護的話：在 `bridge-tick.sh` 的 ttyd 指令加 `--credential user:password`

---

## 授權

MIT。ttyd 與 xterm.js 也是 MIT。
作者：Scott Chen
