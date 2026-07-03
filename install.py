#!/usr/bin/env python3
"""Interactive installer / instance cloner for the Übersicht terminal widget.

Run from the widget folder:

    python3 install.py

It will:
  1. Verify ttyd and Übersicht are present (offer install commands if not).
  2. Sanity-check the current widget folder.
  3. Walk you through cloning N independent instances, each with its own
     port and (optionally) its own ZDOTDIR-based zsh config.
  4. Patch each clone's index.jsx, then refresh Übersicht.

The installer never overwrites without asking and never edits files outside
the widgets/ directory and the chosen ZDOTDIRs.
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Optional

# ── Terminal output helpers ───────────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GRN = "\033[32m"
YLW = "\033[33m"
CYA = "\033[36m"


def info(msg: str) -> None:
    print(f"{CYA}›{RESET} {msg}")


def ok(msg: str) -> None:
    print(f"{GRN}✓{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{YLW}!{RESET} {msg}")


def err(msg: str) -> None:
    print(f"{RED}✗{RESET} {msg}")


def section(title: str) -> None:
    print(f"\n{BOLD}── {title} ──{RESET}")


def ask(prompt: str, default: Optional[str] = None) -> str:
    suffix = f" {DIM}[{default}]{RESET}" if default else ""
    while True:
        try:
            raw = input(f"{prompt}{suffix} › ").strip()
        except EOFError:
            print()
            sys.exit(1)
        if raw:
            return raw
        if default is not None:
            return default
        warn("a value is required")


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "Y/n" if default else "y/N"
    raw = ask(f"{prompt} ({suffix})", default="y" if default else "n").lower()
    return raw.startswith("y")


def ask_int(prompt: str, default: int, lo: int = 1, hi: int = 65535) -> int:
    while True:
        raw = ask(prompt, default=str(default))
        try:
            v = int(raw)
        except ValueError:
            warn("not a number")
            continue
        if lo <= v <= hi:
            return v
        warn(f"out of range ({lo}–{hi})")


# ── Environment checks ────────────────────────────────────────────────────────
WIDGETS_DIR = Path(
    os.path.expanduser("~/Library/Application Support/Übersicht/widgets")
)
SCRIPT_DIR = Path(__file__).resolve().parent


def check_ttyd() -> bool:
    path = shutil.which("ttyd")
    if not path:
        err("ttyd not found")
        info("install with:  brew install ttyd")
        return False
    try:
        v = subprocess.check_output([path, "--version"], text=True, stderr=subprocess.STDOUT).strip()
    except subprocess.SubprocessError:
        v = "unknown"
    ok(f"ttyd at {path}  ({v})")
    return True


def check_uebersicht() -> bool:
    candidates = [
        Path("/Applications/Übersicht.app"),
        Path("/Applications/Ubersicht.app"),
        Path(os.path.expanduser("~/Applications/Übersicht.app")),
    ]
    for p in candidates:
        if p.exists():
            ok(f"Übersicht at {p}")
            return True
    err("Übersicht.app not found in /Applications")
    info("install with:  brew install --cask ubersicht")
    return False


def check_widgets_dir() -> bool:
    if not WIDGETS_DIR.exists():
        err(f"widgets folder missing: {WIDGETS_DIR}")
        info("Launch Übersicht once so it creates this folder, then re-run.")
        return False
    ok(f"widgets folder: {WIDGETS_DIR}")
    return True


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def first_free_port(start: int = 7681) -> int:
    p = start
    while p < 65535:
        if port_free(p):
            return p
        p += 1
    return start


# ── Widget patching ───────────────────────────────────────────────────────────
PORT_RE = re.compile(r"const\s+TTYD_PORT\s*=\s*\d+\s*;")
ZDOT_RE = re.compile(r'const\s+ZDOTDIR\s*=\s*"[^"]*"\s*;')
WDIR_RE = re.compile(r'const\s+WIDGET_DIR\s*=\s*\n?\s*"[^"]*"\s*;')
COMMAND_RE = re.compile(r"export\s+const\s+command\s*=\s*`[^`]*`\s*;")
GREET_RE = re.compile(r'^print -P "[^"]*"\s*$', re.MULTILINE)
AUTORUN_RE = re.compile(r'^WIDGET_AUTORUN="[^"]*"\s*$', re.MULTILINE)
DEFAULT_GREETING = "Hi Scott — terminal ready."


def patch_index(widget_dir: Path, port: int, zdotdir: str) -> None:
    f = widget_dir / "index.jsx"
    text = f.read_text(encoding="utf-8")

    text = PORT_RE.sub(f"const TTYD_PORT = {port};", text, count=1)
    text = ZDOT_RE.sub(f'const ZDOTDIR   = "{zdotdir}";', text, count=1)
    # WIDGET_DIR is multi-line in the source; use DOTALL via PORT_RE-style replace
    text = re.sub(
        r'const\s+WIDGET_DIR\s*=\s*"[^"]*"\s*;',
        f'const WIDGET_DIR =\n  "{widget_dir}";',
        text,
        count=1,
        flags=re.DOTALL,
    )

    f.write_text(text, encoding="utf-8")


def patch_command(widget_dir: Path, backend: str, vault: str, writable: bool) -> None:
    """Rewrite index.jsx's `export const command = …` line for the chosen backend.

    backend:
      "zsh"    → bridge-tick.sh PORT ZDOTDIR         (original desktop terminal)
      "pi"     → agent-bridge-tick.sh PORT VAULT     (Path A: ttyd wraps `pi` TUI)
      "pi-web" → pi-web-tick.sh PORT                 (Path B: iframe Pi web UI)

    ${WIDGET_DIR}/${TTYD_PORT}/${ZDOTDIR} stay as JS template refs so the rest
    of index.jsx (which reads those consts) keeps working untouched.
    """
    f = widget_dir / "index.jsx"
    text = f.read_text(encoding="utf-8")

    if backend == "pi":
        # PI_FLAGS='' lets the agent write/edit/bash; omitted → script default
        # (read-only: --tools read,grep,find,ls).
        prefix = "PI_FLAGS='' " if writable else ""
        vault_arg = f" '{vault}'" if vault else ""
        cmd = (
            "export const command = "
            f"`{prefix}'${{WIDGET_DIR}}/agent-bridge-tick.sh' ${{TTYD_PORT}}{vault_arg}`;"
        )
    elif backend == "pi-web":
        cmd = "export const command = `'${WIDGET_DIR}/pi-web-tick.sh' ${TTYD_PORT}`;"
    else:  # zsh (unchanged from the shipped default)
        cmd = "export const command = `'${WIDGET_DIR}/bridge-tick.sh' ${TTYD_PORT} '${ZDOTDIR}'`;"

    # Use a function replacement so backslashes / group refs in `cmd` are literal.
    text = COMMAND_RE.sub(lambda _m: cmd, text, count=1)
    f.write_text(text, encoding="utf-8")


def check_pi_cli() -> bool:
    path = shutil.which("pi")
    if path:
        ok(f"pi at {path}")
        return True
    warn("pi (Pi coding agent) not found")
    info("install with:  npm install -g --ignore-scripts @earendil-works/pi-coding-agent")
    return False


def check_pi_web() -> bool:
    path = shutil.which("pi-web")
    if path:
        ok(f"pi-web at {path}")
        return True
    warn("pi-web not found")
    info("install with:  npm install -g @jmfederico/pi-web  (Node 22+), then: pi-web install")
    return False


def patch_greeting(widget_dir: Path, greeting: str) -> None:
    """Replace the bundled .zshrc greeting line with the user's text.

    The bundled .zshrc has exactly one `print -P "..."` line at the end
    that prints the welcome message. We swap its content while keeping
    the surrounding zsh prompt-expansion sequences (%F{cyan}…%f) so the
    greeting still renders in colour.
    """
    rc = widget_dir / "zsh" / ".zshrc"
    if not rc.exists():
        warn(f"   no bundled zsh/.zshrc inside {widget_dir.name}; skipped greeting")
        return

    safe = greeting.replace('"', r'\"')
    new_line = f'print -P "%F{{cyan}}{safe}%f"'

    text = rc.read_text(encoding="utf-8")
    if GREET_RE.search(text):
        text = GREET_RE.sub(new_line, text, count=1)
    else:
        # File was modified by hand and no longer has our line; append.
        text = text.rstrip() + "\n\n" + new_line + "\nprint\n"
    rc.write_text(text, encoding="utf-8")


def patch_autorun(widget_dir: Path, autorun: str) -> None:
    """設定 zsh/.zshrc 裡的 WIDGET_AUTORUN — 每次 widget 啟動時自動跑的指令。

    autorun 為空字串時：把現有設定清空（不會執行任何東西）。
    autorun 有值時：把那條指令塞進 WIDGET_AUTORUN="…"，雙引號自動跳脫。
    """
    rc = widget_dir / "zsh" / ".zshrc"
    if not rc.exists():
        warn(f"   no bundled zsh/.zshrc inside {widget_dir.name}; skipped autorun")
        return

    safe = autorun.replace('\\', '\\\\').replace('"', r'\"')
    new_line = f'WIDGET_AUTORUN="{safe}"'

    text = rc.read_text(encoding="utf-8")
    if AUTORUN_RE.search(text):
        text = AUTORUN_RE.sub(new_line, text, count=1)
    else:
        text = text.rstrip() + "\n\n" + new_line + "\n"
    rc.write_text(text, encoding="utf-8")


def ensure_zdotdir(zdotdir: str) -> None:
    """Create ZDOTDIR with a starter .zshrc copied from ~/.zshrc if absent."""
    if not zdotdir:
        return
    p = Path(os.path.expanduser(zdotdir))
    p.mkdir(parents=True, exist_ok=True)
    rc = p / ".zshrc"
    if rc.exists():
        ok(f"ZDOTDIR ready (existing): {p}")
        return
    home_rc = Path(os.path.expanduser("~/.zshrc"))
    if home_rc.exists() and ask_yes_no(
        f"   seed {rc} from ~/.zshrc?", default=True
    ):
        shutil.copy2(home_rc, rc)
        ok(f"ZDOTDIR ready (seeded): {p}")
    else:
        rc.write_text("# Custom .zshrc for Übersicht terminal widget\n")
        ok(f"ZDOTDIR ready (empty stub): {p}")


def clone_widget(src: Path, dst: Path) -> None:
    if dst.exists():
        if not ask_yes_no(f"   {dst.name} already exists — overwrite?", default=False):
            raise SystemExit("aborted by user")
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    # Strip generated artefacts from the clone
    for sub in ("__pycache__", "scripts/__pycache__"):
        bad = dst / sub
        if bad.exists():
            shutil.rmtree(bad, ignore_errors=True)
    for stale in dst.glob("index.jsx.bak.*"):
        stale.unlink(missing_ok=True)


def refresh_uebersicht() -> None:
    """Ask Übersicht to reload all widgets via AppleScript."""
    script = (
        'tell application "System Events" to tell process "Übersicht" '
        "to click menu item \"Refresh All Widgets\" of menu 1 of menu bar item 1 of menu bar 2"
    )
    try:
        subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
        ok("requested Übersicht to refresh widgets")
    except FileNotFoundError:
        warn("osascript not available — refresh widgets manually")


# ── Flow ──────────────────────────────────────────────────────────────────────
def main() -> int:
    print(f"{BOLD}Übersicht Terminal Widget — installer{RESET}\n")

    section("Environment check")
    # ttyd is only needed for the zsh / Pi-TUI backends; pi-web needs none of it.
    # So a missing ttyd is a warning, not a hard stop — the backend picker will
    # tell you exactly what each choice needs.
    check_ttyd()
    fatal = [check_uebersicht(), check_widgets_dir()]
    if not all(fatal):
        err("fix the missing pieces above and re-run")
        return 1

    src = SCRIPT_DIR
    if src.parent != WIDGETS_DIR:
        warn(f"this installer lives outside {WIDGETS_DIR}")
        if ask_yes_no("copy this folder into the widgets directory first?", default=True):
            target = WIDGETS_DIR / src.name
            if target.exists():
                if not ask_yes_no(f"{target} exists — overwrite?", default=False):
                    return 1
                shutil.rmtree(target)
            shutil.copytree(src, target)
            ok(f"installed base widget at {target}")
            src = target

    section("Instances")
    n = ask_int("How many independent terminal widgets do you want?", default=1, lo=1, hi=8)

    instances: list[tuple] = []

    for i in range(n):
        print()
        info(f"Instance {i + 1} of {n}")
        if i == 0:
            name = src.name
            dst = src
            ok(f"   using existing folder: {dst.name}")
        else:
            stem = src.name.removesuffix(".widget")
            default_name = f"{stem}-{i + 1}.widget"
            name = ask("   widget folder name", default=default_name)
            if not name.endswith(".widget"):
                name += ".widget"
            dst = WIDGETS_DIR / name
            clone_widget(src, dst)
            ok(f"   cloned to: {dst.name}")

        # Pick what runs inside this widget.
        print(f"   {DIM}backend: what should this console run?{RESET}")
        print(f"     {DIM}1) zsh     — real shell terminal (ttyd)            [default]{RESET}")
        print(f"     {DIM}2) pi      — Pi agent TUI in ttyd (Path A)         needs ttyd + pi{RESET}")
        print(f"     {DIM}3) pi-web  — iframe Pi web UI, no ttyd (Path B)    needs pi-web{RESET}")
        choice = ask("   choose 1/2/3", default="1")
        backend = {"1": "zsh", "2": "pi", "3": "pi-web"}.get(choice.strip(), "zsh")

        # Sensible default port per backend, then bump to the first free one.
        default_port = {"zsh": 7681, "pi": 7690, "pi-web": 8504}[backend]
        suggested = default_port + i
        while not port_free(suggested):
            suggested += 1
        port = ask_int("   port", default=suggested)

        # Per-backend extras. zdotdir/greeting/autorun only apply to zsh.
        zdotdir = ""
        greeting = DEFAULT_GREETING
        autorun = ""
        vault = ""
        writable = False

        if backend == "zsh":
            if ask_yes_no("   use a custom .zshrc folder for this instance?", default=False):
                default_dir = os.path.expanduser(
                    f"~/.config/widget-zsh-{name.removesuffix('.widget')}"
                )
                zdotdir = ask("     ZDOTDIR (folder with its own .zshrc)", default=default_dir)
                zdotdir = os.path.expanduser(zdotdir)
                ensure_zdotdir(zdotdir)

            if not zdotdir:
                if ask_yes_no("   customise the welcome greeting line?", default=False):
                    greeting = ask("     greeting text", default=DEFAULT_GREETING)
                patch_greeting(dst, greeting)

                if ask_yes_no(
                    "   set an auto-run command on every widget start?", default=False
                ):
                    print(f"     {DIM}examples: 'cd ~/Documents && ls'  /  "
                          f"'tmux attach -t main || tmux new -s main'  /  'claude'{RESET}")
                    autorun = ask("     autorun command", default="")
                patch_autorun(dst, autorun)

        elif backend == "pi":
            check_pi_cli()
            vault = ask(
                "   Second Brain vault path (working dir; blank = $HOME)", default=""
            ) if ask_yes_no("   point this Pi at a Second Brain vault?", default=True) else ""
            if vault:
                vault = os.path.expanduser(vault)
                if not Path(vault).is_dir():
                    warn(f"     {vault} is not an existing folder — Pi will start in $HOME")
                    vault = ""
            writable = ask_yes_no(
                "   allow the agent to WRITE to the vault? (default read-only)", default=False
            )

        elif backend == "pi-web":
            check_pi_web()
            info("   pi-web serves its own web UI; set the vault in ~/.config/pi-web/config.json")
            info("   one-time setup (if not done):  pi-web install && pi-web doctor")

        patch_index(dst, port, zdotdir)
        patch_command(dst, backend, vault, writable)

        label = {"zsh": "zsh terminal", "pi": "Pi agent (ttyd)", "pi-web": "Pi web UI"}[backend]
        ok(f"   patched: backend={label}  port={port}")
        if backend == "zsh":
            ok(f"            ZDOTDIR={zdotdir or '(bundled zsh/)'}")
            if not zdotdir:
                ok(f"            greeting: \"{greeting}\"")
                ok(f"            autorun:  {autorun if autorun else '(none)'}")
        elif backend == "pi":
            ok(f"            vault={vault or '($HOME)'}  mode={'writable' if writable else 'read-only'}")
        instances.append((dst, port, backend, zdotdir, vault, writable, greeting, autorun))

    section("Activate")
    refresh_uebersicht()

    print()
    ok("Installed:")
    for dst, port, backend, zdot, vault, writable, greet, autorun in instances:
        label = {"zsh": "zsh terminal", "pi": "Pi agent (ttyd)", "pi-web": "Pi web UI"}[backend]
        print(f"   • {dst.name:<40s}  port {port}   {DIM}{label}{RESET}")
        if backend == "zsh":
            zlabel = zdot if zdot else "bundled zsh/"
            print(f"     {DIM}{zlabel}{RESET}")
            if not zdot:
                print(f"     {DIM}greeting: \"{greet}\"{RESET}")
                print(f"     {DIM}autorun:  {autorun if autorun else '(none)'}{RESET}")
        elif backend == "pi":
            print(f"     {DIM}vault: {vault or '($HOME)'}   mode: {'writable' if writable else 'read-only'}{RESET}")
        elif backend == "pi-web":
            print(f"     {DIM}iframes http://127.0.0.1:{port} — run 'pi-web install' if not up{RESET}")
    print()
    info("ttyd logs at /tmp/terminal-widget-ttyd-<port>.log (zsh/pi backends).")
    info("Pi agent logs at /tmp/terminal-widget-agent-<port>.log (pi backend).")
    info("To restart a backend: pkill -f 'ttyd -p <port>'  /  pi-web restart")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        err("aborted")
        sys.exit(130)
