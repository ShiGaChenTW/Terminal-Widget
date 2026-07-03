# 可行性評估報告：以 Pi agent 導入 S.2ndbrain，取代 Commander Center 的 console 標籤頁

> 研究主題：「研究 導入 S.2ndbrain 取代 console 的可能性」（agent 由 zerostack 改為 **Pi**）
> 日期：2026-07-02 ｜ 交付物：可行性評估報告
> 選型結論：**採用 Pi**（理由見 §1.1）

---

## 0. 情境定義（已與需求方確認）

| 名詞 | 定義 | 確認狀態 |
|---|---|---|
| **Pi** | [earendil-works/pi](https://github.com/earendil-works/pi)（前身 badlogic/pi-mono）：TypeScript / Node 寫的極簡 coding agent。系統提示 <1000 tokens、4 核心工具（read/write/edit/bash）+ skills/extensions/packages。**MIT 授權**、**官方列 Windows 支援**。核心 CLI 為終端程式；web UI 由**周邊套件**提供。 | 已查證官方 README |
| **S.2ndbrain** | 你**既有的** Second Brain 知識系統（假設為 Obsidian / Markdown vault）。 | 已確認 |
| **console（取代對象）** | **Commander Center 的 console 標籤頁**，目前是**你自寫的「命令 + log」面板**。 | 已確認 |
| **Commander Center** | **你自己掌控原始碼的 app**，console 是其中一個標籤頁。 | 已確認 |

**命題**：把 Commander Center 的自寫命令/log 面板換成 **Pi agent**，並讓它直接讀寫你既有的 Second Brain。

---

## 1. 結論先講（TL;DR）

**高度可行，且 Pi 比 zerostack 更適合這個案子。信心度 8.5/10。**

### 1.1 為何從 zerostack 改採 Pi（關鍵三點）

| 面向 | **Pi** ✅ | zerostack |
|---|---|---|
| **Windows / 跨平台** | ✅ 官方支援（Node 跨平台） | ⚠️ 未測試、不保證 |
| **授權** | ✅ **MIT**（可自由打包進 Commander Center 散佈） | GPL-3.0（copyleft，散佈要顧） |
| **Web UI** | ✅ 有周邊 web 套件（`@earendil-works/pi-web-ui`、`@jmfederico/pi-web`），可嵌進自家 app | ❌ 只有 TUI |
| runtime | Node（較重） | Rust binary（~16MB，極輕） |
| 擴充 | skills / extensions / pi packages（TypeScript） | MCP / subagents |

你的需求是「**嵌進自家 app 的 agent console、可能跨平台、將來要散佈**」——這三點正好是 Pi 相對 zerostack 的優勢，因此改採 Pi。唯一讓給 zerostack 的是極致輕量，但那不是本案的決定因素。

### 1.2 兩條落地路徑

- **路徑 A（PoC 先跑這條，最快）**：console 標籤頁嵌一個終端（xterm.js / 本 repo 的 ttyd），裡面跑 `pi` 的 TUI，working dir 指到 vault。指令已驗證、風險最低。
- **路徑 B（Pi 的真正優勢，最終型態）**：用 Pi 的 **web UI 套件**當 console 標籤頁——若 Commander Center 是 Electron/Tauri/web 殼，可**原生嵌入 web 元件**，不需要 ttyd 包終端。這是 zerostack 做不到的。

**建議**：路徑 A 驗證體感 → 路徑 B 收斂成正式的 console 標籤頁。

---

## 2. 為什麼「自寫命令/log 面板」值得換掉（同前結論）

你目前的 console 是「輸入命令 → 顯示 log」。你自己在 `SKILL.md` 已論證此設計的天花板：跑不動互動式程式、且**它本身不是 agent**（無規劃、工具、記憶、權限）。Pi 一次補齊——它是 agent（4 核心工具 + 可擴充），且有 web UI 套件能原生嵌入你的 app。

---

## 3. 兩條整合路徑（技術細節）

### 路徑 A — 嵌終端跑 `pi`（PoC 採用；已驗證指令）

```
Commander Center → console 標籤頁
  └─ <terminal>  (xterm.js / ttyd, 綁 127.0.0.1)
       └─ 執行: cd <vault> && pi          ← Pi 的 TUI 直接在裡面跑
                ├─ read/write/edit/bash → 直接讀寫 S.2ndbrain(Markdown)
                └─ 首跑唯讀: pi --tools read,grep,find,ls
```

- 已驗證指令（官方 README）：安裝 `npm i -g --ignore-scripts @earendil-works/pi-coding-agent`；跑 `pi`；唯讀 `pi --tools read,grep,find,ls`；provider `export ANTHROPIC_API_KEY=...`。
- 本 repo 的 `agent-bridge-tick.sh`（PoC）就是這條，可直接複用 ttyd + lockfile + health 手法。
- **跨平台注意**：ttyd 這層是 Unix/macOS；Windows 上請走路徑 B，或改用 xterm.js 直接連一個跑 pi 的 pty（見 §6）。

### 路徑 B — Pi 的 web UI 原生嵌入（最終型態）

Pi 生態有現成 web UI：
- `@jmfederico/pi-web`（社群，較完整）：`npm i -g @jmfederico/pi-web` → `pi-web install` → `pi-web doctor` → 服務於 `http://127.0.0.1:8504`。
- `@earendil-works/pi-web-ui`（earendil 官方 org 的 web 元件庫）：可當 React/web components 直接組進你的 app。

```
Commander Center (Electron/Tauri/web)
  └─ console 標籤頁
       └─ 直接嵌 Pi web 元件 / iframe pi-web(127.0.0.1)
            └─ Pi agent 後端 → S.2ndbrain
```

- **優點**：不需 ttyd 包終端；UI 可完全融入 Commander Center；跨平台（含 Windows）。
- **成本**：中——要把 web 元件整合進你的前端，或以子行程管理 pi-web server。
- ⚠️ `pi-web` 的確切 host-bind 旗標請於整合時以其官方為準（務必綁 `127.0.0.1`）。

---

## 4. S.2ndbrain 怎麼接（風險最低）

- **Markdown vault**：Pi 的核心工具 read/write/edit/bash **直接可讀寫**，把 working dir 指到 vault 即可，無需額外套件。
- **語意搜尋 / 結構化**：透過 Pi 的 **skills / extensions / pi packages**（TypeScript）加掛；Pi 對 MCP **非核心內建**，需以 extension 或第三方 package 整合（與 zerostack 直接內建 MCP 不同，這點要留意）。
- 建議以 **S.2ndbrain 為單一知識來源**，避免與 agent 自身記憶分裂。

---

## 5. 風險與緩解

| 風險 | 影響 | 緩解 |
|---|---|---|
| agent 執行破壞性 bash | 中–高 | 首跑 `pi --tools read,grep,find,ls`（唯讀）；正式使用再逐步開放 write/bash；重要操作要求先回述 |
| 敏感資料送雲端 LLM | 中 | 用本機模型 provider；或去識別化 |
| MCP 非核心內建 | 低–中 | 純 Markdown 用內建工具即可；要 MCP 走 extension/package，或評估是否真的需要 |
| Windows 上 `bash` 工具 | 中 | Pi 的 bash 工具在 Windows 需有 bash（Git Bash / WSL）；純 Markdown 讀寫用 read/write/edit 不受影響 |
| web UI 套件成熟度 | 低–中 | `@jmfederico/pi-web` 為社群專案；正式採用前評估維護狀態，或改用 earendil 官方 web 元件庫 |
| Node 依賴/版本 | 低 | web UI 需 Node 22+；以固定版本鎖定 |

> **授權**：Pi 為 **MIT** —— 打包進 Commander Center 散佈無 copyleft 顧慮（相對 zerostack 的 GPL-3.0 是一大加分）。

---

## 6. 落地路線

1. **Phase 0 — 盤點（0.5 天）**：列出 console 標籤頁現在做的事，決定哪些交給 Pi。
2. **Phase 1 — 本機驗證 Pi + Second Brain（0.5 天）**：`npm i -g --ignore-scripts @earendil-works/pi-coding-agent`；`export ANTHROPIC_API_KEY=...`；`cd <vault> && pi --tools read,grep,find,ls`，確認能查你的 Second Brain。
3. **Phase 2 — 路徑 A PoC（本 repo，已做）**：`agent-bridge-tick.sh` 用 ttyd 跑 pi，掛成桌面 widget，驗證體感。
4. **Phase 3 — 路徑 B 原生嵌入（1–3 天）**：把 Pi web 元件整合進 Commander Center 的 console 標籤頁；綁 `127.0.0.1`；vault/port/tools 由 app 設定帶入。
5. **Phase 4 — 退役舊面板**：新 console 穩定後移除自寫命令/log 面板。

---

## 7. 總結

- **採用 Pi、可行且推薦**：MIT + Windows 支援 + web UI 套件，正好對上「嵌進自家 app、可能跨平台、要散佈」三個需求。
- **PoC 走路徑 A**（ttyd 跑 `pi`，指令已驗證），最終型態走**路徑 B**（Pi web 元件原生嵌入 console 標籤頁）。
- **Second Brain 最好接**：Markdown 用 Pi 內建工具即可；要語意搜尋走 extension/package。
- **要留意**：Pi 的 MCP 非核心內建（走 extension）；Windows 上 bash 工具需 Git Bash/WSL；web UI 套件成熟度先評估。

---

## 參考來源

- [earendil-works/pi（GitHub）](https://github.com/earendil-works/pi) ／ 核心套件 [`@earendil-works/pi-coding-agent`](https://www.npmjs.com/package/@earendil-works/pi-coding-agent)
- [Pi coding agent README（安裝/用法）](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/README.md)
- Pi web UI：[`@jmfederico/pi-web`](https://github.com/jmfederico/pi-web) ／ [pi-web.dev](https://pi-web.dev/)
- Armin Ronacher：[Pi — The Minimal Agent Within OpenClaw](https://lucumr.pocoo.org/2026/1/31/pi/)
- 本 repo：`SKILL.md`（iframe-a-real-app）、`README.md`（ttyd + Übersicht）、`bridge-tick.sh`（ttyd 手法）
- 對照（未採用）：[gi-dellav/zerostack](https://github.com/gi-dellav/zerostack)（Rust、GPL-3.0、無 web UI、Windows 未測試）
