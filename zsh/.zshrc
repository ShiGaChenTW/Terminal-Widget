# ─────────────────────────────────────────────────────────────────────────────
# Übersicht Terminal Widget — 內建 zsh 設定檔
# ─────────────────────────────────────────────────────────────────────────────
# 這份 .zshrc 只給 widget 內的 zsh 用，不會影響你平常的終端機設定。
# 修改後重新載入：在 macOS 終端執行 `pkill -f 'ttyd -p 7681'`，下一次 widget
# poll 時會自動重新啟動 ttyd，新設定就會生效。
#
# 可調整區塊（依出現順序）：
#   1. PROMPT      — 提示字元樣式（顏色、層級、符號）
#   2. 招呼語      — 開啟時的歡迎文字
#   3. AUTORUN     — 啟動後自動執行的指令（留空就不跑）
# ─────────────────────────────────────────────────────────────────────────────

# ── Shell 行為（一般不需要動）──────────────────────────────────────────────
export CLICOLOR=1
export LSCOLORS=ExFxCxDxBxegedabagacad
autoload -U colors && colors

# 歷史紀錄獨立存放，不汙染主終端機的 history
HISTFILE="$HOME/.zsh_history_widget"
HISTSIZE=5000
SAVEHIST=5000
setopt INC_APPEND_HISTORY HIST_IGNORE_DUPS HIST_REDUCE_BLANKS

# Homebrew 路徑（Apple Silicon 預設）
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"

# 即使 p10k 被誤載入也保持安靜
typeset -g POWERLEVEL9K_INSTANT_PROMPT=quiet

# ── 1. 提示字元（PROMPT）──────────────────────────────────────────────────
# %2~  → 最多顯示後 2 段路徑，家目錄會自動轉成 ~
#        例：~/Documents/Coding-Project/Project_X/internal/app
#            會顯示成 → internal/app
# %F{...}…%f  → 用顏色（green / cyan / magenta / yellow / red / blue / white）
# 想改成 1 層就把 %2~ 改成 %1~；想顯示完整路徑用 %~
PROMPT='%F{green}%2~%f %F{cyan}[zsh]%f %F{magenta}❯%f '
RPROMPT=''

# ── 2. 招呼語（每次 widget 啟動時印一次）─────────────────────────────────
# 改成你想要的文字即可；想加多行就再加 print -P "..." 即可。
# %F{cyan}…%f 是顏色控制，留著比較好看；不想要顏色就用 print "純文字"
print -P "%F{cyan}Hi Scott — terminal ready.%f"
print

# ── 3. 啟動自動執行指令（AUTORUN）────────────────────────────────────────
# 留空 → 不執行任何東西
# 有值 → 每次 ttyd 拉起新的 zsh 時（亦即每次 widget「重啟」時）會跑這條指令
# 範例：
#   WIDGET_AUTORUN="cd ~/Documents/Coding-Project && ls"
#   WIDGET_AUTORUN="tmux attach -t main || tmux new -s main"
#   WIDGET_AUTORUN="ssh dev-server"
#   WIDGET_AUTORUN="claude"
# 注意：指令裡有雙引號的話用 \" 跳脫
WIDGET_AUTORUN=""
[[ -n "$WIDGET_AUTORUN" ]] && eval "$WIDGET_AUTORUN"
