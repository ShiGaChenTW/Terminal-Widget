# Commander Center × Pi — console 標籤頁整合參考（路徑 B）

把 Commander Center 的自寫「命令 / log」面板，換成內嵌 **Pi agent** 的 console。
這是可行性報告（`docs/pi-secondbrain-console-feasibility.md`）**路徑 B** 的可移植成品。

> 為什麼是 iframe 而不是元件？——`@earendil-works/pi-web-ui` 的 web 元件是更融入的做法，
> 但其確切 tag/props 需以官方範例為準（見文末）。iframe 內嵌 pi-web 服務是**保證可運作**
> 的整合方式，適合先落地；日後再視需要升級成元件。

---

## 檔案

| 檔案 | 用途 |
|---|---|
| `PiConsole.jsx` | React 元件，**drop-in** 到 console 標籤頁（Commander Center 若是 React/Electron/Tauri 前端） |
| `pi-console.html` | 框架無關版，同邏輯；非 React 殼或快速驗證用 |

兩者行為一致：輪詢 pi-web 是否可達 → 未就緒顯示提示 → 就緒後 iframe 進來。

---

## 前置（在跑 Commander Center 的機器上，一次性）

```bash
npm install -g @jmfederico/pi-web        # 需 Node.js 22+
pi-web install && pi-web doctor           # 服務於 http://127.0.0.1:8504
# vault / host / port 於 ~/.config/pi-web/config.json；務必綁 127.0.0.1
```

Pi 為 **MIT**，可放心打包散佈；pi-web 為純 web → **Windows 也能用**（不需 ttyd）。

---

## 整合步驟

### React（Commander Center 前端）

1. 複製 `PiConsole.jsx` 進你的專案。
2. 在 console 標籤頁的元件裡，**把自寫命令/log 面板換成**：

   ```jsx
   import PiConsole from "./PiConsole";

   function ConsoleTab() {
     return (
       <div style={{ position: "absolute", inset: 0 }}>
         <PiConsole port={8504} />
       </div>
     );
   }
   ```

   `PiConsole` 會填滿父容器，請確保父層有明確高度（如上例 `inset:0`）。

3. Props：`host`（預設 `127.0.0.1`）、`port`（預設 `8504`）、`pollMs`（預設 `1500`）。

### 非 React

直接把 `pi-console.html` 當該標籤頁載入的頁面，或參考其 `<script>` 邏輯改寫。
支援 querystring：`pi-console.html?host=127.0.0.1&port=8504`。

---

## 生命週期建議

- 把 `pi-web install` 的 per-user service 當相依：Commander Center 啟動時 `pi-web status` 檢查、
  必要時 `pi-web restart`。元件本身也會持續輪詢，pi-web 掉線會自動回到「連不上」提示、
  恢復後自動 iframe 回來。

## 安全

- **務必只綁 `127.0.0.1`**（在 `~/.config/pi-web/config.json`），不要開 `0.0.0.0`。
- 元件用 `fetch(url, { mode: "no-cors" })` 只做**可達性**探測，不讀回應內容，避開跨來源限制。

---

## 進階：改用 web 元件（無 iframe 邊界）

若要更融入的 UI，可改用 **`@earendil-works/pi-web-ui`**（earendil 官方 org 的 web 元件庫；
另有 `@mariozechner/pi-web-ui`）。它支援 **Direct Mode**（瀏覽器直呼 AI provider API、
金鑰存 localStorage，不經第三方 server）。

⚠️ 其確切的 import、元件 tag、props 請**以官方範例為準**再落地（本環境無法取得逐字 API）：
- 範例目錄：<https://github.com/earendil-works/pi/tree/main/packages/web-ui/example>
- npm：`@earendil-works/pi-web-ui`

確認 API 後，把 `PiConsole.jsx` 的 `<iframe>` 換成該元件即可，其餘（就緒/掉線處理）可沿用。

---

## 相關

- 可行性報告：`../../docs/pi-secondbrain-console-feasibility.md`
- 路徑 A（ttyd 跑 pi TUI）：`../../docs/poc-pi-console.md`、`../../agent-bridge-tick.sh`
- 路徑 B（widget iframe pi-web）：`../../docs/poc-pi-web-console.md`、`../../pi-web-tick.sh`
