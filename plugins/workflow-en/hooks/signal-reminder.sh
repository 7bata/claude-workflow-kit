#!/bin/sh
# signal-reminder.sh — UserPromptSubmit
# When the user message matches the decision/requirement word lists, inject a
# one-line reminder on stdout; never writes files, never blocks.
# Data files are located relative to $(dirname "$0"), since this script will
# eventually be copied to ~/.claude/hooks/ and run standalone.

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

# Clause splitting: split the whole message on sentence-ending punctuation
# (.!?; and newlines/commas, both ASCII and full-width), then run
# match/suppress judgment per clause -- suppression does not cross clause
# boundaries (revised after round 3 of review feedback).
# Each separator is replaced literally (not as a character class), to avoid
# risky multi-byte UTF-8 handling in sed/awk character-class matching.
# Normalize typographic apostrophe (U+2019) to straight quote so word-list
# patterns like "let's" match text pasted from Notes/Slack/iOS keyboards.
normalize_quotes() {
  printf '%s' "$1" | sed "s/\xe2\x80\x99/'/g"
}

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

# Prevent unquoted $(split_into_clauses) expansion from doing pathname
# expansion (guards against * ? etc. in a user message being globbed).
set -f

hit_decision=0
hit_requirement=0

old_ifs="$IFS"
IFS='
'
prompt_text="$(normalize_quotes "$prompt_text")"
for clause in $(split_into_clauses "$prompt_text"); do
  [ -n "$clause" ] || continue

  clause_decision=0
  clause_requirement=0

  if [ -f "$decision_file" ]; then
    if printf '%s' "$clause" | grep -Eqif "$decision_file" 2>/dev/null; then
      clause_decision=1
    fi
  fi
  if [ -f "$requirement_file" ]; then
    if printf '%s' "$clause" | grep -Eqif "$requirement_file" 2>/dev/null; then
      clause_requirement=1
    fi
  fi

  if [ "$clause_decision" -eq 0 ] && [ "$clause_requirement" -eq 0 ]; then
    continue
  fi

  # Veto list: questioning/negating/undecided context (e.g. "...right?",
  # "not sure yet", "haven't decided") within the same clause suppresses that
  # clause's match -- suppression only looks within the same clause, it
  # doesn't affect other clauses in the message.
  if [ -f "$veto_file" ]; then
    if printf '%s' "$clause" | grep -Eqif "$veto_file" 2>/dev/null; then
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
  kind="decision/requirement"
elif [ "$hit_decision" -eq 1 ]; then
  kind="decision"
else
  kind="requirement"
fi

inbox="$cwd/docs/DECISIONS.inbox.md"
pending=0
if [ -f "$inbox" ]; then
  pending="$(grep -c '^## ' "$inbox" 2>/dev/null)"
  case "$pending" in
    ''|*[!0-9]*) pending=0 ;;
  esac
fi

printf 'The previous user message may contain a %s signal -- if it is indeed a decision/requirement, log it per the current-turn capture rule; if it is just casual phrasing, ignore this notice (a high-recall, low-precision soft reminder -- false positives are expected). DECISIONS.inbox currently has %s pending draft entr%s\n' "$kind" "$pending" "$( [ "$pending" -eq 1 ] && echo y || echo ies )"
exit 0
