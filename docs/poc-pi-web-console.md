# PoC（路徑 B）：widget 直接 iframe Pi 的 web UI（pi-web），跳過 ttyd

這是可行性報告 §3「路徑 B」的最小原型，也是最貼近 **Commander Center console 標籤頁最終型態**
的一版：console 就是一個**原生 web UI**，不必再用 ttyd 包一層終端。

差別對照：

| | 路徑 A（`agent-bridge-tick.sh`） | 路徑 B（`pi-web-tick.sh`，本檔） |
|---|---|---|
| console 內容 | ttyd 包住 `pi` 的 TUI | Pi 官方 web UI（pi-web） |
| tick 腳本做什麼 | spawn ttyd + 健康檢查 | **純健康探測，不 spawn** |
| 誰負責啟動 agent | 每次 poll 由腳本 spawn | `pi-web install` 的 per-user service 常駐 |
| 跨平台（含 Windows） | ttyd 這層是 Unix | ✅ 純 web，跨平台 |
| 貼近最終型態 | 中 | ✅ 高 |

> 原本的 zsh 終端 widget、以及路徑 A 的檔案都不受影響，這是**再新增**的獨立一條路。

---

## 一次性設定（手動跑一次，不要放進 widget poll）

```bash
npm install -g @jmfederico/pi-web        # 需 Node.js 22+
pi-web install                            # 裝成 per-user service（會自己常駐）
pi-web doctor                             # 檢查環境
pi-web status                             # 看是否在跑
```

- pi-web 預設服務於 **`http://127.0.0.1:8504`**（綁 localhost，安全）。
- vault 路徑 / host / port 於 `~/.config/pi-web/config.json`（或專案內 `<project>/.pi-web/config.json`）設定。
- ⚠️ 請確認 config 綁 `127.0.0.1`，不要開到 `0.0.0.0`。

---

## 1. 先驗證 pi-web 活著

```bash
./pi-web-tick.sh 8504
# 期望第一行印出 200，第二行 {"port":8504,"agent":"pi-web"}
```

若印出 `000` → pi-web 沒在跑，執行 `pi-web restart`／`pi-web doctor` 排查。
也可直接用瀏覽器開 <http://127.0.0.1:8504> 確認 Pi web UI 出得來。

---

## 2. 把桌面 widget 指到 pi-web（JSX 幾乎不用改）

既有的 `index.jsx` 本來就會 iframe `http://127.0.0.1:${TTYD_PORT}`，並用 `command`
輸出的第一行健康碼判斷 ready。所以只要複製一份 widget 資料夾，改頂部兩處：

```js
const TTYD_PORT = 8504;                                   // 對到 pi-web 的 port
export const command = `'${WIDGET_DIR}/pi-web-tick.sh' ${TTYD_PORT}`;
// 其餘完全不動：iframe、drag/resize、localStorage 都照舊
```

Refresh All Widgets → 桌面上就是一個常駐的 **Pi web UI console**，背後是你的 Second Brain。

---

## 3. 搬進 Commander Center 的 console 標籤頁（最終型態）

這一版幾乎就是終點：

- Commander Center 是 Electron / Tauri / web 殼 → console 標籤頁**直接 iframe
  `http://127.0.0.1:8504`**，或改用 `@earendil-works/pi-web-ui` 的 web 元件**原生組進**你的前端
  （更融入、無 iframe 邊界）。
- vault / port 由 Commander Center 的設定寫進 pi-web config。
- Pi 為 **MIT**，可放心打包散佈；且 pi-web 純 web → **Windows 也能用**。
- 生命週期：把 `pi-web install` 的 service 當相依，Commander Center 啟動時 `pi-web status`
  檢查、必要時 `pi-web restart` 即可。

---

## 檔案

- `pi-web-tick.sh` — 本 PoC：純健康探測（不 spawn），配合 index.jsx 直接 iframe pi-web。
- `agent-bridge-tick.sh` — 路徑 A：ttyd 包 `pi` TUI。
- `docs/poc-pi-console.md` — 路徑 A 說明。
- `docs/pi-secondbrain-console-feasibility.md` — 完整可行性報告。

## 已知限制 / 待確認

- `pi-web` 的 host/port 設定確切鍵名以其官方 config 為準；務必綁 `127.0.0.1`。
- `pi-web` 是社群專案；正式採用前評估維護狀態，或改用 `@earendil-works/pi-web-ui`（earendil 官方 org 的 web 元件庫）自行組 UI。
- 本探測腳本用 `/usr/bin/curl`（macOS 路徑），與本 repo 一致。
