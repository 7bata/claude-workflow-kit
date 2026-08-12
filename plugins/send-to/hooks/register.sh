#!/bin/sh
# register.sh — SessionStart hook:自愿把本会话身份注册到跨 profile 共享注册表
# /tmp/cc-session-registry/,供 send-to skill 的 L2 阶梯(见 SKILL.md)读取认人。
#
# 硬性纪律:
#   - POSIX sh,macOS/Linux 双兼容,不用 bash 数组等非 POSIX 特性。
#   - stdout 绝对零输出(SessionStart hook 的 stdout 会被注入会话上下文)。
#   - 任何失败一律静默 exit 0,绝不影响会话启动。
#   - mktemp 于注册表同目录 + mv 原子写,天然幂等(重复运行覆盖刷新)。
#
# 可测性:三个环境变量可覆盖,供 smoke-test.sh 注入假环境。
#   CC_SOCKS_DIR             默认 /tmp/cc-socks
#   CC_SESSION_REGISTRY_DIR  默认 /tmp/cc-session-registry
#   CC_SELF_PID              默认走祖先链自动定位

SOCKS_DIR="${CC_SOCKS_DIR:-/tmp/cc-socks}"
REGISTRY_DIR="${CC_SESSION_REGISTRY_DIR:-/tmp/cc-session-registry}"

# 停用开关(全局 opt-out):touch ~/.claude/.cc-session-registry-off 即停用
# 注册与清扫,删除该文件恢复。与 speak-human/auto-scaffold 的标志文件同款套路。
[ -f "${HOME:-}/.claude/.cc-session-registry-off" ] && exit 0

# ---------------------------------------------------------------
# 1. 定位自身 pid:沿祖先链上溯,找第一个自身 socket 存在的祖先。
#    上限 10 层防死循环。CC_SELF_PID 可直接覆盖(smoke 测试用)。
# ---------------------------------------------------------------
find_self_pid() {
  if [ -n "${CC_SELF_PID:-}" ]; then
    if [ -S "$SOCKS_DIR/$CC_SELF_PID.sock" ]; then
      printf '%s' "$CC_SELF_PID"
      return 0
    fi
    return 1
  fi

  pid=$$
  i=0
  while [ "$i" -lt 10 ]; do
    if [ -S "$SOCKS_DIR/$pid.sock" ]; then
      printf '%s' "$pid"
      return 0
    fi
    ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
    [ -z "$ppid" ] && return 1
    [ "$ppid" = "$pid" ] && return 1
    pid="$ppid"
    i=$((i + 1))
  done
  return 1
}

SELF_PID=$(find_self_pid 2>/dev/null)
[ -z "$SELF_PID" ] && exit 0

# ---------------------------------------------------------------
# 2. 读 stdin JSON(best-effort)。任何字段缺失/解析失败一律回落。
# ---------------------------------------------------------------
STDIN_JSON=$(cat 2>/dev/null)

json_field() {
  field="$1"
  printf '%s' "$STDIN_JSON" | sed -n "s/.*\"$field\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" 2>/dev/null | head -1
}

SESSION_ID=$(json_field session_id)
[ -z "$SESSION_ID" ] && SESSION_ID="unknown"

SOURCE=$(json_field source)
[ -z "$SOURCE" ] && SOURCE="unknown"

CWD=$(json_field cwd)
[ -z "$CWD" ] && CWD="${PWD:-unknown}"

# ---------------------------------------------------------------
# 3. 取账号:CLAUDE_CONFIG_DIR 已设置时只认 $CLAUDE_CONFIG_DIR/.claude.json,
#    取不到就是 "unknown"——绝不回落 $HOME/.claude.json,否则会把
#    labs/long 等非默认 profile 的会话错标成 default 账号,错标 + 免回声
#    直发(见 SKILL.md「回声双档」)= 投错窗口不自知,危害大于 unknown。
#    未设置 CLAUDE_CONFIG_DIR 时才读 $HOME/.claude.json。
#    单一候选路径,不用 for 循环,天然规避路径含空格时的无引号展开问题。
#    profile 取 CLAUDE_CONFIG_DIR 的 basename,未设置为 "default"。
# ---------------------------------------------------------------
get_account() {
  if [ -n "${CLAUDE_CONFIG_DIR:-}" ]; then
    account_file="$CLAUDE_CONFIG_DIR/.claude.json"
  else
    account_file="${HOME:-}/.claude.json"
  fi

  if [ -n "$account_file" ] && [ -f "$account_file" ]; then
    val=$(sed -n 's/.*"emailAddress"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$account_file" 2>/dev/null | head -1)
    if [ -n "$val" ]; then
      printf '%s' "$val"
      return 0
    fi
  fi
  printf 'unknown'
}

ACCOUNT=$(get_account)

if [ -n "${CLAUDE_CONFIG_DIR:-}" ]; then
  PROFILE=$(basename "$CLAUDE_CONFIG_DIR" 2>/dev/null)
  [ -z "$PROFILE" ] && PROFILE="default"
else
  PROFILE="default"
fi

PROJECT=$(basename "$CWD" 2>/dev/null)
[ -z "$PROJECT" ] && PROJECT="unknown"

REGISTERED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
[ -z "$REGISTERED_AT" ] && REGISTERED_AT="unknown"

# cmd:自身 Claude 主进程(SELF_PID)的启动命令行,供 SKILL.md 读取侧展示与
# 排序弱提示用(带 -p/--print 的多为 headless 一次性进程);旗标不作筛除依据。
# 对自身祖先取命令行属自我登记,不属侦察。
CMD=$(ps -o command= -p "$SELF_PID" 2>/dev/null | head -1)
[ -z "$CMD" ] && CMD="unknown"

SOCKET_PATH="$SOCKS_DIR/$SELF_PID.sock"

# ---------------------------------------------------------------
# 4. 原子写:mktemp 于注册表同目录 -> 写 JSON -> mv。
# ---------------------------------------------------------------
# 转义反斜杠、双引号,并处理 JSON 禁止的裸控制字符(U+0000-U+001F):
# tab 转成字面 \t,其余控制字符(含裸换行/回车)一律删除,保证输出恒为合法 JSON。
# cmd 字段取自 `ps -o command=`,原样保留 argv 里的裸 TAB,若不做此处理会写出
# 无法被 json.load/jq 解析的注册文件。
json_escape() {
  v=$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g' 2>/dev/null)
  v=$(printf '%s' "$v" | awk '{gsub(/\t/, "\\t"); print}' 2>/dev/null)
  printf '%s' "$v" | tr -d '[:cntrl:]' 2>/dev/null
}

mkdir -p "$REGISTRY_DIR" 2>/dev/null || exit 0
chmod 700 "$REGISTRY_DIR" 2>/dev/null

TMP_FILE=$(mktemp "$REGISTRY_DIR/.tmp.XXXXXX" 2>/dev/null) || exit 0

{
  printf '{\n'
  printf '  "pid": %s,\n' "$SELF_PID"
  printf '  "socket": "%s",\n' "$(json_escape "$SOCKET_PATH")"
  printf '  "account": "%s",\n' "$(json_escape "$ACCOUNT")"
  printf '  "profile": "%s",\n' "$(json_escape "$PROFILE")"
  printf '  "cwd": "%s",\n' "$(json_escape "$CWD")"
  printf '  "project": "%s",\n' "$(json_escape "$PROJECT")"
  printf '  "session_id": "%s",\n' "$(json_escape "$SESSION_ID")"
  printf '  "source": "%s",\n' "$(json_escape "$SOURCE")"
  printf '  "cmd": "%s",\n' "$(json_escape "$CMD")"
  printf '  "registered_at": "%s"\n' "$(json_escape "$REGISTERED_AT")"
  printf '}\n'
} > "$TMP_FILE" 2>/dev/null

if [ -s "$TMP_FILE" ]; then
  mv "$TMP_FILE" "$REGISTRY_DIR/$SELF_PID.json" 2>/dev/null
else
  rm -f "$TMP_FILE" 2>/dev/null
fi

# ---------------------------------------------------------------
# 5. 顺手清扫:注册表内「对应 socket 已消失 或 pid 进程已死」的条目
#    一律删除(双判据),自身刚写入的条目除外(自身显然存活,跳过
#    kill -0 检查——CC_SELF_PID 供 smoke 测试注入的假 pid 不必是真实
#    存活进程,不应被自己的清扫逻辑连带删除)。单看 socket 存在不够
#    ——claude 退出后 socket 文件会残留(孤儿 socket),必须再用
#    kill -0 核实 pid 仍存活,否则会留下幻影条目,读取侧误以为可发
#    而实际投不出去。
# ---------------------------------------------------------------
for f in "$REGISTRY_DIR"/*.json; do
  [ -e "$f" ] || continue
  entry_pid=$(basename "$f" .json)
  [ "$entry_pid" = "$SELF_PID" ] && continue
  if [ ! -S "$SOCKS_DIR/$entry_pid.sock" ] || ! kill -0 "$entry_pid" 2>/dev/null; then
    rm -f "$f" 2>/dev/null
  fi
done

exit 0
