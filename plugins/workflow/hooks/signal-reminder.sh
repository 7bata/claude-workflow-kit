#!/bin/sh
# signal-reminder.sh — UserPromptSubmit
# 用户消息命中决策/需求词表时，stdout 注入一行提醒；不写文件、不拦截。
# 词表数据文件用 $(dirname "$0") 相对定位，脚本将来会被拷到 ~/.claude/hooks/ 独立运行。

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

prompt_text="$(printf '%s' "$payload" | jq -r '.prompt // empty' 2>/dev/null)"
[ -n "$prompt_text" ] || exit 0

cwd="$(printf '%s' "$payload" | jq -r '.cwd // empty' 2>/dev/null)"
[ -n "$cwd" ] || cwd="$(pwd)"

if ! git -C "$cwd" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi
if [ ! -d "$cwd/docs" ]; then
  exit 0
fi

script_dir="$(cd "$(dirname "$0")" && pwd)"
decision_file="$script_dir/signals-decision.txt"
requirement_file="$script_dir/signals-requirement.txt"
veto_file="$script_dir/signals-veto.txt"

# 子句切分:整条消息先按 。!?;、换行、逗号(中/英文)及英文 .!?; 切开，
# 命中/压制判定逐子句执行，压制不跨句(2026-08-14 第三轮修订，依评审处方)。
# 逐个分隔符做字面替换(非字符集)，规避 sed/awk 字符集对多字节 UTF-8 的处理风险。
split_into_clauses() {
  printf '%s' "$1" | sed \
    -e 's/。/\
/g' -e 's/！/\
/g' -e 's/？/\
/g' -e 's/；/\
/g' -e 's/、/\
/g' -e 's/，/\
/g' -e 's/,/\
/g' -e 's/\./\
/g' -e 's/!/\
/g' -e 's/?/\
/g' -e 's/;/\
/g' -e 's/:/\
/g' -e 's/：/\
/g'
}

# 未加引号的 $(split_into_clauses) 展开不做路径展开(防用户消息含 * ? 等被 glob)
set -f

hit_decision=0
hit_requirement=0

old_ifs="$IFS"
IFS='
'
for clause in $(split_into_clauses "$prompt_text"); do
  [ -n "$clause" ] || continue

  clause_decision=0
  clause_requirement=0

  if [ -f "$decision_file" ]; then
    if printf '%s' "$clause" | grep -Eqf "$decision_file" 2>/dev/null; then
      clause_decision=1
    fi
  fi
  if [ -f "$requirement_file" ]; then
    if printf '%s' "$clause" | grep -Eqf "$requirement_file" 2>/dev/null; then
      clause_requirement=1
    fi
  fi

  if [ "$clause_decision" -eq 0 ] && [ "$clause_requirement" -eq 0 ]; then
    continue
  fi

  # 否决词表:疑问/否定/未定语境(如"...吗?" "还没" "不确定")在同一子句内
  # 出现时静默该子句的命中——压制只看同子句，不影响消息里的其他子句。
  if [ -f "$veto_file" ]; then
    if printf '%s' "$clause" | grep -Eqf "$veto_file" 2>/dev/null; then
      continue
    fi
  fi

  [ "$clause_decision" -eq 1 ] && hit_decision=1
  [ "$clause_requirement" -eq 1 ] && hit_requirement=1
done
IFS="$old_ifs"

if [ "$hit_decision" -eq 0 ] && [ "$hit_requirement" -eq 0 ]; then
  exit 0
fi

if [ "$hit_decision" -eq 1 ] && [ "$hit_requirement" -eq 1 ]; then
  kind="决策/需求"
elif [ "$hit_decision" -eq 1 ]; then
  kind="决策"
else
  kind="需求"
fi

inbox="$cwd/docs/DECISIONS.inbox.md"
pending=0
if [ -f "$inbox" ]; then
  pending="$(grep -c '^## ' "$inbox" 2>/dev/null)"
  case "$pending" in
    ''|*[!0-9]*) pending=0 ;;
  esac
fi

printf '上一条用户消息疑似含 %s 信号——若确为决策/需求,按当轮落账规则处理;若只是日常表述,忽略本提示即可(高召回低精度的软提醒,误报属预期)。DECISIONS.inbox 现有 %s 条待消化\n' "$kind" "$pending"
exit 0
