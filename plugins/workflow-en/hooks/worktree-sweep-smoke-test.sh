#!/bin/sh
# worktree-sweep-smoke-test.sh — worktree-sweep.sh 冒烟测试
# 全部在 mktemp -d 的临时目录里做；HOME 也指向临时目录，保证开关文件、
# 会话目录默认路径都不碰真实家目录。

HOOKS_DIR="$(cd "$(dirname "$0")" && pwd)"
SWEEP_SH="$HOOKS_DIR/worktree-sweep.sh"

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

assert_starts_with() {
  case "$1" in
    "$2"*) pass ;;
    *) fail "$3 — expected to start with: [$2] got: [$1]" ;;
  esac
}

assert_no_chinese() {
  # en 文案应为纯 ASCII；用 LC_ALL=C 检测任何非 ASCII 可打印字节
  # （多字节 UTF-8 中文字符的字节都落在这个范围之外）。
  if printf '%s' "$1" | LC_ALL=C grep -q '[^ -~]'; then
    fail "$2 — expected pure-ASCII (no Chinese), got: [$1]"
  else
    pass
  fi
}

assert_empty() {
  if [ -z "$1" ]; then
    pass
  else
    fail "$2 — expected empty, got: [$1]"
  fi
}

assert_dir_exists() {
  if [ -d "$1" ]; then
    pass
  else
    fail "$2 — expected dir to exist: $1"
  fi
}

assert_dir_absent() {
  if [ -d "$1" ]; then
    fail "$2 — expected dir to be gone: $1"
  else
    pass
  fi
}

# 把 worktree 自己 git 管理目录下的 index / COMMIT_EDITMSG 改成 40
# 分钟前的 mtime，绕过脚本里的"太新不动"护栏（该护栏现在认的是这两个
# 文件的 mtime，不是 worktree 里 .git 文件本身——.git 文件从建立起就
# 不再变化，测不出"刚提交过"）。好让①②⑦等场景真正测到它们各自要测的
# 判据，而不是被新护栏提前拦下。
backdate_worktree() {
  wt="$1"
  ts="$(date -v-40M +%Y%m%d%H%M 2>/dev/null)"
  if [ -z "$ts" ]; then
    ts="$(date -d '40 minutes ago' +%Y%m%d%H%M 2>/dev/null)"
  fi
  [ -n "$ts" ] || return
  gd="$(git -C "$wt" rev-parse --git-dir 2>/dev/null)"
  case "$gd" in
    /*) ;;
    *) gd="$wt/$gd" ;;
  esac
  if [ -n "$gd" ]; then
    touch -t "$ts" "$gd/index" 2>/dev/null
    [ -f "$gd/COMMIT_EDITMSG" ] && touch -t "$ts" "$gd/COMMIT_EDITMSG" 2>/dev/null
  fi
  # 注意：不要顺带 backdate worktree 里的 .git 文件本身（曾经的「双保险」）
  # ——那会让 fixture 在两种时间戳源实现下行为完全一致，测不出脚本到底
  # 读的是哪一个源，参见场景⑰。
}

# ---- fixture 环境 ----
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

export HOME="$WORK/home"
mkdir -p "$HOME"
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_SYSTEM=/dev/null
unset XDG_CONFIG_HOME GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY
unset WORKTREE_SWEEP_OFF_FILE
unset WORKTREE_SWEEP_STATE_DIR
unset WORKTREE_SWEEP_SESSIONS_ROOTS
export GIT_AUTHOR_NAME="Test"
export GIT_AUTHOR_EMAIL="test@example.com"
export GIT_COMMITTER_NAME="Test"
export GIT_COMMITTER_EMAIL="test@example.com"

make_repo() {
  # $1 = repo 目录路径
  repo="$1"
  mkdir -p "$repo"
  if git init -b main -q "$repo" 2>/dev/null; then
    :
  else
    git init -q "$repo"
    git -C "$repo" checkout -q -b main
  fi
  git -C "$repo" config user.email test@example.com
  git -C "$repo" config user.name "Test"
  echo "init" > "$repo/README.md"
  git -C "$repo" add -A
  git -C "$repo" commit -q -m init
}

run_sweep() {
  # $1 = cwd 传入 payload, $2... 传给脚本的额外参数
  cwd="$1"
  shift
  payload="$(jq -n --arg cwd "$cwd" '{cwd:$cwd, session_id:"sid1", hook_event_name:"Stop"}')"
  printf '%s' "$payload" | sh "$SWEEP_SH" "$@"
}

STATE_DIR="$WORK/state"
mkdir -p "$STATE_DIR"
export WORKTREE_SWEEP_STATE_DIR="$STATE_DIR"

SESS_ROOT="$WORK/sessions"
mkdir -p "$SESS_ROOT"
export WORKTREE_SWEEP_SESSIONS_ROOTS="$SESS_ROOT"

# =========================================================
# ① 已并 main 且干净 → 被删、分支被删、systemMessage 含路径
# =========================================================
REPO1="$WORK/repo1"
make_repo "$REPO1"
git -C "$REPO1" worktree add -q -b feat-clean "$REPO1/.worktrees/feat-clean" >/dev/null 2>&1
git -C "$REPO1" merge -q feat-clean 2>/dev/null || true
backdate_worktree "$REPO1/.worktrees/feat-clean"
OUT1="$(run_sweep "$REPO1")"
assert_dir_absent "$REPO1/.worktrees/feat-clean" "①已并且干净的 worktree 应被删"
assert_contains "$OUT1" "$REPO1/.worktrees/feat-clean" "①systemMessage 含路径"
assert_contains "$OUT1" "feat-clean" "①systemMessage 含分支名"
assert_contains "$OUT1" "已并 main，本地分支已删" "①中文文案整句完整,分支名与全角逗号未被吞掉"
if printf '%s' "$OUT1" | jq -e '.systemMessage' >/dev/null 2>&1; then pass; else fail "①输出应为含 systemMessage 键的合法 JSON"; fi
BRANCH_GONE="$(git -C "$REPO1" branch --list feat-clean)"
assert_empty "$BRANCH_GONE" "①本地分支已删"

# =========================================================
# ② 已并 main 但有未跟踪文件 → 目录仍在、输出提醒；紧接着再跑一次 → 限频无提醒
# =========================================================
REPO2="$WORK/repo2"
make_repo "$REPO2"
git -C "$REPO2" worktree add -q -b feat-dirty "$REPO2/.worktrees/feat-dirty" >/dev/null 2>&1
git -C "$REPO2" merge -q feat-dirty 2>/dev/null || true
: > "$REPO2/.worktrees/feat-dirty/untracked.txt"
backdate_worktree "$REPO2/.worktrees/feat-dirty"
OUT2A="$(run_sweep "$REPO2")"
assert_dir_exists "$REPO2/.worktrees/feat-dirty" "②有未跟踪文件的 worktree 不应被删"
assert_contains "$OUT2A" "feat-dirty" "②提醒消息含分支名"
assert_contains "$OUT2A" "工作区有未提交改动" "②应识别为脏工作区提醒,而非删除失败"
assert_not_contains "$OUT2A" "删除失败" "②脏工作区不应走到删除失败分支"
assert_not_contains "$OUT2A" "已清理" "②脏工作区不应被清理"

# 第一次 run_sweep 里的 git status 会刷新该 worktree 自己 git 管理目录下
# index 的 mtime；不重新 backdate 的话，第二次调用会被判据⑤「太新不动」
# 拦在半路,根本走不到限频代码,断言就成了空断言。这里先补一次 backdate,
# 确保第二次调用真正跑到限频判断。
backdate_worktree "$REPO2/.worktrees/feat-dirty"
OUT2B="$(run_sweep "$REPO2")"
assert_dir_exists "$REPO2/.worktrees/feat-dirty" "②第二次跑目录仍在"
assert_empty "$OUT2B" "②限频后第二次不应再提醒"

# 互补用例：把状态文件内容改成 3700 秒前（超过 1 小时限频窗口），
# backdate 后再跑一次 → 限频过期，提醒应重新出现
STATE2_FILE="$(find "$STATE_DIR" -maxdepth 1 -name 'worktree-sweep-*' 2>/dev/null | head -n 1)"
if [ -n "$STATE2_FILE" ]; then
  NOW2="$(date +%s 2>/dev/null || echo 0)"
  echo "$((NOW2 - 3700))" > "$STATE2_FILE"
  backdate_worktree "$REPO2/.worktrees/feat-dirty"
  OUT2C="$(run_sweep "$REPO2")"
  assert_dir_exists "$REPO2/.worktrees/feat-dirty" "②限频过期后第三次跑目录仍在"
  assert_contains "$OUT2C" "工作区有未提交改动" "②限频过期后提醒应重新出现"
else
  fail "②未能定位限频状态文件，无法验证限频过期后重新提醒"
fi

# =========================================================
# ③ 未并 main（worktree 里多一个提交）→ 目录仍在、无输出
# =========================================================
REPO3="$WORK/repo3"
make_repo "$REPO3"
git -C "$REPO3" worktree add -q -b feat-wip "$REPO3/.worktrees/feat-wip" >/dev/null 2>&1
echo "wip" > "$REPO3/.worktrees/feat-wip/extra.txt"
git -C "$REPO3/.worktrees/feat-wip" add -A
git -C "$REPO3/.worktrees/feat-wip" commit -q -m "wip commit"
backdate_worktree "$REPO3/.worktrees/feat-wip"
OUT3="$(run_sweep "$REPO3")"
assert_dir_exists "$REPO3/.worktrees/feat-wip" "③未并 main 的 worktree 不应被删"
assert_empty "$OUT3" "③未并 main 时无输出"

# =========================================================
# ④ cwd 就在该 worktree 里 → 不动
# =========================================================
REPO4="$WORK/repo4"
make_repo "$REPO4"
git -C "$REPO4" worktree add -q -b feat-cwd "$REPO4/.worktrees/feat-cwd" >/dev/null 2>&1
git -C "$REPO4" merge -q feat-cwd 2>/dev/null || true
backdate_worktree "$REPO4/.worktrees/feat-cwd"
OUT4="$(run_sweep "$REPO4/.worktrees/feat-cwd")"
assert_dir_exists "$REPO4/.worktrees/feat-cwd" "④cwd 所在 worktree 不应被删"
assert_empty "$OUT4" "④cwd 所在 worktree 应静默跳过、无输出"

# ④b cwd 落在该 worktree 的子目录里（不是 worktree 根本身）→ 同样不动。
# 钉住 case "$cwd_real" in "$wt_path"|"$wt_path"/*) 的第二支（前缀分支）：
# 只测 cwd 恰好等于 worktree 根测不出这一支，若该分支被误删成只剩
# "$wt_path") 一支，整套测试仍会全绿，实测已确认。
mkdir -p "$REPO4/.worktrees/feat-cwd/sub"
OUT4B="$(run_sweep "$REPO4/.worktrees/feat-cwd/sub")"
assert_dir_exists "$REPO4/.worktrees/feat-cwd" "④b cwd 落在 worktree 子目录内时不应被删"
assert_empty "$OUT4B" "④b cwd 落在 worktree 子目录内应静默跳过、无输出"

# =========================================================
# ⑤ 开关文件存在 → 无输出、目录仍在
# =========================================================
REPO5="$WORK/repo5"
make_repo "$REPO5"
git -C "$REPO5" worktree add -q -b feat-off "$REPO5/.worktrees/feat-off" >/dev/null 2>&1
git -C "$REPO5" merge -q feat-off 2>/dev/null || true
backdate_worktree "$REPO5/.worktrees/feat-off"
OFF_FILE="$WORK/off-flag"
: > "$OFF_FILE"
OUT5="$(payload="$(jq -n --arg cwd "$REPO5" '{cwd:$cwd}')"; printf '%s' "$payload" | WORKTREE_SWEEP_OFF_FILE="$OFF_FILE" sh "$SWEEP_SH")"
assert_empty "$OUT5" "⑤开关文件存在时无输出"
assert_dir_exists "$REPO5/.worktrees/feat-off" "⑤开关文件存在时目录仍在"
rm -f "$OFF_FILE"

# =========================================================
# ⑥ 目录被 rm -rf 掉的失效登记，配合 --expire 30.minutes.ago：登记本身
#    要"老"到超过窗口才会被清掉。经 /tmp 探针实测钉版：git worktree
#    prune --expire 实际读的是主仓 .git/worktrees/<name>/index 的
#    mtime（与判据⑤读的是同一份 index）——只回溯 gitdir 文件不生效，
#    必须回溯 index。这里把 gitdir 与 index 都回溯到 40 分钟前（gitdir
#    本身语义上也该老化，index 是实测钉住 prune 生效的那个文件）。
# =========================================================
REPO6="$WORK/repo6"
make_repo "$REPO6"
git -C "$REPO6" worktree add -q -b feat-stale "$REPO6/.worktrees/feat-stale" >/dev/null 2>&1
ADMIN6="$REPO6/.git/worktrees/feat-stale"
rm -rf "$REPO6/.worktrees/feat-stale"
TS6="$(date -v-40M +%Y%m%d%H%M 2>/dev/null)"
[ -n "$TS6" ] || TS6="$(date -d '40 minutes ago' +%Y%m%d%H%M 2>/dev/null)"
touch -t "$TS6" "$ADMIN6/gitdir" 2>/dev/null
touch -t "$TS6" "$ADMIN6/index" 2>/dev/null
run_sweep "$REPO6" >/dev/null
LIST_OUT="$(git -C "$REPO6" worktree list)"
assert_not_contains "$LIST_OUT" "feat-stale" "⑥回溯 40 分钟的失效登记应被 prune 掉"

# ⑥反例：不回溯（刚建到一半/刚删掉的登记，admin 文件 mtime 仍是刚创建
# 时的"现在"）→ --expire 30.minutes.ago 不应清掉它，跑完仍在
# worktree list 里
REPO6B="$WORK/repo6b"
make_repo "$REPO6B"
git -C "$REPO6B" worktree add -q -b feat-stale-fresh "$REPO6B/.worktrees/feat-stale-fresh" >/dev/null 2>&1
rm -rf "$REPO6B/.worktrees/feat-stale-fresh"
run_sweep "$REPO6B" >/dev/null
LIST_OUT_B="$(git -C "$REPO6B" worktree list)"
assert_contains "$LIST_OUT_B" "feat-stale-fresh" "⑥反例：不回溯的刚建失效登记不应立即被 prune"

# =========================================================
# ⑦ 会话活动：WORKTREE_SWEEP_SESSIONS_ROOTS 指定临时根下建 <key>/a.jsonl(新鲜) → 不删
# =========================================================
REPO7="$WORK/repo7"
make_repo "$REPO7"
git -C "$REPO7" worktree add -q -b feat-active "$REPO7/.worktrees/feat-active" >/dev/null 2>&1
git -C "$REPO7" merge -q feat-active 2>/dev/null || true
backdate_worktree "$REPO7/.worktrees/feat-active"
WT7_PATH="$REPO7/.worktrees/feat-active"
WT7_REAL="$(cd "$WT7_PATH" && pwd -P)"
KEY7="$(printf '%s' "$WT7_REAL" | sed 's/[^A-Za-z0-9]/-/g')"
mkdir -p "$SESS_ROOT/$KEY7"
: > "$SESS_ROOT/$KEY7/a.jsonl"
OUT7="$(run_sweep "$REPO7")"
assert_dir_exists "$WT7_PATH" "⑦有活跃会话的 worktree 不应被删"
rm -rf "$SESS_ROOT/$KEY7"

# =========================================================
# ⑦b 会话活动：worktree 路径含非 ASCII（中文）目录名，会话 key 用默认
#    locale（本机 UTF-8）计算，与 Claude Code 实际用的 node 正则
#    replace(/[^a-zA-Z0-9]/g,'-') 按字符（而非按字节）替换一致 → 应
#    被识别为活跃会话、不删。已知限制（评审 major #1，未在本轮修复）：
#    若把这条命令换成 LC_ALL=C 强制按字节 locale 跑，同一份 key 会
#    因为按字节替换而与 sessions 目录名对不上，session_active 判定
#    会静默失效——真实环境下这一半防线通常还有 lsof 兜底，且 sh 继承
#    的 locale 在常见的类 UTF-8 环境下与本用例一致，故本条只钉默认
#    locale 行为，不在此加 LC_ALL=C 强制场景的断言。
# =========================================================
REPO7B="$WORK/repo7b"
make_repo "$REPO7B"
git -C "$REPO7B" worktree add -q -b feat-active-cn "$REPO7B/.worktrees/中文" >/dev/null 2>&1
git -C "$REPO7B" merge -q feat-active-cn 2>/dev/null || true
backdate_worktree "$REPO7B/.worktrees/中文"
WT7B_PATH="$REPO7B/.worktrees/中文"
WT7B_REAL="$(cd "$WT7B_PATH" && pwd -P)"
KEY7B="$(printf '%s' "$WT7B_REAL" | sed 's/[^A-Za-z0-9]/-/g')"
mkdir -p "$SESS_ROOT/$KEY7B"
: > "$SESS_ROOT/$KEY7B/a.jsonl"
OUT7B="$(run_sweep "$REPO7B")"
assert_dir_exists "$WT7B_PATH" "⑦b 非 ASCII 路径(默认 locale)下有活跃会话的 worktree 不应被删"
rm -rf "$SESS_ROOT/$KEY7B"

# =========================================================
# ⑦c 会话记录 20 分钟前（仍在 30 分钟窗口内，既不是"刚刚"也不是⑰c 那样
#    早已过期的 40 分钟前）→ 仍应判定为活跃会话、不删——回归防护：若把
#    会话新鲜度判据的 -mmin -30 缩小成 -mmin -1，20 分钟前的记录会被
#    误判为"不新鲜"而继续往下删。
# =========================================================
REPO7C="$WORK/repo7c"
make_repo "$REPO7C"
git -C "$REPO7C" worktree add -q -b feat-active-mid "$REPO7C/.worktrees/feat-active-mid" >/dev/null 2>&1
git -C "$REPO7C" merge -q feat-active-mid 2>/dev/null || true
backdate_worktree "$REPO7C/.worktrees/feat-active-mid"
WT7C_PATH="$REPO7C/.worktrees/feat-active-mid"
WT7C_REAL="$(cd "$WT7C_PATH" && pwd -P)"
KEY7C="$(printf '%s' "$WT7C_REAL" | sed 's/[^A-Za-z0-9]/-/g')"
mkdir -p "$SESS_ROOT/$KEY7C"
: > "$SESS_ROOT/$KEY7C/a.jsonl"
TS7C="$(date -v-20M +%Y%m%d%H%M 2>/dev/null)"
[ -n "$TS7C" ] || TS7C="$(date -d '20 minutes ago' +%Y%m%d%H%M 2>/dev/null)"
touch -t "$TS7C" "$SESS_ROOT/$KEY7C/a.jsonl" 2>/dev/null
OUT7C="$(run_sweep "$REPO7C")"
assert_dir_exists "$WT7C_PATH" "⑦c 20 分钟前(仍在 30 分钟窗口内)的会话记录仍应视为活跃、不删"
rm -rf "$SESS_ROOT/$KEY7C"

# =========================================================
# ⑧ locked 的 worktree → 不动
# =========================================================
REPO8="$WORK/repo8"
make_repo "$REPO8"
git -C "$REPO8" worktree add -q -b feat-locked "$REPO8/.worktrees/feat-locked" >/dev/null 2>&1
git -C "$REPO8" merge -q feat-locked 2>/dev/null || true
git -C "$REPO8" worktree lock "$REPO8/.worktrees/feat-locked" >/dev/null 2>&1
backdate_worktree "$REPO8/.worktrees/feat-locked"
OUT8="$(run_sweep "$REPO8")"
assert_dir_exists "$REPO8/.worktrees/feat-locked" "⑧locked 的 worktree 不应被删"
assert_empty "$OUT8" "⑧locked 的 worktree 应静默跳过、无输出"
git -C "$REPO8" worktree unlock "$REPO8/.worktrees/feat-locked" >/dev/null 2>&1

# =========================================================
# ⑨ 主工作树永远还在
# =========================================================
REPO9="$WORK/repo9"
make_repo "$REPO9"
git -C "$REPO9" worktree add -q -b feat-nine "$REPO9/.worktrees/feat-nine" >/dev/null 2>&1
git -C "$REPO9" merge -q feat-nine 2>/dev/null || true
run_sweep "$REPO9" >/dev/null
assert_dir_exists "$REPO9" "⑨主工作树永远还在"
assert_dir_exists "$REPO9/.git" "⑨主工作树 .git 还在"

# =========================================================
# ⑩ 非 git 目录 → 无输出 exit 0
# =========================================================
NONGIT="$WORK/nongit"
mkdir -p "$NONGIT"
payload10="$(jq -n --arg cwd "$NONGIT" '{cwd:$cwd}')"
OUT10="$(printf '%s' "$payload10" | sh "$SWEEP_SH")"
RC10=$?
assert_empty "$OUT10" "⑩非 git 目录无输出"
if [ "$RC10" -eq 0 ]; then pass; else fail "⑩非 git 目录应 exit 0，实际 $RC10"; fi

# =========================================================
# ⑪ 刚建好的 worktree（<30 分钟）即使已并 main 且干净，也不应立刻被清
#    —— "太新不动" 护栏，防止 Workflow isolation:'worktree' 子代理正在跑时
#    被同仓库另一个会话的 Stop hook 顺手 remove 掉
# =========================================================
REPO11="$WORK/repo11"
make_repo "$REPO11"
git -C "$REPO11" worktree add -q -b feat-fresh "$REPO11/.worktrees/feat-fresh" >/dev/null 2>&1
git -C "$REPO11" merge -q feat-fresh 2>/dev/null || true
OUT11="$(run_sweep "$REPO11")"
assert_dir_exists "$REPO11/.worktrees/feat-fresh" "⑪刚建好(<30分钟)的 worktree 即使已并且干净也不应立刻被删"
assert_empty "$OUT11" "⑪太新不动应静默跳过、无输出"

# =========================================================
# ⑫ 默认会话根（不设 WORKTREE_SWEEP_SESSIONS_ROOTS）：新鲜 jsonl 放在
#    $HOME/.claude-profiles/<profile>/projects/<key>/ 下也应被识别为活跃会话
#    —— 回归防护：set -f 曾让 profile 通配符根永远不展开，这条路径的
#    会话检测形同虚设
# =========================================================
REPO12="$WORK/repo12"
make_repo "$REPO12"
git -C "$REPO12" worktree add -q -b feat-profile "$REPO12/.worktrees/feat-profile" >/dev/null 2>&1
git -C "$REPO12" merge -q feat-profile 2>/dev/null || true
backdate_worktree "$REPO12/.worktrees/feat-profile"
WT12_PATH="$REPO12/.worktrees/feat-profile"
WT12_REAL="$(cd "$WT12_PATH" && pwd -P)"
KEY12="$(printf '%s' "$WT12_REAL" | sed 's/[^A-Za-z0-9]/-/g')"
mkdir -p "$HOME/.claude-profiles/p1/projects/$KEY12"
: > "$HOME/.claude-profiles/p1/projects/$KEY12/a.jsonl"
OUT12="$(unset WORKTREE_SWEEP_SESSIONS_ROOTS; payload="$(jq -n --arg cwd "$REPO12" '{cwd:$cwd}')"; printf '%s' "$payload" | sh "$SWEEP_SH")"
assert_dir_exists "$WT12_PATH" "⑫默认 profile 通配符根应检测到活跃会话，worktree 不应被删"
rm -rf "$HOME/.claude-profiles"

# =========================================================
# ⑬a 已并 main、status --porcelain -uall 干净，但含被 .gitignore 忽略的
#     不可再生黑名单文件（.env）→ 不应被删，提醒消息点名该忽略文件
# =========================================================
REPO13A="$WORK/repo13a"
make_repo "$REPO13A"
git -C "$REPO13A" worktree add -q -b feat-ignored-env "$REPO13A/.worktrees/feat-ignored-env" >/dev/null 2>&1
echo ".env" > "$REPO13A/.worktrees/feat-ignored-env/.gitignore"
git -C "$REPO13A/.worktrees/feat-ignored-env" add .gitignore
git -C "$REPO13A/.worktrees/feat-ignored-env" commit -q -m "add gitignore"
git -C "$REPO13A" merge -q feat-ignored-env 2>/dev/null || true
echo "SECRET=abc" > "$REPO13A/.worktrees/feat-ignored-env/.env"
backdate_worktree "$REPO13A/.worktrees/feat-ignored-env"
OUT13A="$(run_sweep "$REPO13A")"
assert_dir_exists "$REPO13A/.worktrees/feat-ignored-env" "⑬a 含被 .gitignore 忽略的黑名单文件(.env)的 worktree 不应被删"
if [ -f "$REPO13A/.worktrees/feat-ignored-env/.env" ]; then pass; else fail "⑬a .env 不应随目录一起丢失"; fi
assert_not_contains "$OUT13A" "已清理" "⑬a 不应被当作清理"
assert_contains "$OUT13A" "不可再生的被忽略文件" "⑬a 提醒消息应含标准措辞"
assert_not_contains "$OUT13A" "未提交改动" "⑬a 不应误判为未提交改动提醒"

# ⑬a-en 同上场景，走 en 分支：文案应为英文标准措辞、不含中文
REPO13AEN="$WORK/repo13a-en"
make_repo "$REPO13AEN"
git -C "$REPO13AEN" worktree add -q -b feat-ignored-env-en "$REPO13AEN/.worktrees/feat-ignored-env-en" >/dev/null 2>&1
echo ".env" > "$REPO13AEN/.worktrees/feat-ignored-env-en/.gitignore"
git -C "$REPO13AEN/.worktrees/feat-ignored-env-en" add .gitignore
git -C "$REPO13AEN/.worktrees/feat-ignored-env-en" commit -q -m "add gitignore"
git -C "$REPO13AEN" merge -q feat-ignored-env-en 2>/dev/null || true
echo "SECRET=abc" > "$REPO13AEN/.worktrees/feat-ignored-env-en/.env"
backdate_worktree "$REPO13AEN/.worktrees/feat-ignored-env-en"
OUT13AEN="$(run_sweep "$REPO13AEN" en)"
assert_dir_exists "$REPO13AEN/.worktrees/feat-ignored-env-en" "⑬a-en 含黑名单忽略文件(en)的 worktree 不应被删"
assert_contains "$OUT13AEN" "cannot be regenerated" "⑬a-en 提醒消息应含英文标准措辞"
MSG13AEN="$(printf '%s' "$OUT13AEN" | jq -r '.systemMessage' 2>/dev/null)"
assert_no_chinese "$MSG13AEN" "⑬a-en 消息不应含中文"
assert_contains "$OUT13A" ".env" "⑬a 提醒消息应点名被忽略的文件(.env)"

# =========================================================
# ⑬b 只有可再生的忽略文件（node_modules/、dist/、.DS_Store、debug.log，
#     均列在 fixture 的 .gitignore 里）→ 不属于黑名单，照常删除
# =========================================================
REPO13B="$WORK/repo13b"
make_repo "$REPO13B"
git -C "$REPO13B" worktree add -q -b feat-regen "$REPO13B/.worktrees/feat-regen" >/dev/null 2>&1
{
  echo "node_modules/"
  echo "dist/"
  echo ".DS_Store"
  echo "debug.log"
} > "$REPO13B/.worktrees/feat-regen/.gitignore"
git -C "$REPO13B/.worktrees/feat-regen" add .gitignore
git -C "$REPO13B/.worktrees/feat-regen" commit -q -m "add gitignore"
git -C "$REPO13B" merge -q feat-regen 2>/dev/null || true
mkdir -p "$REPO13B/.worktrees/feat-regen/node_modules" "$REPO13B/.worktrees/feat-regen/dist"
: > "$REPO13B/.worktrees/feat-regen/node_modules/x.js"
: > "$REPO13B/.worktrees/feat-regen/dist/out.txt"
: > "$REPO13B/.worktrees/feat-regen/.DS_Store"
: > "$REPO13B/.worktrees/feat-regen/debug.log"
backdate_worktree "$REPO13B/.worktrees/feat-regen"
OUT13B="$(run_sweep "$REPO13B")"
assert_dir_absent "$REPO13B/.worktrees/feat-regen" "⑬b 只含可再生忽略文件的 worktree 应被照常删除"
assert_contains "$OUT13B" "feat-regen" "⑬b 清理消息含分支名"

# =========================================================
# ⑬c 被忽略的 data/ 目录下的文件（data/local.db）→ 不应被删
# =========================================================
REPO13C="$WORK/repo13c"
make_repo "$REPO13C"
git -C "$REPO13C" worktree add -q -b feat-data "$REPO13C/.worktrees/feat-data" >/dev/null 2>&1
echo "data/" > "$REPO13C/.worktrees/feat-data/.gitignore"
git -C "$REPO13C/.worktrees/feat-data" add .gitignore
git -C "$REPO13C/.worktrees/feat-data" commit -q -m "add gitignore"
git -C "$REPO13C" merge -q feat-data 2>/dev/null || true
mkdir -p "$REPO13C/.worktrees/feat-data/data"
: > "$REPO13C/.worktrees/feat-data/data/local.db"
backdate_worktree "$REPO13C/.worktrees/feat-data"
OUT13C="$(run_sweep "$REPO13C")"
assert_dir_exists "$REPO13C/.worktrees/feat-data" "⑬c data/ 目录下的忽略文件不应被删"
if [ -f "$REPO13C/.worktrees/feat-data/data/local.db" ]; then pass; else fail "⑬c data/local.db 不应随目录一起丢失"; fi
assert_not_contains "$OUT13C" "已清理" "⑬c 不应被当作清理"

# =========================================================
# ⑬d 子目录里的同名黑名单文件（sub/.env）→ 不应被删
# =========================================================
REPO13D="$WORK/repo13d"
make_repo "$REPO13D"
git -C "$REPO13D" worktree add -q -b feat-sub-env "$REPO13D/.worktrees/feat-sub-env" >/dev/null 2>&1
echo ".env" > "$REPO13D/.worktrees/feat-sub-env/.gitignore"
git -C "$REPO13D/.worktrees/feat-sub-env" add .gitignore
git -C "$REPO13D/.worktrees/feat-sub-env" commit -q -m "add gitignore"
git -C "$REPO13D" merge -q feat-sub-env 2>/dev/null || true
mkdir -p "$REPO13D/.worktrees/feat-sub-env/sub"
echo "SECRET=abc" > "$REPO13D/.worktrees/feat-sub-env/sub/.env"
backdate_worktree "$REPO13D/.worktrees/feat-sub-env"
OUT13D="$(run_sweep "$REPO13D")"
assert_dir_exists "$REPO13D/.worktrees/feat-sub-env" "⑬d 子目录里的黑名单文件(sub/.env)不应被删"
if [ -f "$REPO13D/.worktrees/feat-sub-env/sub/.env" ]; then pass; else fail "⑬d sub/.env 不应随目录一起丢失"; fi
assert_not_contains "$OUT13D" "已清理" "⑬d 不应被当作清理"

# =========================================================
# ⑬e 含空格的忽略路径（子目录名 "a b"、文件名 "back up.db"）→ 不应被删
#    —— 回归防护：git status 默认 porcelain 对含空格路径加引号，若脚本
#    未用 -z 解析，黑名单 case 会因多出的引号一个都匹配不上而误删
# =========================================================
REPO13E="$WORK/repo13e"
make_repo "$REPO13E"
git -C "$REPO13E" worktree add -q -b feat-spaces "$REPO13E/.worktrees/feat-spaces" >/dev/null 2>&1
{
  echo "*.env"
  echo "*.db"
} > "$REPO13E/.worktrees/feat-spaces/.gitignore"
git -C "$REPO13E/.worktrees/feat-spaces" add .gitignore
git -C "$REPO13E/.worktrees/feat-spaces" commit -q -m "add gitignore"
git -C "$REPO13E" merge -q feat-spaces 2>/dev/null || true
mkdir -p "$REPO13E/.worktrees/feat-spaces/a b"
echo "SECRET=abc" > "$REPO13E/.worktrees/feat-spaces/a b/.env"
echo "binary" > "$REPO13E/.worktrees/feat-spaces/back up.db"
backdate_worktree "$REPO13E/.worktrees/feat-spaces"
OUT13E="$(run_sweep "$REPO13E")"
assert_dir_exists "$REPO13E/.worktrees/feat-spaces" "⑬e 含空格路径的黑名单忽略文件不应被删"
if [ -f "$REPO13E/.worktrees/feat-spaces/a b/.env" ]; then pass; else fail "⑬e 'a b/.env' 不应随目录一起丢失"; fi
if [ -f "$REPO13E/.worktrees/feat-spaces/back up.db" ]; then pass; else fail "⑬e 'back up.db' 不应随目录一起丢失"; fi
assert_not_contains "$OUT13E" "已清理" "⑬e 不应被当作清理"

# =========================================================
# ⑬f 含非 ASCII（中文）路径的忽略文件 → 不应被删 —— 同上一条，
#    默认 porcelain 会把非 ASCII 字节做八进制转义
# =========================================================
REPO13F="$WORK/repo13f"
make_repo "$REPO13F"
git -C "$REPO13F" worktree add -q -b feat-nonascii "$REPO13F/.worktrees/feat-nonascii" >/dev/null 2>&1
echo "*.env" > "$REPO13F/.worktrees/feat-nonascii/.gitignore"
git -C "$REPO13F/.worktrees/feat-nonascii" add .gitignore
git -C "$REPO13F/.worktrees/feat-nonascii" commit -q -m "add gitignore"
git -C "$REPO13F" merge -q feat-nonascii 2>/dev/null || true
mkdir -p "$REPO13F/.worktrees/feat-nonascii/数据"
echo "SECRET=abc" > "$REPO13F/.worktrees/feat-nonascii/数据/.env"
backdate_worktree "$REPO13F/.worktrees/feat-nonascii"
OUT13F="$(run_sweep "$REPO13F")"
assert_dir_exists "$REPO13F/.worktrees/feat-nonascii" "⑬f 含中文路径的黑名单忽略文件不应被删"
if [ -f "$REPO13F/.worktrees/feat-nonascii/数据/.env" ]; then pass; else fail "⑬f 数据/.env 不应随目录一起丢失"; fi
assert_not_contains "$OUT13F" "已清理" "⑬f 不应被当作清理"

# ⑬f2 覆盖「data/ 目录前缀命中」+「非 ASCII 字符」的组合场景（非 ASCII
# 出现在 data/ 之后而不是文件名后缀里，data/数据/x.csv）：黑名单命中要
# 靠 data/ 目录前缀这条分支，而不是靠 .env/*.pem 这类后缀分支；同时钉住
# core.quotePath=false——若脚本漏加这个 git 选项，非 ASCII 字节会被
# git 转义成八进制（如 "data/\346\225..."），提醒消息里就看不到原样的
# 「数据」二字了。
REPO13F2="$WORK/repo13f2"
make_repo "$REPO13F2"
git -C "$REPO13F2" worktree add -q -b feat-nonascii-data "$REPO13F2/.worktrees/feat-nonascii-data" >/dev/null 2>&1
WT13F2="$REPO13F2/.worktrees/feat-nonascii-data"
echo "data/" > "$WT13F2/.gitignore"
git -C "$WT13F2" add .gitignore
git -C "$WT13F2" commit -q -m "add gitignore"
git -C "$REPO13F2" merge -q feat-nonascii-data 2>/dev/null || true
mkdir -p "$WT13F2/data/数据"
: > "$WT13F2/data/数据/x.csv"
backdate_worktree "$WT13F2"
OUT13F2="$(run_sweep "$REPO13F2")"
assert_dir_exists "$WT13F2" "⑬f2 非 ASCII 出现在 data/ 之后的忽略文件不应被删"
if [ -f "$WT13F2/data/数据/x.csv" ]; then pass; else fail "⑬f2 data/数据/x.csv 不应随目录一起丢失"; fi
assert_not_contains "$OUT13F2" "已清理" "⑬f2 不应被当作清理"
assert_contains "$OUT13F2" "不可再生的被忽略文件" "⑬f2 提醒消息应含标准措辞"
assert_contains "$OUT13F2" "数据" "⑬f2 提醒消息应含原样的中文字符(钉住 core.quotePath=false)"

# ⑬f3 data/ 目录下文件名本身含双引号（data/a"b.csv）→ git 即使在
# core.quotePath=false 下，仍会因路径含字面引号而给整条记录加一对外层
# 引号（"data/a\"b.csv"），黑名单正则的行首锚点若不容忍这个外层引号，
# "data/" 前缀就贴不上行首，导致整个 worktree 被误删——本条钉住这条
# 回归防护线：把行首/行尾锚点从 (^|/) 改回不容忍引号的写法，此用例必红
# （已用 /tmp 探针实测复现：旧锚点下这条 fixture 的 data 目录会被真删）。
REPO13F3="$WORK/repo13f3"
make_repo "$REPO13F3"
git -C "$REPO13F3" worktree add -q -b feat-quote-data "$REPO13F3/.worktrees/feat-quote-data" >/dev/null 2>&1
WT13F3="$REPO13F3/.worktrees/feat-quote-data"
echo "data/" > "$WT13F3/.gitignore"
git -C "$WT13F3" add .gitignore
git -C "$WT13F3" commit -q -m "add gitignore"
git -C "$REPO13F3" merge -q feat-quote-data 2>/dev/null || true
mkdir -p "$WT13F3/data"
: > "$WT13F3/data/a\"b.csv"
backdate_worktree "$WT13F3"
OUT13F3="$(run_sweep "$REPO13F3")"
assert_dir_exists "$WT13F3" "⑬f3 data/ 下文件名含双引号的忽略文件不应被删"
if [ -f "$WT13F3/data/a\"b.csv" ]; then pass; else fail "⑬f3 data/a\"b.csv 不应随目录一起丢失"; fi
assert_not_contains "$OUT13F3" "已清理" "⑬f3 不应被当作清理"
assert_contains "$OUT13F3" "不可再生的被忽略文件" "⑬f3 提醒消息应含标准措辞"

# =========================================================
# ⑬g .gitignore 用目录规则（instance/、certs/）折叠掉的整个忽略目录，
#    内部藏着黑名单文件（instance/app.db、certs/server.pem）→ 不应被删
#    —— 回归防护：--ignored=matching 会把整个被忽略的目录折叠成一条
#    目录记录，不列出其中文件，若脚本不深扫会漏判
# =========================================================
REPO13G="$WORK/repo13g"
make_repo "$REPO13G"
git -C "$REPO13G" worktree add -q -b feat-instance "$REPO13G/.worktrees/feat-instance" >/dev/null 2>&1
{
  echo "instance/"
  echo "certs/"
} > "$REPO13G/.worktrees/feat-instance/.gitignore"
git -C "$REPO13G/.worktrees/feat-instance" add .gitignore
git -C "$REPO13G/.worktrees/feat-instance" commit -q -m "add gitignore"
git -C "$REPO13G" merge -q feat-instance 2>/dev/null || true
mkdir -p "$REPO13G/.worktrees/feat-instance/instance" "$REPO13G/.worktrees/feat-instance/certs"
: > "$REPO13G/.worktrees/feat-instance/instance/app.db"
: > "$REPO13G/.worktrees/feat-instance/certs/server.pem"
backdate_worktree "$REPO13G/.worktrees/feat-instance"
OUT13G="$(run_sweep "$REPO13G")"
assert_dir_exists "$REPO13G/.worktrees/feat-instance" "⑬g 折叠目录内的黑名单文件不应被删"
if [ -f "$REPO13G/.worktrees/feat-instance/instance/app.db" ]; then pass; else fail "⑬g instance/app.db 不应随目录一起丢失"; fi
if [ -f "$REPO13G/.worktrees/feat-instance/certs/server.pem" ]; then pass; else fail "⑬g certs/server.pem 不应随目录一起丢失"; fi
assert_not_contains "$OUT13G" "已清理" "⑬g 不应被当作清理"

# =========================================================
# ⑬h 逐模式独立 fixture：黑名单里除 .env/db/sub-.env 之外的其余模式
#    （*.pem、*.key、*.p12、*.pfx、*.jks、*.keystore、*.env、*.sqlite、
#    *.sqlite3、*.secret、id_rsa*、id_ed25519*、secrets/ 含嵌套、data/
#    含嵌套）逐个各建一个新仓库 + 一个 worktree、.gitignore 只写该模式
#    对应的一条规则、只落这一个忽略文件，然后各自断言目录仍在、提醒消息
#    含标准措辞。—— 回归防护：旧版把所有模式塞进同一个 worktree，
#    grep -m 1 只要命中任意一条就通过整个用例，废掉黑名单里 10 个后缀
#    模式（把正则整段改成只剩 (db)）或去掉 *.env 后缀，实测整套仍
#    PASS: 134 FAIL: 0 全绿；拆成逐模式后任一模式从黑名单里消失都会让
#    对应的那一个用例精确变红。
# =========================================================
i13h=0
for pat in server.pem tls.key cert.p12 cert.pfx ks.jks a.keystore app.sqlite app.sqlite3 token.secret id_rsa id_ed25519 config.env secrets/creds.txt sub/secrets/creds.txt data/raw/x.csv; do
  i13h=$((i13h + 1))
  R13H="$WORK/repo13h-$i13h"
  make_repo "$R13H"
  git -C "$R13H" worktree add -q -b "feat-p13h-$i13h" "$R13H/.worktrees/wt" >/dev/null 2>&1
  WTP="$R13H/.worktrees/wt"
  printf '%s\n' "$pat" > "$WTP/.gitignore"
  git -C "$WTP" add .gitignore
  git -C "$WTP" commit -q -m "add gitignore"
  git -C "$R13H" merge -q "feat-p13h-$i13h" 2>/dev/null || true
  case "$pat" in
    */*) mkdir -p "$WTP/$(dirname "$pat")" ;;
  esac
  : > "$WTP/$pat"
  backdate_worktree "$WTP"
  OUTP="$(run_sweep "$R13H")"
  assert_dir_exists "$WTP" "⑬h[$pat] 含该黑名单模式的 worktree 不应被删"
  if [ -f "$WTP/$pat" ]; then pass; else fail "⑬h[$pat] $pat 不应随目录一起丢失"; fi
  assert_not_contains "$OUTP" "已清理" "⑬h[$pat] 不应被当作清理"
  assert_contains "$OUTP" "不可再生的被忽略文件" "⑬h[$pat] 提醒消息应含标准措辞"
done

# =========================================================
# ⑬i 同名 tag 与未合并分支（tag rel 指向 main、分支 rel 有额外未合并提交）
#    → merge-base 若用裸分支名会被解析成 tag，误判为已合并；应静默跳过
# =========================================================
REPOTAG="$WORK/repo-tag"
make_repo "$REPOTAG"
git -C "$REPOTAG" worktree add -q -b rel "$REPOTAG/.worktrees/rel" >/dev/null 2>&1
echo "wip" > "$REPOTAG/.worktrees/rel/extra.txt"
git -C "$REPOTAG/.worktrees/rel" add -A
git -C "$REPOTAG/.worktrees/rel" commit -q -m "wip on rel"
git -C "$REPOTAG" tag rel
backdate_worktree "$REPOTAG/.worktrees/rel"
OUTTAG="$(run_sweep "$REPOTAG")"
assert_dir_exists "$REPOTAG/.worktrees/rel" "⑬i 同名 tag 不应让未并入 main 的分支被误判为已合并"
assert_empty "$OUTTAG" "⑬i 同名 tag 场景下未并 main 应静默跳过、无输出"

# =========================================================
# ⑬j detached worktree（无分支）→ 不应被动、无输出
# =========================================================
REPODET="$WORK/repo-detached"
make_repo "$REPODET"
git -C "$REPODET" worktree add -q --detach "$REPODET/.worktrees/detached1" main >/dev/null 2>&1
backdate_worktree "$REPODET/.worktrees/detached1"
OUTDET="$(run_sweep "$REPODET")"
assert_dir_exists "$REPODET/.worktrees/detached1" "⑬j detached worktree 不应被删"
assert_empty "$OUTDET" "⑬j detached worktree 应静默跳过、无输出"

# =========================================================
# ⑬k 一次 sweep 里同一仓库产生 2 条以上提醒消息 → systemMessage 应仍是
#    合法 JSON、含两个分支名各一行——回归防护：jq -n --arg 的转义若被
#    换成裸 printf，多行/特殊字符会破坏 JSON 合法性且测试不易发现
# =========================================================
REPOJSON="$WORK/repo-json"
make_repo "$REPOJSON"
git -C "$REPOJSON" worktree add -q -b feat-json-a "$REPOJSON/.worktrees/feat-json-a" >/dev/null 2>&1
git -C "$REPOJSON" merge -q feat-json-a 2>/dev/null || true
: > "$REPOJSON/.worktrees/feat-json-a/untracked-a.txt"
backdate_worktree "$REPOJSON/.worktrees/feat-json-a"
git -C "$REPOJSON" worktree add -q -b feat-json-b "$REPOJSON/.worktrees/feat-json-b" >/dev/null 2>&1
git -C "$REPOJSON" merge -q feat-json-b 2>/dev/null || true
: > "$REPOJSON/.worktrees/feat-json-b/untracked-b.txt"
backdate_worktree "$REPOJSON/.worktrees/feat-json-b"
OUTJSON="$(run_sweep "$REPOJSON")"
if printf '%s' "$OUTJSON" | jq -e '.' >/dev/null 2>&1; then pass; else fail "⑬k 多条提醒消息应仍是合法 JSON"; fi
assert_contains "$OUTJSON" "feat-json-a" "⑬k 消息应含分支 a"
assert_contains "$OUTJSON" "feat-json-b" "⑬k 消息应含分支 b"
LINES_JSON="$(printf '%s' "$OUTJSON" | jq -r '.systemMessage' 2>/dev/null | grep -c 'worktree-sweep:' || true)"
if [ "$LINES_JSON" -ge 2 ] 2>/dev/null; then pass; else fail "⑬k systemMessage 应至少含 2 条消息，实际 $LINES_JSON"; fi

# =========================================================
# ⑬l worktree 路径含双引号字符 → systemMessage 仍应是合法 JSON
# =========================================================
REPOQUOTE="$WORK/repo-quote"
make_repo "$REPOQUOTE"
QDIR="$REPOQUOTE/.worktrees/feat-quo\"te"
git -C "$REPOQUOTE" worktree add -q -b feat-quote "$QDIR" >/dev/null 2>&1
git -C "$REPOQUOTE" merge -q feat-quote 2>/dev/null || true
: > "$QDIR/untracked.txt"
backdate_worktree "$QDIR"
OUTQUOTE="$(run_sweep "$REPOQUOTE")"
if printf '%s' "$OUTQUOTE" | jq -e '.' >/dev/null 2>&1; then pass; else fail "⑬l 路径含引号时输出仍应是合法 JSON"; fi
assert_dir_exists "$QDIR" "⑬l 路径含引号、有未提交改动的 worktree 不应被删"

# =========================================================
# ⑬m data/ 用文件级规则忽略（data/*.csv，未整目录折叠）→ git 逐个列出
#     文件路径而非折叠目录记录，data/local.csv 仍应被判黑名单命中、不删
# =========================================================
REPO13M="$WORK/repo13m"
make_repo "$REPO13M"
git -C "$REPO13M" worktree add -q -b feat-data-file "$REPO13M/.worktrees/feat-data-file" >/dev/null 2>&1
echo "data/*.csv" > "$REPO13M/.worktrees/feat-data-file/.gitignore"
git -C "$REPO13M/.worktrees/feat-data-file" add .gitignore
git -C "$REPO13M/.worktrees/feat-data-file" commit -q -m "add gitignore"
git -C "$REPO13M" merge -q feat-data-file 2>/dev/null || true
mkdir -p "$REPO13M/.worktrees/feat-data-file/data"
: > "$REPO13M/.worktrees/feat-data-file/data/local.csv"
backdate_worktree "$REPO13M/.worktrees/feat-data-file"
OUT13M="$(run_sweep "$REPO13M")"
assert_dir_exists "$REPO13M/.worktrees/feat-data-file" "⑬m 文件级 data/*.csv 规则忽略的文件不应被删"
if [ -f "$REPO13M/.worktrees/feat-data-file/data/local.csv" ]; then pass; else fail "⑬m data/local.csv 不应随目录一起丢失"; fi
assert_not_contains "$OUT13M" "已清理" "⑬m 不应被当作清理"

# =========================================================
# ⑬n data/ 用 data/* + 否定例外忽略（标准"用 .gitkeep 占位保留空目录"
#     写法：data/ 会连目录本身一起排除、导致 !data/.gitkeep 这条否定规则
#     被 git 判定为不可能生效而报错，必须用 data/* 只排除内容不排除目录
#     本身）→ 该写法下 git 无法把整个目录折叠成一条记录，必须逐个列出
#     文件；data/dump.csv 仍应被判黑名单命中、不删
# =========================================================
REPO13N="$WORK/repo13n"
make_repo "$REPO13N"
git -C "$REPO13N" worktree add -q -b feat-data-negate "$REPO13N/.worktrees/feat-data-negate" >/dev/null 2>&1
{
  echo "data/*"
  echo "!data/.gitkeep"
} > "$REPO13N/.worktrees/feat-data-negate/.gitignore"
mkdir -p "$REPO13N/.worktrees/feat-data-negate/data"
: > "$REPO13N/.worktrees/feat-data-negate/data/.gitkeep"
git -C "$REPO13N/.worktrees/feat-data-negate" add .gitignore data/.gitkeep
git -C "$REPO13N/.worktrees/feat-data-negate" commit -q -m "add gitignore with negation"
git -C "$REPO13N" merge -q feat-data-negate 2>/dev/null || true
: > "$REPO13N/.worktrees/feat-data-negate/data/dump.csv"
backdate_worktree "$REPO13N/.worktrees/feat-data-negate"
OUT13N="$(run_sweep "$REPO13N")"
assert_dir_exists "$REPO13N/.worktrees/feat-data-negate" "⑬n 带否定例外的 data/ 规则下 data/dump.csv 不应被删"
if [ -f "$REPO13N/.worktrees/feat-data-negate/data/dump.csv" ]; then pass; else fail "⑬n data/dump.csv 不应随目录一起丢失"; fi
assert_not_contains "$OUT13N" "已清理" "⑬n 不应被当作清理"

# =========================================================
# ⑬o 非黑名单目录名（instance/）折叠掉的忽略目录里，嵌套着一个真正的
#     data/ 子目录，其中文件名本身也不命中任何黑名单后缀
#     （instance/data/x.csv）→ 仍应靠目录名判断拦下、不删
# =========================================================
REPO13O="$WORK/repo13o"
make_repo "$REPO13O"
git -C "$REPO13O" worktree add -q -b feat-nested-data "$REPO13O/.worktrees/feat-nested-data" >/dev/null 2>&1
echo "instance/" > "$REPO13O/.worktrees/feat-nested-data/.gitignore"
git -C "$REPO13O/.worktrees/feat-nested-data" add .gitignore
git -C "$REPO13O/.worktrees/feat-nested-data" commit -q -m "add gitignore"
git -C "$REPO13O" merge -q feat-nested-data 2>/dev/null || true
mkdir -p "$REPO13O/.worktrees/feat-nested-data/instance/data"
: > "$REPO13O/.worktrees/feat-nested-data/instance/data/x.csv"
backdate_worktree "$REPO13O/.worktrees/feat-nested-data"
OUT13O="$(run_sweep "$REPO13O")"
assert_dir_exists "$REPO13O/.worktrees/feat-nested-data" "⑬o 折叠目录内嵌套的 data/ 子目录不应被删"
if [ -f "$REPO13O/.worktrees/feat-nested-data/instance/data/x.csv" ]; then pass; else fail "⑬o instance/data/x.csv 不应随目录一起丢失"; fi
assert_not_contains "$OUT13O" "已清理" "⑬o 不应被当作清理"

# =========================================================
# ⑬p secrets/ 被整目录折叠、里面只有一个文件名不命中任何 find 黑名单
#     模式的 notes.txt，worktree 里没有别的忽略文件 → 仍应靠 secrets/
#     这个目录名本身拦下、不删（单独钉住 case 里 secrets/ 精确匹配分支：
#     去掉该分支、只剩深扫时，notes.txt 不命中文件名模式、也不在
#     mindepth 1 之内命中目录名判断——因为顶层目录自身被 mindepth 1
#     排除在外——此用例必红）
# =========================================================
REPO13P="$WORK/repo13p"
make_repo "$REPO13P"
git -C "$REPO13P" worktree add -q -b feat-secrets-only "$REPO13P/.worktrees/feat-secrets-only" >/dev/null 2>&1
echo "secrets/" > "$REPO13P/.worktrees/feat-secrets-only/.gitignore"
git -C "$REPO13P/.worktrees/feat-secrets-only" add .gitignore
git -C "$REPO13P/.worktrees/feat-secrets-only" commit -q -m "add gitignore"
git -C "$REPO13P" merge -q feat-secrets-only 2>/dev/null || true
mkdir -p "$REPO13P/.worktrees/feat-secrets-only/secrets"
: > "$REPO13P/.worktrees/feat-secrets-only/secrets/notes.txt"
backdate_worktree "$REPO13P/.worktrees/feat-secrets-only"
OUT13P="$(run_sweep "$REPO13P")"
assert_dir_exists "$REPO13P/.worktrees/feat-secrets-only" "⑬p 整目录折叠的 secrets/ 不应被删，即使里面文件名不命中黑名单"
if [ -f "$REPO13P/.worktrees/feat-secrets-only/secrets/notes.txt" ]; then pass; else fail "⑬p secrets/notes.txt 不应随目录一起丢失"; fi
assert_not_contains "$OUT13P" "已清理" "⑬p 不应被当作清理"

# =========================================================
# ⑬q .env 变体覆盖：.env.local、.env.production、sub/.env.local
#     （.gitignore 用 .env* 一条规则覆盖所有层级）→ 均不应被删
# =========================================================
REPO13Q="$WORK/repo13q"
make_repo "$REPO13Q"
git -C "$REPO13Q" worktree add -q -b feat-env-variants "$REPO13Q/.worktrees/feat-env-variants" >/dev/null 2>&1
WT13Q="$REPO13Q/.worktrees/feat-env-variants"
echo ".env*" > "$WT13Q/.gitignore"
git -C "$WT13Q" add .gitignore
git -C "$WT13Q" commit -q -m "add gitignore"
git -C "$REPO13Q" merge -q feat-env-variants 2>/dev/null || true
: > "$WT13Q/.env.local"
: > "$WT13Q/.env.production"
mkdir -p "$WT13Q/sub"
: > "$WT13Q/sub/.env.local"
backdate_worktree "$WT13Q"
OUT13Q="$(run_sweep "$REPO13Q")"
assert_dir_exists "$WT13Q" "⑬q .env 变体(.env.local/.env.production/sub/.env.local)不应被删"
for f in .env.local .env.production sub/.env.local; do
  if [ -f "$WT13Q/$f" ]; then pass; else fail "⑬q $f 不应随目录一起丢失"; fi
done
assert_not_contains "$OUT13Q" "已清理" "⑬q 不应被当作清理"
assert_contains "$OUT13Q" "不可再生的被忽略文件" "⑬q 提醒消息应含标准措辞"

# =========================================================
# ⑬r data/、secrets/ 嵌套子目录：文件名本身不带任何黑名单后缀，
#     仍应靠目录名判断拦下；外加反例 mydata/（目录名不精确匹配 data）
#     照常删除
# =========================================================
# (a) data/* + !data/.gitkeep（提交 data/.gitkeep 占位保留空目录）
#     + data/raw/dump.csv
REPO13Ra="$WORK/repo13ra"
make_repo "$REPO13Ra"
git -C "$REPO13Ra" worktree add -q -b feat-data-gitkeep "$REPO13Ra/.worktrees/feat-data-gitkeep" >/dev/null 2>&1
WT13Ra="$REPO13Ra/.worktrees/feat-data-gitkeep"
{
  echo "data/*"
  echo "!data/.gitkeep"
} > "$WT13Ra/.gitignore"
mkdir -p "$WT13Ra/data"
: > "$WT13Ra/data/.gitkeep"
git -C "$WT13Ra" add .gitignore data/.gitkeep
git -C "$WT13Ra" commit -q -m "add gitignore with gitkeep"
git -C "$REPO13Ra" merge -q feat-data-gitkeep 2>/dev/null || true
mkdir -p "$WT13Ra/data/raw"
: > "$WT13Ra/data/raw/dump.csv"
backdate_worktree "$WT13Ra"
OUT13Ra="$(run_sweep "$REPO13Ra")"
assert_dir_exists "$WT13Ra" "⑬r(a) data/.gitkeep 占位下 data/raw/dump.csv 不应被删"
if [ -f "$WT13Ra/data/raw/dump.csv" ]; then pass; else fail "⑬r(a) data/raw/dump.csv 不应随目录一起丢失"; fi
assert_contains "$OUT13Ra" "不可再生的被忽略文件" "⑬r(a) 提醒消息应含标准措辞"
assert_not_contains "$OUT13Ra" "已清理" "⑬r(a) 不应被当作清理"

# (b) secrets/*（整目录未跟踪，无占位文件）+ secrets/sub/keys.txt
REPO13Rb="$WORK/repo13rb"
make_repo "$REPO13Rb"
git -C "$REPO13Rb" worktree add -q -b feat-secrets-star "$REPO13Rb/.worktrees/feat-secrets-star" >/dev/null 2>&1
WT13Rb="$REPO13Rb/.worktrees/feat-secrets-star"
echo "secrets/*" > "$WT13Rb/.gitignore"
git -C "$WT13Rb" add .gitignore
git -C "$WT13Rb" commit -q -m "add gitignore"
git -C "$REPO13Rb" merge -q feat-secrets-star 2>/dev/null || true
mkdir -p "$WT13Rb/secrets/sub"
: > "$WT13Rb/secrets/sub/keys.txt"
backdate_worktree "$WT13Rb"
OUT13Rb="$(run_sweep "$REPO13Rb")"
assert_dir_exists "$WT13Rb" "⑬r(b) secrets/sub/keys.txt 不应被删"
if [ -f "$WT13Rb/secrets/sub/keys.txt" ]; then pass; else fail "⑬r(b) secrets/sub/keys.txt 不应随目录一起丢失"; fi
assert_contains "$OUT13Rb" "不可再生的被忽略文件" "⑬r(b) 提醒消息应含标准措辞"
assert_not_contains "$OUT13Rb" "已清理" "⑬r(b) 不应被当作清理"

# (c) api/data/*（data/ 出现在深层子路径）+ api/data/raw/dump.csv
REPO13Rc="$WORK/repo13rc"
make_repo "$REPO13Rc"
git -C "$REPO13Rc" worktree add -q -b feat-api-data "$REPO13Rc/.worktrees/feat-api-data" >/dev/null 2>&1
WT13Rc="$REPO13Rc/.worktrees/feat-api-data"
echo "api/data/*" > "$WT13Rc/.gitignore"
git -C "$WT13Rc" add .gitignore
git -C "$WT13Rc" commit -q -m "add gitignore"
git -C "$REPO13Rc" merge -q feat-api-data 2>/dev/null || true
mkdir -p "$WT13Rc/api/data/raw"
: > "$WT13Rc/api/data/raw/dump.csv"
backdate_worktree "$WT13Rc"
OUT13Rc="$(run_sweep "$REPO13Rc")"
assert_dir_exists "$WT13Rc" "⑬r(c) api/data/raw/dump.csv 不应被删"
if [ -f "$WT13Rc/api/data/raw/dump.csv" ]; then pass; else fail "⑬r(c) api/data/raw/dump.csv 不应随目录一起丢失"; fi
assert_contains "$OUT13Rc" "不可再生的被忽略文件" "⑬r(c) 提醒消息应含标准措辞"
assert_not_contains "$OUT13Rc" "已清理" "⑬r(c) 不应被当作清理"

# 反例：mydata/x.csv 被忽略，但目录名不是精确的 data（多了前缀 my）→ 照删
REPO13Rd="$WORK/repo13rd"
make_repo "$REPO13Rd"
git -C "$REPO13Rd" worktree add -q -b feat-mydata "$REPO13Rd/.worktrees/feat-mydata" >/dev/null 2>&1
WT13Rd="$REPO13Rd/.worktrees/feat-mydata"
echo "mydata/" > "$WT13Rd/.gitignore"
git -C "$WT13Rd" add .gitignore
git -C "$WT13Rd" commit -q -m "add gitignore"
git -C "$REPO13Rd" merge -q feat-mydata 2>/dev/null || true
mkdir -p "$WT13Rd/mydata"
: > "$WT13Rd/mydata/x.csv"
backdate_worktree "$WT13Rd"
OUT13Rd="$(run_sweep "$REPO13Rd")"
assert_dir_absent "$WT13Rd" "⑬r(反例) mydata/ 目录名不精确匹配 data，应照常删除"
assert_contains "$OUT13Rd" "feat-mydata" "⑬r(反例) 清理消息含分支名"

# =========================================================
# ⑬s git ls-files 失败（桩：参数里含 ls-files 就 exit 128，否则转真 git）
#     → 无法确认被忽略的文件，不删，提醒含固定措辞
# =========================================================
REPO13S="$WORK/repo13s"
make_repo "$REPO13S"
git -C "$REPO13S" worktree add -q -b feat-lsfiles-fail "$REPO13S/.worktrees/feat-lsfiles-fail" >/dev/null 2>&1
git -C "$REPO13S" merge -q feat-lsfiles-fail 2>/dev/null || true
backdate_worktree "$REPO13S/.worktrees/feat-lsfiles-fail"
REAL_GIT="$(command -v git)"
FAKEBIN_LS="$WORK/fakebin-lsfiles"
mkdir -p "$FAKEBIN_LS"
cat > "$FAKEBIN_LS/git" <<EOF
#!/bin/sh
for a in "\$@"; do
  if [ "\$a" = "ls-files" ]; then
    exit 128
  fi
done
exec "$REAL_GIT" "\$@"
EOF
chmod +x "$FAKEBIN_LS/git"
OUT13S="$(
  PATH="$FAKEBIN_LS:$PATH"
  run_sweep "$REPO13S"
)"
assert_dir_exists "$REPO13S/.worktrees/feat-lsfiles-fail" "⑬s ls-files 失败时不应被删"
assert_contains "$OUT13S" "无法确认被忽略的文件" "⑬s 应提示无法确认被忽略文件"

# =========================================================
# ⑬t git status 失败（桩：参数里含 status 就 exit 128，否则转真 git）
#     → 无法确认工作区状态，不删，提醒含固定措辞
# =========================================================
REPO13T="$WORK/repo13t"
make_repo "$REPO13T"
git -C "$REPO13T" worktree add -q -b feat-status-fail "$REPO13T/.worktrees/feat-status-fail" >/dev/null 2>&1
git -C "$REPO13T" merge -q feat-status-fail 2>/dev/null || true
backdate_worktree "$REPO13T/.worktrees/feat-status-fail"
FAKEBIN_ST="$WORK/fakebin-status"
mkdir -p "$FAKEBIN_ST"
cat > "$FAKEBIN_ST/git" <<EOF
#!/bin/sh
for a in "\$@"; do
  if [ "\$a" = "status" ]; then
    exit 128
  fi
done
exec "$REAL_GIT" "\$@"
EOF
chmod +x "$FAKEBIN_ST/git"
OUT13T="$(
  PATH="$FAKEBIN_ST:$PATH"
  run_sweep "$REPO13T"
)"
assert_dir_exists "$REPO13T/.worktrees/feat-status-fail" "⑬t git status 失败时不应被删"
assert_contains "$OUT13T" "无法确认工作区状态" "⑬t 应提示无法确认工作区状态"

# =========================================================
# ⑬u 被忽略目录内嵌套着另一个 git 仓库（vendored clone）→ git ls-files
#    在仓库边界处不会展开，只输出一条折叠的目录项（plugins/lib/），其
#    内部的 .env、data/ 等不可再生文件对黑名单正则完全不可见；这类折叠
#    项应按「无法确认」处理，不删、不清理。fixture 特意放在非依赖目录名
#    （plugins/lib，而不是 vendor/lib）下——vendor/ 现在整体按依赖目录
#    放行，若继续放在 vendor/lib 下，折叠项会先被依赖目录白名单过滤掉，
#    测不到「折叠目录」这条判据本身。
# =========================================================
REPO13U="$WORK/repo13u"
make_repo "$REPO13U"
git -C "$REPO13U" worktree add -q -b feat-nested-repo "$REPO13U/.worktrees/feat-nested-repo" >/dev/null 2>&1
WT13U="$REPO13U/.worktrees/feat-nested-repo"
echo "plugins/" > "$WT13U/.gitignore"
git -C "$WT13U" add .gitignore
git -C "$WT13U" commit -q -m "add gitignore"
git -C "$REPO13U" merge -q feat-nested-repo 2>/dev/null || true
mkdir -p "$WT13U/plugins/lib/data"
git init -q "$WT13U/plugins/lib" >/dev/null 2>&1
git -C "$WT13U/plugins/lib" config user.email test@example.com
git -C "$WT13U/plugins/lib" config user.name "Test"
echo "SECRET=abc" > "$WT13U/plugins/lib/.env"
: > "$WT13U/plugins/lib/data/rows.csv"
echo "x" > "$WT13U/plugins/lib/README.md"
git -C "$WT13U/plugins/lib" add -A
git -C "$WT13U/plugins/lib" commit -q -m "nested repo commit"
backdate_worktree "$WT13U"
OUT13U="$(run_sweep "$REPO13U")"
assert_dir_exists "$WT13U" "⑬u 被忽略目录内含未展开嵌套仓库的 worktree 不应被删"
if [ -f "$WT13U/plugins/lib/.env" ]; then pass; else fail "⑬u plugins/lib/.env 不应随目录一起丢失"; fi
if [ -f "$WT13U/plugins/lib/data/rows.csv" ]; then pass; else fail "⑬u plugins/lib/data/rows.csv 不应随目录一起丢失"; fi
assert_not_contains "$OUT13U" "已清理" "⑬u 不应被当作清理"
assert_contains "$OUT13U" "存在未展开的嵌套仓库目录" "⑬u 提醒消息应点名未展开的嵌套仓库"
assert_contains "$OUT13U" "无法确认被忽略的文件" "⑬u 提醒消息应含无法确认措辞"

# ⑬u2 反例：同样是被忽略目录内嵌套一个未展开的 git 仓库，但这次嵌套点
# 落在依赖目录（node_modules/lib）之内，且仓库内含 data/x.csv → 依赖
# 目录整体放行优先于「折叠目录看不见内部文件」的无法确认判断（折叠项
# 本身在 grep -vE 依赖目录过滤那一步就被剔除了，根本不会走到折叠检查），
# 应照常删除
REPO13U2="$WORK/repo13u2"
make_repo "$REPO13U2"
git -C "$REPO13U2" worktree add -q -b feat-nested-dep-repo "$REPO13U2/.worktrees/feat-nested-dep-repo" >/dev/null 2>&1
WT13U2="$REPO13U2/.worktrees/feat-nested-dep-repo"
echo "node_modules/" > "$WT13U2/.gitignore"
git -C "$WT13U2" add .gitignore
git -C "$WT13U2" commit -q -m "add gitignore"
git -C "$REPO13U2" merge -q feat-nested-dep-repo 2>/dev/null || true
mkdir -p "$WT13U2/node_modules/lib/data"
git init -q "$WT13U2/node_modules/lib" >/dev/null 2>&1
git -C "$WT13U2/node_modules/lib" config user.email test@example.com
git -C "$WT13U2/node_modules/lib" config user.name "Test"
: > "$WT13U2/node_modules/lib/data/x.csv"
echo "x" > "$WT13U2/node_modules/lib/README.md"
git -C "$WT13U2/node_modules/lib" add -A
git -C "$WT13U2/node_modules/lib" commit -q -m "nested dep repo commit"
backdate_worktree "$WT13U2"
OUT13U2="$(run_sweep "$REPO13U2")"
assert_dir_absent "$WT13U2" "⑬u2 依赖目录(node_modules)下未展开的嵌套仓库应照常删除"
assert_contains "$OUT13U2" "feat-nested-dep-repo" "⑬u2 清理消息含分支名"
assert_contains "$OUT13U2" "已清理" "⑬u2 应被当作清理"

# =========================================================
# ⑬v 被忽略目录内嵌套着另一个 worktree（同一仓库的第二个 worktree 挂在
#    被忽略路径下）→ 同样在仓库边界处折叠，无法看到其内部未提交/未跟踪
#    的改动；按「无法确认」处理，不删、不清理
# =========================================================
REPO13V="$WORK/repo13v"
make_repo "$REPO13V"
git -C "$REPO13V" worktree add -q -b feat-nested-wt "$REPO13V/.worktrees/feat-nested-wt" >/dev/null 2>&1
WT13V="$REPO13V/.worktrees/feat-nested-wt"
echo "nested/" > "$WT13V/.gitignore"
git -C "$WT13V" add .gitignore
git -C "$WT13V" commit -q -m "add gitignore"
git -C "$REPO13V" merge -q feat-nested-wt 2>/dev/null || true
mkdir -p "$WT13V/nested"
git -C "$REPO13V" worktree add -q -b feat-nested-inner "$WT13V/nested/inner" >/dev/null 2>&1
echo "wip" > "$WT13V/nested/inner/wip.txt"
git -C "$WT13V/nested/inner" add -A
git -C "$WT13V/nested/inner" commit -q -m "wip inner"
backdate_worktree "$WT13V"
OUT13V="$(run_sweep "$REPO13V")"
assert_dir_exists "$WT13V" "⑬v 被忽略目录内含未展开嵌套 worktree 的 worktree 不应被删"
assert_dir_exists "$WT13V/nested/inner" "⑬v 嵌套 worktree 的内容不应随外层目录一起丢失"
assert_not_contains "$OUT13V" "已清理" "⑬v 不应被当作清理"
assert_contains "$OUT13V" "存在未展开的嵌套仓库目录" "⑬v 提醒消息应点名未展开的嵌套仓库"

# =========================================================
# ⑰ 判据⑤的时间戳源钉版：worktree 建立已超过 30 分钟（.git 文件本身
#    显示"很旧"），但 git 管理目录下的 index 刚被刷新（模拟仍在使用，
#    只是没有走到会话/进程检测覆盖的路径）→ 不应被删、无输出。
#    若实现改回读 worktree 里 .git 文件本身的 mtime 判断"太新"，会误判
#    为"已建立超过 30 分钟"而继续往下删——此用例必红。
# =========================================================
REPO17="$WORK/repo17"
make_repo "$REPO17"
git -C "$REPO17" worktree add -q -b feat-still-active "$REPO17/.worktrees/feat-still-active" >/dev/null 2>&1
git -C "$REPO17" merge -q feat-still-active 2>/dev/null || true
WT17="$REPO17/.worktrees/feat-still-active"
TS17="$(date -v-40M +%Y%m%d%H%M 2>/dev/null)"
[ -n "$TS17" ] || TS17="$(date -d '40 minutes ago' +%Y%m%d%H%M 2>/dev/null)"
GD17="$(git -C "$WT17" rev-parse --git-dir 2>/dev/null)"
case "$GD17" in
  /*) ;;
  *) GD17="$WT17/$GD17" ;;
esac
# 先把三样都置成 40 分钟前，模拟"建立于 40 分钟前"
touch -t "$TS17" "$WT17/.git" 2>/dev/null
touch -t "$TS17" "$GD17/index" 2>/dev/null
[ -f "$GD17/COMMIT_EDITMSG" ] && touch -t "$TS17" "$GD17/COMMIT_EDITMSG" 2>/dev/null
# 再单独把 index 刷新为"现在"，模拟"此刻仍在使用"，但不碰 .git 文件本身
touch "$GD17/index" 2>/dev/null
OUT17="$(run_sweep "$REPO17")"
assert_dir_exists "$WT17" "⑰仍在用(index 刚更新)的 worktree 不应被删，即使 .git 文件本身显示已建立超过 30 分钟"
assert_empty "$OUT17" "⑰仍在用的 worktree 应静默跳过、无输出"

# =========================================================
# ⑰b 30 分钟窗口的中间地带钉版：index/COMMIT_EDITMSG 只提前到 10 分钟前
#    （仍在窗口内，既不是"刚刚"也不是"早已过期的 40 分钟前"）→ 仍应判定
#    为"太新不动"，不应被删、无输出——回归防护：若把判据⑤的 -mmin -30
#    缩小成 -mmin -5，10 分钟前会被误判为"已超过窗口"而继续往下删。
# =========================================================
REPO17B="$WORK/repo17b"
make_repo "$REPO17B"
git -C "$REPO17B" worktree add -q -b feat-mid-window "$REPO17B/.worktrees/feat-mid-window" >/dev/null 2>&1
git -C "$REPO17B" merge -q feat-mid-window 2>/dev/null || true
WT17B="$REPO17B/.worktrees/feat-mid-window"
TS17B="$(date -v-10M +%Y%m%d%H%M 2>/dev/null)"
[ -n "$TS17B" ] || TS17B="$(date -d '10 minutes ago' +%Y%m%d%H%M 2>/dev/null)"
GD17B="$(git -C "$WT17B" rev-parse --git-dir 2>/dev/null)"
case "$GD17B" in
  /*) ;;
  *) GD17B="$WT17B/$GD17B" ;;
esac
touch -t "$TS17B" "$GD17B/index" 2>/dev/null
[ -f "$GD17B/COMMIT_EDITMSG" ] && touch -t "$TS17B" "$GD17B/COMMIT_EDITMSG" 2>/dev/null
OUT17B="$(run_sweep "$REPO17B")"
assert_dir_exists "$WT17B" "⑰b 10 分钟前(仍在 30 分钟窗口内)的 worktree 不应被删"
assert_empty "$OUT17B" "⑰b 窗口中间地带应静默跳过、无输出"

# =========================================================
# ⑰c 会话记录时间窗钉版：worktree 其余判据均满足（已并 main、干净、
#    index/COMMIT_EDITMSG 已 backdate 到窗口外），但会话记录目录下的
#    jsonl 是 40 分钟前的陈旧记录（不是"新鲜"会话）→ 不应被判定为
#    "有活跃会话"，应照常删除——回归防护：若判据④的会话检测去掉
#    -mmin -30、只剩 -name '*.jsonl'，陈旧会话记录会让 worktree 永远
#    清不掉。
# =========================================================
REPO17C="$WORK/repo17c"
make_repo "$REPO17C"
git -C "$REPO17C" worktree add -q -b feat-stale-session "$REPO17C/.worktrees/feat-stale-session" >/dev/null 2>&1
git -C "$REPO17C" merge -q feat-stale-session 2>/dev/null || true
backdate_worktree "$REPO17C/.worktrees/feat-stale-session"
WT17C_PATH="$REPO17C/.worktrees/feat-stale-session"
WT17C_REAL="$(cd "$WT17C_PATH" && pwd -P)"
KEY17C="$(printf '%s' "$WT17C_REAL" | sed 's/[^A-Za-z0-9]/-/g')"
mkdir -p "$SESS_ROOT/$KEY17C"
: > "$SESS_ROOT/$KEY17C/a.jsonl"
TS17C="$(date -v-40M +%Y%m%d%H%M 2>/dev/null)"
[ -n "$TS17C" ] || TS17C="$(date -d '40 minutes ago' +%Y%m%d%H%M 2>/dev/null)"
touch -t "$TS17C" "$SESS_ROOT/$KEY17C/a.jsonl" 2>/dev/null
OUT17C="$(run_sweep "$REPO17C")"
assert_dir_absent "$WT17C_PATH" "⑰c 会话记录已陈旧(40 分钟前)的 worktree 应照常删除"
assert_contains "$OUT17C" "feat-stale-session" "⑰c 清理消息含分支名"
rm -rf "$SESS_ROOT/$KEY17C"

# =========================================================
# ⑱ 进程占用检测：worktree 里有一个进程的 cwd 落在该目录下（模拟仍在
#    只读探索、不提交也不跑 git 命令的子代理），即使已并 main、工作区
#    干净、时间戳判据也判定"够旧" → 仍不应被删、无输出
#    —— 本用例本身依赖 lsof；缺 lsof 时脚本按设计不阻断删除（保持原
#    行为，不因缺 lsof 而新增误报），断言必红，所以缺 lsof 时打印 SKIP
#    而不是让本来就该红的假阳性冒充成通过。
# =========================================================
if command -v lsof >/dev/null 2>&1; then
  REPO18="$WORK/repo18"
  make_repo "$REPO18"
  git -C "$REPO18" worktree add -q -b feat-proc-active "$REPO18/.worktrees/feat-proc-active" >/dev/null 2>&1
  git -C "$REPO18" merge -q feat-proc-active 2>/dev/null || true
  backdate_worktree "$REPO18/.worktrees/feat-proc-active"
  WT18="$REPO18/.worktrees/feat-proc-active"
  ( cd "$WT18" && exec sleep 20 ) &
  PROC18=$!
  # 给后台进程一点时间把 cwd 落进去再跑 sweep
  i=0
  while [ "$i" -lt 20 ]; do
    if lsof -a -d cwd -F n +D "$WT18" 2>/dev/null | grep -q .; then
      break
    fi
    i=$((i + 1))
    sleep 0.2 2>/dev/null || sleep 1
  done
  OUT18="$(run_sweep "$REPO18")"
  assert_dir_exists "$WT18" "⑱进程 cwd 落在 worktree 内时不应被删"
  assert_empty "$OUT18" "⑱进程占用应静默跳过、无输出"
  kill "$PROC18" >/dev/null 2>&1
  wait "$PROC18" 2>/dev/null

  # ⑱b 进程 cwd 落在 worktree 的子目录里（子代理常见工作形态：在子目录
  # 下干活，而不是直接停在 worktree 根）→ 同样不应被删——回归防护：若
  # lsof 判断只剩 q==p 这一支（丢掉 index(q, p "/")==1 的前缀分支），
  # 本用例必红。
  REPO18B="$WORK/repo18b"
  make_repo "$REPO18B"
  git -C "$REPO18B" worktree add -q -b feat-proc-active-sub "$REPO18B/.worktrees/feat-proc-active-sub" >/dev/null 2>&1
  git -C "$REPO18B" merge -q feat-proc-active-sub 2>/dev/null || true
  backdate_worktree "$REPO18B/.worktrees/feat-proc-active-sub"
  WT18B="$REPO18B/.worktrees/feat-proc-active-sub"
  mkdir -p "$WT18B/sub"
  ( cd "$WT18B/sub" && exec sleep 20 ) &
  PROC18B=$!
  i=0
  while [ "$i" -lt 20 ]; do
    if lsof -a -d cwd -F n +D "$WT18B/sub" 2>/dev/null | grep -q .; then
      break
    fi
    i=$((i + 1))
    sleep 0.2 2>/dev/null || sleep 1
  done
  OUT18B="$(run_sweep "$REPO18B")"
  assert_dir_exists "$WT18B" "⑱b 进程 cwd 落在 worktree 子目录内时不应被删"
  assert_empty "$OUT18B" "⑱b 进程占用(子目录)应静默跳过、无输出"
  kill "$PROC18B" >/dev/null 2>&1
  wait "$PROC18B" 2>/dev/null
else
  echo "SKIP: ⑱ 进程占用检测（本机未安装 lsof）"
fi

# =========================================================
# (19) 依赖目录整体放行的多文件钉版：.gitignore 写 node_modules/ 与
#      dist/，node_modules 下混入 css-tree/tldts/certifi 这几个真实存在
#      过的第三方包里带 data/ 目录或 .pem 后缀的路径（css-tree/data/、
#      tldts/src/data/、certifi/cacert.pem），dist/ 下混入 bundle.js →
#      均应视为可再生，目录照常删除、消息含「已清理」——回归防护：若
#      依赖目录白名单正则漏写 node_modules 或 dist 中任一个，这几个
#      真实包名路径会让黑名单误命中，整个 worktree 被拦下不删。
# =========================================================
REPO19="$WORK/repo19"
make_repo "$REPO19"
git -C "$REPO19" worktree add -q -b feat-deps-multi "$REPO19/.worktrees/feat-deps-multi" >/dev/null 2>&1
WT19="$REPO19/.worktrees/feat-deps-multi"
{
  echo "node_modules/"
  echo "dist/"
} > "$WT19/.gitignore"
git -C "$WT19" add .gitignore
git -C "$WT19" commit -q -m "add gitignore"
git -C "$REPO19" merge -q feat-deps-multi 2>/dev/null || true
mkdir -p "$WT19/node_modules/css-tree/data" "$WT19/node_modules/tldts/src/data" "$WT19/node_modules/certifi" "$WT19/dist"
: > "$WT19/node_modules/css-tree/data/patch.json"
: > "$WT19/node_modules/tldts/src/data/trie.ts"
: > "$WT19/node_modules/certifi/cacert.pem"
: > "$WT19/dist/bundle.js"
backdate_worktree "$WT19"
OUT19="$(run_sweep "$REPO19")"
assert_dir_absent "$WT19" "(19) node_modules/dist 下真实包名的 data/*.pem 路径不应拦下删除"
assert_contains "$OUT19" "已清理" "(19) 应被当作清理"
assert_contains "$OUT19" "feat-deps-multi" "(19) 清理消息含分支名"

# =========================================================
# (20) locale 双跑钉版：worktree 路径含非 ASCII（.worktrees/中文），会话
#      目录 key 用 python3 按 Claude Code 实际规则（逐字符、非
#      [A-Za-z0-9] 替换成 -，与 sed 按字节替换不同）计算，落一份新鲜
#      a.jsonl；分别用默认 locale 与 LC_ALL=C 跑 sweep，都应判定为活跃
#      会话、不删——脚本对同一路径算两个候选 key（LC_ALL=C 按字节、
#      LC_ALL=en_US.UTF-8 按字符），内部固定用这两个 locale 跑 sed、
#      与外层调用者的 locale 无关，所以两种外层 locale 下结果应一致。
# =========================================================
if command -v python3 >/dev/null 2>&1; then
  REPO20="$WORK/repo20"
  make_repo "$REPO20"
  git -C "$REPO20" worktree add -q -b feat-locale-cn "$REPO20/.worktrees/中文" >/dev/null 2>&1
  git -C "$REPO20" merge -q feat-locale-cn 2>/dev/null || true
  backdate_worktree "$REPO20/.worktrees/中文"
  WT20_PATH="$REPO20/.worktrees/中文"
  WT20_REAL="$(cd "$WT20_PATH" && pwd -P)"
  KEY20="$(python3 -c 'import sys, re
print(re.sub(r"[^A-Za-z0-9]", "-", sys.argv[1]))' "$WT20_REAL")"
  mkdir -p "$SESS_ROOT/$KEY20"
  : > "$SESS_ROOT/$KEY20/a.jsonl"
  OUT20A="$(run_sweep "$REPO20")"
  assert_dir_exists "$WT20_PATH" "(20) 默认 locale 下 python3 规则算出的会话 key 应判定为活跃、不删"
  OUT20B="$(LC_ALL=C run_sweep "$REPO20")"
  assert_dir_exists "$WT20_PATH" "(20) LC_ALL=C 下同一份会话 key 仍应判定为活跃、不删"
  rm -rf "$SESS_ROOT/$KEY20"
else
  echo "SKIP: (20) 本机未安装 python3，跳过 locale 会话 key 用例"
fi

# =========================================================
# (21) 主工作树区分：主 checkout 切到与 main 同一提交的 wipwork 分支，
#      另建一个兄弟 worktree（挂在仓库目录之外，分支 other），cwd 传
#      该兄弟 worktree 跑 sweep——即便主工作树当前检出的不是 main、cwd
#      也不在主工作树里，porcelain 第一条记录（主工作树）永远不该被当作
#      候选评估。backdate 主仓 .git/index 与 .git/worktrees/other/index，
#      让"太新不动"护栏不会顺带保护本该测的这条判据。
# =========================================================
REPO21="$WORK/repo21"
make_repo "$REPO21"
git -C "$REPO21" checkout -q -b wipwork
WT21_PATH="$WORK/repo21-wt"
git -C "$REPO21" worktree add -q -b other "$WT21_PATH" >/dev/null 2>&1
backdate_worktree "$REPO21"
backdate_worktree "$WT21_PATH"
OUT21="$(run_sweep "$WT21_PATH")"
assert_dir_exists "$REPO21" "(21) 主工作树目录应仍在"
assert_dir_exists "$REPO21/.git" "(21) 主工作树 .git 应仍在"
if [ -f "$REPO21/README.md" ]; then pass; else fail "(21) 主工作树 README.md 应仍在"; fi
assert_not_contains "$OUT21" "$REPO21" "(21) 输出不应含主工作树路径(可以含 other 那条)"

# =========================================================
# (22) 多根 SESSIONS_ROOTS（第一根不存在）+ 第二根命中新鲜会话 → 不删；
#      外加 prunable 记录（目录已删、admin 未回溯）→ run_sweep 应静默
#      跳过、无输出。bare 标记只会出现在 bare 仓库的主工作树那一条记录
#      上，而主工作树在进入 flags 判断之前就已经被 first 计数器跳过——
#      没有办法在"非首条记录"上构造出 bare 标记来单独测这条 case 分支，
#      构造不了，如实记录本限制，不加断言。
# =========================================================
REPO22="$WORK/repo22"
make_repo "$REPO22"
git -C "$REPO22" worktree add -q -b feat-multiroot "$REPO22/.worktrees/feat-multiroot" >/dev/null 2>&1
git -C "$REPO22" merge -q feat-multiroot 2>/dev/null || true
backdate_worktree "$REPO22/.worktrees/feat-multiroot"
WT22_PATH="$REPO22/.worktrees/feat-multiroot"
WT22_REAL="$(cd "$WT22_PATH" && pwd -P)"
KEY22="$(printf '%s' "$WT22_REAL" | sed 's/[^A-Za-z0-9]/-/g')"
mkdir -p "$WORK/globroot/p1/projects/$KEY22"
: > "$WORK/globroot/p1/projects/$KEY22/a.jsonl"
OUT22="$(payload="$(jq -n --arg cwd "$REPO22" '{cwd:$cwd}')"; printf '%s' "$payload" | WORKTREE_SWEEP_SESSIONS_ROOTS="$WORK/emptyroot:$WORK/globroot/*/projects" sh "$SWEEP_SH")"
assert_dir_exists "$WT22_PATH" "(22) 多根中第一根不存在、第二根命中新鲜会话时不应被删"
rm -rf "$WORK/globroot"

REPO22B="$WORK/repo22b"
make_repo "$REPO22B"
git -C "$REPO22B" worktree add -q -b feat-prunable "$REPO22B/.worktrees/feat-prunable" >/dev/null 2>&1
rm -rf "$REPO22B/.worktrees/feat-prunable"
OUT22B="$(run_sweep "$REPO22B")"
assert_empty "$OUT22B" "(22) prunable 记录(未回溯，不足 30 分钟)应静默跳过、无输出"

# =========================================================
# (23) 连跑两次、中间不再 backdate：钉住 --no-optional-locks——已并 main
#      但有未提交改动的 worktree，第一次跑给出「未提交改动」提醒；删掉
#      限频状态文件绕开"同仓一小时限一次"，不重新 backdate 直接再跑一次，
#      第二次仍应给出同样的提醒。若 git status 换成不带
#      --no-optional-locks 的版本，第一次跑就会把 admin 目录里 index 的
#      mtime 刷新到"现在"，第二次跑会被判据⑤"太新不动"拦在半路，变成
#      静默无输出而不是提醒。
# =========================================================
REPO23="$WORK/repo23"
make_repo "$REPO23"
git -C "$REPO23" worktree add -q -b feat-double-run "$REPO23/.worktrees/feat-double-run" >/dev/null 2>&1
git -C "$REPO23" merge -q feat-double-run 2>/dev/null || true
: > "$REPO23/.worktrees/feat-double-run/untracked.txt"
backdate_worktree "$REPO23/.worktrees/feat-double-run"
MARKER23="$WORK/marker23"
touch "$MARKER23"
OUT23A="$(run_sweep "$REPO23")"
assert_contains "$OUT23A" "工作区有未提交改动" "(23) 第一次跑应识别为未提交改动"
STATE23_FILE="$(find "$STATE_DIR" -maxdepth 1 -name 'worktree-sweep-*' -newer "$MARKER23" 2>/dev/null | head -n 1)"
[ -n "$STATE23_FILE" ] && rm -f "$STATE23_FILE"
OUT23B="$(run_sweep "$REPO23")"
assert_contains "$OUT23B" "工作区有未提交改动" "(23) 第二次跑(不重新 backdate)仍应识别为未提交改动,钉住 --no-optional-locks"

# =========================================================
# ⑭ en 提示语：已并 main 且干净 → 清理成功文案为英文，且以固定前缀开头
# =========================================================
REPO14="$WORK/repo14"
make_repo "$REPO14"
git -C "$REPO14" worktree add -q -b feat-clean-en "$REPO14/.worktrees/feat-clean-en" >/dev/null 2>&1
git -C "$REPO14" merge -q feat-clean-en 2>/dev/null || true
backdate_worktree "$REPO14/.worktrees/feat-clean-en"
OUT14="$(run_sweep "$REPO14" en)"
assert_dir_absent "$REPO14/.worktrees/feat-clean-en" "⑭en:已并且干净的 worktree 应被删"
assert_contains "$OUT14" "merged into main, local branch deleted" "⑭en 清理成功文案应为英文"
MSG14="$(printf '%s' "$OUT14" | jq -r '.systemMessage' 2>/dev/null)"
assert_starts_with "$MSG14" "worktree-sweep: cleaned up" "⑭en 消息应以固定前缀开头"
assert_no_chinese "$MSG14" "⑭en 消息不应含中文"
if printf '%s' "$OUT14" | jq -e '.systemMessage' >/dev/null 2>&1; then pass; else fail "⑭en 输出应为含 systemMessage 键的合法 JSON"; fi

# =========================================================
# ⑮ WORKTREE_SWEEP_SESSIONS_ROOTS 显式传含通配符的根（回归防护：set -f
#    曾让通配符根永远不展开，导致会话检测形同虚设）→ 新鲜 jsonl 应被识别，
#    worktree 不应被删
# =========================================================
REPO15="$WORK/repo15"
make_repo "$REPO15"
git -C "$REPO15" worktree add -q -b feat-glob-root "$REPO15/.worktrees/feat-glob-root" >/dev/null 2>&1
git -C "$REPO15" merge -q feat-glob-root 2>/dev/null || true
backdate_worktree "$REPO15/.worktrees/feat-glob-root"
WT15_PATH="$REPO15/.worktrees/feat-glob-root"
WT15_REAL="$(cd "$WT15_PATH" && pwd -P)"
KEY15="$(printf '%s' "$WT15_REAL" | sed 's/[^A-Za-z0-9]/-/g')"
GLOB_ROOT_BASE="$WORK/globroots"
mkdir -p "$GLOB_ROOT_BASE/p1/projects/$KEY15"
: > "$GLOB_ROOT_BASE/p1/projects/$KEY15/a.jsonl"
OUT15="$(payload="$(jq -n --arg cwd "$REPO15" '{cwd:$cwd}')"; printf '%s' "$payload" | WORKTREE_SWEEP_SESSIONS_ROOTS="$GLOB_ROOT_BASE/*/projects" sh "$SWEEP_SH")"
assert_dir_exists "$WT15_PATH" "⑮显式传通配符 SESSIONS_ROOTS 应检测到活跃会话，worktree 不应被删"
rm -rf "$GLOB_ROOT_BASE"

# =========================================================
# ⑯ en 提示语：已并 main 但有未提交改动 → 提醒文案为英文
# =========================================================
REPO16="$WORK/repo16"
make_repo "$REPO16"
git -C "$REPO16" worktree add -q -b feat-dirty-en "$REPO16/.worktrees/feat-dirty-en" >/dev/null 2>&1
git -C "$REPO16" merge -q feat-dirty-en 2>/dev/null || true
: > "$REPO16/.worktrees/feat-dirty-en/untracked.txt"
backdate_worktree "$REPO16/.worktrees/feat-dirty-en"
OUT16="$(run_sweep "$REPO16" en)"
assert_dir_exists "$REPO16/.worktrees/feat-dirty-en" "⑯en:有未提交改动的 worktree 不应被删"
assert_contains "$OUT16" "uncommitted changes" "⑯en 提醒文案应为英文"
if printf '%s' "$OUT16" | jq -e '.systemMessage' >/dev/null 2>&1; then pass; else fail "⑯en 输出应为含 systemMessage 键的合法 JSON"; fi

# =========================================================
# 汇总
# =========================================================
echo "----------------------------------------"
echo "PASS: $PASS  FAIL: $FAIL"
if [ "$FAIL" -gt 0 ]; then
  printf '%s' "$FAIL_MSGS"
  exit 1
fi
echo "全部通过"
exit 0
