---
name: uebersicht-interactive-widget
description: Build interactive Übersicht desktop widgets — terminals, REPLs, anything needing input/IO — by iframing a localhost web app instead of fighting Übersicht's flat-render model. Distilled from a real session that took a broken PTY-relay terminal widget to a working ttyd-backed one.
origin: scott-self-built
created: 2026-05-15
---

# Übersicht Interactive Widget Construction

## When to use

Trigger this skill when you are:

- Building or fixing an Übersicht widget that needs **bidirectional interaction**
  (typed input, clickable controls, live data exchange) rather than passive
  display.
- Trying to embed an interactive program (terminal, REPL, log tailer with
  filters, dashboard with controls) on the macOS desktop.
- Confronting an existing widget that "loads but does nothing" or shows
  garbled output from a fancy CLI tool (zsh + p10k, htop, vim).

If the widget only displays read-only periodic output (CPU, weather, clock),
you don't need this skill — Übersicht's stock `command + render` model is fine.

## Mental model: what Übersicht actually is

Übersicht widgets are **WebKit pages glued to a `command` poll loop**. They
are NOT terminal emulators. They render whatever HTML/JSX you produce, and
re-run a shell `command` every `refreshFrequency` ms, feeding the stdout to
`updateState(event, prev)` where `event = {type:"UB/COMMAND_RAN", output, error}`.

Three frequent misconceptions to unlearn:

1. **`export default class` is not the API.** Übersicht expects named
   exports: `command`, `refreshFrequency`, `initialState`, `updateState`,
   `render`, `className`. Class-based widgets you find in old gists were a
   different lifecycle that no longer works.
2. **`event` is not a string.** It's an object with `.output` (stdout) and
   `.error`. Treating it as a string yields silently empty state forever.
3. **A `command` string is `bash -c`'d as a single line.** Multi-line shell
   logic embedded via `JSON.stringify(script)` has its `\n` flattened into
   literal `\n`s inside double quotes — bash sees one un-parseable line.
   Move multi-line scripts to a sidecar `.sh` file and call it.

## The architectural pivot that unlocks everything

> **Don't fight the render model. Iframe a real web app and let it own the
> hard parts.**

Trying to render an interactive shell as a flat text stream means
re-implementing terminal emulation (ANSI/CSI/OSC, alt-screen, cursor moves,
zle/readline echo suppression). It cannot be done well in a few hundred
lines.

Instead: run a local web server that already does the hard part, and embed
its UI in an `<iframe>`. The widget becomes a thin chrome (drag bar, resize
handle, position state) around proven software.

| Problem | Wrong approach | Right approach |
|---|---|---|
| Terminal | Custom PTY → strip ANSI → display | iframe **ttyd** (xterm.js) |
| REPL (Python/Node) | Capture stdout, render lines | iframe **Jupyter** or a local `flask` REPL UI |
| Log tailer with filters | Build interactive HTML controls + dispatch | iframe **frontail** or a tiny FastAPI page |
| Database explorer | Build query UI in widget | iframe **adminer** / **DBeaver web** |

ttyd specifically: `brew install ttyd`, `ttyd -p PORT -i 127.0.0.1 -W zsh`.
Localhost-bound, no auth, ~1 MB binary, MIT-licensed.

## Standard widget skeleton

```jsx
// index.jsx
const APP_PORT = 7681;
const APP_URL  = `http://127.0.0.1:${APP_PORT}`;
const WIDGET_DIR = "/absolute/path/to/this.widget";   // for sidecar scripts

const MIN_W = 320, MIN_H = 180;

export const refreshFrequency = 1500;       // health check cadence
export const command = `'${WIDGET_DIR}/bridge-tick.sh' ${APP_PORT}`;
export const initialState = {
  ready: false,
  pos:  { x: 60, y: 60 },
  size: { w: 720, h: 440 },
};

export const updateState = (event, prev) => {
  if (event && typeof event === "object") {
    if (event.type === "MOVE")   return { ...prev, pos:  { x: event.x, y: event.y } };
    if (event.type === "RESIZE") return { ...prev, size: { w: event.w, h: event.h } };
    if (typeof event.output === "string") {
      const health = event.output.split("\n", 1)[0].trim();
      return { ...prev, ready: health === "200" };
    }
  }
  return prev;
};

const startDrag = (e, dispatch, pos) => { /* document.addEventListener … */ };
const startResize = (e, dispatch, size) => { /* document.addEventListener … */ };

export const className = `
  & .root { position:absolute; overflow:hidden; border-radius:10px;
            background:#141418; box-shadow:0 12px 40px rgba(0,0,0,.5);
            display:flex; flex-direction:column; }
  & .drag { height:8px; cursor:move; background:rgba(255,255,255,0.04); }
  & .frame-wrap { flex:1; overflow:hidden; }
  & .frame { width:calc(100% + 18px); height:100%; border:none; }   /* hides scrollbar */
  & .resize { position:absolute; right:0; bottom:0; width:16px; height:16px;
              cursor:nwse-resize; }
`;

export const render = ({ ready, pos, size }, dispatch) => (
  <div>
    <div className="root" style={{
      left:`${pos.x}px`, top:`${pos.y}px`,
      width:`${size.w}px`, height:`${size.h}px`,
    }}>
      <div className="drag" onMouseDown={(e)=>startDrag(e, dispatch, pos)} />
      {ready
        ? <div className="frame-wrap"><iframe className="frame" src={APP_URL} /></div>
        : <div>starting…</div>}
      <div className="resize" onMouseDown={(e)=>startResize(e, dispatch, size)} />
    </div>
  </div>
);
```

```bash
# bridge-tick.sh — sidecar so multi-line shell isn't flattened
#!/bin/bash
PORT="${1:-7681}"
LOCK="/tmp/widget-${PORT}.lock"

if ! /usr/sbin/lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  if /bin/mkdir "$LOCK" 2>/dev/null; then
    trap '/bin/rmdir "$LOCK" 2>/dev/null' EXIT
    /usr/bin/nohup /opt/homebrew/bin/ttyd -p "$PORT" -i 127.0.0.1 -W \
      /bin/zsh -l >/tmp/widget-${PORT}.log 2>&1 &
    /bin/sleep 0.6
  fi
fi

HEALTH=$(/usr/bin/curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:"$PORT"/ \
         2>/dev/null || /bin/echo 000)
/bin/echo "$HEALTH"
```

## The five debugging traps that cost the most time

Each trap below burned a real iteration in the originating session. Recognise
them quickly:

1. **`/run/` returns HTTP 500 in Web Inspector** → your shell command is
   either timing out, exiting non-zero, or — most likely — multi-line bash
   that got serialised into one line. **Fix**: move script to a sidecar
   file. Verify with `head -50 /tmp/<your>-bridge.log`.

2. **`out of pty devices` after a few refreshes** → `command` runs every
   tick; if your spawn check is slow (`curl /health` against not-yet-bound
   port), you fork a new backend per tick. They pile up and exhaust PTY
   slots. **Fix**: check **port-binding** with `lsof -nP -iTCP:PORT -sTCP:LISTEN`
   (instant) plus a `mkdir <lockdir>` atomic guard so only one tick spawns.

3. **State stays empty even though `command` returns data** → you're
   treating `event` as a string. Inspect Übersicht's source:
   `dispatch({type:"UB/COMMAND_RAN", output})`. **Fix**: read `event.output`.

4. **CORS preflight rejects POSTs from widget** → `Content-Type:
   application/json` triggers preflight; many simple HTTP backends don't
   implement `OPTIONS`. **Fix**: send body as `Content-Type: text/plain`
   (CORS "simple request"); JSON-decoding servers don't care about the
   declared type. Or implement `do_OPTIONS` properly.

5. **Output is garbled glyph soup** → you piped a real PTY into a renderer
   that has no terminal emulator. Stop trying to strip ANSI in regex. Either
   iframe a real terminal (xterm.js via ttyd) or downgrade scope to
   one-shot `bash -c` runs without PTY.

## Multi-instance pattern

Übersicht treats each `*.widget` folder as one instance. To run N
independent copies:

1. Duplicate the widget folder N times (`work.widget`, `play.widget`, …).
2. Each copy's `index.jsx` sets a unique `APP_PORT`.
3. For per-instance shell config, accept a second argument in `bridge-tick.sh`
   and `env ZDOTDIR=$2 ttyd …`. Each `ZDOTDIR` is a folder containing its
   own `.zshrc` (and optionally `.zshenv`).

A small interactive Python installer that automates the cloning, port
allocation, and `ZDOTDIR` setup is worth writing once you have ≥ 2
instances; ad-hoc copy/paste is error-prone.

## Default-on safety: localhost binding

Always bind the embedded web app to `127.0.0.1` only (`-i 127.0.0.1` for
ttyd, `host="127.0.0.1"` for Python's `HTTPServer`, `--host 127.0.0.1` for
most frameworks). Without that the LAN can reach your shell. This is also
what lets you skip authentication: localhost connections already mean shell
access via the user account.

## Anti-patterns to refuse

- Embedding shell credentials, tokens, or paths in `command` strings — they
  are visible in `ps aux` every poll cycle.
- Using `setInterval` in `render` to fetch — Übersicht's `command` poll
  already handles cadence, and React-style re-renders blow away your
  intervals.
- Mutating Übersicht's state object — always return a new `{...prev, …}`.
- `dangerously…` flags or skipping safety checks to "make it work faster" —
  the bug is almost never permissions, it's always the architecture
  misunderstanding above.

## Verification checklist before shipping

- [ ] `widget.json` exists with `name`/`version`
- [ ] `command` is single-line (sidecar script if more than trivial)
- [ ] No top-level `import default class …` — only named exports
- [ ] Sidecar scripts: `chmod +x` and absolute paths quoted (the widgets
      directory contains spaces and `Übersicht` — quote everything)
- [ ] Backend bound to `127.0.0.1` only
- [ ] Lockfile guard around backend spawn
- [ ] Tested with **Web Inspector** open (right-click widget in dev mode)
- [ ] Tested by killing backend (`pkill …`) — widget should re-spawn within
      one tick
- [ ] State changes survive a `Refresh All Widgets` tick

## Reference: today's session in one sentence per phase

1. Read original code → spotted `export default class` + 12 undeclared
   globals. Verdict: was written for OpenCode, never adapted.
2. Rewrote with named exports, ANSI regex, fetch-based input. Failed:
   `bash -c` flattened multi-line script.
3. Pulled script into `bridge-tick.sh`. Worked, but PTY backend leaked file
   descriptors → "out of pty devices" because spawn check raced.
4. Added port-binding check + `mkdir` lockfile. Bridge stable, but xterm
   output garbled because zsh + p10k requires a real terminal emulator.
5. Tried bash with `--noediting --noprofile` — bash silently consumed
   input. Wrong layer.
6. Pivoted: replaced PTY relay with stateless `bash -c` runner. Worked but
   no `vim`/`htop`.
7. Pivoted again: ttyd + iframe. **One-iteration solve.** vim, htop, ssh,
   tmux, fzf — all working with zero terminal-emulation code on our side.
8. Polished: hide xterm scrollbar (iframe `width: calc(100% + 18px)`,
   wrap `overflow: hidden`), add per-instance `ZDOTDIR` support, ship
   `install.py`.

The lesson: **every architectural pivot was forced by reality, never by
new requirements.** Reach for the iframe-a-real-app pattern earlier next
time.
