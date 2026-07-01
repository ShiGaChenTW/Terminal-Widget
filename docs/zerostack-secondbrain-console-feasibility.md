# 可行性評估報告：以 zerostack 導入 S.2ndbrain 取代 web console

> 研究主題：「研究 zerostack 導入 S.2ndbrain 取代 console 的可能性」
> 日期：2026-07-01 ｜ 交付物：可行性評估報告（不改動現有程式）

---

## 0. 名詞定義與假設（先對齊）

| 名詞 | 本報告採用的定義 | 來源 / 確認 |
|---|---|---|
| **zerostack** | [gi-dellav/zerostack](https://github.com/gi-dellav/zerostack)：Rust 寫的極簡 coding agent。~26MB binary、~16MB RAM、多 LLM provider、內建 git-worktree / MCP / subagents / loop / memory / ACP。**只有 CLI/TUI，沒有內建 web UI。** GPL-3.0。 | 已查證官方 repo |
| **S.2ndbrain** | 你**既有的** Second Brain 知識系統（本報告假設為 Obsidian vault 型態的 Markdown 知識庫；若為其他載體，見 §6 的前提判斷）。 | 你已確認「我已有的 Second Brain 系統」 |
| **console** | 你目前使用的**某個 web／管理後台 console**（GUI、瀏覽器操作）。 | 你已確認「某個 web/管理後台 console」 |

**命題拆解**：把一個「用瀏覽器點按的 web 管理後台」，改成「在終端機用自然語言驅動的 zerostack agent，並讓它直接讀寫你既有的 Second Brain」。也就是 **從 GUI 操作模式 → agent + MCP 操作模式** 的轉換。

> ⚠️ 有一個關鍵事實你需要在讀下去之前知道：**zerostack 不提供 web 介面。** 所以它不可能是「另一個網頁後台」的 1:1 替換。它替換的是**操作方式**（點按 → 對話），而非「換一個網站」。這會直接決定下方的結論。

---

## 1. 結論先講（TL;DR）

**技術上可行，但不是「換一個後台網站」，而是「換一種操作範式」。可行程度取決於一個前提：你那個 web console 底層有沒有 API / CLI / 可被包成 MCP 的介面。**

- ✅ **可行**：若該 console 的功能背後有 REST API / CLI / DB，可以包成 MCP server 或直接讓 agent 呼叫 → zerostack 就能用自然語言完成原本要點按的操作，並同時查／寫你的 Second Brain。
- ⚠️ **有條件**：若 console 是純前端、沒有可程式化介面、或含大量圖形化儀表板（趨勢圖、拖拉排版、即時監控），agent 無法「取代」這些視覺互動，只能取代其中「查詢／異動／批次操作」的部分。
- ❌ **不建議直接取代**：若該 console 涉及多人協作、RBAC 權限稽核、法遵留痕、對外服務 → 單機、單人、非確定性的 LLM agent 不是合適替代品（見 §5 風險）。

**建議路線**：不要一步到位「取代」，而是先做**旁路（augment）**——讓 zerostack 成為 console 的「第二種入口」，接上 Second Brain，跑 1–2 個月覆蓋你 80% 的日常操作後，再決定是否退役 console。

**信心度**：架構可行性高（8/10）；「完全取代」可行性中等（5/10，強烈取決於 §6 前提）。

---

## 2. 三方能力盤點

### 2.1 zerostack 能做什麼 / 不能做什麼

| 面向 | 能力 | 對「取代 console」的意義 |
|---|---|---|
| 介面 | Crossterm TUI、slash commands（`/model` `/mode` `/worktree` `/loop` `/queue` …）、一次性 `-p "..."`、headless `--loop` | 操作是**對話式**，非表單/儀表板 |
| Web UI | **無** | 無法直接呈現圖表、看板、即時監控 |
| 外部整合 | **MCP server 支援**（gated feature）→ 可掛任意 MCP 工具 | ✅ 這是接 console 後端與 Second Brain 的關鍵 |
| 編輯器整合 | **ACP**（Agent Communication Protocol），stdio 或 TCP（`--acp --acp-host --acp-port`） | 可被 Zed 等前端當後端 agent 掛載 |
| 記憶 | `memory` feature：跨 session 的 Markdown 筆記於 `$XDG_DATA_HOME/zerostack/agent/memory/` | 與 Second Brain 概念重疊，可互補 |
| 權限 | 5 種模式：`restrictive`/`readonly`/`guarded`/`standard`/`yolo`；per-tool glob 允許清單；doom-loop 偵測 | ✅ 對「取代管理後台」的破壞性操作控管很重要 |
| LLM | OpenRouter（預設）/ OpenAI / Anthropic / Gemini / Ollama / 自訂 | 可用 Ollama 走本機、避免把後台資料送雲端 |
| 授權 | **GPL-3.0-only** | 若你要商用/內部封裝散佈，需留意 copyleft |

### 2.2 S.2ndbrain（既有 Second Brain）怎麼接進 agent

主流且成熟的做法是 **Obsidian vault + MCP server**：讓 agent 具備 read / search / create / update 筆記的能力。生態已有多個實作（[Open Second Brain](https://mcpserver.space/mcp/open-second-brain/)、kazuph、MarkusPfundstein 等 Obsidian MCP server；以及 [obsidian-second-brain](https://github.com/eugeniughelbur/obsidian-second-brain) 這類跨 CLI 的 skill 套件）。

- 若你的 Second Brain 就是 Markdown 檔案樹 → **zerostack 內建的 file 工具（read/write/edit/grep/find_files）其實已經能直接操作**，連 MCP 都不一定需要。
- 若需要語意搜尋 / 雙向連結 / 結構化查詢 → 掛一個 Obsidian MCP server 效果更好。

### 2.3 那個 web console 扮演什麼角色（本報告最大未知）

你選了「某個 web/管理後台」，未指名具體產品。**這是整份評估的關鍵變數**，因為可行性完全取決於它「能不能被程式驅動」。見 §6 決策樹。

---

## 3. 提議架構

```
┌──────────────────────────────────────────────────────────────┐
│  桌面入口（可選）                                                │
│  ├─ 方案 A：純終端機視窗跑 zerostack                             │
│  └─ 方案 B：本 repo 的 Terminal Widget（ttyd + Übersicht）      │
│            → iframe 一個跑著 zerostack 的 ttyd session          │
│              等於把「agent console」釘在桌面上                    │
└───────────────┬──────────────────────────────────────────────┘
                │ 使用者用自然語言下指令
                ▼
        ┌───────────────────┐
        │     zerostack      │  ← orchestrator（TUI / ACP）
        │  權限模式 guarded   │
        └───┬───────────┬────┘
            │ MCP        │ MCP / 內建 file 工具
            ▼            ▼
   ┌─────────────────┐  ┌──────────────────────┐
   │ console 後端      │  │  S.2ndbrain           │
   │ MCP adapter      │  │  (Obsidian vault)     │
   │ 包 REST/CLI/DB   │  │  read/search/write .md │
   └─────────────────┘  └──────────────────────┘
```

**重點設計取捨**：
1. **zerostack 當協調層**，不是當網站。console 的「功能」被拆成 MCP 工具，Second Brain 當知識/記憶層。
2. **桌面化**用你**現有的 Terminal Widget** 就能達成——這正是本 repo 已驗證過的 pattern（見 `SKILL.md`：「不要對抗 render model，iframe 一個真正的 web app」；ttyd 把 zerostack 的 TUI 包成 localhost web terminal，Übersicht widget 再 iframe 它）。這讓「agent console」有一個常駐桌面的外觀，補上 zerostack 沒有 web UI 的缺口。
3. **資料落地**：用 Ollama provider 可讓後台敏感資料不出本機。

---

## 4. 逐面向可行性分析

| 維度 | 評估 | 說明 |
|---|---|---|
| **功能覆蓋** | ⚠️ 取決於前提 | 「查詢 / 新增 / 修改 / 批次 / 匯出」→ agent 很擅長。「即時儀表板 / 圖表 / 拖拉排版 / 視覺監控」→ agent 幾乎無法取代 |
| **互動模式** | ⚠️ 範式轉換 | 從「肌肉記憶點按」變「用講的」。對重複性、跨系統、需組合的操作，agent 更快；對一眼掃視狀態，GUI 更快 |
| **Second Brain 整合** | ✅ 高 | Markdown vault 用內建 file 工具即可讀寫；要語意搜尋再加 Obsidian MCP。這是最成熟的一塊 |
| **整合成本** | ⚠️ 中 | 主成本在「把 console 後端包成 MCP/CLI」。若已有 API → 低；若要逆向或無 API → 高 |
| **正確性 / 確定性** | ⚠️ 需護欄 | LLM 非確定性。管理後台的破壞性操作要靠 `guarded`/`readonly` 模式 + per-tool 允許清單 + 二次確認 |
| **多人 / 稽核 / 權限** | ❌ 弱 | zerostack 是單機單人工具，無 RBAC、無多人稽核。若 console 有這些需求，agent 不能取代 |
| **維運** | ✅ 佳 | 26MB binary、16MB RAM、`brew install zerostack`；比重型 agent 輕非常多。可搭本 repo 的 `scripts/bootstrap.sh` 做環境初始化 |
| **授權** | ⚠️ 留意 | GPL-3.0；個人/內部使用無虞，封裝散佈需評估 copyleft |
| **安全** | ✅ 可控 | 沿用本 repo 原則：所有本機服務綁 `127.0.0.1`；agent 走 Ollama 本機模型可避免資料外流 |

---

## 5. 主要風險與緩解

| 風險 | 影響 | 緩解 |
|---|---|---|
| Agent 執行破壞性後台操作（刪除、批次改動） | 高 | 預設 `guarded` 或 `readonly`；破壞性動作需人工確認；per-tool glob 白名單；先只給讀權限跑一段時間 |
| 「取代」了但少了視覺監控 | 中 | 保留 console 做儀表板；agent 只接管操作面 → 定位為 augment 而非 replace |
| console 無 API，需逆向 | 中–高 | 先做 §6 盤點；無 API 就縮小範圍到「有 CLI/DB 的子功能」 |
| LLM 誤解意圖 | 中 | 用 `/plan` 先產計畫再執行；重要操作要求 agent 先回述再動手 |
| 資料外流到雲端 LLM | 中 | 用 Ollama 本機 provider；或只送去識別化後的內容 |
| GPL-3.0 copyleft | 低–中 | 個人使用無虞；若要包成產品散佈再諮詢授權 |
| 單點/單人 | 中 | 不適合多人協作場景；那類需求維持用原 console |

---

## 6. 關鍵前提：一張決策樹（做或不做，看這裡）

**問題：你那個 web console 的功能，底層能不能被程式驅動？**

```
你的 console 有沒有 REST/GraphQL API 或官方 CLI？
├─ 有 ──────────────► 高度可行。包成 MCP server（或讓 agent 直接呼叫 CLI）→ 可取代「操作面」。動手做 PoC。
├─ 沒有，但能直接連它的 DB / 檔案 ─► 中度可行。agent 直接操作資料層，但要自己補回 console 原本的驗證/商業邏輯（風險↑）。
└─ 都沒有（純前端、閉源 SaaS 無 API）─► 低度可行。
        └─ 只能靠瀏覽器自動化（Playwright MCP）模擬點按 → 脆弱、不建議當主力。
           此時「取代」不划算，建議維持 console。
```

> 👉 **下一步最該做的一件事**：確認你那個 console 屬於上面哪一類。這決定了整件事是「值得做」還是「不划算」。若你願意告訴我是哪個 console（或它是否有 API/CLI），我可以把本報告的抽象前提換成具體結論，甚至直接做 PoC。

---

## 7. 建議落地路線（若前提為「有 API/CLI」）

分階段、低風險、可隨時停損：

1. **Phase 0 — 盤點（0.5 天）**：列出你在 console 上最常做的 10 個操作；確認各自有無 API/CLI。
2. **Phase 1 — 唯讀接入（1 天）**：`zerostack --read-only`，接上 Second Brain（Markdown 直接讀，或加 Obsidian MCP）。先用來「查詢 + 交叉筆記」，零風險驗證體感。
3. **Phase 2 — console MCP adapter（2–3 天）**：把最常用的 3 個 console 操作包成 MCP server（或 CLI wrapper），權限設 `guarded`。
4. **Phase 3 — 桌面化（0.5 天，選配）**：用本 repo 的 Terminal Widget，把跑著 zerostack 的 ttyd session iframe 到 Übersicht，做成常駐桌面「agent console」。環境初始化沿用 `scripts/bootstrap.sh`（工具中立，已與 Superset adapter 解耦）。
5. **Phase 4 — 評估退役（跑滿 1 個月後）**：統計 agent 覆蓋率。達 ~80% 且信任度足夠 → 逐步退役 console；否則維持雙軌（agent 管操作、console 管監控）。

---

## 8. 總結

- **「用 zerostack + 既有 Second Brain 取代 web console」在技術上成立**，但它取代的是**操作範式**（對話式 agent）而非「換一個網頁後台」——因為 zerostack 沒有 web UI。
- **成敗關鍵單一變數**：那個 console 後端能否被程式驅動（API/CLI/DB）。有 → 值得做；純前端無 API → 不划算。
- **Second Brain 這一塊最穩**：Markdown vault 用內建工具或 Obsidian MCP 即可接入，是整個方案風險最低的部分。
- **這個 repo 是天然的桌面外殼**：Terminal Widget 的 ttyd + iframe pattern 正好補上 zerostack 缺 web UI 的缺口，`scripts/bootstrap.sh` 也能重用。
- **建議先 augment、後 replace**：唯讀接入 → MCP adapter → 桌面化 → 再評估退役，全程可停損。

---

## 參考來源

- [gi-dellav/zerostack（GitHub）](https://github.com/gi-dellav/zerostack)
- [zerostack — minimal coding agent（官網）](https://gi-dellav.github.io/zerostack/)
- [Build an AI Second Brain with Claude Code and Obsidian（MindStudio）](https://www.mindstudio.ai/blog/build-ai-second-brain-claude-code-obsidian)
- [Open Second Brain — MCP Server](https://mcpserver.space/mcp/open-second-brain/)
- [obsidian-second-brain（跨 CLI skill 套件）](https://github.com/eugeniughelbur/obsidian-second-brain)
- 本 repo：`SKILL.md`（iframe-a-real-app pattern）、`scripts/bootstrap.sh`（工具中立初始化）、`README.md`（Terminal Widget 架構）
