#!/bin/sh
# capture-decisions.sh — PostToolUse(matcher: AskUserQuestion)
# 把拍板问答确定性追加进项目 docs/DECISIONS.inbox.md。
# 失败必须静默：任何异常都不得影响会话，全程 exit 0。
# 数据文件/自身路径一律用 $(dirname "$0") 相对定位，脚本将来会被拷到 ~/.claude/hooks/ 独立运行。

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
  # 连 JSON 都不是，拿不到 cwd，无处可写，静默退出
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

inbox="$cwd/docs/DECISIONS.inbox.md"

session_id="$(printf '%s' "$payload" | jq -r '.session_id // empty' 2>/dev/null)"
sid8="$(printf '%s' "$session_id" | cut -c1-8)"
now="$(date '+%Y-%m-%d %H:%M')"

# inbox 已存在且末尾不是换行时先补一个，防止新条目的 "## " 粘在上一条最后一行末尾
# （拖累 grep -c '^## ' 的条目计数）。
ensure_inbox_trailing_newline() {
  if [ -s "$inbox" ]; then
    trailing_nl="$(tail -c 1 "$inbox" 2>/dev/null | wc -l | tr -d ' ')"
    if [ "$trailing_nl" = "0" ]; then
      printf '\n' >> "$inbox" 2>/dev/null
    fi
  fi
}

write_raw_fallback() {
  ensure_inbox_trailing_newline
  {
    printf '## %s %s\n' "$now" "$sid8"
    printf '**解析失败,原始负载**:\n'
    printf '```json\n'
    printf '%s\n' "$payload"
    printf '```\n\n'
  } >> "$inbox" 2>/dev/null
  exit 0
}

tool_response_type="$(printf '%s' "$payload" | jq -r '.tool_response | type' 2>/dev/null)"
if [ "$tool_response_type" = "string" ]; then
  # 用户取消/拒绝问答时 tool_response 是一段以 "Error: ..." 开头的说明字符串，
  # 不是真实决策数据，直接放行，不污染 inbox、不触发原始 JSON 兜底。
  exit 0
fi

has_shape="$(printf '%s' "$payload" | jq -e '
  (.tool_response.questions | type) == "array" and
  (.tool_response.answers | type) == "object" and
  ((.tool_response.questions | length) > 0)
' >/dev/null 2>&1 && echo yes || echo no)"

if [ "$has_shape" != "yes" ]; then
  write_raw_fallback
fi

block="$(printf '%s' "$payload" | jq -r --arg now "$now" --arg sid8 "$sid8" '
  # 精确成员比对：不对 $selected 按 ", " 切分（label 本身可能含 ", "，切分会误判该选项为
  # 未知候选/Other）。改为逐步用完整 label 字符串消费 $selected 前缀（贪心，优先匹配更长的
  # label），全部消费完才判定为已知候选组合。
  def consumeLabels($labels):
    . as $s
    | if $s == "" then true
      else
        ($labels | sort_by(-length) | map(select($s | startswith(.)))) as $matches
        | if ($matches | length) == 0 then false
          else
            reduce $matches[] as $m (false;
              if . then .
              else
                ($s[($m | length):]) as $rest
                | if $rest == "" then true
                  elif ($rest | startswith(", ")) then ($rest[2:] | consumeLabels($labels))
                  else false
                  end
              end)
          end
      end;
  .tool_response as $r
  | ($r.questions // []) as $qs
  | ($r.answers // {}) as $ans
  | $qs[]
  | . as $q
  | ($q.question // "") as $qtext
  | ($ans[$qtext] // "") as $selected
  | (($q.options // []) | map(.label // "")) as $labels
  | ($labels | join(" | ")) as $cands
  | (if $selected == "" then true else ($selected | consumeLabels($labels)) end) as $allKnown
  | "## \($now) \($sid8)\n" +
    "**Q**: \($qtext)\n" +
    "**候选**: \($cands)\n" +
    "**选择**: \($selected)\n" +
    (if ($allKnown | not) and ($selected != "") then "**备注**: \($selected)\n" else "" end) +
    "\n"
' 2>/dev/null)"
jq_status=$?

if [ "$jq_status" -ne 0 ] || [ -z "$block" ]; then
  write_raw_fallback
fi

# 命令替换会剥掉 $block 末尾全部换行；追加时补回两个换行（含条目间空行分隔），
# 避免下一条 "## " 粘在上一条最后一行末尾。
ensure_inbox_trailing_newline
printf '%s\n\n' "$block" >> "$inbox" 2>/dev/null
exit 0
