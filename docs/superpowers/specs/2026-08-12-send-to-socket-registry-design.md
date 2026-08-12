# send-to:socket 直发标准化 + 会话身份注册表 — Design Spec

- 日期:2026-08-12
- 状态:已获 Tony 逐节确认(2026-08-12 会话内:B2 方案、设计骨架均选"照此定")
- 依据:交接任务书 `/tmp/send-to-handoff-claude-workflow-kit.md` 任务 B;2026-08-12 真实转达事故(见 1.1)

## 1. 背景

### 1.1 触发事故(B1)

2026-08-12,一个会话要向本窗口(不同登录账号、不同 profile,互不在对方 ListAgents)转达任务,按现行 SKILL.md 行文直接降级到了文件交接,被 Tony 当场纠正"用 socket id 来发不行吗"。诊断:SKILL.md 确实写了「未列出 socket 的直发」,但**行文基调把它写成边角料**(地址来源第 4 条标注"最后手段,多数情况根本走不通",通篇强调硬禁止与失败率),执行者读完的直觉是"这条路不通"。这是 skill 的表述问题,不是执行者的理解问题。

### 1.2 认人窘境(B2)

`ls -lt /tmp/cc-socks/` 只有 pid + mtime,拿不到任何身份信息(哪个账号、哪个项目、主会话还是子代理),用户自己也认不出(Tony 原话:「我看不到 socket 我也不知道」)。本次事故中发起方对着 8 个 socket 只能靠排除法收窄,期间还发生误投(靠对方回声纠正)。

### 1.3 版本分叉现状(2026-08-12 md5 核实)

- **本机三个 profile**(`~/.claude/skills/`、`~/.claude-profiles/labs/skills/`、`~/.claude-profiles/long/skills/` 下的 `send-to/SKILL.md`)内容完全一致,为**新版基线**:含 2026-08-10 受控实验定谳(uds 直发跨账号可达)与「未列出 socket 的直发」节。
- **kit 仓中英双版**与 **huake 仓副本**三者一致,为**旧版**(2026-08-08「跨账号不可发」口径,无直发节)。
- 结论:本次改造**以本机新版为基线**重写,不在 kit 旧版上打补丁;kit 中文版为源,英文版全文同义重译。

## 2. 目标与非目标

**目标**:

1. (B1)把「凭 `uds:` 地址直发」从事实上的 fallback 提升为**标准路径**;文件交接退回真正的最后兜底;删除劝退式行文。
2. (B2)会话身份可发现:SessionStart hook 自愿注册身份到跨 profile 共享注册表,把 socket 清单翻译成人能认的条目。

**非目标 / 硬约束(改后必须原样成立)**:

- **投递通道只有 SendMessage 一条**(含 `uds:` 地址形态)。注册表只改善"发现/认人",不新增投递通道。
- 现行全部硬禁令原样保留:不许手写对方 socket、动对方 profile 注册/会话文件、切 `CLAUDE_CONFIG_DIR` 起中继、`--resume` 接管、tmux 注键;不许拿 pid 翻进程/终端单方侦察。
- 权限边界不变:本会话被拒的操作不得以任何形式转嫁对方会话。
- Windows 原生不支持照旧;消息自包含硬规则、投递状态如实汇报("只可说已发送"、held 挂起语义)照旧。

## 3. 设计

### 3.1 找目标:四级阶梯(SKILL.md「步骤 2」重构)

- **L1** `ListAgents` 命中 → 按名发(现行规则不变:精确/前缀直发、仅子串需确认、多命中亮列表)。
- **L2【标准路径】** 0 命中 → **读身份注册表** `/tmp/cc-session-registry/`,过滤掉 socket 已消失的条目后:
  - 唯一匹配用户所指目标(按项目名/账号/启动时间对照)→ `uds:` 直发;
  - 多候选 → 把**人话身份**(项目名、账号、profile、启动时间)亮给用户挑——用户认得出这些,认不出 pid;
  - 行文要求:本级写成"标准路径",不带任何"多数情况走不通"式劝退语。
- **L3** 注册表无条目(对方 profile 没装 hook)→ 现行地址来源阶梯:① 对方消息里自报过(`from=` 照抄)→ ② 让目标窗口先开口 → ③ 用户在目标窗口拿地址粘过来 → ④ 候选辨认(念 socket 清单,由用户指认;此处才保留"最后手段"定位与其现行全部限制)。
- **L4** 全部落空,或对用户指认地址发送仍失败 → **文件交接降级**(真正的最后兜底;触发门槛沿用现行两条)。

### 3.2 回声双档(替换现行"首发必须索回声"单一规则)

- **注册表确证**(三条件同时满足:注册条目存在 + 对应 socket 存在**且其 pid 进程存活** + 条目的项目/账号与用户所指目标对得上):直发**不必阻塞等回声**;首发仍自报家门(哪个项目/profile 的窗口),并附「若你不是 <目标>,请回我一声并忽略」作为零成本纠错邀请。投递状态汇报照旧只可说"已发送"(held 挂起风险与身份确证无关)。
- **非确证**(排除法收窄、用户口头指认、L3 各来源):照旧强制索取回声,等不到回声不得当作已送达,该转文件交接就转。

### 3.3 身份注册表(SKILL.md 新增一节)

注册表规范:

- 目录:`/tmp/cc-session-registry/`,不存在时由 hook 创建,权限 `0700`(仅本用户)。**不放** `/tmp/cc-socks/` 内——那是 Claude Code 自建自管目录(实测 0700、由它创建),塞外来文件有被清理/冲突风险。
- 文件:`<pid>.json`,pid 与 `/tmp/cc-socks/<pid>.sock` 对齐,一会话一文件(天然避免并发写冲突)。
- 字段:

  | 字段 | 含义 | 取不到时 |
  |---|---|---|
  | `pid` | Claude Code 主进程 pid(int) | 必有(定位不到则不写文件) |
  | `socket` | `/tmp/cc-socks/<pid>.sock` 全路径 | 同上 |
  | `account` | 登录账号邮箱 | `"unknown"` |
  | `profile` | `CLAUDE_CONFIG_DIR` 的 basename | `"default"` |
  | `cwd` | 会话工作目录全路径 | `"unknown"` |
  | `project` | cwd 的 basename | `"unknown"` |
  | `session_id` | hook stdin JSON 里的 session_id | `"unknown"` |
  | `source` | hook 触发源(startup/resume/clear/compact) | `"unknown"` |
  | `cmd` | 自身 Claude 主进程的启动命令行(`ps -o command=` 对**自身祖先**取,属自我登记不属侦察),用于区分交互主会话与派生/headless 进程 | `"unknown"` |
  | `registered_at` | ISO8601 注册时间 | 必有(`date -u`) |

- 有效性:条目仅当「对应 socket 仍存在 **且其 pid 进程仍存活**(`kill -0` 级检查)」时有效;**读取侧必须先按此双判据过滤**。单看 socket 文件不够:claude 退出后 socket 会残留(实证:本机 29473.sock 已无对应进程),孤儿 socket + 单判据 = 幻影条目 + 假"已发送"。
- 清理:hook 每次运行顺手删除「socket 已消失**或 pid 已死**」的条目;整个目录可随时 `rm -rf`,无副作用(各会话下次 SessionStart 重建)。
- 性质声明(必须写进 SKILL.md,防未来执行者不敢用):**注册表是各会话自愿自报的名片,与 ListAgents 的注册同性质;读注册表 ≠ 侦察**。硬禁止针对的是"单方拿 pid 翻进程/终端替用户拍板",那条禁令原样有效。
- 覆盖范围如实声明:只有装了本插件(或挂了注册 hook)的 profile 的会话才有条目;**没条目 ≠ 不存在**,走 L3。

### 3.4 注册 hook(新组件)

- `plugins/send-to/hooks/hooks.json`:`SessionStart`,matcher `startup|resume|clear|compact`,`timeout: 5`,command `sh "${CLAUDE_PLUGIN_ROOT}/hooks/register.sh"`(仿 speak-human hook 结构;send-to-en 同构一份)。
- `plugins/send-to/hooks/register.sh`(POSIX sh,macOS/Linux 兼容,`send-to-en` 同文件):
  1. **定位自身 pid**:从自身进程沿祖先链上溯(`ps -o ppid= -p`),找到第一个满足 `[ -S "$SOCKS_DIR/<pid>.sock" ]` 的祖先 pid;上溯步数设硬上限(如 10)防死循环;找不到 → 静默 `exit 0` 不写文件。
  2. **读 stdin JSON**(best-effort,sed/awk 提取 `session_id`、`cwd`、`source`;解析失败一律回落 `"unknown"`,cwd 回落 `$PWD`)。
  3. **取账号**:`CLAUDE_CONFIG_DIR` 已设置时**只认** `$CLAUDE_CONFIG_DIR/.claude.json`(取不到写 `"unknown"`,**不回落** `$HOME`——回落会把 labs/long profile 的会话错标成 default 账号,错标 + 免回声直发 = 投错窗口不自知,危害大于 unknown);未设置时读 `$HOME/.claude.json`。路径处理必须耐空格(不许无引号 for-loop 展开)。profile 取 `basename "$CLAUDE_CONFIG_DIR"`,未设置为 `"default"`。
  4. **原子写**:mktemp 于注册表**同目录**内 → 写 JSON → `mv` 到 `<pid>.json`(幂等,重复运行覆盖刷新)。
  5. **顺手清扫**:遍历注册表内 `*.json`,「对应 socket 不存在**或 pid 进程已死**」则删除(双判据,防孤儿 socket 幻影条目)。
  6. **静默纪律**:**stdout 绝不输出任何内容**(SessionStart hook 的 stdout 会被注入会话上下文,speak-human 是刻意注入,本 hook 必须零输出);任何失败静默 `exit 0`,绝不影响会话启动。
- 可测性:`CC_SOCKS_DIR`(默认 `/tmp/cc-socks`)、`CC_SESSION_REGISTRY_DIR`(默认 `/tmp/cc-session-registry`)、`CC_SELF_PID`(默认走祖先链)三个环境变量可覆盖,供 smoke 测试注入假环境。
- **smoke 测试**:`plugins/send-to/hooks/smoke-test.sh`,临时目录内验证至少七例:① 正常注册(字段齐、JSON 可解析);② 注册表目录不存在时自动创建且 0700;③ 陈旧条目(socket 已删)被清扫;④ 定位不到自身 socket 时退出 0 且不写文件、无 stdout 输出;⑤ 重复运行幂等;⑥ 孤儿条目(socket 文件在、pid 已死)被清扫;⑦ `CLAUDE_CONFIG_DIR` 指向无 `.claude.json` 的目录时 account 为 `"unknown"`(即便 `$HOME/.claude.json` 存在也不回落)。TDD:先写 smoke 测试跑到失败,再写 register.sh。

### 3.5 实现前实测清单(不确定点)

实现单元动手前先在本机实测,结论回填实现;拿不准一律写保守分支(字段缺 → `"unknown"`,流程不 fail):

1. ~~子代理是否有自己的 socket~~ **已实测(2026-08-12,本会话,两轮)**:Workflow 派生的 agent 是独立 `claude` 进程,各有自己的 `/tmp/cc-socks/<pid>.sock`。**旗标不可作硬判据**(终审反证:同机全部交互主会话的 cmd 同样带 `--effort ultracode`,与派生进程无差别;按"cmd 无 --effort"筛选会筛掉 100% 主会话)。第二轮实测:项目级 settings hook 就位后跑最小 workflow agent,注册表**未出现**派生进程条目——污染实测未复现。设计应对:`cmd` 仅作弱提示(带 `-p`/`--print` 的多为 headless 一次性进程,排序靠后),**绝不作筛除依据**;同一项目多条活条目一律把候选(项目、账号、启动时间、cmd)亮给用户挑,不替用户拍板;
2. hook stdin JSON 实际有哪些字段(session_id/cwd/source 的真实键名);
3. hook 进程到 Claude Code 主进程的祖先链层数与形态;
4. `.claude.json` 中账号邮箱的实际 JSON 路径(profile 与默认两种布局)。

### 3.6 SKILL.md 其余同步修改

- 「环境要求」:发现通道表述更新为三条(ListAgents + 身份注册表 + socket 目录清单);受控实验定谳表述(2026-08-10)自本机基线保留。
- 「常见错误」表:新增「零命中不先读注册表就开始折腾地址阶梯」条;「零命中张口就念 socket 清单」条改为指向 L2→L3 顺序;其余各条(混杂样本、盲发禁令、通道禁令等)保留。
- 中文版为源;英文版(`plugins/send-to-en/`)全文同义重译(旧版结构已落后,不做逐段 patch)。
- `plugins/send-to{,-en}/.claude-plugin/plugin.json`:版本 0.2.0 → 0.3.0,description 更新(socket 直发标准路径 + 身份注册表 + hook)。

### 3.7 README(zh/en)send-to 节与目录树

- 「附赠插件:send-to」节:第 4 条 bullet(「跨账号识别 + 文件交接降级」)改写为新口径:跨 profile 不可见但可直发(受控实验定谳)、身份注册表认人、四级阶梯、文件交接为最后兜底;补一句 hook 说明与「hook 要在每个 profile 生效才能注册该 profile 的会话」。
- 仓库结构目录树:`plugins/send-to/` 下补 `hooks/`。

## 4. 改动文件清单(kit 仓,本分支)

| 文件 | 改动 |
|---|---|
| `plugins/send-to/skills/send-to/SKILL.md` | 以本机新版为基线重写:3.1/3.2/3.3/3.6 |
| `plugins/send-to-en/skills/send-to/SKILL.md` | 自中文终稿全文同义重译 |
| `plugins/send-to/hooks/hooks.json` + `register.sh` + `smoke-test.sh` | 新增,3.4 |
| `plugins/send-to-en/hooks/`(同构三文件) | 新增 |
| `plugins/send-to/.claude-plugin/plugin.json`、`plugins/send-to-en/.claude-plugin/plugin.json` | 版本+描述 |
| `.claude-plugin/marketplace.json` | send-to / send-to-en 两条 description 换新口径(uds: 直发标准路径 + 身份注册表 + 四级阶梯),与 0.3.0 plugin.json 对齐 |
| `README.zh-CN.md`、`README.md` | 3.7(send-to 节 + 目录树) |

## 5. merge 后外部同步(不在本分支内)

1. **本机三个 profile** 的 `skills/send-to/SKILL.md` ← kit 中文终稿(三份现为同一内容,同步后仍保持一致)。
2. **本机注册 hook**:裸 skill 目录装不了 hook → 向三个 profile 的 `settings.json` 各挂一条 SessionStart hook,指向共享脚本(建议 `~/.claude/hooks/cc-session-register.sh`,内容同 register.sh)。**动 settings.json 前逐份向 Tony 确认**。
3. **huake 仓** `claude-toolkit-engineer`:send-to SKILL.md 整文件替换为 kit 中文终稿(其当前副本与 kit 旧版逐字节一致,整替换安全);其 `hooks/hooks.json` **JSON 合并**追加第三条 hook(该文件已有 speak-human 与 auto-scaffold 两条注入,绝不整文件覆盖);新增 register.sh。走其自身 wip → Tony 确认 → merge 流程。

## 6. 验收条款

1. 中文 SKILL.md 含:四级阶梯(L2 为标准路径行文)、回声双档、身份注册表节(含性质声明与覆盖范围声明)、更新后的常见错误表;新版基线内容(受控实验定谳、held 语义、[ref]、自包含硬规则)无遗失。
2. **硬禁令逐条核对保留**:手写对方 socket / 动对方注册文件 / 切 CLAUDE_CONFIG_DIR 中继 / --resume 接管 / tmux 注键 / pid 侦察 / 盲发未指认地址 / 权限转嫁,一条不许少、语气不许弱化。
3. 英文 SKILL.md 与中文语义逐节一致(结构同序)。
4. smoke-test.sh 全部用例通过(实现单元附运行输出);真实环境冒烟:本机跑一次 register.sh 后 `/tmp/cc-session-registry/` 出现本会话条目且字段非全 unknown。
5. hooks.json 结构与 speak-human 版同构;register.sh 无 stdout 输出(smoke 用例 ④ 断言)。
6. plugin.json 版本 0.3.0、双语 README send-to 节与目录树已更新。
7. 乱码扫描通过(`LC_ALL=C grep -l $'\xef\xbf\xbd'` 于全部被改 md/sh)。
8. 3.5 实测清单四项均有结论记录(写进实现 commit message 或评审记录)。

## 7. 实施与评审档位

- 分支:`wip/send-to-socket-registry`,commit 即 push。
- ultracode 编排:实测清单(主对话亲自或 sonnet/low 探测)→ register.sh + smoke(sonnet/medium,TDD)与 zh SKILL.md 重写(sonnet/medium)并行 → en 重译(sonnet/medium,输入 zh 终稿)→ plugin.json + README 双语节(sonnet/low)。
- 评审:每单元 opus/medium;SKILL.md 单元评审必须带「硬禁令保留」镜头;打回重跑升 high。
- 终审:opus/high(跨会话通信 skill 涉及权限边界语义,属安全类评审)。
- merge 进 main 前找 Tony 确认(门禁)。
