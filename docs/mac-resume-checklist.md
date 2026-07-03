# 回 Mac 後：完成 Pi console 整合的逐步清單

從雲端 session 回到 Mac 後，照這份把 `PiConsole` 整合進 Commander Center 的 console 標籤頁。

---

## 0. 前置

- Node.js **22 以上**（`node -v` 確認）
- 這個 repo 已在 GitHub 分支 `claude/zerostack-s2ndbrain-console-8whmxw`

---

## 1. 把這份成果拉到 Mac

```bash
# 沒 clone 過：
git clone https://github.com/ShiGaChenTW/Terminal-Widget.git
cd Terminal-Widget && git checkout claude/zerostack-s2ndbrain-console-8whmxw

# 已 clone：
# cd <你的 Terminal-Widget> && git fetch origin \
#   && git checkout claude/zerostack-s2ndbrain-console-8whmxw && git pull
```

確認檔案在：`ls examples/commander-console/`（應有 `PiConsole.jsx`、`pi-console.html`、`README.md`）

---

## 2. 啟動 Pi 的 web UI（一次性）

```bash
npm install -g @jmfederico/pi-web        # Node 22+
pi-web install && pi-web doctor           # 服務於 http://127.0.0.1:8504
pi-web status                             # 確認在跑
```

- 在 `~/.config/pi-web/config.json` 把工作目錄設到你的 **Second Brain vault**，並確認 **綁 `127.0.0.1`**。
- 瀏覽器開 <http://127.0.0.1:8504> 看得到 Pi UI = OK。

---

## 3. 複製 PiConsole 進 Commander Center

```bash
CC=<你的 Commander Center 資料夾>          # 例如 ~/Developer/commander-center
mkdir -p "$CC/src/components"
cp examples/commander-console/PiConsole.jsx "$CC/src/components/PiConsole.jsx"
```

---

## 4. 找到 console 標籤頁並換掉

```bash
cd "$CC"
rg -n -i "console|command|log|terminal" src --glob '*.{jsx,tsx,js,ts}' -C2
```

找到那個「命令 + log 面板」元件後，把它的 return 換成：

```jsx
import PiConsole from "./components/PiConsole";  // 路徑對應你放的位置

function ConsoleTab() {
  return (
    <div style={{ position: "absolute", inset: 0 }}>
      <PiConsole port={8504} />
    </div>
  );
}
```

> 父層一定要有明確高度（`inset:0` 或 `flex:1`），否則 iframe 變 0 高看不到。

---

## 5. 處理 iframe 的 CSP（依你的殼）

- **純 web / Electron**：若有 CSP，`frame-src` 要含 `http://127.0.0.1:8504`；Electron 別關 `webSecurity`。
- **Tauri**：`tauri.conf.json` 的 `security.csp` 加 `frame-src http://127.0.0.1:8504 http://localhost:8504`。

---

## 6. 驗證

1. `pi-web status` 有在跑。
2. 啟動 Commander Center → console 標籤頁看到 Pi UI = 成功。
3. 卡在「connecting to Pi…」→ `pi-web restart`。
4. 空白/被擋 → 回第 5 步加 `frame-src`。

---

## 7. 收尾

- 確認穩定後，刪掉舊的命令/log 面板元件與相關程式碼。
- 在 Commander Center repo commit + push。

---

## 附：可直接貼給「Mac 本機 Claude Code」的 prompt

在 Commander Center 資料夾裡執行 `claude`，貼上下面這段（`<...>` 換成你的實際值）：

```
我要把這個 app（Commander Center）的「console 標籤頁」從自寫的命令/log 面板，
改成內嵌 Pi agent 的 console。整合成品在另一個 repo：
https://github.com/ShiGaChenTW/Terminal-Widget 分支 claude/zerostack-s2ndbrain-console-8whmxw
的 examples/commander-console/PiConsole.jsx（React 元件，iframe 本機 pi-web 的
web UI，預設 http://127.0.0.1:8504，用 no-cors 探測可達性後才 iframe）。

請幫我：
1. 把 PiConsole.jsx 放進本專案（放你判斷合適的元件資料夾），import 路徑對應好。
2. 找出目前 render「命令輸入 + log 輸出」的 console 標籤頁元件，把它的內容換成
   <PiConsole port={8504} />，並確保父容器有明確高度（inset:0 或 flex:1）。
3. 依本專案的殼（先判斷是 Electron / Tauri / 純 web）設定 CSP，讓 iframe 能載入
   http://127.0.0.1:8504（Tauri 要改 tauri.conf.json 的 security.csp 的 frame-src）。
4. 先不要刪舊面板，保留成可切換或註解，等我確認新的能動再移除。
5. 改完告訴我怎麼啟動驗證（我已用 `pi-web install` 起好 pi-web）。

前置我已完成：pi-web 已安裝並在 127.0.0.1:8504 跑、vault 已在 ~/.config/pi-web/config.json 設好。
本專案技術棧：<Electron / Tauri / 純 web，React？>。console 標籤頁大概在 <檔案或資料夾，如果知道>。
```
