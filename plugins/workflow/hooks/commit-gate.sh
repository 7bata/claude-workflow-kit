#!/bin/sh
set -f
# commit-gate.sh — PreToolUse(matcher: Bash，命令含 git commit)
# commit 前检查①DECISIONS.inbox 待消化条目②staged 含源码但未见 docs/Progress.md 更新。
# 首警二放：对 staged 内容取哈希，首次提示并阻止，哈希不变的下一次直接放行。

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
# git commit 识别：要求 "git commit" 出现在命令词法位置（行首，或紧跟 &&、;、| 之后，
# 允许其间有空白），而不是对整条命令字符串做子串匹配——避免命令里的引号内文本/heredoc
# 正文（例如 git commit -m "... 提到 git commit ..."）被误当成真实的 commit 调用。
is_git_commit=0
old_ifs="$IFS"
IFS='
'
for line in $command_str; do
  rest="$line"
  while [ -n "$rest" ]; do
    # 去掉前导空白
    rest="${rest#"${rest%%[![:space:]]*}"}"
    case "$rest" in
      "git commit"|"git commit "*)
        is_git_commit=1
        break 2
        ;;
    esac
    # 找下一个分隔符 && ; | 之后的片段，继续在同一行内检查
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
    reasons="${reasons}DECISIONS.inbox.md 有 ${pending} 条待消化草稿：提炼成 What/Why/Changes 进 DECISIONS.md，需求进 REQUIREMENTS 目标台账，噪音删除。\n"
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
      # 该目录下的无扩展名文件通常是可执行脚本，也算源码
      case "$base" in
        *.*) : ;;
        *) has_source=1 ;;
      esac
      ;;
    *)
      # 常见的无扩展名构建/编排文件
      case "$base" in
        Makefile|Dockerfile|Rakefile|Gemfile|Vagrantfile|Procfile|Jenkinsfile) has_source=1 ;;
      esac
      ;;
  esac
done
IFS="$old_ifs"

if [ "$has_source" -eq 1 ] && [ "$has_progress" -eq 0 ]; then
  reasons="${reasons}staged 改动含源码但未见 docs/Progress.md 更新：补一行变更日志再提交。\n"
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

reasons="${reasons}确认无需补充则原样重跑本命令即放行（同一 staged 内容只提示一次）。\n"
# reasons 里的 \n 是字面反斜杠+n（用于分行），用 %b 让 printf 解释参数里的转义，
# 而不是像原来那样把 $reasons 整个当格式串传给 printf（一旦内容混入用户输入的 % 会被误解释）。
reason_text="$(printf '%b' "$reasons")"
jq -n --arg reason "$reason_text" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: $reason
  }
}'
exit 0
