#!/bin/sh
# docs-capture-smoke-test.sh — smoke tests for capture-decisions.sh / signal-reminder.sh /
# commit-gate.sh (English plugin face). Mirrors plugins/workflow/hooks/docs-capture-smoke-test.sh
# but uses English fixtures/word lists; runs in a temp fixture git repo, never touches this repo.

HOOKS_DIR="$(cd "$(dirname "$0")" && pwd)"
CAPTURE_SH="$HOOKS_DIR/capture-decisions.sh"
REMINDER_SH="$HOOKS_DIR/signal-reminder.sh"
GATE_SH="$HOOKS_DIR/commit-gate.sh"

PASS=0
FAIL=0
FAIL_MSGS=""

fail() {
  FAIL=$((FAIL + 1))
  FAIL_MSGS="${FAIL_MSGS}FAIL: $1
"
}

pass() {
  PASS=$((PASS + 1))
}

assert_contains() {
  # $1=haystack $2=needle $3=label
  case "$1" in
    *"$2"*) pass ;;
    *) fail "$3 — expected to contain: [$2] got: [$1]" ;;
  esac
}

assert_not_contains() {
  case "$1" in
    *"$2"*) fail "$3 — expected NOT to contain: [$2] got: [$1]" ;;
    *) pass ;;
  esac
}

assert_eq() {
  # $1=actual $2=expected $3=label
  if [ "$1" = "$2" ]; then
    pass
  else
    fail "$3 — expected [$2] got [$1]"
  fi
}

assert_empty() {
  if [ -z "$1" ]; then
    pass
  else
    fail "$2 — expected empty, got: [$1]"
  fi
}

# ---- fixture environment ----
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

REPO="$WORK/fixture-repo"
mkdir -p "$REPO/docs"
git -C "$REPO" init -q
git -C "$REPO" config user.email test@example.com
git -C "$REPO" config user.name "Test"
: > "$REPO/docs/.gitkeep"
git -C "$REPO" add -A
git -C "$REPO" commit -q -m init

NON_DOCS_REPO="$WORK/no-docs-repo"
mkdir -p "$NON_DOCS_REPO"
git -C "$NON_DOCS_REPO" init -q
git -C "$NON_DOCS_REPO" config user.email test@example.com
git -C "$NON_DOCS_REPO" config user.name "Test"
: > "$NON_DOCS_REPO/README.md"
git -C "$NON_DOCS_REPO" add -A
git -C "$NON_DOCS_REPO" commit -q -m init

# =========================================================
# ① capture-decisions.sh: inbox entry format is correct
# =========================================================
INBOX="$REPO/docs/DECISIONS.inbox.md"
rm -f "$INBOX"

PAYLOAD_1='{
  "session_id": "abcdef1234567890",
  "cwd": "'"$REPO"'",
  "hook_event_name": "PostToolUse",
  "tool_name": "AskUserQuestion",
  "tool_response": {
    "questions": [
      {
        "question": "Which database should we use?",
        "header": "Database",
        "multiSelect": false,
        "options": [
          {"label": "PostgreSQL (Recommended)", "description": "..."},
          {"label": "SQLite", "description": "..."}
        ]
      }
    ],
    "answers": {
      "Which database should we use?": "PostgreSQL (Recommended)"
    }
  }
}'

printf '%s' "$PAYLOAD_1" | sh "$CAPTURE_SH"

OUT1="$(cat "$INBOX" 2>/dev/null)"
assert_contains "$OUT1" "## " "①inbox has a ## heading"
assert_contains "$OUT1" "abcdef12" "①sid8 first 8 chars"
assert_contains "$OUT1" "**Q**: Which database should we use?" "①Q line"
assert_contains "$OUT1" "**Candidates**: PostgreSQL (Recommended) | SQLite" "①candidates line"
assert_contains "$OUT1" "**Selected**: PostgreSQL (Recommended)" "①selected line"

# =========================================================
# ② Other/free-text answer is preserved verbatim
# =========================================================
rm -f "$INBOX"

PAYLOAD_2='{
  "session_id": "22223333aaaa",
  "cwd": "'"$REPO"'",
  "tool_response": {
    "questions": [
      {
        "question": "Anything else to add?",
        "options": [
          {"label": "A"},
          {"label": "B"}
        ]
      }
    ],
    "answers": {
      "Anything else to add?": "Neither, I want a custom approach: ship an MVP first, then iterate"
    }
  }
}'
printf '%s' "$PAYLOAD_2" | sh "$CAPTURE_SH"
OUT2="$(cat "$INBOX" 2>/dev/null)"
assert_contains "$OUT2" "Neither, I want a custom approach: ship an MVP first, then iterate" "②Other text fully preserved (selected line)"
assert_contains "$OUT2" "**Notes**: Neither, I want a custom approach: ship an MVP first, then iterate" "②Other text fully preserved (notes line)"

# =========================================================
# ③ Non-methodology directory: zero output
# =========================================================
NO_DOCS_DIR="$WORK/no-docs-target"
mkdir -p "$NO_DOCS_DIR"
git -C "$NO_DOCS_DIR" init -q 2>/dev/null
PAYLOAD_3='{"session_id":"zzz","cwd":"'"$NO_DOCS_DIR"'","tool_response":{"questions":[{"question":"q","options":[]}],"answers":{"q":"a"}}}'
OUT3="$(printf '%s' "$PAYLOAD_3" | sh "$CAPTURE_SH")"
assert_empty "$OUT3" "③non-methodology dir (no docs/): capture zero stdout output"
[ -f "$NO_DOCS_DIR/docs/DECISIONS.inbox.md" ] && fail "③non-methodology dir should not create inbox" || pass

OUT3B="$(printf '%s' "$PAYLOAD_3" | sh "$REMINDER_SH")"
# reminder is driven by the prompt field; the non-git/no-docs zero-output case for
# reminder is verified separately below (see ⑤).

# =========================================================
# ④ Parse failure falls back to raw JSON
# =========================================================
rm -f "$INBOX"
BAD_PAYLOAD='{"session_id":"bad1","cwd":"'"$REPO"'","tool_response":{"unexpected":"shape"}}'
printf '%s' "$BAD_PAYLOAD" | sh "$CAPTURE_SH"
OUT4="$(cat "$INBOX" 2>/dev/null)"
assert_contains "$OUT4" '```json' "④parse-failure raw JSON fenced block"
assert_contains "$OUT4" '"unexpected"' "④parse-failure raw payload content preserved"

# Completely invalid JSON must not crash, and must not write anything (cwd is
# unreachable, so it must exit silently).
rm -f "$INBOX"
printf 'not even json{{{' | sh "$CAPTURE_SH"
if [ -f "$INBOX" ]; then
  fail "④invalid JSON should not produce inbox content"
else
  pass
fi

# =========================================================
# ⑤ Layer-2 word-list judging cases: judgment cases are owned separately from
#    the word-list implementation (spec hard rule) — this file only asserts
#    "input sentence -> expected hit/no-hit and which signal category", and
#    does not prescribe how clause splitting etc. is implemented internally.
#
# Suite A — positive examples (>=12, of which >=8 are multi-clause real
#           messages: a decision/requirement main clause plus an incidental
#           question/small-talk clause) — all must be asserted to hit their
#           category.
# Suite B — general trap sentences: contain word-list roots but sit in a
#           questioning/negating/undecided context (an in-clause veto phrase)
#           — all must be asserted NOT to hit.
# Suite C — "no suppression word" trap sub-class (>=20): the sentence does
#           contain a decision/requirement word-list root, used as a noun/verb
#           continuation without an object anchor or end-of-clause anchor, and
#           contains ZERO veto phrases — this is what exposes bare-pattern
#           over-matching (suppression alone can't save these); all must be
#           asserted NOT to hit, one false positive fails the whole run.
# =========================================================
rm -f "$INBOX"

DECISION_SENTENCES="That's settled
That's final no more discussion
Decided
The final decision
We'll go with this
We'll use the React plan
Let's go with this one
Let's just go with it
Going with that
Let's finalize this design
We finally selected the Go framework
Locking in this plan
The plan is decided
Selected plan A as the final baseline
We selected as the final approach"

REQUIREMENT_SENTENCES="I want to export this report
I want it to work offline
I want to support offline mode
I want to add a search feature
I want it to automatically run tests
Make sure it can auto rollback
It'd be best to add a search box
It'd be best to turn it into a feature
It'd be best to support multi-language
Make sure the task gets done
This feature must be done
This needs to be done properly
Don't forget to add logging
Must support multi-language
We need to add a module
Add one more feature
There's a requirement to add a permission check
We need to add retry logic
It must have a rollback plan"

# ---------------------------------------------------------
# Suite A — multi-clause real messages (decision/requirement main clause plus
# an incidental question/small-talk clause). spec §3 layer-2: suppression
# never crosses clause boundaries, so the trailing question must NOT suppress
# the main clause's hit.
# ---------------------------------------------------------
MULTICLAUSE_DECISION_SENTENCES="That's settled, we'll use PostgreSQL. Can you check this error for me?
Decided, we'll go with React. Do you like this icon?
Let's go with this, starting with the backend. By the way, what's for lunch?
We finally selected the Go framework; can you check the dependency version for me?
The final decision then. Is your environment set up on your end?
Let's just go with it, moving forward. Have you reviewed this PR yet?
Locking in this plan. What's the weather like today?
Going with it, no other option really. Did you review this PR yet?"

MULTICLAUSE_REQUIREMENT_SENTENCES="I want to add a search box. What do you think of this color scheme?
Must support multi-language, this is top priority. Just to check, what time is it now?
Need to add an export feature, let's schedule it soon. Is your test environment ready on your end?
Don't forget to add logging, this really matters. By the way, what's the deployment window today?"

# Daily sentences (contain none of the word-list terms; confirms the lists
# don't fire on unrelated text)
DAILY_SENTENCES="We can think about this a bit more
The weather is nice today, good for coding
Can you take a look at this code for a bug
How is the performance of this function
Let's compare the pros and cons of the three candidates
Let's run the tests and see the results
This UI looks pretty good
The database connection failed, here's the error message
I'd like to understand how this library is used
The build finished without errors this time"

# ---------------------------------------------------------
# Suite B — general trap sentences: contain a word-list root but sit inside a
# questioning/negating/undecided clause (in-clause veto phrase) — verifies
# spec §5's asymmetric gate: one false positive fails the whole run.
# ---------------------------------------------------------
TRAP_SENTENCES="I'm not sure that's the final decision
Maybe we'll go with this
Should we finalize this design
We haven't decided whether to lock in this plan
It's undecided but let's go with this one
Not sure if the plan is decided
Which one should we say is selected as the final approach
No rush but that's settled
It's not yet decided
I'm not sure I want to add a search feature
Maybe it'd be best to add a search box
Should we make sure the task gets done
Not sure if this feature must be done
We haven't decided but we need to add a permission
Don't forget to add logging even though we're not sure
Maybe we should finalize the proposal
Not sure this must have a rollback plan
Should we say the plan is chosen
It must support offline mode though we haven't decided yet
Which one actually has the final answer"

# ---------------------------------------------------------
# Suite C — "no suppression word" trap sub-class (>=20): a decision/requirement
# root used as a noun/verb continuation with no object anchor or end-of-clause
# anchor, and containing zero veto phrases.
# ---------------------------------------------------------
NO_SUPPRESSION_TRAP_SENTENCES="The settled dust made the room dusty
Decided is not a word I like using here
Finalize is the last stage of the project timeline
The selected files were deleted by mistake
Locking mechanisms are common in old doors
Going with the flow is sometimes fine
We want to add feature films to our streaming catalog
The export data logs are stored separately
APIs must support many different customers well
The retry logic module was refactored last week
The plan is complicated but doable
This feature must undergo more testing next quarter
Needs improvement across the board this quarter
Don't forget to add sugar to the recipe
We need to add more chairs to the classroom
It'd be best to relax this weekend
Make sure the coffee machine is clean
There's a requirement to submit paperwork by Friday
Must have breakfast before the meeting starts
The final answer key was published online yesterday
Selected plan documents are stored in the archive room
We'll use the plan of action loosely defined for now"

decision_ok=1
IFS='
'
for s in $DECISION_SENTENCES; do
  payload="$(jq -n --arg cwd "$REPO" --arg p "$s" '{cwd:$cwd, prompt:$p}')"
  out="$(printf '%s' "$payload" | sh "$REMINDER_SH")"
  case "$out" in
    *decision*) : ;;
    *) decision_ok=0; fail "⑤decision sentence did not hit: [$s] -> [$out]" ;;
  esac
done
[ "$decision_ok" = 1 ] && pass

requirement_ok=1
for s in $REQUIREMENT_SENTENCES; do
  payload="$(jq -n --arg cwd "$REPO" --arg p "$s" '{cwd:$cwd, prompt:$p}')"
  out="$(printf '%s' "$payload" | sh "$REMINDER_SH")"
  case "$out" in
    *requirement*) : ;;
    *) requirement_ok=0; fail "⑤requirement sentence did not hit: [$s] -> [$out]" ;;
  esac
done
[ "$requirement_ok" = 1 ] && pass

daily_ok=1
for s in $DAILY_SENTENCES; do
  payload="$(jq -n --arg cwd "$REPO" --arg p "$s" '{cwd:$cwd, prompt:$p}')"
  out="$(printf '%s' "$payload" | sh "$REMINDER_SH")"
  if [ -n "$out" ]; then
    daily_ok=0
    fail "⑤daily sentence false-triggered (must not hit): [$s] -> [$out]"
  fi
done
[ "$daily_ok" = 1 ] && pass

trap_ok=1
for s in $TRAP_SENTENCES; do
  payload="$(jq -n --arg cwd "$REPO" --arg p "$s" '{cwd:$cwd, prompt:$p}')"
  out="$(printf '%s' "$payload" | sh "$REMINDER_SH")"
  if [ -n "$out" ]; then
    trap_ok=0
    fail "⑤【Suite B】trap sentence false-triggered (contains word-list substring but not a decision/requirement, must not hit): [$s] -> [$out]"
  fi
done
[ "$trap_ok" = 1 ] && pass

# ---- Suite A: multi-clause real messages (incidental question must not suppress the main clause's hit) ----
multiclause_decision_ok=1
for s in $MULTICLAUSE_DECISION_SENTENCES; do
  payload="$(jq -n --arg cwd "$REPO" --arg p "$s" '{cwd:$cwd, prompt:$p}')"
  out="$(printf '%s' "$payload" | sh "$REMINDER_SH")"
  case "$out" in
    *decision*) : ;;
    *) multiclause_decision_ok=0; fail "⑤【Suite A】multi-clause decision message did not hit (incidental question clause should not suppress main clause): [$s] -> [$out]" ;;
  esac
done
[ "$multiclause_decision_ok" = 1 ] && pass

multiclause_requirement_ok=1
for s in $MULTICLAUSE_REQUIREMENT_SENTENCES; do
  payload="$(jq -n --arg cwd "$REPO" --arg p "$s" '{cwd:$cwd, prompt:$p}')"
  out="$(printf '%s' "$payload" | sh "$REMINDER_SH")"
  case "$out" in
    *requirement*) : ;;
    *) multiclause_requirement_ok=0; fail "⑤【Suite A】multi-clause requirement message did not hit (incidental question clause should not suppress main clause): [$s] -> [$out]" ;;
  esac
done
[ "$multiclause_requirement_ok" = 1 ] && pass

# ---- Suite C: no-suppression-word trap sub-class (bare-pattern over-matching without an object/end anchor) ----
no_suppression_trap_ok=1
for s in $NO_SUPPRESSION_TRAP_SENTENCES; do
  payload="$(jq -n --arg cwd "$REPO" --arg p "$s" '{cwd:$cwd, prompt:$p}')"
  out="$(printf '%s' "$payload" | sh "$REMINDER_SH")"
  if [ -n "$out" ]; then
    no_suppression_trap_ok=0
    fail "⑤【Suite C】no-veto-word trap sentence false-triggered (bare pattern without an object/end anchor, must not hit): [$s] -> [$out]"
  fi
done
[ "$no_suppression_trap_ok" = 1 ] && pass
unset IFS

# =========================================================
# ⑥ Off flag / eval env: all three scripts stay silent
# =========================================================
# Use a fake HOME for isolation; never touch the real ~/.claude/.docs-capture-off
FAKE_HOME="$WORK/fake-home"
mkdir -p "$FAKE_HOME/.claude"
: > "$FAKE_HOME/.claude/.docs-capture-off"

rm -f "$INBOX"
printf '%s' "$PAYLOAD_1" | HOME="$FAKE_HOME" sh "$CAPTURE_SH"
[ -f "$INBOX" ] && fail "⑥off flag: capture should not write inbox" || pass

PAYLOAD_OFF_REMINDER="$(jq -n --arg cwd "$REPO" --arg p "That's settled" '{cwd:$cwd, prompt:$p}')"
OUT_OFF_REMINDER="$(printf '%s' "$PAYLOAD_OFF_REMINDER" | HOME="$FAKE_HOME" sh "$REMINDER_SH")"
assert_empty "$OUT_OFF_REMINDER" "⑥off flag: reminder zero output"

git -C "$REPO" add -A >/dev/null 2>&1
echo "x" >> "$REPO/foo.sh"
git -C "$REPO" add "$REPO/foo.sh" >/dev/null 2>&1
OUT_OFF_GATE="$(printf '%s' "$(jq -n --arg cwd "$REPO" '{cwd:$cwd, tool_name:"Bash", tool_input:{command:"git commit -m x"}}')" | HOME="$FAKE_HOME" sh "$GATE_SH")"
assert_empty "$OUT_OFF_GATE" "⑥off flag: commit-gate zero output"
git -C "$REPO" reset >/dev/null 2>&1
rm -f "$REPO/foo.sh"

# env isolation flag
rm -f "$INBOX"
DOCS_CAPTURE_EVALS_HERMETIC=1 sh -c "printf '%s' '$PAYLOAD_1' | sh '$CAPTURE_SH'"
[ -f "$INBOX" ] && fail "⑥HERMETIC env: capture should not write inbox" || pass

# =========================================================
# ⑦ Commit gate: warn once, then allow
# =========================================================
rm -f "$INBOX"
GIT_DIR_FIXTURE="$(git -C "$REPO" rev-parse --git-dir)"
case "$GIT_DIR_FIXTURE" in
  /*) : ;;
  *) GIT_DIR_FIXTURE="$REPO/$GIT_DIR_FIXTURE" ;;
esac
rm -f "$GIT_DIR_FIXTURE/docs-capture-warned"

echo "console.log(1)" > "$REPO/app.js"
git -C "$REPO" add "$REPO/app.js"

PAYLOAD_GATE="$(jq -n --arg cwd "$REPO" '{cwd:$cwd, tool_name:"Bash", tool_input:{command:"git commit -m test"}}')"

OUT7A="$(printf '%s' "$PAYLOAD_GATE" | sh "$GATE_SH")"
assert_contains "$OUT7A" '"permissionDecision": "deny"' "⑦first commit should be flagged/blocked"

OUT7B="$(printf '%s' "$PAYLOAD_GATE" | sh "$GATE_SH")"
assert_empty "$OUT7B" "⑦second attempt with same staged content should pass through (zero output)"

# =========================================================
# ⑧ Staged content change re-triggers the warning
# =========================================================
echo "console.log(2)" >> "$REPO/app.js"
git -C "$REPO" add "$REPO/app.js"
OUT8="$(printf '%s' "$PAYLOAD_GATE" | sh "$GATE_SH")"
assert_contains "$OUT8" '"permissionDecision": "deny"' "⑧staged content change should re-trigger the warning"

git -C "$REPO" reset >/dev/null 2>&1
rm -f "$REPO/app.js"
rm -f "$GIT_DIR_FIXTURE/docs-capture-warned"

# =========================================================
# ⑨ Gate check ① stays quiet when inbox is empty (only when no source change
#    / Progress.md already staged)
# =========================================================
rm -f "$INBOX"
: > "$REPO/docs/Progress.md"
echo "console.log(1)" > "$REPO/app2.js"
git -C "$REPO" add "$REPO/app2.js" "$REPO/docs/Progress.md"
rm -f "$GIT_DIR_FIXTURE/docs-capture-warned"
OUT9="$(printf '%s' "$PAYLOAD_GATE" | sh "$GATE_SH")"
assert_empty "$OUT9" "⑨inbox empty and Progress.md staged: gate should pass through"
git -C "$REPO" reset >/dev/null 2>&1
rm -f "$REPO/app2.js" "$REPO/docs/Progress.md"

# =========================================================
# ⑩ jq missing: silent degrade
# =========================================================
FAKE_BIN_DIR="$WORK/fake-bin-no-jq"
mkdir -p "$FAKE_BIN_DIR"
# Build a PATH that has no jq (keep only the real dirs that lack a jq binary)
NO_JQ_PATH=""
for d in $(printf '%s' "$PATH" | tr ':' '\n'); do
  if [ ! -x "$d/jq" ]; then
    NO_JQ_PATH="${NO_JQ_PATH}${d}:"
  fi
done

rm -f "$INBOX"
OUT10A="$(printf '%s' "$PAYLOAD_1" | PATH="$NO_JQ_PATH" sh "$CAPTURE_SH")"
assert_empty "$OUT10A" "⑩jq missing: capture zero output"
[ -f "$INBOX" ] && fail "⑩jq missing: should not write inbox" || pass

PAYLOAD_10B="$(jq -n --arg cwd "$REPO" --arg p "That's settled" '{cwd:$cwd, prompt:$p}')"
OUT10B="$(printf '%s' "$PAYLOAD_10B" | PATH="$NO_JQ_PATH" sh "$REMINDER_SH")"
assert_empty "$OUT10B" "⑩jq missing: reminder zero output"

echo "console.log(1)" > "$REPO/app3.js"
git -C "$REPO" add "$REPO/app3.js"
rm -f "$GIT_DIR_FIXTURE/docs-capture-warned"
OUT10C="$(printf '%s' "$PAYLOAD_GATE" | PATH="$NO_JQ_PATH" sh "$GATE_SH")"
assert_empty "$OUT10C" "⑩jq missing: commit-gate zero output (pass through)"
git -C "$REPO" reset >/dev/null 2>&1
rm -f "$REPO/app3.js"

# =========================================================
# ⑪ Three consecutive appends do not run together (entries need a boundary newline)
# =========================================================
rm -f "$INBOX"
for i in 1 2 3; do
  seq_payload="$(jq -n --arg cwd "$REPO" --arg sid "seq0000000${i}" \
    '{cwd:$cwd, session_id:$sid, tool_response:{questions:[{question:("Consecutive append #" + ($i|tostring)),options:[{label:"A"},{label:"B"}]}],answers:{("Consecutive append #" + ($i|tostring)):"A"}}}' \
    --argjson i "$i")"
  printf '%s' "$seq_payload" | sh "$CAPTURE_SH"
done
OUT11="$(cat "$INBOX" 2>/dev/null)"
h_count="$(printf '%s' "$OUT11" | grep -c '^## ')"
assert_eq "$h_count" "3" "⑪after 3 consecutive appends, grep -c '^## ' should be 3 (entries must end with a newline, not run into the next one)"
assert_not_contains "$OUT11" '**Selected**: A##' "⑪entry boundaries must not run together (**Selected**: A should not be directly followed by ## )"

# =========================================================
# ⑫ Non-methodology directory (git repo, no docs/): all three scripts zero
#    output, zero writes
# =========================================================
PAYLOAD_NON_DOCS="$(jq -n --arg cwd "$NON_DOCS_REPO" '{cwd:$cwd, session_id:"nondocs01", tool_response:{questions:[{question:"q",options:[{label:"A"}]}],answers:{q:"A"}}}')"
OUT12A="$(printf '%s' "$PAYLOAD_NON_DOCS" | sh "$CAPTURE_SH")"
assert_empty "$OUT12A" "⑫no docs/ git repo: capture zero output"
[ -d "$NON_DOCS_REPO/docs" ] && fail "⑫no docs/ git repo: capture should not create a docs dir" || pass

PAYLOAD_12B="$(jq -n --arg cwd "$NON_DOCS_REPO" --arg p "That's settled" '{cwd:$cwd, prompt:$p}')"
OUT12B="$(printf '%s' "$PAYLOAD_12B" | sh "$REMINDER_SH")"
assert_empty "$OUT12B" "⑫no docs/ git repo: reminder zero output"

echo "console.log(1)" > "$NON_DOCS_REPO/x.js"
git -C "$NON_DOCS_REPO" add "x.js"
OUT12C="$(printf '%s' "$(jq -n --arg cwd "$NON_DOCS_REPO" '{cwd:$cwd, tool_name:"Bash", tool_input:{command:"git commit -m x"}}')" | sh "$GATE_SH")"
assert_empty "$OUT12C" "⑫no docs/ git repo: commit-gate zero output (pass through)"
git -C "$NON_DOCS_REPO" reset >/dev/null 2>&1
rm -f "$NON_DOCS_REPO/x.js"

# =========================================================
# ⑬ Non-git directory: all three scripts zero output, zero crash (including
#    various malformed JSON shapes / empty stdin)
# =========================================================
PLAIN_DIR="$WORK/plain-non-git-dir"
mkdir -p "$PLAIN_DIR/docs"

run_in_plain_dir() {
  # $1=script $2=payload (empty string means empty stdin)
  ( cd "$PLAIN_DIR" && printf '%s' "$2" | sh "$1" )
}

for mp in 'null' '[]' '{}' '"just a string"' ''; do
  o_cap="$(run_in_plain_dir "$CAPTURE_SH" "$mp")"
  ec_cap=$?
  assert_empty "$o_cap" "⑬non-git dir + malformed payload[$mp]: capture zero output"
  [ "$ec_cap" -eq 0 ] || fail "⑬non-git dir + malformed payload[$mp]: capture should exit 0, got $ec_cap"
  [ -f "$PLAIN_DIR/docs/DECISIONS.inbox.md" ] && fail "⑬non-git dir + malformed payload[$mp]: should not produce inbox" || pass

  o_rem="$(run_in_plain_dir "$REMINDER_SH" "$mp")"
  assert_empty "$o_rem" "⑬non-git dir + malformed payload[$mp]: reminder zero output"

  o_gate="$(run_in_plain_dir "$GATE_SH" "$mp")"
  assert_empty "$o_gate" "⑬non-git dir + malformed payload[$mp]: commit-gate zero output"
done

# =========================================================
# ⑭ Malformed tool_response shape (cwd present, but object field missing/wrong
#    type): falls back to raw JSON, no crash
# =========================================================
rm -f "$INBOX"
for tr_payload in \
  '{"cwd":"'"$REPO"'","session_id":"shape01","tool_response":null}' \
  '{"cwd":"'"$REPO"'","session_id":"shape02","tool_response":[]}' \
  '{"cwd":"'"$REPO"'","session_id":"shape03","tool_response":{}}' \
  ; do
  printf '%s' "$tr_payload" | sh "$CAPTURE_SH"
done
OUT14="$(cat "$INBOX" 2>/dev/null)"
h_count14="$(printf '%s' "$OUT14" | grep -c '^## ')"
assert_eq "$h_count14" "3" "⑭malformed tool_response shapes (null/[]/{}) each fall back to raw payload, each should produce one ## entry"

# =========================================================
# ⑮ Cancelled question (tool_response is a string, e.g. user rejected/
#    clarified): must not pollute the inbox
# =========================================================
rm -f "$INBOX"
CANCEL_PAYLOAD='{"cwd":"'"$REPO"'","session_id":"cancel01","tool_response":"Error: The user doesn'"'"'t want to proceed with this tool use. The tool use was rejected (further instructions were provided)."}'
printf '%s' "$CANCEL_PAYLOAD" | sh "$CAPTURE_SH"
[ -f "$INBOX" ] && fail "⑮user-cancelled question should not produce an inbox entry (tool_response is a rejection string)" || pass

# =========================================================
# ⑯ Multi-select answer (comma-joined string) must not be misclassified as
#    Other/free-text
# =========================================================
rm -f "$INBOX"
MULTI_PAYLOAD='{
  "session_id": "multi0001",
  "cwd": "'"$REPO"'",
  "tool_response": {
    "questions": [
      {
        "question": "Why do you want to switch?",
        "multiSelect": true,
        "options": [
          {"label": "Too slow to iterate"},
          {"label": "Stability"},
          {"label": "Code quality"}
        ]
      }
    ],
    "answers": {
      "Why do you want to switch?": "Too slow to iterate, Stability, Code quality"
    }
  }
}'
printf '%s' "$MULTI_PAYLOAD" | sh "$CAPTURE_SH"
OUT16="$(cat "$INBOX" 2>/dev/null)"
assert_contains "$OUT16" "**Selected**: Too slow to iterate, Stability, Code quality" "⑯multi-select selected line fully preserved"
assert_not_contains "$OUT16" "**Notes**" "⑯multi-select (all sub-items are known candidates) should not produce an Other/notes line"

# =========================================================
# ⑰ Gate check ① fires alone (inbox has undigested entries, but this commit's
#    staged content has no source changes)
# =========================================================
rm -f "$INBOX"
: > "$INBOX"
printf '## %s testsid\n**Q**: q\n**Candidates**: A | B\n**Selected**: A\n\n' "$(date '+%Y-%m-%d %H:%M')" >> "$INBOX"
echo "note" > "$REPO/docs/NOTE.md"
git -C "$REPO" add "$REPO/docs/NOTE.md"
rm -f "$GIT_DIR_FIXTURE/docs-capture-warned"
OUT17="$(printf '%s' "$PAYLOAD_GATE" | sh "$GATE_SH")"
assert_contains "$OUT17" '"permissionDecision": "deny"' "⑰inbox has undigested entries only (no source change): gate check ① should fire alone"
assert_contains "$OUT17" "DECISIONS.inbox.md" "⑰deny reason should mention DECISIONS.inbox.md undigested entries"
git -C "$REPO" reset >/dev/null 2>&1
rm -f "$REPO/docs/NOTE.md"
rm -f "$GIT_DIR_FIXTURE/docs-capture-warned"
rm -f "$INBOX"

# =========================================================
# ⑱ Regression: when a candidate label itself contains ", ", a single-select
# choice of that label must not be misjudged as Other/free-text (non-blocker
# a — split(", ") multi-select boundary regression)
# =========================================================
rm -f "$INBOX"
LABEL_WITH_COMMA_PAYLOAD='{
  "session_id": "regr0001",
  "cwd": "'"$REPO"'",
  "tool_response": {
    "questions": [
      {
        "question": "Why do you want to switch?",
        "multiSelect": false,
        "options": [
          {"label": "Improve reliability, performance"},
          {"label": "Other reasons"}
        ]
      }
    ],
    "answers": {
      "Why do you want to switch?": "Improve reliability, performance"
    }
  }
}'
printf '%s' "$LABEL_WITH_COMMA_PAYLOAD" | sh "$CAPTURE_SH"
OUT18="$(cat "$INBOX" 2>/dev/null)"
assert_contains "$OUT18" "**Selected**: Improve reliability, performance" "⑱single-select answer with an embedded comma should be preserved intact on the selected line"
assert_not_contains "$OUT18" "**Notes**" "⑱a label with an embedded comma should not be misjudged as Other/free-text"
rm -f "$INBOX"

# =========================================================
# ⑲ Regression: commit-gate's git-commit detection should be word-position /
# command matching, not a whole-command substring match (non-blocker b —
# echo "git commit" should not trigger the gate)
# =========================================================
echo "console.log(1)" > "$REPO/app4.js"
git -C "$REPO" add "$REPO/app4.js"
rm -f "$GIT_DIR_FIXTURE/docs-capture-warned"
PAYLOAD_ECHO_GIT_COMMIT="$(jq -n --arg cwd "$REPO" '{cwd:$cwd, tool_name:"Bash", tool_input:{command:"echo \"git commit\""}}')"
OUT19="$(printf '%s' "$PAYLOAD_ECHO_GIT_COMMIT" | sh "$GATE_SH")"
assert_empty "$OUT19" "⑲echo \"git commit\" should not trigger the gate (not an actual git commit command, just a string substring)"
git -C "$REPO" reset >/dev/null 2>&1
rm -f "$REPO/app4.js"
rm -f "$GIT_DIR_FIXTURE/docs-capture-warned"

# =========================================================
# Summary
# =========================================================
echo "----------------------------------------"
echo "PASS: $PASS  FAIL: $FAIL"
if [ "$FAIL" -gt 0 ]; then
  printf '%s' "$FAIL_MSGS"
  exit 1
fi
echo "All passed"
exit 0
