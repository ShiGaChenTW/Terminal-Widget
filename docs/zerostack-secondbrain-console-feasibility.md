# 可行性評估報告：以 zerostack 導入 S.2ndbrain，取代 Commander Center 的 console 標籤頁

> 研究主題：「研究 zerostack 導入 S.2ndbrain 取代 console 的可能性」
> 日期：2026-07-01 ｜ 交付物：可行性評估報告（不改動現有程式）

---

## 0. 情境定義（已與需求方確認）

| 名詞 | 定義 | 確認狀態 |
|---|---|---|
| **zerostack** | [gi-dellav/zerostack](https://github.com/gi-dellav/zerostack)：Rust 極簡 coding agent。~26MB binary、~16MB RAM、多 LLM provider、內建 git-worktree / MCP / subagents / loop / memory / **ACP（stdio 或 TCP）**。只有 CLI/TUI，**無 web UI**。GPL-3.0-only。 | 已查證 |
| **S.2ndbrain** | 你**既有的** Second Brain 知識系統（假設為 Obsidian / Markdown vault）。 | 你已確認「我已有的」 |
| **console（取代對象）** | **Commander Center 的 console 標籤頁**，目前是一個**你自寫的「命令輸入 + log 輸出」面板**。 | 你已確認 |
| **Commander Center** | **你自己掌控原始碼的 app**，console 只是其中一個標籤頁。 | 你已確認 |

**命題**：把 Commander Center 裡「自寫的命令/log 面板」換掉，改由 **zerostack 當這個標籤頁的引擎**，並讓它直接讀寫你既有的 Second Brain。

---

## 1. 結論先講（TL;DR）

**高度可行，而且方向正確——這是本案最有利的組合。** 三個理由：

1. **你掌控 Commander Center 原始碼** → 換掉單一標籤頁的實作沒有外部相依阻力。
2. **要取代的只是「自寫命令/log 面板」** → 這正是你自己 `SKILL.md` 裡點名的反模式（把互動程式當成 flat text stream 來 render，會garble、跑不動 vim/htop/互動式 agent）。用 zerostack 取代它，等於順著你既有的結論走。
3. **zerostack 有兩條乾淨的接入路徑**（見 §3），且 Second Brain 這塊用 file 工具或 Obsidian MCP 就能接，是全案風險最低的部分。

**唯一需要認真對待的事**：zerostack 是 **GPL-3.0**。以「獨立 process（CLI/ACP 呼叫）」方式整合通常屬於 aggregation、風險低；但若你要把它 bundle 進 Commander Center 一起散佈，需先釐清授權（見 §5）。

**信心度**：8.5/10。

---

## 2. 為什麼「自寫命令/log 面板」值得換掉

你目前的 console 標籤頁是「輸入一行命令 → 顯示 log」。這種設計的天花板，你在 `SKILL.md` 裡已經踩過並寫下來了：

- **無法跑真正的互動程式**：vim、htop、tmux、fzf、甚至互動式 AI agent 的 TUI，都需要一個能解讀 ANSI/CSI/OSC、alt-screen、游標移動的**終端模擬器**。純命令/log 面板沒有，輸出會變 glyph soup。
- **不是 agent**：它只是把字串丟給 shell 再收回來，沒有 LLM 規劃、工具呼叫、記憶、權限控管。

zerostack 一次補齊這兩件事：它**本身就是一個 agent**（會規劃、呼叫工具、有權限模式與記憶），而它的 TUI 若跑在真正的終端模擬器裡（見路徑 A），vim/htop 那類也順帶解決。

---

## 3. 兩條整合路徑（依 Commander Center 技術棧擇一）

### 路徑 A — 嵌入真終端跑 zerostack（**最穩、最快、最貼合本 repo 的既有結論**）

在 console 標籤頁裡放一個**真正的終端模擬器**（xterm.js；或沿用本 repo 驗證過的 **ttyd + iframe** pattern），裡面直接跑 `zerostack`。

```
Commander Center
└─ console 標籤頁
   └─ <terminal>  (xterm.js / ttyd iframe, 綁 127.0.0.1)
        └─ 執行: zerostack        ← agent TUI 直接在裡面跑
                 ├─ 內建 file 工具 / Obsidian MCP → S.2ndbrain
                 └─ 權限模式 guarded、Ollama 可走本機
```

- **優點**：零終端模擬程式碼（交給 xterm.js）；vim/htop/互動式一次到位；本 repo 的 `SKILL.md` + Terminal Widget 已經證明這條路可行，可直接抄。
- **適用**：Commander Center 是 Electron / Tauri（webview）/ 任何能塞 web 元件的殼。
- **成本**：低。若是 web 殼，等於把本 repo 的 iframe-ttyd 手法搬過去。

### 路徑 B — ACP 原生後端，保留你自訂的 UI

zerostack 支援 **ACP（Agent Communication Protocol）**，可用 stdio 或 TCP 起服務：

```bash
zerostack --acp --acp-host 127.0.0.1 --acp-port 7243
```

Commander Center 的 console 標籤頁改成 **ACP client**，把使用者輸入送給 zerostack、把 agent 的串流回覆/工具呼叫渲染成你自己的 UI（就像 Zed 把 agent 當後端那樣）。

- **優點**：UI 完全由你掌控（可保留現有排版/樣式），不受限於終端外觀；互動更「原生」。
- **缺點**：要實作 ACP client 協定對接，工程量比路徑 A 高；且要處理 process 生命週期。
- **適用**：你想要精緻、非終端外觀的 agent 面板時。

> **建議**：先走 **路徑 A** 落地驗證體感（1–2 天內可見），確定 zerostack + Second Brain 的工作流對味後，若對外觀有更高要求，再投資 **路徑 B**。

---

## 4. S.2ndbrain 怎麼接（風險最低的一塊）

- **若 Second Brain 是 Markdown 檔案樹**：zerostack **內建的 file 工具（read/write/edit/grep/find_files）已足夠**直接讀寫，連 MCP 都不必。只要啟動 zerostack 時把 working dir 指到 vault，或在 prompt/`AGENTS.md` 告訴它 vault 路徑。
- **要語意搜尋 / 雙向連結 / 結構化查詢**：加掛一個 Obsidian MCP server（生態成熟，如 [Open Second Brain](https://mcpserver.space/mcp/open-second-brain/)、kazuph、MarkusPfundstein 等），在 zerostack 的 `config.yaml` 註冊即可。
- **與 zerostack 自身 memory 的關係**：zerostack 有 `memory` feature（`$XDG_DATA_HOME/zerostack/agent/memory/`）。建議**以 S.2ndbrain 為主記憶**，zerostack memory 只當短期 scratch，避免兩套知識庫分裂。

---

## 5. 風險與緩解

| 風險 | 影響 | 緩解 |
|---|---|---|
| **GPL-3.0 授權** | 中 | 以獨立 process（路徑 A 的 CLI、路徑 B 的 ACP over TCP）呼叫 → 一般視為 aggregation，風險低。**若要 bundle zerostack binary 一起散佈 Commander Center，需先確認 copyleft 義務。** 個人自用無虞 |
| agent 執行破壞性命令 | 中–高 | 預設 `guarded` 或 `readonly`；破壞性操作二次確認；per-tool glob 白名單；doom-loop 偵測已內建 |
| 敏感資料送雲端 LLM | 中 | 用 Ollama 本機 provider；或去識別化後再送 |
| zerostack process 生命週期（殘留、殭屍） | 低–中 | 路徑 A 沿用本 repo 的 lockfile + port-binding 檢查（`SKILL.md` 已有解法）；路徑 B 由 Commander Center 管理子行程 |
| loop/worktree 尚為實驗性 | 低 | 這些是選配功能，初期不啟用即可 |
| 覆蓋不了原本 log 面板的「即時 tail」 | 低 | 若 console 標籤頁原本也負責看即時 log，agent 不擅長被動即時 tail；可保留一個小 log pane，agent 面板與 log 面板並存 |

---

## 6. 落地路線（路徑 A 為主）

1. **Phase 0 — 盤點（0.5 天）**：列出 console 標籤頁現在被用來做的事（下命令？看 log？兩者？），確認哪些要交給 agent、哪些保留。
2. **Phase 1 — 本機起 zerostack + 接 Second Brain（0.5 天）**：`brew install zerostack`；working dir 指到 vault（或註冊 Obsidian MCP）；先在一般終端跑 `zerostack --read-only` 驗證能查你的 Second Brain。
3. **Phase 2 — 嵌入 console 標籤頁（1–2 天）**：在標籤頁放 xterm.js/ttyd，跑 zerostack；綁 `127.0.0.1`；套用 lockfile guard。權限設 `guarded`。
4. **Phase 3 — 收斂 UI 與工作流（1–2 天）**：調整字型/主題（沿用本 repo `bridge-tick.sh` 的 ttyd `-t` 主題參數作法）；把常用操作寫成 zerostack 自訂 prompt（`$XDG_CONFIG_HOME/zerostack/`）。
5. **Phase 4（選配）— 升級到 ACP 原生 UI**：若要非終端外觀，改實作 ACP client（路徑 B）。
6. **Phase 5 — 退役舊面板**：新面板穩定後移除自寫命令/log 面板的舊程式碼。

---

## 7. 總結

- **可行且推薦。** 你掌控 Commander Center 原始碼、要換的又只是單一「自寫命令/log 面板」，阻力最小。
- **方向與你既有的結論一致**：`SKILL.md` 已論證「別自寫 flat 面板、要嵌入真 app」；用 zerostack 取代 console 標籤頁正是這條路的自然延伸——而且升級成了「有 agent 大腦」的版本。
- **最省事路徑**：路徑 A（xterm.js/ttyd 跑 zerostack），幾乎可直接複用本 repo 的 Terminal Widget 手法；要精緻 UI 再走路徑 B（ACP）。
- **Second Brain 最好接**：Markdown vault 用內建 file 工具即可，語意搜尋再加 Obsidian MCP；以 S.2ndbrain 為主記憶。
- **唯一要先想清楚的**：GPL-3.0 的散佈義務——自用無虞，要打包散佈 Commander Center 前先確認。

---

## 參考來源

- [gi-dellav/zerostack（GitHub）](https://github.com/gi-dellav/zerostack) ／ [官網](https://gi-dellav.github.io/zerostack/)
- [Open Second Brain — MCP Server](https://mcpserver.space/mcp/open-second-brain/)
- [obsidian-second-brain（跨 CLI skill）](https://github.com/eugeniughelbur/obsidian-second-brain)
- [Build an AI Second Brain with Claude Code + Obsidian](https://www.mindstudio.ai/blog/build-ai-second-brain-claude-code-obsidian)
- 本 repo：`SKILL.md`（iframe-a-real-app、五大除錯陷阱）、`README.md`（ttyd + Übersicht 架構）、`bridge-tick.sh`（ttyd 主題/lockfile 手法）、`scripts/bootstrap.sh`（工具中立初始化）
