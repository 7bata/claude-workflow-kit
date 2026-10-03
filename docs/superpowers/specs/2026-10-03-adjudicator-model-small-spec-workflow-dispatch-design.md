# Spec:裁决轮用主对话模型 + 小改动也写小 spec 直接开干 + 并行派活统一走 Workflow

日期:2026-10-03
状态:Tony 2026-10-03 拍板,按新规则写完即开工
依据:2026-10-02 prompt 审计查出的三处跨文件冲突(评审由谁裁决;小改动要不要写 spec 与等批准;并行派活用哪种工具)

## 1. 三条决定(Tony 原话)

1. 「按照当前这个对话model来当评审裁决(比如,现在这个里面的model是fable,那就让fable当。如果另外一个窗口是opus,那就opus当)」
2. 「可以,小改动就写一个小的spec,但是这个就不用让我看了,直接写spec就直接开干」
3. 「统一走workflow」

主对话对第 1 条的理解(已在对话里向 Tony 复述):只管评审链最后一轮「裁决」;盲审轮与续挖轮照旧用 `opus`。

## 2. 目标覆盖声明

- **覆盖**:目标清单 2026-10-03 行(三条规则拍板);2026-10-02「prompt 审计的后续」行里的三处冲突。
- **不覆盖**:
  - 审计的其余建议改法(全局规则 27 块、用户级 skill 17 块)——等 Tony 定。唯一例外:全局规则第 57 行那句失效的 stellark-whats-next 引用,因为同一段要按第 2、3 条重写,一并去掉。
  - dev-toolkit 盲审轮里的外部 CLI(cwcode / codex):Tony 只定了裁决由谁出,盲审怎么组成没定,本批不动,各文件现有写法保留。
  - stellark-parallel-do 示例脚本里「每个单元挂一个评审」的写法:本批只改它档位表里裁决轮那一格。
  - 机械子代理调用名要带插件前缀的问题:另行处理。
  - Codex 版(workflow-codex、huake 的 codex 工具包):没有逐 stage 的模型档位,也没有 Workflow 工具,第 1、3 条不适用;只同步第 2 条里「获批后」这类措辞。

## 3. 规范文本

以本机全局规则为准写出全文;其余各面按「要素清单」(第 4 节)落实,公开面不写内部名称。以句子内容定位,行号只是 2026-10-03 的参考。标点沿用所在文件原有风格。规范文本之外的句子不动。

### 3.1 第 1 条:裁决轮用主对话当前的模型

**全局 `~/.claude/CLAUDE.md`:**

- 三层分工表评审一行,「谁来做」一格由 `` `opus` 子代理 `` 改为:

  > `opus` 子代理(盲审、续挖);裁决轮用主对话当前的模型

- 档位表小标题改为:

  > ### 档位表(`model` 与 `effort` 都必须显式写,不许省略;裁决轮的 `model` 例外,见规则 2)

- 档位表裁决轮一行,model 一格由 `` `opus` `` 改为:

  > 主对话当前的模型(脚本里省略 `model`)

- 规则 2 里的裁决轮一句,由「**裁决轮**——链的最后一轮(`opus` + `high`,带全链发现出结论,不占镜头);」改为:

  > **裁决轮**——链的最后一轮(用主对话当前的模型 + `high`:脚本里这一个 stage 省略 `model`、继承主会话,主对话是 Fable 就由 Fable 裁决,是 Opus 就由 Opus 裁决;带全链发现出结论,不占镜头);

- 规则 3 里「评审链每一轮(盲审 3 个、续挖轮也含)都用 `opus` + `high`,」改为:

  > 评审链每一轮都用 `high`(盲审 3 个与续挖轮用 `opus`,裁决轮用主对话当前的模型),

- 「Workflow(ultracode)脚本里的 `agent()` 按上表**逐 stage 显式写 `model` + `effort`**。」之后紧接着加一句括注:

  > (裁决轮例外:省略 `model`,继承主会话模型。)

- 直通流程第 2 步:「每单元完成即派评审链(`model: 'opus'`,编排见本步末尾)验证裁决」改为:

  > 每单元完成即派评审链(盲审与续挖 `model: 'opus'`,裁决轮省略 `model`、用主对话当前的模型;编排见本步末尾)验证裁决

  同一步末尾「末轮裁决 `opus` + `high`(见档位表规则 2,2026-09-22 改)」改为:

  > 末轮裁决用主对话当前的模型 + `high`(见档位表规则 2)

**英文面的对应说法**(README.md 与英文模板按所在句子的结构改写,用词以此为准):the adjudication round uses "the main conversation's current model (omit `model` in the script so the stage inherits it — if the main conversation runs Fable, Fable adjudicates; if it runs Opus, Opus does)";标题括注 "the adjudication round's `model` is the one exception, see rule 2";规则 3 "every round runs at `high` (the blind reviewers and dig-deeper rounds on `opus`, the adjudication round on the main conversation's current model)"。

**内部 dev-toolkit 的异构变体**:凡写「裁决一律由 `model: fable` 子代理出」「fable 裁决」「`fable` 子代理」作裁决轮模型的地方,改成「裁决轮用主对话当前的模型(脚本里省略 `model`,继承主会话)」;盲审里的外部 CLI 写法不动。

### 3.2 第 2 条:小改动也写小 spec,写完直接开干

**全局 `~/.claude/CLAUDE.md`:**

- 直通流程开头那段,在「(若我在 brainstorming 过程中或 spec 写入后主动喊停,则照常停下)。」之后、「流程:」之前加:

  > 小改动(brainstorming 的 bounded 路径)同样走这条:写一份小 spec(几段即可,目标覆盖声明一句即可)落 `docs/superpowers/specs/`,不在对话里等我说 yes、不用给我看,写完直接实现,规模小就少拆单元。

- 「本规则覆盖 brainstorming SKILL.md 的…」那一段整段改为:

  > 本规则覆盖 brainstorming SKILL.md 的这几处:架构路径「the ONLY skill you invoke after brainstorming is writing-plans」(含其 checklist 第 9 项与流程图终态);架构路径 checklist 第 8 项与「User Review Gate」(写完 spec 等用户审阅批准);bounded 路径的「不写 spec、在对话里给出设计后停下等批准」;以及 HARD-GATE 里「每条路径都要先获批准才能实现」。bounded 与架构路径都按上面的做法:写 spec、不等批准、直接实现;spike 路径(只产出结论、不留代码)照 brainstorming 原样。也覆盖 superpowers:dispatching-parallel-agents:并行派活一律走 Workflow,不在一条回复里平行派裸子代理。subagent-driven-development / executing-plans 因不再有 plan 文档而失去入口,属预期,不必绕路满足它们。

**公开版 README.zh-CN.md:**七.2 句末加上面「小改动…」那句的公开版(「等我说 yes、不用给我看」写成「等用户确认」);七.6 改成上面那一段的公开版(引用四节的写法用「见四」)。README.md 对应英文:

> Small changes (brainstorming's bounded path) take the same route: write a small spec (a few paragraphs; a one-line goal-coverage statement is enough), don't wait for the user's yes in chat, and implement as soon as it is written — split into fewer units when the scope is small.

> This flow overrides these parts of the brainstorming SKILL.md: the architectural path's "the ONLY skill you invoke after brainstorming is writing-plans" (including checklist item 9 and the flowchart's terminal state); the architectural path's checklist item 8 and its User Review Gate (waiting for the user to approve the written spec); the bounded path's "no spec file, present a short design in chat and stop for approval"; and the HARD-GATE's rule that every path needs approval before implementation. Both the bounded and the architectural path follow the steps above: write the spec, don't wait for approval, implement. The spike path (an answer, no kept code) stays as brainstorming defines it. It also overrides superpowers:dispatching-parallel-agents: parallel work always goes through Workflow (see Section 4), never bare subagents dispatched in parallel from one reply. subagent-driven-development / executing-plans lose their entry point because there is no plan document any more — that is expected; don't work around it.

**各处的旧措辞:**

- 「spec 获批后」「spec 经用户批准后」「once a spec is approved」一律改成「spec 写入后」「once the spec is written」(模板、whats-next、scaffold 汇报句、PLAN 模板里的注释,含 Codex 版)。
- scaffold 汇报句里「改动小到一个原子 commit 能覆盖、且不新增模块与对外接口时,可跳过 spec 直接做,但要在 `docs/Progress.md` 记一句为什么跳过,否则一律先出 spec」改成「小改动也写一份小 spec(几段即可),写完直接做」(Codex 版同样改)。
- whats-next 表里「该 spec 是否已获用户批准拿不准时,先问一句再开」改成「Progress 或 spec 里记着被用户喊停的除外,那种先问一句」。
- whats-next 末尾「结尾问用户:现在开始吗?」保留:那是回答「下一步干什么」的收尾,不是 spec 审批。

### 3.3 第 3 条:并行派活统一走 Workflow

- 全局「所以批量机械活仍优先走 Workflow 编排,别用裸 Agent 分叉。」与 README.zh-CN.md「所以批量/并行任务仍一律优先 Workflow 编排,别用裸 Agent 分叉。」都改为:

  > 所以批量与并行任务一律走 Workflow 编排,不用裸 Agent 平行分叉(单个子代理的一次性委派不在此列)。

- README.md 对应句改为:

  > So batch and parallel work always goes through Workflow orchestration — never fan out bare Agent calls in parallel (a one-off delegation to a single subagent is not covered by this).

- 模板压缩句结尾「→ 批量机械活优先走 Workflow 编排」改成「→ 批量与并行任务一律走 Workflow 编排」(英文 "→ batch and parallel work always goes through Workflow orchestration")。
- 点名覆盖 superpowers:dispatching-parallel-agents 的那句已在 3.2 的覆盖段里。

### 3.4 第 1 轮评审后的修订(2026-10-03;评审链第 1 轮)

(a) **README 第九节的 whats-next 判断表**(README.zh-CN.md 与 README.md):「spec 是否已获批准拿不准时先问一句」改成与插件 whats-next 相同的说法(中文「Progress 或 spec 里记着被用户喊停的除外,那种先问一句」;英文与 workflow-en whats-next 的句子一致)。

(b) **脚手架模板加一条**(本仓中英模板、dev-toolkit 模板、huake 的 Claude 版模板;Codex 版不加),紧跟在「spec 写入后直接用 ultracode…实现」那一条后面,标点沿用该模板的风格:

> - **小改动(brainstorming 的 bounded 路径)也写一份小 spec,写完直接实现、不等用户确认**——这条覆盖 brainstorming 里「不写 spec、停下等批准」的要求

> - **Small changes (brainstorming's bounded path) also get a small spec and are implemented as soon as it is written — don't wait for the user's confirmation.** This overrides brainstorming's "no spec, stop for approval" requirement

(c) **「opus 评审」的旧说法**:模板与 parallel-do 里「每个写入单元(子任务)后面挂一个 opus 评审 stage」改成「…挂一个评审 stage(盲审与续挖 `opus`,裁决轮用主对话当前的模型)」;parallel-do 里「sonnet 实现 → opus 评审」这类流水线说法、「逐单元评审已经…由 opus agent 做完了」去掉模型名或加同样的括注;README 流程图里的「opus 逐单元评审」改成「逐单元评审链」(英文对应);README 中英与全局规则里「所有 / 全部评审(`opus`)照旧加载 CLAUDE.md」去掉「(`opus`)」。

(d) **英文面轮次名统一叫 verdict round**(README.md 与英文模板原本的叫法);3.1 里的 "adjudication round" 只是说明,不作为用词。

(e) **「按点名的方式执行」那一句**:本仓 README 中英去掉「/ 并行分派」("parallel dispatch")这一项;dev-toolkit 的 WORKFLOW.md 与核心 SKILL.md 把「并行分派」写成「parallel-do」(与全局规则一致)。

(f) **第四节标题**:中文「四、批量与并行任务走 Workflow,不走裸 Agent」,英文 "4. Batch and parallel work goes through Workflow, not bare Agent";dev-toolkit 的 WORKFLOW.md 与核心 SKILL.md 的同名标题同样改(核心受 token 上限约束,见 k)。

(g) **覆盖段补一处**(全文面:全局规则、README 中英、dev-toolkit WORKFLOW.md):在「HARD-GATE 里「每条路径都要先获批准才能实现」」之后加「(含「Too Simple To Need Approval」一节的同一要求)」;英文在 HARD-GATE 那一项后加 (including the same requirement in its "Too Simple To Need Approval" section)。

(h) **全局规则**:「省略 `model` 继承主会话的 Fable、不会落到 opus」改成「省略 `model` 继承主会话当前的模型、不会落到 opus」。

(i) **parallel-do(dev-toolkit 与 huake 的 Claude 版)**:写着「`model` / `effort` 每个 stage 都必须显式写」的两处,各加「(裁决轮的 `model` 例外:省略,继承主会话)」;三层分工句里「评审=`opus` agent」后加「(裁决轮用主对话当前的模型)」;「修完仍挂 `opus` + `high` 复审」改成「修完接回原链:修的是 P1 就跑裁决轮(省略 `model`、`effort: 'high'`),修的是 P0 先跑一轮续挖(`opus` + `medium`)再裁决」。示例脚本的结构不动。

(j) **driving-codex**:「`high` for the verdict round and security verdicts」改成不暗示 codex 跑裁决轮的说法(codex 只参与盲审与续挖)。

(k) **dev-toolkit 核心 `stellark-workflow/SKILL.md`**:
- 恢复首轮为省 token 删掉的两处:第一节主对话职责里的「评审裁决、」;七.4 开头指向 stellark-parallel-do 的入口括注。
- 第一节评审行的「谁来做」写成「`opus` + 外部 CLI 盲审,主对话模型裁决」(不再叫「异构三方」);该行说明里去掉「、不再平行投票,改为」这类相对旧版本的说法,直接写现行流程。
- 七.6 改成压缩的覆盖句:「本流程覆盖 brainstorming 的 writing-plans 交接、spec 审阅关口、bounded 停下等批准与 HARD-GATE(spike 照原样),也覆盖 dispatching-parallel-agents(并行一律走 Workflow);subagent-driven-development/executing-plans 因无 plan 失去入口,属预期。」
- 第四节「每个 `agent()` 按档位表显式写 `model`+`effort`」后加「(裁决轮 `model` 例外)」。
- token 仍然只许不增加(基线:该仓 origin/main 上这个文件的 6534.0)。允许用来抵消的只有两类:本批决定已经取代的字眼(把裁决写死成 fable / opus 的说法、「不再平行投票,改为」);与同一文件别处逐字重复、且不是入口句的字眼。不许删约束、理由、禁令词、指向 references 或别的 skill 的入口句。做不到就停下,把每一处增减的 token 数和差额报出来,不硬塞。

(l) **huake 两个 README**:Claude 版「brainstorming → spec 获批 → ultracode 直接实现」改成「brainstorming → spec 写入 → ultracode 直接实现」;两个 README 的版本说明区按各仓以往的写法各加一行(Claude 版 0.26.0、Codex 版 0.14.0),写明镜像 kit 2026-10-03 的内容(Claude 版:裁决轮用主对话当前的模型、spec 写入后直接实现且小改动也写小 spec、批量与并行任务一律走 Workflow;Codex 版:spec 写入后直接实现且小改动也写小 spec)。

(m) **workflow-en whats-next**:分号后悬空的 unless 从句改通顺(例如 "…directly from that spec, unless Progress or the spec records that the user called a halt — in that case ask first")。

所有权随之扩大:U2 含 README 中英的第九节表、流程图、「所有评审」一句、七.7、第四节标题;U3 含三个模板的新增条目与「opus 评审 stage」一句、英文模板的轮次名、workflow-en whats-next;U1 含全局规则里 (c)(g)(h) 涉及的三句;U4 含 dev-toolkit 的 WORKFLOW.md、核心 SKILL.md、parallel-do、driving-codex、脚手架模板里上面各条涉及的句子;U5 含 huake Claude 版的 parallel-do、模板与两个仓库的 README.md。

### 3.5 第 2 轮裁决后的处理(2026-10-03)

裁决结果:U1、U2、U3、U5 通过;U4 未通过——dev-toolkit 核心 SKILL.md 按 3.4(k) 全部落实会到 6593.1,比基线 6534.0 多 59.1,修复 agent 按要求停下报了数字。主对话定的做法:

- 核心 SKILL.md 落实这几项:恢复「评审裁决、」与七.4 开头的 parallel-do 入口括注;评审行改写(「谁来做」写成「`opus`+外部 CLI 盲审,主对话模型裁决」,说明里去掉「、不再平行投票,改为」,裁决模型指到第二节);七.6 换成 3.4(k) 的压缩覆盖句;七.7「并行分派」写成 parallel-do。
- 为守 token 上限,按该仓「换短说法、不丢要素」的既有做法再缩两句:计划与架构设计一行的括注缩成「盲审→续挖(可选)→裁决轮」;五.4 的依据句去掉核查日期与数字,只留原因。主对话按该仓公式实算:6532.0,不超过基线。计划行括注里省掉的「opus∥cwcode/codex」只是这一处不再重复:盲审含外部 CLI 的定义仍在评审行与盲审轮行,第 2 节「外部 CLI 的现有写法保留」指的是这两处定义。
- 塞不下、记为遗留的两处:核心第四节标题不改;核心第四节「显式写 `model`+`effort`」后不加裁决轮例外的括注(例外已在第二节标题与档位表里)。这两处差异写进 references/upstream-map.md。
- 顺带改掉裁决轮新报的三处小问题:dev-toolkit WORKFLOW.md「全部评审(`opus`)照旧加载」去掉「(`opus`)」;driving-codex 那句补回安全类评审用 high;本仓英文模板把修复轮超范围改掉的 "conflict resolution" 改回 "conflict adjudication"。
- 不改、记为遗留:dev-toolkit parallel-do 示例脚本里单个 `opus` + `high` 的评审 stage(huake 版示例注明画的是裁决轮,已省略 model;dev-toolkit 版是泛指的单轮评审,要不要换成评审链还没定);模板标题里「其他并行分派」的字眼;本仓模板里两个括注相连与引号体例;huake parallel-do「opus 的意见不是圣旨」;huake 的 Claude 版插件名以 claude- 开头被校验判为保留名(本批之前就有)。

第 3 轮裁决(2026-10-03):U4 通过,五个单元全部通过。记录见评审链文件「第 3 轮」与「收尾」。

## 4. 要素清单(各面逐条落实,评审逐面核对)

**第 1 条**
1. 裁决轮的模型写成「主对话当前的模型」,并说明脚本里这个 stage 省略 `model`;`effort` 仍是 `high`。
2. 全文版给出例子:主对话是 Fable 就由 Fable 裁决,是 Opus 就由 Opus 裁决。压缩版可以不带例子。
3. 盲审轮、续挖轮的写法不变。
4. 写着「`model` 与 `effort` 都必须显式写」的地方,注明裁决轮的 `model` 是例外。
5. 文件里不再有把裁决轮写死成 `opus` 或 `fable` 的说法。

**第 2 条**
6. 小改动(bounded 路径)也写小 spec,写完直接实现,不等用户确认。
7. 覆盖段点名四处:架构路径交给 writing-plans、架构路径第 8 项与 User Review Gate、bounded 路径不写 spec 且停下等批准、HARD-GATE;spike 路径照原样。
8. 文件里不再有「获批后 / 经用户批准后 / once … is approved」与「可跳过 spec 直接做」。
9. whats-next 的「拿不准是否获批先问」改成只在被用户喊停过时先问;结尾问句保留。

**第 3 条**
10. 批量与并行任务一律走 Workflow;单个子代理的一次性委派不在此列。
11. 覆盖段点名 superpowers:dispatching-parallel-agents(全文版);压缩句同步「一律走」。

**通用**
12. 改一句之前,先在同一行和相邻段里搜引用同一对象的半句,不留下与新句矛盾的旧说法。
13. 公开面(本仓)新增内容不出现内部主机名、组名、仓名。

## 5. 单元与文件所有权

实现 agent 不做任何 git 写操作,由主对话在评审后按单元提交。

| 单元 | 组 | 位置 | 只许改 |
|---|---|---|---|
| U1 | S(sonnet + medium) | 本机 | `~/.claude/CLAUDE.md`(主对话已备份到 `~/.claude/CLAUDE.md.bak-20261003-adjudicator`) |
| U2 | O(opus + medium) | 本仓 | `README.zh-CN.md`、`README.md` |
| U3 | S(sonnet + medium) | 本仓 | `plugins/workflow`、`plugins/workflow-en`、`plugins/workflow-codex` 下的脚手架模板、whats-next、scaffold 的 SKILL.md、PLAN 模板,以及三个插件清单里的版本号(workflow / workflow-en `0.15.0` → `0.16.0`;workflow-codex `0.14.0` → `0.15.0`) |
| U4 | O(opus + medium) | dev-toolkit 的 worktree | `WORKFLOW.md`、`plugins/dev-toolkit/skills/` 下的 stellark-workflow(含 references)、stellark-parallel-do、stellark-whats-next、stellark-scaffold(含模板)、driving-codex;版本号由该仓 CI 升,不手改 |
| U5 | S(sonnet + medium) | huake 两个工具包的 worktree | Claude 版:parallel-do、whats-next、scaffold(含模板);Codex 版:whats-next、scaffold(含模板),只做第 2 条的措辞;版本号按各仓惯例 |

dev-toolkit 的核心 `stellark-workflow/SKILL.md` 有 token 上限(只许不增加):按该仓记录的算法量,做不到不增加就停下报数字,不硬塞。

评审三组,每组 2 个互不可见的 `opus` + `medium` 盲审:公开面(U2 + U3)、本机与 dev-toolkit(U1 + U4)、huake(U5)。裁决轮按新规则用主对话当前的模型(本批是 Fable)+ `high`。本批不属于规则 3 的高风险类别。当前机器负载偏高,实现与盲审都按并发 2 分批跑。

## 6. 验收条款

- AC1:第 4 节 13 条要素在各自适用的面上逐条成立(Codex 面只适用第 8 条与第 12、13 条)。
- AC2:全局文件与备份的 diff 只落在第 3 节点名的句子上;行数不变。
- AC3:本仓 8 个 Claude 插件与仓库根 `claude plugin validate --strict` 全过(README「维护者:发版前检查」第一段末行 `ALL PASSED (8 plugins)`)。
- AC4:各仓 `git diff` 只涉及第 5 节点名的文件。
- AC5:dev-toolkit 核心 SKILL.md 的 token 数不增加(给出前后数字)。
- AC6:各文件里搜「获批」「经用户批准」「approved」「可跳过 spec」「`fable` 子代理」「fable 裁决」「裁决轮…`opus`」,只剩与本批无关的命中(逐条说明)。
- AC7:盲审无 P0 / P1 未闭合。

## 7. 回滚

- 本仓、dev-toolkit、huake:`git revert` 对应提交。
- 全局规则:下一次有人改这个文件之前可以 `cp ~/.claude/CLAUDE.md.bak-20261003-adjudicator ~/.claude/CLAUDE.md`;之后只把本批改过的句子按备份改回去。
