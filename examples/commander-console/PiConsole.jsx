// ─────────────────────────────────────────────────────────────────────────────
// PiConsole — 可直接搬進 Commander Center「console 標籤頁」的參考元件（路徑 B）
// ─────────────────────────────────────────────────────────────────────────────
// 用途：取代自寫的「命令 + log」面板，改成內嵌 Pi 的 web UI（pi-web）。
// 這是「保證可運作」的整合方式：pi-web 自己就是一個本機 web 服務，直接 iframe 它即可。
// （更進階、無 iframe 邊界的做法是改用 @earendil-works/pi-web-ui 的 web 元件，
//   但其確切 tag/props 請以該套件的 packages/web-ui/example 為準——見本資料夾 README。）
//
// 一次性前置（在跑 Commander Center 的機器上）：
//   npm install -g @jmfederico/pi-web        # 需 Node.js 22+
//   pi-web install && pi-web doctor           # 服務於 http://127.0.0.1:8504
//   # vault / host / port 在 ~/.config/pi-web/config.json 設定，務必綁 127.0.0.1
//
// 用法（在 console 標籤頁的元件裡）：
//   import PiConsole from "./PiConsole";
//   <PiConsole port={8504} />
//
// Props：
//   host    預設 "127.0.0.1"（請維持 localhost，勿開 0.0.0.0）
//   port    預設 8504
//   pollMs  可達性輪詢間隔（毫秒），預設 1500
// ─────────────────────────────────────────────────────────────────────────────

import React, { useEffect, useRef, useState } from "react";

export default function PiConsole({ host = "127.0.0.1", port = 8504, pollMs = 1500 }) {
  const url = `http://${host}:${port}/`;
  const [ready, setReady] = useState(false);
  const [checked, setChecked] = useState(false); // 第一次探測完成前顯示「connecting」
  const timer = useRef(null);

  useEffect(() => {
    let cancelled = false;

    // 只需判斷「連得上」，不需要讀回應內容 → 用 no-cors 避開跨來源限制。
    // 連得上：Promise resolve（opaque response）；連不上：reject。
    const probe = async () => {
      try {
        await fetch(url, { mode: "no-cors", cache: "no-store" });
        if (!cancelled) setReady(true);
      } catch {
        if (!cancelled) setReady(false);
      } finally {
        if (!cancelled) setChecked(true);
      }
    };

    probe();
    timer.current = setInterval(probe, pollMs);
    return () => {
      cancelled = true;
      clearInterval(timer.current);
    };
  }, [url, pollMs]);

  if (ready) {
    return (
      <iframe
        title="Pi console"
        src={url}
        style={{ width: "100%", height: "100%", border: "none", background: "#141418" }}
      />
    );
  }

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        background: "#141418",
        color: "#d4d4d4",
        font: "13px/1.5 -apple-system, Menlo, monospace",
      }}
    >
      <div>{checked ? "Pi web UI 連不上" : "connecting to Pi…"}</div>
      <div style={{ opacity: 0.6 }}>{url}</div>
      {checked && !ready && (
        <div style={{ opacity: 0.6 }}>
          請先執行 <code>pi-web install</code> / <code>pi-web restart</code>
        </div>
      )}
    </div>
  );
}
