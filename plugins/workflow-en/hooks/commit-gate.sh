#!/bin/sh
set -f
# commit-gate.sh — PreToolUse(matcher: Bash, command contains git commit)
# Before commit, checks ①docs/DECISIONS.inbox.md has undigested entries
# ②staged changes include source files but no docs/Progress.md update.
# Warn-once-then-allow: hashes staged content, blocks and warns the first
# time, allows through the next time if the hash is unchanged.

if [ -e "${HOME}/.claude/.docs-capture-off" ]; then
  exit 0
fi
if [ -n "${DOCS_CAPTURE_EVALS_HERMETIC:-}" ]; then
  exit 0
fi
if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

payload="$(cat)"

if ! printf '%s' "$payload" | jq -e '.' >/dev/null 2>&1; then
  exit 0
fi

tool_name="$(printf '%s' "$payload" | jq -r '.tool_name // empty' 2>/dev/null)"
if [ "$tool_name" != "Bash" ]; then
  exit 0
fi

command_str="$(printf '%s' "$payload" | jq -r '.tool_input.command // empty' 2>/dev/null)"
# git commit detection: requires "git commit" to appear in a lexical command
# position (start of line, or right after &&, ;, | allowing whitespace in
# between) rather than a plain substring match against the whole command
# string -- this avoids false positives from text inside quotes/heredoc
# bodies (e.g. git commit -m "... mentions git commit ...") being mistaken
# for an actual commit invocation.
is_git_commit=0
old_ifs="$IFS"
IFS='
'
for line in $command_str; do
  rest="$line"
  while [ -n "$rest" ]; do
    # strip leading whitespace
    rest="${rest#"${rest%%[![:space:]]*}"}"
    case "$rest" in
      "git commit"|"git commit "*)
        is_git_commit=1
        break 2
        ;;
    esac
    # find the next && ; | separator and keep checking the remainder of the line
    case "$rest" in
      *"&&"*) rest="${rest#*&&}" ;;
      *";"*) rest="${rest#*;}" ;;
      *"|"*) rest="${rest#*|}" ;;
      *) rest="" ;;
    esac
  done
done
IFS="$old_ifs"
if [ "$is_git_commit" -ne 1 ]; then
  exit 0
fi

cwd="$(printf '%s' "$payload" | jq -r '.cwd // empty' 2>/dev/null)"
[ -n "$cwd" ] || cwd="$(pwd)"

if ! git -C "$cwd" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi
if [ ! -d "$cwd/docs" ]; then
  exit 0
fi

git_dir="$(git -C "$cwd" rev-parse --git-dir 2>/dev/null)"
[ -n "$git_dir" ] || exit 0
case "$git_dir" in
  /*) : ;;
  *) git_dir="$cwd/$git_dir" ;;
esac

reasons=""

inbox="$cwd/docs/DECISIONS.inbox.md"
if [ -f "$inbox" ]; then
  pending="$(grep -c '^## ' "$inbox" 2>/dev/null)"
  case "$pending" in
    ''|*[!0-9]*) pending=0 ;;
  esac
  if [ "$pending" -gt 0 ]; then
    reasons="${reasons}DECISIONS.inbox.md has ${pending} pending draft entr$( [ "$pending" -eq 1 ] && echo y || echo ies ): distill decisions into What/Why/Changes in DECISIONS.md, move requirements into the REQUIREMENTS goal ledger, delete noise.\n"
  fi
fi

staged_files="$(git -C "$cwd" diff --cached --name-only 2>/dev/null)"
has_source=0
has_progress=0
old_ifs="$IFS"
IFS='
'
for f in $staged_files; do
  case "$f" in
    docs/Progress.md) has_progress=1 ;;
  esac
  base="${f##*/}"
  case "$f" in
    docs/*) : ;;
    *.md|*.json|*.yml|*.yaml|*.txt|*.gitignore|*.lock) : ;;
    *.sh|*.py|*.js|*.jsx|*.ts|*.tsx|*.go|*.rb|*.java|*.rs|*.c|*.cpp|*.h|*.hpp|*.php|*.sql|*.css|*.html|*.vue|*.kt|*.swift|*.scss)
      has_source=1 ;;
    */bin/*|bin/*|*/scripts/*|scripts/*)
      # extensionless files under this directory are usually executable scripts, also counts as source
      case "$base" in
        *.*) : ;;
        *) has_source=1 ;;
      esac
      ;;
    *)
      # common extensionless build/orchestration files
      case "$base" in
        Makefile|Dockerfile|Rakefile|Gemfile|Vagrantfile|Procfile|Jenkinsfile) has_source=1 ;;
      esac
      ;;
  esac
done
IFS="$old_ifs"

if [ "$has_source" -eq 1 ] && [ "$has_progress" -eq 0 ]; then
  reasons="${reasons}staged changes include source files but no docs/Progress.md update: add a changelog line before committing.\n"
fi

if [ -z "$reasons" ]; then
  exit 0
fi

if command -v shasum >/dev/null 2>&1; then
  diff_hash="$(git -C "$cwd" diff --cached 2>/dev/null | shasum -a 256 | awk '{print $1}')"
else
  diff_hash="$(git -C "$cwd" diff --cached 2>/dev/null | cksum | awk '{print $1"-"$2}')"
fi

warn_file="$git_dir/docs-capture-warned"
prev_hash=""
[ -f "$warn_file" ] && prev_hash="$(cat "$warn_file" 2>/dev/null)"

if [ -n "$diff_hash" ] && [ "$diff_hash" = "$prev_hash" ]; then
  exit 0
fi

if [ -n "$diff_hash" ]; then
  printf '%s' "$diff_hash" > "$warn_file" 2>/dev/null
fi

reasons="${reasons}If nothing needs to be added, re-run this command as-is to proceed (the same staged content is only flagged once).\n"
# The \n in $reasons are literal backslash-n (used for line breaks); use %b so
# printf interprets the escapes in the argument, instead of passing $reasons
# as the format string itself as before (any % in the content would then be
# misinterpreted).
reason_text="$(printf '%b' "$reasons")"
jq -n --arg reason "$reason_text" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: $reason
  }
}'
exit 0
