# Terminal Widget for Übersicht

A draggable, resizable desktop terminal that runs your real shell —
**vim, htop, ssh, tmux, fzf** all work — by embedding [ttyd](https://github.com/tsl0922/ttyd)
inside an Übersicht widget.

![architecture](https://img.shields.io/badge/stack-Übersicht%20%2B%20ttyd%20%2B%20xterm.js-blue)

---

## Why this exists

Übersicht widgets render a flat HTML/JS page on the desktop — they have no
built-in terminal emulator. Naïve PTY-relay implementations (the original
design of this widget) garble interactive programs because there is no one to
interpret ANSI cursor sequences, alt-screen switches, or per-keystroke echo.

This widget delegates that work to **xterm.js**, packaged by **ttyd** as a
tiny localhost web terminal, and wraps it in a movable Übersicht container.
The widget itself is ~150 lines of JSX — all the terminal heavy-lifting is
done by mature, battle-tested code.

```
┌─────────────────────────────────────────┐
│  Übersicht widget (index.jsx)           │
│  ┌──────────────────────────────────┐   │
│  │  <iframe src=localhost:7681>     │   │   ←  xterm.js front end
│  │   ▲                              │   │
│  └───┼──────────────────────────────┘   │
└──────┼──────────────────────────────────┘
       │  WebSocket
       ▼
   ttyd ──spawns──► /bin/zsh -l   (your real shell)
```

---

## Features

- ✅ Full interactive shell — vim, htop, ssh, tmux, fzf, less, watch
- ✅ Powerlevel10k / oh-my-zsh / Nerd Font glyphs render correctly
- ✅ Drag to move (top 8 px strip), drag bottom-right corner to resize
- ✅ Multiple independent instances (each with its own port + `.zshrc`)
- ✅ Hidden scrollbar for a clean desktop look
- ✅ No login screen, localhost-only — never exposed to the network

---

## Requirements

| Dependency | Install |
|---|---|
| macOS                              | already there |
| [Übersicht](https://tracesof.net/uebersicht/) | App Store / `brew install --cask ubersicht` |
| [ttyd](https://github.com/tsl0922/ttyd) ≥ 1.7 | `brew install ttyd` |
| zsh (or any shell of your choice)  | macOS ships with zsh |
| A Nerd Font (optional, for prompt glyphs) | `brew install font-jetbrains-mono-nerd-font` |

---

## Install

### Option A — interactive installer (recommended)

```bash
cd "/Users/<you>/Library/Application Support/Übersicht/widgets/terminal-widget.widget"
python3 install.py
```

The installer walks you through:
1. Checking ttyd / Übersicht
2. Choosing how many independent widget instances to create
3. Picking a port and (optionally) a custom `ZDOTDIR` for each instance
4. Cloning the widget folder, patching constants, and refreshing Übersicht

### Option B — manual

1. Drop this folder into `~/Library/Application Support/Übersicht/widgets/`
2. Übersicht menu → **Refresh All Widgets**

That's it. The widget will spawn ttyd on first tick and connect to it.

---

## Run multiple independent terminals

Each instance needs (a) its own widget folder, (b) a unique port, and
optionally (c) its own `.zshrc`.

The installer automates this. Manually:

```bash
# 1. Clone the widget folder
cp -R terminal-widget.widget terminal-widget-work.widget

# 2. (optional) Prepare a separate zsh config dir
mkdir -p ~/.config/widget-zsh-work
cp ~/.zshrc ~/.config/widget-zsh-work/.zshrc
# … edit to taste — different aliases, prompt, PATH, etc.

# 3. Edit the new widget's index.jsx — change the two constants at the top:
#       const TTYD_PORT = 7682;
#       const ZDOTDIR   = "/Users/scottchen/.config/widget-zsh-work";
```

Refresh Übersicht and you have a second, fully isolated zsh session living
on the desktop.

---

## File layout

```
terminal-widget.widget/
├── index.jsx          ← Übersicht widget: iframe + drag/resize + state
├── bridge-tick.sh     ← per-poll launcher: ensures ttyd is running
├── install.py         ← interactive installer / instance cloner
├── widget.json        ← Übersicht metadata
└── README.md
```

Logs:
- `/tmp/terminal-widget-ttyd-<port>.log` — ttyd's stderr per instance
- `/tmp/terminal-widget-ttyd-<port>.lock` — race-prevention lock dir

---

## Configuration knobs

Top of `index.jsx`:

```js
const TTYD_PORT = 7681;                                     // unique per instance
const ZDOTDIR   = "/Users/scottchen/.config/widget-zsh-a";  // "" → use ~/.zshrc
```

Inside `bridge-tick.sh`:

```bash
SHELL_BIN="/bin/zsh"   # change to bash / fish / nushell etc.
```

ttyd theming (also in `bridge-tick.sh`) — passed via `-t key=value`:

```bash
-t 'fontFamily=JetBrainsMono Nerd Font, Menlo, monospace'
-t 'fontSize=13'
-t 'theme={"background":"#141418","foreground":"#d4d4d4","cursor":"#5fd7af"}'
-t 'cursorStyle=bar'
```

Full xterm.js options: <https://xtermjs.org/docs/api/terminal/interfaces/iterminaloptions/>

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "starting ttyd…" never goes away | Check `cat /tmp/terminal-widget-ttyd-7681.log` — typically a port conflict or missing `ttyd` binary |
| Widget loads but iframe is blank | Refresh once more; ttyd needs ~0.5 s to bind on first launch |
| Glyphs show as boxes | Install a Nerd Font and update `fontFamily` in `bridge-tick.sh` |
| Two widgets fight over the same shell | They share a port — give each its own `TTYD_PORT` |
| Powerlevel10k complains about instant prompt | Add `POWERLEVEL9K_INSTANT_PROMPT=quiet` to your `.zshrc` (or `.p10k.zsh`) |
| Want a true logout instead of disconnect on close | Restart Übersicht or `pkill -f 'ttyd -p <port>'` |

### Reset everything

```bash
pkill -f 'ttyd -p 768'              # kills all widget ttyds in the 768x range
rm -f /tmp/terminal-widget-ttyd-*   # logs + lock dirs
```

---

## Security

- ttyd binds to **127.0.0.1 only** (`-i 127.0.0.1`). Nothing on your LAN can
  reach it.
- No authentication is required for localhost connections — anyone able to
  open `http://127.0.0.1:7681` already has shell access via your user account
  anyway.
- If you don't trust other local users on this Mac, add `--credential
  user:password` to the ttyd invocation in `bridge-tick.sh`.

---

## License

MIT. ttyd is also MIT. xterm.js is MIT.
Author: Scott Chen.
