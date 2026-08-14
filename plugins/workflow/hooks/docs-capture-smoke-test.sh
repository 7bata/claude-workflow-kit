#!/bin/sh
# docs-capture-smoke-test.sh — capture-decisions.sh / signal-reminder.sh / commit-gate.sh 冒烟测试
# 仿 send-to 10 例；在临时目录建 fixture git 仓跑，不污染本仓。

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

# ---- fixture 环境 ----
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
# ① capture-decisions.sh: inbox 追加格式正确
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
        "question": "数据库选哪个?",
        "header": "数据库",
        "multiSelect": false,
        "options": [
          {"label": "PostgreSQL (Recommended)", "description": "..."},
          {"label": "SQLite", "description": "..."}
        ]
      }
    ],
    "answers": {
      "数据库选哪个?": "PostgreSQL (Recommended)"
    }
  }
}'

printf '%s' "$PAYLOAD_1" | sh "$CAPTURE_SH"

OUT1="$(cat "$INBOX" 2>/dev/null)"
assert_contains "$OUT1" "## " "①inbox 有 ## 级标题"
assert_contains "$OUT1" "abcdef12" "①sid8 前8位"
assert_contains "$OUT1" "**Q**: 数据库选哪个?" "①Q 行"
assert_contains "$OUT1" "**候选**: PostgreSQL (Recommended) | SQLite" "①候选行"
assert_contains "$OUT1" "**选择**: PostgreSQL (Recommended)" "①选择行"

# =========================================================
# ② Other 文本被完整保留
# =========================================================
rm -f "$INBOX"

PAYLOAD_2='{
  "session_id": "22223333aaaa",
  "cwd": "'"$REPO"'",
  "tool_response": {
    "questions": [
      {
        "question": "还有什么补充?",
        "options": [
          {"label": "A"},
          {"label": "B"}
        ]
      }
    ],
    "answers": {
      "还有什么补充?": "都不是,我想用自定义方案:先做 MVP 再迭代"
    }
  }
}'
printf '%s' "$PAYLOAD_2" | sh "$CAPTURE_SH"
OUT2="$(cat "$INBOX" 2>/dev/null)"
assert_contains "$OUT2" "都不是,我想用自定义方案:先做 MVP 再迭代" "②Other 原文完整保留(选择行)"
assert_contains "$OUT2" "**备注**: 都不是,我想用自定义方案:先做 MVP 再迭代" "②Other 原文完整保留(备注行)"

# =========================================================
# ③ 非方法论目录零输出
# =========================================================
NO_DOCS_DIR="$WORK/no-docs-target"
mkdir -p "$NO_DOCS_DIR"
git -C "$NO_DOCS_DIR" init -q 2>/dev/null
PAYLOAD_3='{"session_id":"zzz","cwd":"'"$NO_DOCS_DIR"'","tool_response":{"questions":[{"question":"q","options":[]}],"answers":{"q":"a"}}}'
OUT3="$(printf '%s' "$PAYLOAD_3" | sh "$CAPTURE_SH")"
assert_empty "$OUT3" "③非方法论目录(无 docs/)capture 零 stdout 输出"
[ -f "$NO_DOCS_DIR/docs/DECISIONS.inbox.md" ] && fail "③非方法论目录不应生成 inbox" || pass

OUT3B="$(printf '%s' "$PAYLOAD_3" | sh "$REMINDER_SH")"
# reminder 走 prompt 字段，这里单独验证非 git 仓/无 docs 的 reminder 零输出见下 ⑤

# =========================================================
# ④ 解析失败走原始 JSON 兜底
# =========================================================
rm -f "$INBOX"
BAD_PAYLOAD='{"session_id":"bad1","cwd":"'"$REPO"'","tool_response":{"unexpected":"shape"}}'
printf '%s' "$BAD_PAYLOAD" | sh "$CAPTURE_SH"
OUT4="$(cat "$INBOX" 2>/dev/null)"
assert_contains "$OUT4" '```json' "④解析失败原始 JSON fenced block"
assert_contains "$OUT4" '"unexpected"' "④解析失败原始负载内容保留"

# 完全非法 JSON 也不能崩，且不写入（因为连 cwd 都拿不到时应静默 exit 0）
rm -f "$INBOX"
printf 'not even json{{{' | sh "$CAPTURE_SH"
if [ -f "$INBOX" ]; then
  fail "④非法 JSON 不应生成 inbox 内容"
else
  pass
fi

# =========================================================
# ⑤ 层2判例(2026-08-14 第三轮修订后重构为三套件,判例与词表实现分权:
#    本文件只定义「输入句子 → 期望是否命中/命中何类信号」的数据驱动断言,
#    不预设子句切分等实现方式——命中判定完全由 signal-reminder.sh 内部逻辑决定。)
#
# 套件 A — 正例(≥12 条,其中 ≥8 条为多子句真实消息:拍板/需求主句 +
#           附带疑问或闲聊子句),全部断言必须命中对应信号类别。
# 套件 B — 原陷阱集保留(含词表词根但非拍板/需求语境:疑问/否定/未定/
#           非技术日常四类),全部断言不得命中。
# 套件 C — 新增「不含任何压制词」陷阱子类(≥20 句):句中确有决策/需求
#           词根但作名词性续接、无宾语或收尾锚定,且句内不含任何压制/
#           语气词(吗、还没、不确定…)——旧实现靠压制词表兜底,这批句子
#           暴露裸模式误报;全部断言不得命中,误触发一票即整体失败。
# =========================================================
rm -f "$INBOX"

DECISION_SENTENCES='这个就这么定,用 PostgreSQL 吧
拍板了,用这个方案
好,拍板了,用 React
定了就这么办
选定方案作为最终版本
一锤定音,用 Go 后端
拍这版设计吧
就按这个走
最终选定 SQLite
拍死这个方案,不用讨论了
方案B就这么定了
定这个吧,别改了'

REQUIREMENT_SENTENCES='希望能支持深色模式
要能离线运行就好了
最好是加个搜索框
这个功能得做完
别忘了加日志
必须支持多语言
需要新增导出功能
补一个功能进去,批量删除
要求增加权限校验
得加上重试机制
一定要有回滚方案
审计日志这块得做好'

# ---------------------------------------------------------
# 套件 A — 多子句真实消息正例(拍板/需求主句 + 附带疑问/闲聊子句)
# spec §3 层2 第三轮修订:压制不跨句——附带疑问子句不得压制主句的命中。
# ---------------------------------------------------------
MULTICLAUSE_DECISION_SENTENCES='就这么定了,用 PostgreSQL。另外你能帮我看看这个报错吗?
拍板了,用这个方案。顺便问一下,今天的会议几点开始?
好,拍板了,用 React。你觉得这个图标好看吗?
就按这个走,先做后端。对了,午饭吃什么?
一锤定音,用 Go 后端;顺便帮我查一下这个依赖的版本号。
最终选定 SQLite。你那边环境配好了吗?
选定方案 A 了,别再改了。话说回来,今天天气怎么样?
定了就这么办,别再纠结了。顺便问下,这个 PR 你审了吗?'

MULTICLAUSE_REQUIREMENT_SENTENCES='希望能加个搜索框。对了,你觉得这个配色怎么样?
必须支持多语言,这个优先级最高。顺便问一句,现在几点了?
需要新增导出功能,尽快排期。你那边测试环境搭好了吗?
别忘了加日志,这个很重要。另外,今天的部署窗口是几点?'

# 日常句(不含词表任何词,验证词表不匹配无关文本)
DAILY_SENTENCES='这几个方案还在讨论中,还没定
我们可以考虑一下这个方案
今天天气不错,适合写代码
帮我看看这段代码有没有 bug
这个函数的性能怎么样
我们对比一下三个候选方案的优劣
先跑一下测试看看结果
这个 UI 看起来还行
数据库连接失败了,报错信息如下
我想了解一下这个库的用法'

# ---------------------------------------------------------
# 套件 B — 原陷阱集保留(含词表词根/子串,但不是拍板/需求语境——验证
# spec §5 非对称门禁:误触发一票即不达线。
# 构造原则:含词表词根但处于疑问句(...吗?/...行不行/哪个更好)、否定句
# (还没/不确定/没确定/拿不准)、未定语境(不一定/不急/下次讨论)或非技术日常
# 语境(加班/作业/穿衣服)——覆盖旧词表下曾 100% 误报的一批(1-15),
# 评审用全新日常句实测复现误报、原样纳入回归的一批(16-29,评审报告原句,
# 不作为本轮构造独立性的证据),以及本轮由实现方自行独立构造、
# 不复用任一轮评审样本的一批(30 号起,同样覆盖疑问/否定/未定/非技术四类语境,
# 逐句都含词表裸模式的字面子串,用于验证否决词表/结构收窄在"未给出的新句子"
# 上同样有效,而不是只对评审报告里出现过的原句有效;其中末 4 句是自测过程中
# 额外发现的真实误报,已连带修好收进回归)。
# ---------------------------------------------------------
TRAP_SENTENCES='这个参数就用默认值行不行?
你觉得方案A和方案B哪个更好?我还没想清楚
希望你能先解释一下这段代码
别忘了刚才那个报错还没解决
我得做个实验验证一下
这个库必须支持 windows 吗?我不确定
不能少了这一步吗
就用 git log 看一下
要能通过测试就已经很好了吧,不一定要能上线
最好是问一下负责人,我拿不准
需要新增吗?这个我们下次讨论
补一个想法,不一定要做
培训要求增加了很多内容
得加上一件衣服,外面冷
一定要有耐心,别着急
确定这个方案之前先看看数据
我还没确定这个用不用
不确定这个库靠不靠谱
就按这个报错去搜一下
就按这个文件的格式改
希望能先解释一下这段代码
希望能有个例子看看,不急
别忘了加班的事
作业得做完了才能玩
他们最好是加班
拍板了吗?还没吧
这个库必须支持windows吗?我不确定
必须支持吗?
需要新增字段吗
这周末要不要加班,还没定
他今天穿了件外套,最好是加个围巾
今天这事能拍板吗,我看还早
领导那边还没拍板,先别声张
我不确定是不是就这么定了
要不要定了就发布,大家没商量好
选定方案这事我拿不准,再想想
这几个候选哪个更好,还没到最终选定的地步
谁一锤定音这事都没确定呢
拍这版行不行还得再看看
拍死这个方案的事还没商量
这个是不是该定这个方案,我还没想好
这功能希望能做完吗,大家拿不准主意
这个必须支持吗,我还没想清楚要不要
需要新增这个字段的事还没定
是不是得加上重试机制,我不确定
一定要有回滚方案这事我拿不准
要求增加权限校验的事还没拍板
别忘了加字段吗,我们再核实一下
最好是加个选项,不确定要不要
补一个功能这事,哪个更好还没聊
就按这个走还是等等,大家还没商量好
定这个之前,我们先确定一下预算
需要新增么?我看未必,再讨论讨论
最终选定权在老板那边,我们说了不算
拍这版之前先出个草稿看看'

# ---------------------------------------------------------
# 套件 C — 「不含任何压制词」陷阱子类(≥20 句,上一轮 opus 评审逐句定位
# 的裸模式无宾语/收尾锚定误报;句内不含吗/还没/不确定/拿不准等任何压制
# 语气词——旧实现靠压制词表兜住,这批句子暴露裸模式本身的误报)。
# 前 12 句为评审报告原句,原样纳入回归,验证否决/收窄对已知误报仍生效;
# 后续句为在此基础上补充构造,覆盖 得做好/希望能自动/就按这个(办|定)/
# 拍死这个X/一锤定音/定这个/最终选定/必须支持 等词根的更多名词性续接场景,
# 验证收窄在"未给出的新句子"上同样有效。
# ---------------------------------------------------------
NO_SUPPRESSION_TRAP_SENTENCES='就按这个来复现
拍板这个词英文怎么说
拍死这个蚊子
必须支持球队
希望能加班费翻倍
选定方案的评审会
一锤定音这个成语
最终选定名单
需要新增依赖时请在PR里说明
得做完才轮到下一步
定了就别改了这句话我记下了
别忘了加测试用例的注释
就按这个办的办公室在三楼
就按这个定的价格表贴在墙上
就按这个走的意思是照套路来,是个成语
拍死这个蚊子用什么牌子的杀虫剂比较好
拍板这个动作在会议纪要里怎么写比较正式
一锤定音这个词组翻译成英文
选定方案这四个字做成一张海报
最终选定的字体名称叫宋体
必须支持这四个字用加粗字体
需要新增这个词组造个句子
审计日志这块得做好几个字的排版
希望能自动这个词后面接名词还是动词
定这个词的拼音怎么标'

decision_ok=1
IFS='
'
for s in $DECISION_SENTENCES; do
  payload="$(jq -n --arg cwd "$REPO" --arg p "$s" '{cwd:$cwd, prompt:$p}')"
  out="$(printf '%s' "$payload" | sh "$REMINDER_SH")"
  case "$out" in
    *决策*) : ;;
    *) decision_ok=0; fail "⑤决策句未命中: [$s] -> [$out]" ;;
  esac
done
[ "$decision_ok" = 1 ] && pass

requirement_ok=1
for s in $REQUIREMENT_SENTENCES; do
  payload="$(jq -n --arg cwd "$REPO" --arg p "$s" '{cwd:$cwd, prompt:$p}')"
  out="$(printf '%s' "$payload" | sh "$REMINDER_SH")"
  case "$out" in
    *需求*) : ;;
    *) requirement_ok=0; fail "⑤需求句未命中: [$s] -> [$out]" ;;
  esac
done
[ "$requirement_ok" = 1 ] && pass

daily_ok=1
for s in $DAILY_SENTENCES; do
  payload="$(jq -n --arg cwd "$REPO" --arg p "$s" '{cwd:$cwd, prompt:$p}')"
  out="$(printf '%s' "$payload" | sh "$REMINDER_SH")"
  if [ -n "$out" ]; then
    daily_ok=0
    fail "⑤日常句误触发(不得命中): [$s] -> [$out]"
  fi
done
[ "$daily_ok" = 1 ] && pass

trap_ok=1
for s in $TRAP_SENTENCES; do
  payload="$(jq -n --arg cwd "$REPO" --arg p "$s" '{cwd:$cwd, prompt:$p}')"
  out="$(printf '%s' "$payload" | sh "$REMINDER_SH")"
  if [ -n "$out" ]; then
    trap_ok=0
    fail "⑤【套件B】陷阱句误触发(含词表子串但非拍板/需求,不得命中): [$s] -> [$out]"
  fi
done
[ "$trap_ok" = 1 ] && pass

# ---- 套件 A:多子句真实消息正例(附带疑问/闲聊子句不得压制主句命中) ----
multiclause_decision_ok=1
for s in $MULTICLAUSE_DECISION_SENTENCES; do
  payload="$(jq -n --arg cwd "$REPO" --arg p "$s" '{cwd:$cwd, prompt:$p}')"
  out="$(printf '%s' "$payload" | sh "$REMINDER_SH")"
  case "$out" in
    *决策*) : ;;
    *) multiclause_decision_ok=0; fail "⑤【套件A】多子句决策消息未命中(附带疑问子句不应压制主句): [$s] -> [$out]" ;;
  esac
done
[ "$multiclause_decision_ok" = 1 ] && pass

multiclause_requirement_ok=1
for s in $MULTICLAUSE_REQUIREMENT_SENTENCES; do
  payload="$(jq -n --arg cwd "$REPO" --arg p "$s" '{cwd:$cwd, prompt:$p}')"
  out="$(printf '%s' "$payload" | sh "$REMINDER_SH")"
  case "$out" in
    *需求*) : ;;
    *) multiclause_requirement_ok=0; fail "⑤【套件A】多子句需求消息未命中(附带疑问子句不应压制主句): [$s] -> [$out]" ;;
  esac
done
[ "$multiclause_requirement_ok" = 1 ] && pass

# ---- 套件 C:不含任何压制词的陷阱子类(裸模式无宾语/收尾锚定误报) ----
no_suppression_trap_ok=1
for s in $NO_SUPPRESSION_TRAP_SENTENCES; do
  payload="$(jq -n --arg cwd "$REPO" --arg p "$s" '{cwd:$cwd, prompt:$p}')"
  out="$(printf '%s' "$payload" | sh "$REMINDER_SH")"
  if [ -n "$out" ]; then
    no_suppression_trap_ok=0
    fail "⑤【套件C】不含压制词的陷阱句误触发(裸模式无宾语/收尾锚定,不得命中): [$s] -> [$out]"
  fi
done
[ "$no_suppression_trap_ok" = 1 ] && pass
unset IFS

# =========================================================
# ⑥ 关闭标志 / 评测 env 下三脚本全静默
# =========================================================
# 用假 HOME 隔离，绝不触碰真实 ~/.claude/.docs-capture-off
FAKE_HOME="$WORK/fake-home"
mkdir -p "$FAKE_HOME/.claude"
: > "$FAKE_HOME/.claude/.docs-capture-off"

rm -f "$INBOX"
printf '%s' "$PAYLOAD_1" | HOME="$FAKE_HOME" sh "$CAPTURE_SH"
[ -f "$INBOX" ] && fail "⑥off 标志下 capture 不应写 inbox" || pass

OUT_OFF_REMINDER="$(printf '%s' "$(jq -n --arg cwd "$REPO" --arg p "就这么定" '{cwd:$cwd, prompt:$p}')" | HOME="$FAKE_HOME" sh "$REMINDER_SH")"
assert_empty "$OUT_OFF_REMINDER" "⑥off 标志下 reminder 零输出"

git -C "$REPO" add -A >/dev/null 2>&1
echo "x" >> "$REPO/foo.sh"
git -C "$REPO" add "$REPO/foo.sh" >/dev/null 2>&1
OUT_OFF_GATE="$(printf '%s' "$(jq -n --arg cwd "$REPO" '{cwd:$cwd, tool_name:"Bash", tool_input:{command:"git commit -m x"}}')" | HOME="$FAKE_HOME" sh "$GATE_SH")"
assert_empty "$OUT_OFF_GATE" "⑥off 标志下 commit-gate 零输出"
git -C "$REPO" reset >/dev/null 2>&1
rm -f "$REPO/foo.sh"

# env 隔离开关
rm -f "$INBOX"
DOCS_CAPTURE_EVALS_HERMETIC=1 sh -c "printf '%s' '$PAYLOAD_1' | sh '$CAPTURE_SH'"
[ -f "$INBOX" ] && fail "⑥HERMETIC env 下 capture 不应写 inbox" || pass

# =========================================================
# ⑦ 门禁首警二放
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
assert_contains "$OUT7A" '"permissionDecision": "deny"' "⑦首次 commit 应被提示/阻止"

OUT7B="$(printf '%s' "$PAYLOAD_GATE" | sh "$GATE_SH")"
assert_empty "$OUT7B" "⑦同一 staged 内容第二次应放行(零输出)"

# =========================================================
# ⑧ staged 变化后重新警
# =========================================================
echo "console.log(2)" >> "$REPO/app.js"
git -C "$REPO" add "$REPO/app.js"
OUT8="$(printf '%s' "$PAYLOAD_GATE" | sh "$GATE_SH")"
assert_contains "$OUT8" '"permissionDecision": "deny"' "⑧staged 变化后应重新提示"

git -C "$REPO" reset >/dev/null 2>&1
rm -f "$REPO/app.js"
rm -f "$GIT_DIR_FIXTURE/docs-capture-warned"

# =========================================================
# ⑨ inbox 空时门禁检查①不响(仅当无源码改动/已有 Progress.md 时应放行)
# =========================================================
rm -f "$INBOX"
: > "$REPO/docs/Progress.md"
echo "console.log(1)" > "$REPO/app2.js"
git -C "$REPO" add "$REPO/app2.js" "$REPO/docs/Progress.md"
rm -f "$GIT_DIR_FIXTURE/docs-capture-warned"
OUT9="$(printf '%s' "$PAYLOAD_GATE" | sh "$GATE_SH")"
assert_empty "$OUT9" "⑨inbox 空且 Progress.md 已 staged 时门禁应放行"
git -C "$REPO" reset >/dev/null 2>&1
rm -f "$REPO/app2.js" "$REPO/docs/Progress.md"

# =========================================================
# ⑩ jq 缺失静默退化
# =========================================================
FAKE_BIN_DIR="$WORK/fake-bin-no-jq"
mkdir -p "$FAKE_BIN_DIR"
# 构造一个不含 jq 的 PATH（仅保留必要基础命令的真实路径）
NO_JQ_PATH=""
for d in $(printf '%s' "$PATH" | tr ':' '\n'); do
  if [ ! -x "$d/jq" ]; then
    NO_JQ_PATH="${NO_JQ_PATH}${d}:"
  fi
done

rm -f "$INBOX"
OUT10A="$(printf '%s' "$PAYLOAD_1" | PATH="$NO_JQ_PATH" sh "$CAPTURE_SH")"
assert_empty "$OUT10A" "⑩jq 缺失时 capture 零输出"
[ -f "$INBOX" ] && fail "⑩jq 缺失时不应写 inbox" || pass

OUT10B="$(printf '%s' "$(jq -n --arg cwd "$REPO" --arg p "就这么定" '{cwd:$cwd, prompt:$p}')" | PATH="$NO_JQ_PATH" sh "$REMINDER_SH")"
assert_empty "$OUT10B" "⑩jq 缺失时 reminder 零输出"

echo "console.log(1)" > "$REPO/app3.js"
git -C "$REPO" add "$REPO/app3.js"
rm -f "$GIT_DIR_FIXTURE/docs-capture-warned"
OUT10C="$(printf '%s' "$PAYLOAD_GATE" | PATH="$NO_JQ_PATH" sh "$GATE_SH")"
assert_empty "$OUT10C" "⑩jq 缺失时 commit-gate 零输出(放行)"
git -C "$REPO" reset >/dev/null 2>&1
rm -f "$REPO/app3.js"

# =========================================================
# ⑪ 连续追加 3 条不粘连(条目边界须有换行)
# =========================================================
rm -f "$INBOX"
for i in 1 2 3; do
  seq_payload="$(jq -n --arg cwd "$REPO" --arg sid "seq0000000${i}" \
    '{cwd:$cwd, session_id:$sid, tool_response:{questions:[{question:("连续追加第" + ($i|tostring) + "条"),options:[{label:"A"},{label:"B"}]}],answers:{("连续追加第" + ($i|tostring) + "条"):"A"}}}' \
    --argjson i "$i")"
  printf '%s' "$seq_payload" | sh "$CAPTURE_SH"
done
OUT11="$(cat "$INBOX" 2>/dev/null)"
h_count="$(printf '%s' "$OUT11" | grep -c '^## ')"
assert_eq "$h_count" "3" "⑪连续追加 3 条后 grep -c '^## ' 应为 3(条目末尾须有换行,不与下一条粘连)"
assert_not_contains "$OUT11" '**选择**: A##' "⑪条目边界不应粘连(**选择**: A 后不应直接接 ## )"

# =========================================================
# ⑫ 非方法论目录(git 仓但无 docs/):三脚本零输出、零写入
# =========================================================
PAYLOAD_NON_DOCS="$(jq -n --arg cwd "$NON_DOCS_REPO" '{cwd:$cwd, session_id:"nondocs01", tool_response:{questions:[{question:"q",options:[{label:"A"}]}],answers:{q:"A"}}}')"
OUT12A="$(printf '%s' "$PAYLOAD_NON_DOCS" | sh "$CAPTURE_SH")"
assert_empty "$OUT12A" "⑫无 docs/ 的 git 仓:capture 零输出"
[ -d "$NON_DOCS_REPO/docs" ] && fail "⑫无 docs/ 的 git 仓:capture 不应创建 docs 目录" || pass

OUT12B="$(printf '%s' "$(jq -n --arg cwd "$NON_DOCS_REPO" --arg p "就这么定" '{cwd:$cwd, prompt:$p}')" | sh "$REMINDER_SH")"
assert_empty "$OUT12B" "⑫无 docs/ 的 git 仓:reminder 零输出"

echo "console.log(1)" > "$NON_DOCS_REPO/x.js"
git -C "$NON_DOCS_REPO" add "x.js"
OUT12C="$(printf '%s' "$(jq -n --arg cwd "$NON_DOCS_REPO" '{cwd:$cwd, tool_name:"Bash", tool_input:{command:"git commit -m x"}}')" | sh "$GATE_SH")"
assert_empty "$OUT12C" "⑫无 docs/ 的 git 仓:commit-gate 零输出(放行)"
git -C "$NON_DOCS_REPO" reset >/dev/null 2>&1
rm -f "$NON_DOCS_REPO/x.js"

# =========================================================
# ⑬ 非 git 目录:三脚本零输出、零崩溃(含各类畸形 JSON / 空 stdin)
# =========================================================
PLAIN_DIR="$WORK/plain-non-git-dir"
mkdir -p "$PLAIN_DIR/docs"

run_in_plain_dir() {
  # $1=script $2=payload(可为空串代表空 stdin)
  ( cd "$PLAIN_DIR" && printf '%s' "$2" | sh "$1" )
}

MALFORMED_LABEL="null [] {} 纯字符串 空stdin"
for mp in 'null' '[]' '{}' '"just a string"' ''; do
  o_cap="$(run_in_plain_dir "$CAPTURE_SH" "$mp")"
  ec_cap=$?
  assert_empty "$o_cap" "⑬非 git 目录+畸形负载[$mp]:capture 零输出"
  [ "$ec_cap" -eq 0 ] || fail "⑬非 git 目录+畸形负载[$mp]:capture 应 exit 0,实得 $ec_cap"
  [ -f "$PLAIN_DIR/docs/DECISIONS.inbox.md" ] && fail "⑬非 git 目录+畸形负载[$mp]:不应生成 inbox" || pass

  o_rem="$(run_in_plain_dir "$REMINDER_SH" "$mp")"
  assert_empty "$o_rem" "⑬非 git 目录+畸形负载[$mp]:reminder 零输出"

  o_gate="$(run_in_plain_dir "$GATE_SH" "$mp")"
  assert_empty "$o_gate" "⑬非 git 目录+畸形负载[$mp]:commit-gate 零输出"
done

# =========================================================
# ⑭ 畸形 tool_response 形状(有 cwd,对象但字段缺失/类型不对):走原始 JSON 兜底,不崩溃
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
assert_eq "$h_count14" "3" "⑭畸形 tool_response 形状(null/[]/{})各自走原始兜底,应各生成一条 ## 条目"

# =========================================================
# ⑮ 取消问答(tool_response 是字符串,如用户拒绝/澄清):不得污染 inbox
# =========================================================
rm -f "$INBOX"
CANCEL_PAYLOAD='{"cwd":"'"$REPO"'","session_id":"cancel01","tool_response":"Error: The user doesn'"'"'t want to proceed with this tool use. The tool use was rejected (further instructions were provided)."}'
printf '%s' "$CANCEL_PAYLOAD" | sh "$CAPTURE_SH"
[ -f "$INBOX" ] && fail "⑮用户取消问答不应生成 inbox 条目(tool_response 为拒绝字符串)" || pass

# =========================================================
# ⑯ 多选答案(逗号拼接串)不得被误标为 Other/自定义作答
# =========================================================
rm -f "$INBOX"
MULTI_PAYLOAD='{
  "session_id": "multi0001",
  "cwd": "'"$REPO"'",
  "tool_response": {
    "questions": [
      {
        "question": "为什么想切换?",
        "multiSelect": true,
        "options": [
          {"label": "改动太慢"},
          {"label": "稳定性"},
          {"label": "代码质量"}
        ]
      }
    ],
    "answers": {
      "为什么想切换?": "改动太慢, 稳定性, 代码质量"
    }
  }
}'
printf '%s' "$MULTI_PAYLOAD" | sh "$CAPTURE_SH"
OUT16="$(cat "$INBOX" 2>/dev/null)"
assert_contains "$OUT16" "**选择**: 改动太慢, 稳定性, 代码质量" "⑯多选选择行完整保留"
assert_not_contains "$OUT16" "**备注**" "⑯多选(全部子项均在候选内)不应生成 Other/自定义备注行"

# =========================================================
# ⑰ 门禁检查①单独触发(inbox 有待消化条目,但本次 staged 无源码改动)
# =========================================================
rm -f "$INBOX"
: > "$INBOX"
printf '## %s testsid\n**Q**: q\n**候选**: A | B\n**选择**: A\n\n' "$(date '+%Y-%m-%d %H:%M')" >> "$INBOX"
echo "note" > "$REPO/docs/NOTE.md"
git -C "$REPO" add "$REPO/docs/NOTE.md"
rm -f "$GIT_DIR_FIXTURE/docs-capture-warned"
OUT17="$(printf '%s' "$PAYLOAD_GATE" | sh "$GATE_SH")"
assert_contains "$OUT17" '"permissionDecision": "deny"' "⑰仅 inbox 有待消化条目(无源码改动)时门禁检查①应单独触发 deny"
assert_contains "$OUT17" "DECISIONS.inbox.md" "⑰deny 理由应提及 DECISIONS.inbox.md 待消化"
git -C "$REPO" reset >/dev/null 2>&1
rm -f "$REPO/docs/NOTE.md"
rm -f "$GIT_DIR_FIXTURE/docs-capture-warned"
rm -f "$INBOX"

# =========================================================
# ⑱ 回归:候选项 label 本身含「, 」时,单选选中该 label 不应被误判为
# Other/自定义备注(非阻断项 a——split(", ") 判多选边界回归)
# =========================================================
rm -f "$INBOX"
LABEL_WITH_COMMA_PAYLOAD='{
  "session_id": "regr0001",
  "cwd": "'"$REPO"'",
  "tool_response": {
    "questions": [
      {
        "question": "为什么想切换?",
        "multiSelect": false,
        "options": [
          {"label": "Improve reliability, performance"},
          {"label": "Other reasons"}
        ]
      }
    ],
    "answers": {
      "为什么想切换?": "Improve reliability, performance"
    }
  }
}'
printf '%s' "$LABEL_WITH_COMMA_PAYLOAD" | sh "$CAPTURE_SH"
OUT18="$(cat "$INBOX" 2>/dev/null)"
assert_contains "$OUT18" "**选择**: Improve reliability, performance" "⑱label 含「, 」的单选答案应完整保留在选择行"
assert_not_contains "$OUT18" "**备注**" "⑱label 本身含「, 」不应被误判为 Other/自定义备注"
rm -f "$INBOX"

# =========================================================
# ⑲ 回归:commit-gate 对 git commit 的匹配应为词首/命令匹配,不是全命令
# 子串匹配(非阻断项 b——echo "git commit" 不应触发门禁)
# =========================================================
echo "console.log(1)" > "$REPO/app4.js"
git -C "$REPO" add "$REPO/app4.js"
rm -f "$GIT_DIR_FIXTURE/docs-capture-warned"
PAYLOAD_ECHO_GIT_COMMIT="$(jq -n --arg cwd "$REPO" '{cwd:$cwd, tool_name:"Bash", tool_input:{command:"echo \"git commit\""}}')"
OUT19="$(printf '%s' "$PAYLOAD_ECHO_GIT_COMMIT" | sh "$GATE_SH")"
assert_empty "$OUT19" "⑲echo \"git commit\" 不应触发门禁(非 git commit 命令本身,只是字符串子串)"
git -C "$REPO" reset >/dev/null 2>&1
rm -f "$REPO/app4.js"
rm -f "$GIT_DIR_FIXTURE/docs-capture-warned"

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
