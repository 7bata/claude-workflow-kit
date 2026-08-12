#!/bin/sh
# smoke-test.sh — register.sh 的冒烟测试(POSIX sh,macOS/Linux 兼容)。
# 在 mktemp 出的临时目录内构造假环境,不触碰 /tmp/cc-socks/ 或真实注册表。
#
# 用例:
#   1) 正常注册:字段齐、JSON 可解析
#   2) 注册表目录不存在时自动创建且权限 0700
#   3) 陈旧条目(对应 socket 已删)被清扫
#   4) 定位不到自身 socket 时 exit 0、不写文件、零 stdout
#   5) 重复运行幂等
#   6) 未设 CC_SELF_PID 时祖先链正向走通
#   7) 未设 CC_SELF_PID 且祖先链耗尽仍未命中
#   8) 孤儿条目:socket 文件仍在、但对应 pid 已死 → 被清扫
#   9) CLAUDE_CONFIG_DIR 指向无 .claude.json 的目录时 account 为 "unknown",
#      即便 HOME 下有 .claude.json 也不回落
#  10) 停用标志 ~/.claude/.cc-session-registry-off 存在时 exit 0、不写文件、
#      零 stdout(全局 opt-out,删除标志恢复)

set -u

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REGISTER_SH="$SCRIPT_DIR/register.sh"

PASS=0
FAIL=0

pass() {
  PASS=$((PASS + 1))
  printf 'PASS: %s\n' "$1"
}

fail() {
  FAIL=$((FAIL + 1))
  printf 'FAIL: %s\n' "$1"
}

# 提取 JSON 字符串字段的值(测试用简易 grep/sed,不依赖 jq)
json_field() {
  file="$1"
  field="$2"
  sed -n "s/.*\"$field\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" "$file" | head -1
}

new_tmpdir() {
  mktemp -d "${TMPDIR:-/tmp}/send-to-smoke.XXXXXX"
}

# 用例 1/2/3/5 用 CC_SELF_PID 直接覆盖定位逻辑,聚焦 register.sh 自身行为(写入/清扫/幂等);
# 祖先链走查逻辑本身(register.sh 的 find_self_pid,未设 CC_SELF_PID 时的分支)单独由
# 用例 6(正向:走通祖先链找到自身 socket)与用例 7(负向:上溯 10 层耗尽仍未命中)覆盖,
# 不依赖人工验证。

# ---------------------------------------------------------------
# 用例 1:正常注册,字段齐且 JSON 可解析
# ---------------------------------------------------------------
test_normal_registration() {
  name="1-normal-registration"
  T=$(new_tmpdir)
  SOCKS_DIR="$T/cc-socks"
  REGISTRY_DIR="$T/cc-session-registry"
  HOME_DIR="$T/home"
  mkdir -p "$SOCKS_DIR" "$HOME_DIR"
  FAKE_PID=12345
  # register.sh 用 -S 判断 socket,普通文件不满足;用 python3 造真 UDS 更贴近现实。
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "
import socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.bind(sys.argv[1])
" "$SOCKS_DIR/$FAKE_PID.sock"
  else
    fail "$name (无 python3,无法造 UDS 测试环境)"
    return
  fi

  cat > "$HOME_DIR/.claude.json" <<'EOF'
{"emailAddress": "smoke@example.com", "other": "field"}
EOF

  # 假 ps:让 cmd 字段原样带上裸 TAB(\t)与其它控制字符(\001、\037),
  # 逼出 json_escape 对 JSON 禁止字符的处理路径(参见 register.sh 注释)。
  FAKEBIN="$T/fakebin"
  mkdir -p "$FAKEBIN"
  cat > "$FAKEBIN/ps" <<'PSEOF'
#!/bin/sh
printf 'python3 -c import time x\ty\001z\037w\n'
PSEOF
  chmod +x "$FAKEBIN/ps"

  STDOUT=$(printf '{"session_id":"sess-123","cwd":"%s/myproj","hook_event_name":"SessionStart","source":"startup"}' "$T" | \
    CC_SOCKS_DIR="$SOCKS_DIR" CC_SESSION_REGISTRY_DIR="$REGISTRY_DIR" CC_SELF_PID="$FAKE_PID" HOME="$HOME_DIR" \
    PATH="$FAKEBIN:$PATH" \
    sh "$REGISTER_SH" 2>"$T/stderr.log")
  RC=$?

  OK=1
  [ "$RC" -eq 0 ] || { OK=0; fail "$name (exit code = $RC, expected 0)"; }
  [ -z "$STDOUT" ] || { OK=0; fail "$name (stdout 非空: $STDOUT)"; }

  ENTRY="$REGISTRY_DIR/$FAKE_PID.json"
  if [ ! -f "$ENTRY" ]; then
    OK=0
    fail "$name (未生成注册文件 $ENTRY)"
  else
    # JSON 可解析的最低检验:每个字段都能被简易正则提取到非空值,且大括号配对
    if ! python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$ENTRY" >/dev/null 2>&1; then
      OK=0
      fail "$name (注册文件不是合法 JSON)"
    fi
    # cmd 字段来自假 ps 的裸控制字符:JSON 仍须合法,tab 保留(转义形式)、
    # 其余控制字符(\001、\037)被剔除。
    if ! python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
cmd = d['cmd']
assert '\t' in cmd, 'tab not preserved in cmd: %r' % cmd
assert '\x01' not in cmd and '\x1f' not in cmd, 'control chars not stripped from cmd: %r' % cmd
" "$ENTRY" 2>"$T/cmd-check.err"; then
      OK=0
      fail "$name (cmd 字段控制字符处理不合规: $(cat "$T/cmd-check.err"))"
    fi
    pid_v=$(sed -n 's/.*"pid"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$ENTRY" | head -1)
    account_v=$(json_field "$ENTRY" account)
    cwd_v=$(json_field "$ENTRY" cwd)
    project_v=$(json_field "$ENTRY" project)
    session_v=$(json_field "$ENTRY" session_id)
    source_v=$(json_field "$ENTRY" source)
    registered_v=$(json_field "$ENTRY" registered_at)
    socket_v=$(json_field "$ENTRY" socket)
    cmd_v=$(json_field "$ENTRY" cmd)

    [ -n "$cmd_v" ] || { OK=0; fail "$name (cmd 字段为空)"; }
    [ "$account_v" = "smoke@example.com" ] || { OK=0; fail "$name (account 字段 = '$account_v',期望 smoke@example.com)"; }
    [ "$cwd_v" = "$T/myproj" ] || { OK=0; fail "$name (cwd 字段 = '$cwd_v')"; }
    [ "$project_v" = "myproj" ] || { OK=0; fail "$name (project 字段 = '$project_v')"; }
    [ "$session_v" = "sess-123" ] || { OK=0; fail "$name (session_id 字段 = '$session_v')"; }
    [ "$source_v" = "startup" ] || { OK=0; fail "$name (source 字段 = '$source_v')"; }
    [ -n "$registered_v" ] || { OK=0; fail "$name (registered_at 为空)"; }
    [ "$socket_v" = "$SOCKS_DIR/$FAKE_PID.sock" ] || { OK=0; fail "$name (socket 字段 = '$socket_v')"; }
    printf '%s' "$pid_v" | grep -q "$FAKE_PID" || { OK=0; fail "$name (pid 字段 = '$pid_v')"; }
  fi

  [ "$OK" -eq 1 ] && pass "$name"
  rm -rf "$T"
}

# ---------------------------------------------------------------
# 用例 2:注册表目录不存在时自动创建且 0700
# ---------------------------------------------------------------
test_registry_dir_autocreate() {
  name="2-registry-dir-autocreate-0700"
  T=$(new_tmpdir)
  SOCKS_DIR="$T/cc-socks"
  REGISTRY_DIR="$T/nested/does/not/exist/cc-session-registry"
  HOME_DIR="$T/home"
  mkdir -p "$SOCKS_DIR" "$HOME_DIR"
  FAKE_PID=23456
  if ! command -v python3 >/dev/null 2>&1; then
    fail "$name (无 python3)"
    rm -rf "$T"
    return
  fi
  python3 -c "
import socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.bind(sys.argv[1])
" "$SOCKS_DIR/$FAKE_PID.sock"

  [ ! -d "$REGISTRY_DIR" ] || { fail "$name (前置条件失败:目录已存在)"; rm -rf "$T"; return; }

  printf '{}' | CC_SOCKS_DIR="$SOCKS_DIR" CC_SESSION_REGISTRY_DIR="$REGISTRY_DIR" CC_SELF_PID="$FAKE_PID" HOME="$HOME_DIR" \
    sh "$REGISTER_SH" >"$T/stdout.log" 2>"$T/stderr.log"

  OK=1
  [ -d "$REGISTRY_DIR" ] || { OK=0; fail "$name (目录未被创建)"; }
  if [ -d "$REGISTRY_DIR" ]; then
    PERM=$(stat -f '%Lp' "$REGISTRY_DIR" 2>/dev/null || stat -c '%a' "$REGISTRY_DIR" 2>/dev/null)
    [ "$PERM" = "700" ] || { OK=0; fail "$name (权限 = $PERM,期望 700)"; }
  fi
  [ -f "$REGISTRY_DIR/$FAKE_PID.json" ] || { OK=0; fail "$name (未生成注册文件)"; }
  [ -s "$T/stdout.log" ] && { OK=0; fail "$name (stdout 非空)"; }

  [ "$OK" -eq 1 ] && pass "$name"
  rm -rf "$T"
}

# ---------------------------------------------------------------
# 用例 3:陈旧条目(socket 已删)被清扫
# ---------------------------------------------------------------
test_stale_entry_cleanup() {
  name="3-stale-entry-cleanup"
  T=$(new_tmpdir)
  SOCKS_DIR="$T/cc-socks"
  REGISTRY_DIR="$T/cc-session-registry"
  HOME_DIR="$T/home"
  mkdir -p "$SOCKS_DIR" "$REGISTRY_DIR" "$HOME_DIR"
  chmod 700 "$REGISTRY_DIR"
  FAKE_PID=34567
  STALE_PID=99999
  if ! command -v python3 >/dev/null 2>&1; then
    fail "$name (无 python3)"
    rm -rf "$T"
    return
  fi
  python3 -c "
import socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.bind(sys.argv[1])
" "$SOCKS_DIR/$FAKE_PID.sock"

  # 陈旧条目:注册文件存在,但对应 socket 不存在
  cat > "$REGISTRY_DIR/$STALE_PID.json" <<EOF
{"pid": $STALE_PID, "socket": "$SOCKS_DIR/$STALE_PID.sock", "account": "unknown", "profile": "default", "cwd": "unknown", "project": "unknown", "session_id": "unknown", "source": "unknown", "registered_at": "2020-01-01T00:00:00Z"}
EOF

  printf '{}' | CC_SOCKS_DIR="$SOCKS_DIR" CC_SESSION_REGISTRY_DIR="$REGISTRY_DIR" CC_SELF_PID="$FAKE_PID" HOME="$HOME_DIR" \
    sh "$REGISTER_SH" >"$T/stdout.log" 2>"$T/stderr.log"

  OK=1
  [ -f "$REGISTRY_DIR/$STALE_PID.json" ] && { OK=0; fail "$name (陈旧条目未被清扫)"; }
  [ -f "$REGISTRY_DIR/$FAKE_PID.json" ] || { OK=0; fail "$name (本会话条目未写入)"; }
  [ -s "$T/stdout.log" ] && { OK=0; fail "$name (stdout 非空)"; }

  [ "$OK" -eq 1 ] && pass "$name"
  rm -rf "$T"
}

# ---------------------------------------------------------------
# 用例 4:找不到自身 socket 时 exit 0、不写文件、零 stdout
# ---------------------------------------------------------------
test_no_self_socket() {
  name="4-no-self-socket-exit0-nowrite-nostdout"
  T=$(new_tmpdir)
  SOCKS_DIR="$T/cc-socks"
  REGISTRY_DIR="$T/cc-session-registry"
  HOME_DIR="$T/home"
  mkdir -p "$SOCKS_DIR" "$HOME_DIR"
  NONEXISTENT_PID=88888
  # 故意不创建对应 socket 文件

  STDOUT=$(printf '{}' | CC_SOCKS_DIR="$SOCKS_DIR" CC_SESSION_REGISTRY_DIR="$REGISTRY_DIR" CC_SELF_PID="$NONEXISTENT_PID" HOME="$HOME_DIR" \
    sh "$REGISTER_SH" 2>"$T/stderr.log")
  RC=$?

  OK=1
  [ "$RC" -eq 0 ] || { OK=0; fail "$name (exit code = $RC, expected 0)"; }
  [ -z "$STDOUT" ] || { OK=0; fail "$name (stdout 非空: $STDOUT)"; }
  [ -e "$REGISTRY_DIR" ] && { OK=0; fail "$name (注册表目录被创建,预期未创建/未写文件)"; }

  [ "$OK" -eq 1 ] && pass "$name"
  rm -rf "$T"
}

# ---------------------------------------------------------------
# 用例 5:重复运行幂等
# ---------------------------------------------------------------
test_idempotent_rerun() {
  name="5-idempotent-rerun"
  T=$(new_tmpdir)
  SOCKS_DIR="$T/cc-socks"
  REGISTRY_DIR="$T/cc-session-registry"
  HOME_DIR="$T/home"
  mkdir -p "$SOCKS_DIR" "$HOME_DIR"
  FAKE_PID=45678
  if ! command -v python3 >/dev/null 2>&1; then
    fail "$name (无 python3)"
    rm -rf "$T"
    return
  fi
  python3 -c "
import socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.bind(sys.argv[1])
" "$SOCKS_DIR/$FAKE_PID.sock"
  cat > "$HOME_DIR/.claude.json" <<'EOF'
{"emailAddress": "rerun@example.com"}
EOF

  for i in 1 2 3; do
    printf '{"session_id":"sess-%s","cwd":"%s/proj","source":"startup"}' "$i" "$T" | \
      CC_SOCKS_DIR="$SOCKS_DIR" CC_SESSION_REGISTRY_DIR="$REGISTRY_DIR" CC_SELF_PID="$FAKE_PID" HOME="$HOME_DIR" \
      sh "$REGISTER_SH" >"$T/stdout-$i.log" 2>"$T/stderr-$i.log"
  done

  OK=1
  COUNT=$(find "$REGISTRY_DIR" -maxdepth 1 -name '*.json' | wc -l | tr -d ' ')
  [ "$COUNT" = "1" ] || { OK=0; fail "$name (注册表文件数 = $COUNT,期望 1)"; }
  ENTRY="$REGISTRY_DIR/$FAKE_PID.json"
  session_v=$(json_field "$ENTRY" session_id)
  [ "$session_v" = "sess-3" ] || { OK=0; fail "$name (末次写入未生效,session_id = '$session_v')"; }
  for i in 1 2 3; do
    [ -s "$T/stdout-$i.log" ] && { OK=0; fail "$name (第 $i 次运行 stdout 非空)"; }
  done

  [ "$OK" -eq 1 ] && pass "$name"
  rm -rf "$T"
}

# ---------------------------------------------------------------
# 用例 6:未设 CC_SELF_PID 时,祖先链定位逻辑正向走通
#   (spec 3.4 步骤 1:从 register.sh 自身进程沿 ppid 上溯,找到第一个
#   自身 socket 存在的祖先)。构造:当前测试 shell 的 pid 建一个假 socket,
#   直接(不经命令替换 $(...) 额外分叉一层)以简单命令形式调用
#   `sh register.sh`,使其父进程恰是本测试 shell —— 上溯 1 层即命中。
# ---------------------------------------------------------------
test_ancestor_chain_walk_hits_self_socket() {
  name="6-ancestor-chain-walk-hits-self-socket"
  T=$(new_tmpdir)
  SOCKS_DIR="$T/cc-socks"
  REGISTRY_DIR="$T/cc-session-registry"
  HOME_DIR="$T/home"
  mkdir -p "$SOCKS_DIR" "$HOME_DIR"
  SELF_TEST_PID=$$
  if ! command -v python3 >/dev/null 2>&1; then
    fail "$name (无 python3)"
    rm -rf "$T"
    return
  fi
  python3 -c "
import socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.bind(sys.argv[1])
" "$SOCKS_DIR/$SELF_TEST_PID.sock"

  # 不设 CC_SELF_PID,不用 $(...) 包裹(command substitution 会多分叉一层子 shell,
  # 打乱祖先链层数),直接把 stdout/stderr 重定向到文件。
  printf '{}' | CC_SOCKS_DIR="$SOCKS_DIR" CC_SESSION_REGISTRY_DIR="$REGISTRY_DIR" HOME="$HOME_DIR" \
    sh "$REGISTER_SH" >"$T/stdout.log" 2>"$T/stderr.log"
  RC=$?

  OK=1
  [ "$RC" -eq 0 ] || { OK=0; fail "$name (exit code = $RC, expected 0)"; }
  [ -s "$T/stdout.log" ] && { OK=0; fail "$name (stdout 非空)"; }
  ENTRY="$REGISTRY_DIR/$SELF_TEST_PID.json"
  if [ ! -f "$ENTRY" ]; then
    OK=0
    fail "$name (祖先链未定位到 pid=$SELF_TEST_PID 的注册文件;check $REGISTRY_DIR)"
  else
    pid_v=$(sed -n 's/.*"pid"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$ENTRY" | head -1)
    [ "$pid_v" = "$SELF_TEST_PID" ] || { OK=0; fail "$name (pid 字段 = '$pid_v',期望 $SELF_TEST_PID)"; }
  fi

  [ "$OK" -eq 1 ] && pass "$name"
  rm -rf "$T"
}

# ---------------------------------------------------------------
# 用例 7:未设 CC_SELF_PID 且假 socks 目录为空 —— 祖先链上任何 pid 都不会
#   命中,上溯 10 层硬上限耗尽后放弃(spec 3.4 步骤 1「上限防死循环」的负向覆盖)。
# ---------------------------------------------------------------
test_ancestor_chain_walk_exhausted() {
  name="7-ancestor-chain-walk-exhausted-exit0-nowrite-nostdout"
  T=$(new_tmpdir)
  SOCKS_DIR="$T/cc-socks"
  REGISTRY_DIR="$T/cc-session-registry"
  HOME_DIR="$T/home"
  mkdir -p "$SOCKS_DIR" "$HOME_DIR"
  # 故意留空:祖先链上无论走到哪个真实 pid,都不会有对应的假 socket 文件。

  printf '{}' | CC_SOCKS_DIR="$SOCKS_DIR" CC_SESSION_REGISTRY_DIR="$REGISTRY_DIR" HOME="$HOME_DIR" \
    sh "$REGISTER_SH" >"$T/stdout.log" 2>"$T/stderr.log"
  RC=$?

  OK=1
  [ "$RC" -eq 0 ] || { OK=0; fail "$name (exit code = $RC, expected 0)"; }
  [ -s "$T/stdout.log" ] && { OK=0; fail "$name (stdout 非空)"; }
  [ -e "$REGISTRY_DIR" ] && { OK=0; fail "$name (注册表目录被创建,预期未创建/未写文件)"; }

  [ "$OK" -eq 1 ] && pass "$name"
  rm -rf "$T"
}

# ---------------------------------------------------------------
# 用例 8:孤儿条目——注册表条目存在、对应 socket 文件仍在,但 pid 已死
#   (spec 3.3「有效性」双判据的负向覆盖:单看 socket 存在不够,
#   claude 退出后 socket 会残留,必须再核对 pid 是否存活)。
#   构造死亡但曾真实存在过的 pid:fork 一个子进程,kill 后 wait 回收,
#   避免僵尸进程状态下 kill -0 判断模糊。
# ---------------------------------------------------------------
test_orphan_entry_dead_pid_cleanup() {
  name="8-orphan-entry-dead-pid-cleanup"
  T=$(new_tmpdir)
  SOCKS_DIR="$T/cc-socks"
  REGISTRY_DIR="$T/cc-session-registry"
  HOME_DIR="$T/home"
  mkdir -p "$SOCKS_DIR" "$REGISTRY_DIR" "$HOME_DIR"
  chmod 700 "$REGISTRY_DIR"
  FAKE_PID=56789
  if ! command -v python3 >/dev/null 2>&1; then
    fail "$name (无 python3)"
    rm -rf "$T"
    return
  fi
  python3 -c "
import socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.bind(sys.argv[1])
" "$SOCKS_DIR/$FAKE_PID.sock"

  ( sleep 100 ) &
  DEAD_PID=$!
  kill "$DEAD_PID" 2>/dev/null
  wait "$DEAD_PID" 2>/dev/null

  # 孤儿条目:socket 文件仍在,但 pid 已死
  python3 -c "
import socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.bind(sys.argv[1])
" "$SOCKS_DIR/$DEAD_PID.sock"
  cat > "$REGISTRY_DIR/$DEAD_PID.json" <<EOF
{"pid": $DEAD_PID, "socket": "$SOCKS_DIR/$DEAD_PID.sock", "account": "unknown", "profile": "default", "cwd": "unknown", "project": "unknown", "session_id": "unknown", "source": "unknown", "cmd": "unknown", "registered_at": "2020-01-01T00:00:00Z"}
EOF

  printf '{}' | CC_SOCKS_DIR="$SOCKS_DIR" CC_SESSION_REGISTRY_DIR="$REGISTRY_DIR" CC_SELF_PID="$FAKE_PID" HOME="$HOME_DIR" \
    sh "$REGISTER_SH" >"$T/stdout.log" 2>"$T/stderr.log"

  OK=1
  [ -f "$REGISTRY_DIR/$DEAD_PID.json" ] && { OK=0; fail "$name (孤儿条目未被清扫:socket 文件在但 pid 已死)"; }
  [ -f "$REGISTRY_DIR/$FAKE_PID.json" ] || { OK=0; fail "$name (本会话条目未写入)"; }
  [ -s "$T/stdout.log" ] && { OK=0; fail "$name (stdout 非空)"; }

  [ "$OK" -eq 1 ] && pass "$name"
  rm -rf "$T"
}

# ---------------------------------------------------------------
# 用例 9:CLAUDE_CONFIG_DIR 指向无 .claude.json 的目录时 account 为
#   "unknown",即便 HOME 下有 .claude.json 也不回落
#   (spec 3.4 步骤 3:防 labs/long profile 会话被错标成 default 账号)。
# ---------------------------------------------------------------
test_config_dir_no_fallback_to_home() {
  name="9-config-dir-set-no-claude-json-no-home-fallback"
  T=$(new_tmpdir)
  SOCKS_DIR="$T/cc-socks"
  REGISTRY_DIR="$T/cc-session-registry"
  HOME_DIR="$T/home"
  CONFIG_DIR="$T/empty profile"
  mkdir -p "$SOCKS_DIR" "$HOME_DIR" "$CONFIG_DIR"
  FAKE_PID=67890
  if ! command -v python3 >/dev/null 2>&1; then
    fail "$name (无 python3)"
    rm -rf "$T"
    return
  fi
  python3 -c "
import socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.bind(sys.argv[1])
" "$SOCKS_DIR/$FAKE_PID.sock"

  # HOME 下有 .claude.json(验证不会被错误回落读取)
  cat > "$HOME_DIR/.claude.json" <<'EOF'
{"emailAddress": "home-account@example.com"}
EOF
  # CONFIG_DIR(模拟 CLAUDE_CONFIG_DIR,目录名含空格测耐空格路径处理)下没有 .claude.json

  printf '{}' | CC_SOCKS_DIR="$SOCKS_DIR" CC_SESSION_REGISTRY_DIR="$REGISTRY_DIR" CC_SELF_PID="$FAKE_PID" \
    HOME="$HOME_DIR" CLAUDE_CONFIG_DIR="$CONFIG_DIR" \
    sh "$REGISTER_SH" >"$T/stdout.log" 2>"$T/stderr.log"

  OK=1
  ENTRY="$REGISTRY_DIR/$FAKE_PID.json"
  if [ ! -f "$ENTRY" ]; then
    OK=0
    fail "$name (未生成注册文件)"
  else
    account_v=$(json_field "$ENTRY" account)
    [ "$account_v" = "unknown" ] || { OK=0; fail "$name (account = '$account_v',期望 unknown,即不得回落 HOME)"; }
    profile_v=$(json_field "$ENTRY" profile)
    [ "$profile_v" = "empty profile" ] || { OK=0; fail "$name (profile = '$profile_v',期望 'empty profile')"; }
  fi
  [ -s "$T/stdout.log" ] && { OK=0; fail "$name (stdout 非空)"; }

  [ "$OK" -eq 1 ] && pass "$name"
  rm -rf "$T"
}

test_off_flag_disables_registration() {
  name="10-off-flag-disables-registration"
  T=$(new_tmpdir)
  SOCKS_DIR="$T/cc-socks"
  REGISTRY_DIR="$T/cc-session-registry"
  HOME_DIR="$T/home"
  mkdir -p "$SOCKS_DIR" "$HOME_DIR/.claude"
  FAKE_PID=76543
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "
import socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.bind(sys.argv[1])
" "$SOCKS_DIR/$FAKE_PID.sock"
  else
    fail "$name (无 python3,无法造 UDS 测试环境)"
    return
  fi
  # 停用标志存在:即便 socket/pid 一切就绪也不得注册、不得清扫、零输出
  : > "$HOME_DIR/.claude/.cc-session-registry-off"

  STDOUT=$(printf '{"session_id":"sess-off","source":"startup"}' | \
    CC_SOCKS_DIR="$SOCKS_DIR" CC_SESSION_REGISTRY_DIR="$REGISTRY_DIR" CC_SELF_PID="$FAKE_PID" HOME="$HOME_DIR" \
    sh "$REGISTER_SH" 2>"$T/stderr.log")
  RC=$?

  OK=1
  [ "$RC" -eq 0 ] || { OK=0; fail "$name (exit code = $RC, expected 0)"; }
  [ -z "$STDOUT" ] || { OK=0; fail "$name (stdout 非空: $STDOUT)"; }
  [ -e "$REGISTRY_DIR" ] && { OK=0; fail "$name (停用标志在,注册表目录仍被创建)"; }

  [ "$OK" -eq 1 ] && pass "$name"
  rm -rf "$T"
}

test_normal_registration
test_registry_dir_autocreate
test_stale_entry_cleanup
test_no_self_socket
test_idempotent_rerun
test_ancestor_chain_walk_hits_self_socket
test_ancestor_chain_walk_exhausted
test_orphan_entry_dead_pid_cleanup
test_config_dir_no_fallback_to_home
test_off_flag_disables_registration

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
