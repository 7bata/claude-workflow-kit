#!/bin/sh
# capture-decisions.sh — PostToolUse(matcher: AskUserQuestion)
# Deterministically append answered questions to the project's docs/DECISIONS.inbox.md.
# Failures must be silent: nothing here may ever affect the session, always exit 0.
# Data files / own path are always located relative to $(dirname "$0"), since this
# script will eventually be copied to ~/.claude/hooks/ and run standalone.

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
  # Not even valid JSON, can't get cwd, nowhere to write, exit silently
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

# If the inbox already exists and doesn't end with a newline, add one first, so
# a new entry's "## " doesn't stick to the end of the previous entry's last line
# (which would throw off the entry count from grep -c '^## ').
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
    printf '**Parse failed, raw payload**:\n'
    printf '```json\n'
    printf '%s\n' "$payload"
    printf '```\n\n'
  } >> "$inbox" 2>/dev/null
  exit 0
}

tool_response_type="$(printf '%s' "$payload" | jq -r '.tool_response | type' 2>/dev/null)"
if [ "$tool_response_type" = "string" ]; then
  # When the user cancels/rejects the question, tool_response is an explanatory
  # string starting with "Error: ..." -- not real decision data, pass through
  # without polluting the inbox or triggering the raw JSON fallback.
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
  # Exact member comparison: do not split $selected on ", " (a label itself may
  # contain ", ", splitting would misclassify that option as an unknown
  # candidate/Other). Instead greedily consume $selected using full label
  # strings as prefixes (longest label first); only counts as a known-candidate
  # combination once fully consumed.
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
    "**Candidates**: \($cands)\n" +
    "**Selected**: \($selected)\n" +
    (if ($allKnown | not) and ($selected != "") then "**Notes**: \($selected)\n" else "" end) +
    "\n"
' 2>/dev/null)"
jq_status=$?

if [ "$jq_status" -ne 0 ] || [ -z "$block" ]; then
  write_raw_fallback
fi

# Command substitution strips all trailing newlines from $block; add two back
# (including the blank-line separator between entries) when appending, so the
# next entry's "## " doesn't stick to the end of the previous entry's last line.
ensure_inbox_trailing_newline
printf '%s\n\n' "$block" >> "$inbox" 2>/dev/null
exit 0
