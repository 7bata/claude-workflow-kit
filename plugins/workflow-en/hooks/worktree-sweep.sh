#!/bin/sh
# worktree-sweep.sh — Stop / SessionEnd
# 清理已并入 main 且工作区干净、当前无会话在用的非主 worktree；
# 仅在满足以下判据全部为真时才删除：
#   1) 分支已被 main（或 master）合并（git merge-base --is-ancestor，
#      用全 ref 而非裸分支名，避免同名 tag 把未合并分支误判为已合并）
#   2) 工作区无未提交/未跟踪改动（git status --porcelain -uall 为空）
#   3) 被 .gitignore 忽略的文件里没有「不可再生」的那几类——黑名单判定，
#      命中任一即不删、走提醒：.env、.env.*、*.env、*.pem、*.key、*.p12、
#      *.pfx、*.jks、*.keystore、*.db、*.sqlite、*.sqlite3、*.secret、
#      id_rsa*、id_ed25519*、data/ 目录下任何文件、secrets/ 目录下任何
#      文件（任意深度，如 sub/.env、api/data/raw/x.csv）；其余忽略文件
#      （node_modules、dist、build、.DS_Store、*.log、缓存等）视为可再生，
#      不阻止删除。清单来自 git ls-files --others --ignored --exclude-standard
#      （逐个列出文件、不折叠目录），先剔除依赖/构建目录（node_modules、
#      .venv、vendor、site-packages 等，整体视为可再生），再用一条正则匹配
#      黑名单；该命令或 git status 失败（非零退出）、或被忽略目录里嵌套着
#      另一个 git 仓库（ls-files 只给一条折叠目录项）时，一律按「无法确认」
#      处理：不删，提醒。
#   4) 不是当前会话所在目录；30 分钟内没有别的会话在其中活动（会话记录
#      目录的 *.jsonl mtime）；也没有任何进程的 cwd 落在该 worktree 内
#      （有 lsof 才查，lsof 不存在时跳过这一项）
#   5) 30 分钟内既没新建也没在里面提交过（时间戳源是 worktree 自己 git
#      管理目录下的 index / COMMIT_EDITMSG，不是 worktree 内那个建立后就
#      不再变化的 .git 文件）——给 Workflow isolation:'worktree' 子代理
#      留出写第一个文件的窗口
# 误删上限：分支已并 main、无未提交改动的目录，git 内容可用
# git worktree add 重建；可再生的忽略文件（依赖、构建产物）随目录删掉；
# 黑名单那几类命中即不删。
# 绝不使用 --force、绝不 rm -rf、绝不动主工作树、绝不动当前 cwd、
# 绝不动未并 main 的分支。
#
# 用法：sh worktree-sweep.sh [en]   # 传 en 时提示语用英文
set -f

lang="${1:-zh}"

off_file="${WORKTREE_SWEEP_OFF_FILE:-${HOME}/.claude/.worktree-sweep-off}"
if [ -e "$off_file" ]; then
  exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

payload="$(cat)"

if ! printf '%s' "$payload" | jq -e '.' >/dev/null 2>&1; then
  exit 0
fi

cwd="$(printf '%s' "$payload" | jq -r '.cwd // empty' 2>/dev/null)"
[ -n "$cwd" ] || cwd="$(pwd)"

if ! git -C "$cwd" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

# 规范化 cwd（macOS 上 /var 是 /private/var 的符号链接，pwd -P 解析符号链接后
# 才能跟 git worktree list --porcelain 报告的路径做字面比较）
cwd_real="$(cd "$cwd" 2>/dev/null && pwd -P)"
[ -n "$cwd_real" ] || cwd_real="$cwd"

main_branch=""
if git -C "$cwd" show-ref --verify --quiet refs/heads/main; then
  main_branch="main"
elif git -C "$cwd" show-ref --verify --quiet refs/heads/master; then
  main_branch="master"
else
  exit 0
fi

# 先清失效登记（目录已被物理删除的 worktree 记录）；--expire 30 分钟：刚建
# 到一半的 worktree 登记不会被立刻清掉（判的是登记文件的年龄，管不到
# 卸载的外置卷：建了超过 30 分钟的登记在卷卸载后照样会被清，重挂后
# git worktree repair 可恢复）
git -C "$cwd" worktree prune --expire 30.minutes.ago >/dev/null 2>&1

porcelain="$(git -C "$cwd" worktree list --porcelain 2>/dev/null)"
[ -n "$porcelain" ] || exit 0

# 把 porcelain 输出转成 path<TAB>branch<TAB>flags 每行一条记录
records="$(printf '%s\n' "$porcelain" | awk '
  BEGIN { path=""; branch=""; flags="" }
  /^worktree / {
    if (path != "") { print path "\t" branch "\t" flags }
    path=substr($0,10); branch=""; flags=""
  }
  /^branch / { branch=substr($0,8) }
  /^detached$/ { flags=flags "detached," }
  /^locked/ { flags=flags "locked," }
  /^prunable/ { flags=flags "prunable," }
  /^bare$/ { flags=flags "bare," }
  END { if (path != "") print path "\t" branch "\t" flags }
')"

main_worktree=""
cleaned_msgs=""
reminder_msgs=""
first=1

old_ifs="$IFS"
IFS='
'
for rec in $records; do
  wt_path="$(printf '%s' "$rec" | awk -F'\t' '{print $1}')"
  wt_branchref="$(printf '%s' "$rec" | awk -F'\t' '{print $2}')"
  wt_flags="$(printf '%s' "$rec" | awk -F'\t' '{print $3}')"

  if [ "$first" -eq 1 ]; then
    # 第一条永远是主工作树，永不动
    main_worktree="$wt_path"
    first=0
    continue
  fi

  case "$wt_flags" in
    *detached*|*locked*|*prunable*|*bare*) continue ;;
  esac
  [ -n "$wt_branchref" ] || continue

  branch="${wt_branchref#refs/heads/}"
  [ -n "$branch" ] || continue
  [ "$branch" != "$main_branch" ] || continue

  case "$cwd_real" in
    "$wt_path"|"$wt_path"/*) continue ;;
  esac

  # 用全 ref（refs/heads/...）而非裸分支名做 merge-base：裸名在
  # refs/tags 与 refs/heads 同名时会被 git 解析成 tag（tag 排在
  # heads 前面），可能把未并入 main 的分支误判为已合并。
  if ! git -C "$cwd" merge-base --is-ancestor "$wt_branchref" "refs/heads/$main_branch" 2>/dev/null; then
    # 未并入 main，视为进行中，静默跳过
    continue
  fi

  # 太新不动：worktree 刚建好、或刚在其中提交过时不动。时间戳源用
  # worktree 自己的 git 管理目录（git worktree add 时新建，commit 时
  # index/COMMIT_EDITMSG 会更新 mtime），而不是 worktree 里那个从建立
  # 起就不再变化的 .git 文件本身——用 .git 文件只能测出「建了多久」，
  # 测不出「刚提交过」，会把仍在被子代理使用、只是这一刻工作区恰好
  # 干净的 worktree 当成太旧直接清掉。
  wt_git_dir="$(git -C "$wt_path" rev-parse --git-dir 2>/dev/null)"
  case "$wt_git_dir" in
    /*) ;;
    "") wt_git_dir="$wt_path/.git" ;;
    *) wt_git_dir="$wt_path/$wt_git_dir" ;;
  esac
  if find "$wt_git_dir" -maxdepth 1 \( -name index -o -name COMMIT_EDITMSG \) -mmin -30 2>/dev/null | grep -q .; then
    continue
  fi

  # --no-optional-locks：status 不回写 index，否则 hook 自己每跑一次都会把
  # 判据⑤的时间戳源（index mtime）顶到当下
  status_out="$(git -C "$wt_path" --no-optional-locks status --porcelain -uall 2>/dev/null)"
  status_rc=$?
  if [ "$status_rc" -ne 0 ]; then
    # git status 本身失败：无法确认工作区状态，宁可不删
    if [ "$lang" = "en" ]; then
      reminder_msgs="${reminder_msgs}worktree-sweep: could not verify the working tree of $wt_path (branch $branch, git status failed); not removed, please handle it
"
    else
      reminder_msgs="${reminder_msgs}worktree-sweep:${wt_path}（分支 ${branch}）无法确认工作区状态（git status 失败），未删，请处理
"
    fi
    continue
  fi
  if [ -n "$status_out" ]; then
    if [ "$lang" = "en" ]; then
      reminder_msgs="${reminder_msgs}worktree-sweep: branch <$branch> of $wt_path is merged into $main_branch but the working tree has uncommitted changes; not removed, please handle it
"
    else
      reminder_msgs="${reminder_msgs}worktree-sweep:$wt_path 的分支 $branch 已并 $main_branch 但工作区有未提交改动，未删，请处理
"
    fi
    continue
  fi

  # 被 .gitignore 忽略的文件删目录时会一并消失且 git 无法恢复；只有命中
  # 「不可再生」黑名单的那几类才拦（.env 系、证书/密钥、本地数据库、
  # id_rsa* 等私钥、data/ 与 secrets/ 目录下任意深度的文件），其余忽略
  # 文件（依赖、构建产物、.DS_Store、*.log 等）一律视为可再生，不拦删除。
  # git ls-files --others --ignored --exclude-standard 通常逐个列出忽略
  # 文件（不折叠目录，嵌套再深也逐条出现），core.quotePath=false 让非
  # ASCII 路径原样输出；含引号/控制字符的路径 git 仍会给整条路径加双引号
  # （即使路径本身以 data/、secrets/ 等黑名单前缀开头，行首也会先出现一个
  # 多余的引号），正则的行首与行尾锚点都容忍一个多余的引号，避免这类路径
  # 的黑名单前缀因为多出的引号而匹配不上。命令失败（老版本 git、仓库损坏）
  # → 按「无法确认」不删。
  ign_list="$(git -C "$wt_path" -c core.quotePath=false ls-files --others --ignored --exclude-standard 2>/dev/null)"
  ign_rc=$?
  if [ "$ign_rc" -ne 0 ]; then
    if [ "$lang" = "en" ]; then
      reminder_msgs="${reminder_msgs}worktree-sweep: could not list git-ignored files of $wt_path (branch $branch); not removed, please handle it
"
    else
      reminder_msgs="${reminder_msgs}worktree-sweep:${wt_path}（分支 ${branch}）无法确认被忽略的文件（git ls-files 失败），未删，请处理
"
    fi
    continue
  fi
  # 依赖/构建目录（node_modules、.venv、vendor、site-packages 等）整体视为
  # 可再生，里面的文件不参与黑名单判定——否则 css-tree/data/、certifi/cacert.pem
  # 这类依赖内部路径会让判据③在装过依赖的仓库上恒命中，hook 形同虚设。
  ign_scan="$(printf '%s\n' "$ign_list" | grep -vE '(^"?|/)(node_modules|\.venv|venv|vendor|site-packages|\.tox|target|\.next|\.nuxt|\.pnpm-store|\.yarn|\.cache)/')"
  # 被忽略目录内嵌套着另一个 git 仓库（vendored clone、嵌套 worktree 等）
  # 时，ls-files 在仓库边界处不会展开，只输出一条折叠的目录项（以 / 结尾，
  # 加引号时为 /"）；这类条目里可能藏着 .env / data 等不可再生文件却对
  # 黑名单正则完全不可见，按「无法确认」处理，不删。普通忽略文件的路径
  # 不会以 / 结尾，不会误命中这条判断。
  if printf '%s\n' "$ign_scan" | grep -qE '/"?$'; then
    if [ "$lang" = "en" ]; then
      reminder_msgs="${reminder_msgs}worktree-sweep: could not list git-ignored files of $wt_path (branch $branch) because an ignored directory contains an unexpanded nested git repo; not removed, please handle it
"
    else
      reminder_msgs="${reminder_msgs}worktree-sweep:${wt_path}（分支 ${branch}）存在未展开的嵌套仓库目录，无法确认被忽略的文件，未删，请处理
"
    fi
    continue
  fi
  ign_hit=""
  if [ -n "$ign_scan" ]; then
    ign_hit="$(printf '%s\n' "$ign_scan" | grep -E -m 1 '(^"?|/)(\.env(\..*)?|[^/]*\.(env|pem|key|p12|pfx|jks|keystore|db|sqlite|sqlite3|secret)|id_rsa[^/]*|id_ed25519[^/]*)"?$|(^"?|/)(data|secrets)/')"
  fi
  if [ -n "$ign_hit" ]; then
    if [ "$lang" = "en" ]; then
      reminder_msgs="${reminder_msgs}worktree-sweep: branch <$branch> of $wt_path is merged into $main_branch but the working tree has git-ignored files that would be lost and cannot be regenerated ($ign_hit); not removed, please handle it
"
    else
      reminder_msgs="${reminder_msgs}worktree-sweep:$wt_path 的分支 $branch 已并 $main_branch 但工作区含不可再生的被忽略文件（${ign_hit}），未删，请处理
"
    fi
    continue
  fi

  # 会话活动检测：path 里每个非 [A-Za-z0-9] 字符替换成 -。Claude Code 按
  # 字符替换（一个中文字符 → 一个 -），sed 的替换粒度随 locale 变（C 下按
  # 字节，一个中文字符 → 三个 -），所以两种 locale 各算一个候选 key，任一
  # 目录命中即视为活跃——多算一次活跃只会推迟清理，永远安全。
  key_c="$(printf '%s' "$wt_path" | LC_ALL=C sed 's/[^A-Za-z0-9]/-/g')"
  key_u="$(printf '%s' "$wt_path" | LC_ALL=en_US.UTF-8 sed 's/[^A-Za-z0-9]/-/g' 2>/dev/null)"
  [ -n "$key_u" ] || key_u="$key_c"

  default_roots="${HOME}/.claude/projects:${HOME}/.claude-profiles/*/projects"
  sessions_roots="${WORKTREE_SWEEP_SESSIONS_ROOTS:-$default_roots}"

  session_active=0
  old_ifs2="$IFS"
  IFS=':'
  for root_pattern in $sessions_roots; do
    IFS="$old_ifs2"
    set +f
    for root_dir in $root_pattern; do
      for key in "$key_c" "$key_u"; do
        [ -d "$root_dir/$key" ] || continue
        fresh="$(find "$root_dir/$key" -maxdepth 1 -name '*.jsonl' -mmin -30 2>/dev/null | head -n 1)"
        if [ -n "$fresh" ]; then
          session_active=1
        fi
      done
    done
    set -f
    IFS=':'
  done
  IFS="$old_ifs2"

  if [ "$session_active" -eq 1 ]; then
    continue
  fi

  # 进程占用检测：会话记录（sidechain）只落在发起子代理的父会话目录里，
  # 若子代理在该 worktree 里长时间只读探索/调研、不提交也不跑 git 命令，
  # 上面两道时间戳与会话检测都测不出「正在用」。这里再查一遍是否有任何
  # 进程的 cwd 落在该 worktree 内；lsof 不存在或调用失败时不阻断（保持
  # 原行为，不因缺 lsof 而新增误报）。
  if command -v lsof >/dev/null 2>&1; then
    # 不用 +D（那会递归遍历整棵目录树，node_modules 多的仓库会跑很久），
    # 而是列出所有进程的 cwd，再比对是否等于该 worktree 或落在其下。
    # 路径经 ENVIRON 传入（awk -v 会对反斜杠做转义解释），lsof 输出里的
    # 反斜杠自身转义成 \\，比对前先还原。
    WT_P="$wt_path"
    export WT_P
    if lsof -a -d cwd -F n 2>/dev/null | awk '
        BEGIN { p=ENVIRON["WT_P"] }
        substr($0,1,1)=="n" { q=substr($0,2); gsub(/\\\\/, "\\", q); if (q==p || index(q, p "/")==1) { found=1; exit } }
        END { exit !found }'; then
      continue
    fi
  fi

  if git -C "$main_worktree" worktree remove "$wt_path" >/dev/null 2>&1; then
    branch_deleted=1
    if ! git -C "$main_worktree" branch -d "$branch" >/dev/null 2>&1; then
      branch_deleted=0
    fi
    if [ "$lang" = "en" ]; then
      if [ "$branch_deleted" -eq 1 ]; then
        cleaned_msgs="${cleaned_msgs}worktree-sweep: cleaned up $wt_path (branch $branch merged into $main_branch, local branch deleted)
"
      else
        cleaned_msgs="${cleaned_msgs}worktree-sweep: cleaned up $wt_path (branch $branch merged into $main_branch, but local branch deletion failed, please handle it)
"
      fi
    else
      if [ "$branch_deleted" -eq 1 ]; then
        cleaned_msgs="${cleaned_msgs}worktree-sweep:已清理 $wt_path(分支 $branch 已并 ${main_branch}，本地分支已删)
"
      else
        cleaned_msgs="${cleaned_msgs}worktree-sweep:已清理 $wt_path(分支 $branch 已并 ${main_branch}，但本地分支删除失败，请处理)
"
      fi
    fi
    git -C "$main_worktree" worktree prune --expire 30.minutes.ago >/dev/null 2>&1
  else
    if [ "$lang" = "en" ]; then
      reminder_msgs="${reminder_msgs}worktree-sweep: failed to remove $wt_path (branch $branch merged into $main_branch); please handle it
"
    else
      reminder_msgs="${reminder_msgs}worktree-sweep:$wt_path(分支 $branch 已并 $main_branch)删除失败，请处理
"
    fi
  fi
done
IFS="$old_ifs"

# 提醒限频：同一仓库一小时内只提醒一次；清理成功的消息不限频
if [ -n "$reminder_msgs" ]; then
  state_dir="${WORKTREE_SWEEP_STATE_DIR:-${TMPDIR:-/tmp}}"
  cksum_val="$(printf '%s' "$main_worktree" | cksum | awk '{print $1}')"
  state_file="${state_dir}/worktree-sweep-${cksum_val}"
  now_epoch="$(date +%s 2>/dev/null || echo 0)"
  last_epoch=0
  if [ -f "$state_file" ]; then
    last_epoch="$(cat "$state_file" 2>/dev/null)"
    case "$last_epoch" in
      ''|*[!0-9]*) last_epoch=0 ;;
    esac
  fi
  elapsed=$((now_epoch - last_epoch))
  if [ "$last_epoch" -gt 0 ] && [ "$elapsed" -lt 3600 ]; then
    reminder_msgs=""
  else
    mkdir -p "$state_dir" 2>/dev/null
    printf '%s' "$now_epoch" > "$state_file" 2>/dev/null
  fi
fi

all_msgs="${cleaned_msgs}${reminder_msgs}"
if [ -n "$all_msgs" ]; then
  # 去掉末尾多余换行，拼成一个字符串，交给 jq -n --arg 生成合法 JSON
  msg_body="${all_msgs%
}"
  jq -n --arg m "$msg_body" '{systemMessage: $m}'
fi

exit 0
