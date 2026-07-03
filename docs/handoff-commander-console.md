# HANDOFF：把 Pi console 整合進 Commander Center 的 console 標籤頁

> **對象**：在 Mac 本機、於 **Commander Center repo** 內執行的 agent（Claude Code 等）。
> 本文件自足（self-contained），不需要先前對話的上下文即可執行。
> **日期**：2026-07-03 ｜ **交接自**：雲端 session（Terminal-Widget repo，分支
> `claude/zerostack-s2ndbrain-console-8whmxw`，PR #1）

---

## 1. 背景（30 秒版）

Commander Center 是使用者自己開發的 app，其中有一個 **console 標籤頁**，目前是
自寫的「命令輸入 + log 輸出」面板。目標：**把它換成內嵌 Pi coding agent 的 console**，
讓使用者能用自然語言操作、並讓 agent 直接讀寫他既有的 Second Brain（Obsidian/Markdown vault）。

方案已定案（可行性報告：Terminal-Widget repo 的
`docs/pi-secondbrain-console-feasibility.md`）：**路徑 B** —— console 標籤頁 iframe
本機 pi-web 服務的 web UI，用現成的 `PiConsole.jsx` 元件。

## 2. 目前狀態（已完成、已驗證）

| 項目 | 狀態 |
|---|---|
| pi-web `1.202606.7` 安裝於 `/opt/homebrew`（brew node v22.23.1） | ✅ |
| 服務（LaunchAgents）：web + sessiond 皆 running | ✅ |
| `curl http://127.0.0.1:8504/api/pi-web/version` → web 與 sessiond 均 `"available": true` | ✅ 已驗證 |
| 整合元件 `PiConsole.jsx` 已寫好 | ✅ 在 Terminal-Widget repo |
| Commander Center 端的修改 | ❌ **← 本次要做的** |

pi-web 若不在跑：`pi-web status` 檢查；服務不見時用 **`pi-web install` 重新註冊**
（不要狂 `pi-web restart`，會被 launchd 節流甚至弄掉 job）。其他坑見
Terminal-Widget repo `docs/mac-resume-checklist.md` 的 Troubleshooting 段。

## 3. 素材位置

整合元件在 **Terminal-Widget** repo（GitHub: `ShiGaChenTW/Terminal-Widget`，
分支 `claude/zerostack-s2ndbrain-console-8whmxw`）。使用者本機 clone 在
`~/20_Projects/Coding/Terminal-Widget`（若無，從 GitHub 抓）：

- `examples/commander-console/PiConsole.jsx` — React 元件：以 `fetch(no-cors)` 輪詢
  `http://127.0.0.1:8504` 可達性，就緒後 iframe；未就緒顯示提示、掉線自動恢復。
  Props：`host`（預設 `127.0.0.1`）、`port`（預設 `8504`）、`pollMs`（預設 `1500`）。
- `examples/commander-console/pi-console.html` — 框架無關版（非 React 時用）。
- `examples/commander-console/README.md` — 整合細節。

## 4. 任務（依序執行）

### T1 — 偵察
1. 判斷本專案（Commander Center）的殼與前端：Electron？Tauri？純 web？React/Vue/其他？
2. 找出 console 標籤頁的元件：搜 `console|command|log|terminal`，特徵是
   「命令輸入框 + log 清單」或 tab 定義如 `{ id:"console", label:"Console", ... }`。
3. 回報找到的檔案路徑再繼續。

### T2 — 放入元件
- React：把 `PiConsole.jsx` 複製進本專案慣用的元件資料夾，調整 import 路徑。
- 非 React：改用 `pi-console.html` 的邏輯（iframe + 可達性輪詢），以本專案的方式實作。

### T3 — 替換 console 標籤頁
- 把 console 標籤頁的內容換成 `<PiConsole port={8504} />`。
- **父容器必須有明確高度**（`position:absolute; inset:0` 或 `flex:1`），否則 iframe 0 高。
- **舊面板先不要刪**：保留為可切換（feature flag / 註解 / 第二個 tab），等使用者驗收後再移除。

### T4 — CSP / 載入權限（依殼擇一）
- **Electron**：確認 renderer 的 CSP `frame-src` 含 `http://127.0.0.1:8504`；不得關閉 `webSecurity`。
- **Tauri**：`tauri.conf.json` → `security.csp` 的 `frame-src` 加
  `http://127.0.0.1:8504 http://localhost:8504`。
- **純 web**：有 CSP 就加 `frame-src http://127.0.0.1:8504`。

### T5 — 驗證
1. `pi-web status` 兩個服務 running（不是的話 `pi-web install` 重註冊）。
2. 啟動 Commander Center → console 標籤頁應顯示 Pi 的 web UI，能開對話。
3. 測掉線恢復：`pi-web install` 重啟服務期間，標籤頁應顯示「connecting…」並在恢復後自動載回。
4. 常見失敗：卡「connecting to Pi…」→ pi-web 沒跑；空白/被擋 → T4 的 CSP 沒設對。

### T6 — 收尾
- 在 Commander Center repo 開分支、commit（訊息清楚說明取代 console 面板）、push。
- 回報：改了哪些檔、殼是什麼、CSP 動了哪裡、驗證結果、以及舊面板的切換方式。

## 5. 護欄（必守）

- **只綁 localhost**：任何設定都不得把 pi-web 或 iframe 目標開到 `0.0.0.0` 或對外網段。
- **不要動 pi-web 的全域安裝**（`/opt/homebrew/lib/node_modules/...`）；它已修好
  （node-pty spawn-helper 權限等），重裝會把修復弄掉。
- **不刪舊面板**直到使用者明確驗收（T3）。
- 不確定 console 標籤頁是哪個元件時，**先問使用者**，不要猜著改。
- vault 設定屬 pi-web（`~/.config/pi-web/config.json`），不在 Commander Center 內硬編。

## 6. 完成的定義（DoD）

- [ ] console 標籤頁顯示可互動的 Pi web UI（能發訊息）
- [ ] pi-web 掉線時有提示、恢復後自動回來
- [ ] CSP 設定最小必要（只多 `frame-src` 的 127.0.0.1:8504）
- [ ] 舊面板保留可切換
- [ ] 變更已 commit + push，並附回報摘要
