// ─────────────────────────────────────────────────────────────────────────────
// Übersicht Terminal Widget — 桌面終端機（後端用 ttyd + xterm.js）
// ─────────────────────────────────────────────────────────────────────────────
// 修改後到 Übersicht 選單列 → Refresh All Widgets 即可生效。
//
// 想要再開一個獨立的終端 widget：
//   1. 複製整個 .widget 資料夾為 terminal-widget-2.widget 等
//   2. 把下面 TTYD_PORT 改成沒被佔用的 port（7682、7683…）
//   3. 想換獨立 .zshrc 就把 ZDOTDIR 指到另一個資料夾，否則保持 "" 用內建的
//      zsh/ 資料夾（裡面有招呼語、AUTORUN 設定可調）
// （或直接執行 install.py 由互動安裝程式幫你做這些。）
// ─────────────────────────────────────────────────────────────────────────────

// ─── 本實例設定（每份複本各自調整）─────────────────────────────────────────
const TTYD_PORT = 7681;        // 此 widget 用的 port，多開時每份要不同
const ZDOTDIR   = "";          // 留空 → 用內建 zsh/；填路徑 → 用該資料夾的 .zshrc
// ─────────────────────────────────────────────────────────────────────────────

const TTYD_URL = `http://127.0.0.1:${TTYD_PORT}`;
const WIDGET_DIR =
  "/Users/scottchen/Library/Application Support/Übersicht/widgets/terminal-widget.widget";

// widget 視窗最小尺寸（拖縮時不能比這個更小）
const MIN_W = 320;
const MIN_H = 180;

// ─── 位置／尺寸／鎖定狀態的記憶（用 localStorage，依 port 區分）─────────────
// 用瀏覽器 localStorage 存，所以 Übersicht 重啟、Mac 重開機都記得。
// 想完全重置某 widget 的位置：在 Web Inspector Console 執行
//   localStorage.removeItem('terminal-widget:7681')
// 然後 Refresh All Widgets 即可恢復成 initialState 預設值。
const LS_KEY = `terminal-widget:${TTYD_PORT}`;

const loadPersisted = () => {
  try {
    const raw = window.localStorage && localStorage.getItem(LS_KEY);
    if (!raw) return null;
    const p = JSON.parse(raw);
    return {
      pos:    p.pos    && Number.isFinite(p.pos.x)  ? p.pos    : null,
      size:   p.size   && Number.isFinite(p.size.w) ? p.size   : null,
      locked: !!p.locked,
    };
  } catch {
    return null;
  }
};

const persist = (state) => {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify({
      pos: state.pos, size: state.size, locked: state.locked,
    }));
  } catch { /* private mode etc. */ }
};

const _persisted = loadPersisted() || {};

export const refreshFrequency = 1500;

export const command = `'${WIDGET_DIR}/bridge-tick.sh' ${TTYD_PORT} '${ZDOTDIR}'`;

// 第一次啟動的預設位置與大小（之後使用者調整過就以 localStorage 為準）
export const initialState = {
  ready:  false,
  pos:    _persisted.pos    || { x: 60, y: 60 },     // 預設左上角座標
  size:   _persisted.size   || { w: 720, h: 440 },   // 預設寬 × 高
  locked: _persisted.locked || false,                // 預設未鎖定
};

export const updateState = (event, prev) => {
  if (event && typeof event === "object") {
    if (event.type === "MOVE") {
      const next = { ...prev, pos: { x: event.x, y: event.y } };
      persist(next);
      return next;
    }
    if (event.type === "RESIZE") {
      const next = { ...prev, size: { w: event.w, h: event.h } };
      persist(next);
      return next;
    }
    if (event.type === "TOGGLE_LOCK") {
      const next = { ...prev, locked: !prev.locked };
      persist(next);
      return next;
    }

    const out = typeof event.output === "string" ? event.output : null;
    if (out !== null) {
      const nl = out.indexOf("\n");
      const health = (nl >= 0 ? out.slice(0, nl) : out).trim();
      return { ...prev, ready: health === "200" };
    }
  }
  return prev;
};

// ─── Drag / Resize via document-level listeners ──────────────────────────────
//
// Two perf tricks here:
//   1. While dragging we cover the screen with a transparent overlay so the
//      iframe stops stealing mouse events the moment the cursor enters it.
//   2. Mouse moves are coalesced into one dispatch per animation frame
//      (~60Hz instead of 200+/s), eliminating reducer churn.
const installDragShield = (cursor) => {
  const shield = document.createElement("div");
  shield.style.cssText =
    `position:fixed; inset:0; z-index:99999;
     cursor:${cursor}; background:transparent; user-select:none;`;
  document.body.appendChild(shield);
  return shield;
};

const beginDragLoop = (cursor, onMove) => {
  const shield = installDragShield(cursor);
  let pending = null;
  let raf = 0;

  const flush = () => {
    raf = 0;
    if (pending) { onMove(pending); pending = null; }
  };
  const handleMove = (ev) => {
    pending = ev;
    if (!raf) raf = requestAnimationFrame(flush);
  };
  const handleUp = () => {
    if (raf) cancelAnimationFrame(raf);
    document.removeEventListener("mousemove", handleMove);
    document.removeEventListener("mouseup", handleUp);
    shield.remove();
  };
  document.addEventListener("mousemove", handleMove);
  document.addEventListener("mouseup", handleUp);
};

const startDrag = (e, dispatch, pos, locked) => {
  if (locked) return;
  e.preventDefault();
  const sx = e.clientX, sy = e.clientY;
  const ox = pos.x, oy = pos.y;
  beginDragLoop("move", (ev) =>
    dispatch({ type: "MOVE", x: ox + (ev.clientX - sx), y: oy + (ev.clientY - sy) })
  );
};

const startResize = (e, dispatch, size, locked) => {
  if (locked) return;
  e.preventDefault();
  e.stopPropagation();
  const sx = e.clientX, sy = e.clientY;
  const ow = size.w, oh = size.h;
  beginDragLoop("nwse-resize", (ev) =>
    dispatch({
      type: "RESIZE",
      w: Math.max(MIN_W, ow + (ev.clientX - sx)),
      h: Math.max(MIN_H, oh + (ev.clientY - sy)),
    })
  );
};

// ─── Styles ──────────────────────────────────────────────────────────────────
export const className = `
  & .root {
    position: absolute;
    top: 0; left: 0;
    background: #141418;
    border-radius: 10px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.5);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  & .drag {
    height: 8px;
    width: 100%;
    cursor: move;
    background: rgba(255,255,255,0.04);
    flex-shrink: 0;
  }
  & .drag.locked {
    cursor: default;
    background: transparent;
    pointer-events: none;
  }
  & .frame-wrap {
    flex: 1;
    overflow: hidden;
    position: relative;
    background: #141418;
  }
  & .frame {
    /* Push xterm.js scrollbar past the right edge of the wrap. */
    width: calc(100% + 18px);
    height: 100%;
    border: none;
    display: block;
    background: #141418;
  }
  & .veil {
    position: absolute;
    inset: 8px 0 0 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #888;
    font: 12px 'JetBrainsMono Nerd Font', Menlo, monospace;
    background: #141418;
    pointer-events: none;
  }
  & .resize {
    position: absolute;
    right: 0; bottom: 0;
    width: 16px; height: 16px;
    cursor: nwse-resize;
    background:
      linear-gradient(135deg, transparent 0%, transparent 55%,
        rgba(255,255,255,0.35) 55%, rgba(255,255,255,0.35) 60%,
        transparent 60%, transparent 70%,
        rgba(255,255,255,0.35) 70%, rgba(255,255,255,0.35) 75%,
        transparent 75%);
    z-index: 2;
  }
  & .resize.locked { display: none; }

  /* When locked, this transparent veil sits on top of the iframe so clicks
     never reach (and focus) it — meaning subsequent keystrokes go nowhere. */
  & .lock-veil {
    position: absolute;
    inset: 0;
    background: transparent;
    cursor: not-allowed;
    z-index: 2;
  }

  & .lock-btn {
    position: absolute;
    left: 6px; bottom: 6px;
    width: 22px; height: 22px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 6px;
    background: rgba(0,0,0,0.45);
    color: #d4d4d4;
    cursor: pointer;
    z-index: 3;
    opacity: 0;
    transition: opacity 0.15s ease;
    user-select: none;
  }
  & .root:hover .lock-btn,
  & .lock-btn.is-locked { opacity: 0.85; }
  & .lock-btn:hover { opacity: 1; background: rgba(0,0,0,0.7); }
  & .lock-btn svg { width: 13px; height: 13px; display: block; }
`;

// ─── Render ──────────────────────────────────────────────────────────────────
const LockIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"
       strokeLinecap="round" strokeLinejoin="round">
    <rect x="4" y="11" width="16" height="10" rx="2" />
    <path d="M8 11V7a4 4 0 0 1 8 0v4" />
  </svg>
);

const UnlockIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"
       strokeLinecap="round" strokeLinejoin="round">
    <rect x="4" y="11" width="16" height="10" rx="2" />
    <path d="M8 11V7a4 4 0 0 1 7.5-2" />
  </svg>
);

export const render = ({ ready, pos, size, locked }, dispatch) => (
  <div>
    <div
      className="root"
      style={{
        // translate3d goes through the GPU compositor → no layout reflow
        // when dragging, only width/height changes during resize cost layout.
        transform: `translate3d(${pos.x}px, ${pos.y}px, 0)`,
        width:  `${size.w}px`,
        height: `${size.h}px`,
        willChange: "transform",
      }}
    >
      <div
        className={`drag ${locked ? "locked" : ""}`}
        onMouseDown={(e) => startDrag(e, dispatch, pos, locked)}
      />

      {ready ? (
        <div className="frame-wrap">
          <iframe className="frame" src={TTYD_URL} allow="clipboard-read; clipboard-write" />
          {locked && (
            <div
              className="lock-veil"
              onMouseDown={(e) => e.preventDefault()}
              title="Locked — unlock to interact"
            />
          )}
        </div>
      ) : (
        <div className="veil">starting ttyd…</div>
      )}

      <div
        className={`resize ${locked ? "locked" : ""}`}
        onMouseDown={(e) => startResize(e, dispatch, size, locked)}
        title="Drag to resize"
      />

      <div
        className={`lock-btn ${locked ? "is-locked" : ""}`}
        onClick={() => {
          // About to lock: pull keyboard focus out of the iframe so any
          // currently-active terminal session stops receiving keystrokes.
          if (!locked) {
            try { document.activeElement && document.activeElement.blur(); } catch {}
            try { window.focus(); } catch {}
          }
          dispatch({ type: "TOGGLE_LOCK" });
        }}
        title={locked ? "Locked — click to unlock" : "Unlocked — click to lock"}
      >
        {locked ? <LockIcon /> : <UnlockIcon />}
      </div>
    </div>
  </div>
);
