# 评审链:裁决轮用主对话模型 + 小改动也写小 spec 直接开干 + 并行派活统一走 Workflow

spec:`docs/superpowers/specs/2026-10-03-adjudicator-model-small-spec-workflow-dispatch-design.md`。本文件由主对话维护,每轮结束后追加;下一轮评审 prompt 给本文件路径,轮次计数由本文件继承。

单元与分组(实现模型在首轮实现后补实际模型 ID):U1 本机全局规则(S 组,sonnet + medium);U2 本仓 README 中英(O 组,opus + medium);U3 本仓三个 workflow 插件的模板、whats-next、scaffold 与版本号(S 组,sonnet + medium);U4 dev-toolkit(O 组,opus + medium);U5 huake 两个工具包(S 组,sonnet + medium)。评审三组,每组 2 个互不可见的 opus + medium 盲审:公开面(U2 + U3)、本机与 dev-toolkit(U1 + U4)、huake(U5)。裁决轮按本批的新规则用主对话当前的模型(Fable)+ high。本批不属于规则 3 的高风险类别。

执行:2026-10-03 本机 10 核,开跑前 1 分钟负载 7.3(超过 70%,未超核数),实现与盲审都按并发 2 分批跑。

实现模型(取自 Workflow 进度的 model 字段):U1 claude-sonnet-5-5(S);U2 claude-opus-5-5(O);U3 claude-sonnet-5-5(S);U4 claude-opus-5-5(O);U5 claude-sonnet-5-5(S),都是 medium。首个提交:本仓 U3 c359cbc、U2 8a67151;dev-toolkit U4 e1242d6;huake Claude 版 9b45a06、Codex 版 cb0c76e;U1 是本机文件,不在 git 里。


## 第 1 轮 盲审 — 公开面(U2 + U3)(claude-opus-5-5,medium,2 个)

| # | 严重度 | 位置 | 评审者 | 发现 |
|---|---|---|---|---|
| P1 | P1 | README.zh-CN.md:345 | A、B | 第九节 whats-next 判断表里漏改一句旧说法:「最新 spec 尚未实现 \| 用 ultracode 直接从该 spec 实现;spec 是否已获批准拿不准时先问一句」。这违反要素 8、9 和 AC6:应改成「Progress 或 spec 里记着被用户喊停的除外,那种先问一句」。它也和本次新写的七.2、七.6(写完 spec 不等批准)直接矛盾。插件里的 whats-next 已经改了,README 里描述它的这一节没跟着改,两边口径不一致。 |
| P2 | P1 | README.md:344 | A、B | Section 9 的 whats-next 表仍写 "if unsure whether the spec has been approved, ask first",和 workflow-en whats-next 的新句("unless Progress or the spec records that the user called a halt — in that case ask first")不一致,违反要素 8、9、12 与 AC6。实现者自报 "README.md 搜 approved 0 次" 不对:第 344 行命中 approved。 |
| P3 | P2 | plugins/workflow-en/skills/scaffold/templates/CLAUDE.md.tmpl:102 | A、B | 新加的例外括注用 "the adjudication round's `model`",同一文件第 112、117、120 行都叫 "verdict round"。同一个轮次在一个文件里出现两个名字,读者可能以为是两种轮次;README.md 统一用了 verdict round,这里应当一致。 |
| P4 | P2 | README.zh-CN.md:216 | A、B | 「常规实现(`sonnet`)与所有评审(`opus`)照旧加载 CLAUDE.md」仍把全部评审标成 `opus`,和要素 5(不再把裁决轮写死成 opus)有轻微冲突;README.md 第 215 行 "all review (`opus`) agents" 同样。这句的本意是讲加载 CLAUDE.md,不是定模型,所以列 P2。可改成「所有评审」或「评审(盲审、续挖 `opus`)」。全局规则的同义句是否一起改,交裁决轮决定。 |
| P5 | P2 | plugins/workflow/skills/scaffold/templates/CLAUDE.md.tmpl:119 | A、B | 「每个写入单元后面挂一个 opus 评审 stage」:同一模板里写明裁决轮在同一个评审 stage 内顺序跑,所以「opus 评审 stage」字面上把裁决轮也包进了 opus,和要素 5 有轻微冲突。workflow-en 同一行 "Attach an opus review stage" 同样,README.zh-CN.md 第 157 行流程图「opus 逐单元评审」也有这种口径残留。 |
| P6 | P1/P2,conflict | plugins/workflow/skills/scaffold/templates/CLAUDE.md.tmpl:97 | A、B | 脚手架模板第 7 节只把「获批后」改成了「写入后」,没有落实要素 6:小改动(bounded 路径)也写小 spec、写完直接实现,不等用户确认。用这个模板铺出的项目里,CLAUDE.md 没有任何一句覆盖 brainstorming 的 bounded 路径和 HARD-GATE,小改动仍会按 brainstorming 的默认做法:不写 spec,停下来等批准,和用户第 2 条决定相违。同一个插件的 scaffold/SKILL.md 第 162 行汇报句却已经写了「小改动也写一份小 spec,写完直接做」,铺出的 CLAUDE.md 和铺设时的汇报说法不一致。英文模板 plugins/workflow-en/skills/scaffold/templates/CLAUDE.md.tmpl 第 96-99 行同样缺这条。 |
| P7 | P2 | README.zh-CN.md:302 | A | 七.7「用户明确点名要 … / 并行分派时,按点名的方式执行」紧挨着新的七.6(覆盖 dispatching-parallel-agents:并行派活一律走 Workflow)。作为用户点名时的例外可以说得通,但「并行分派」到底指什么没写清,读起来像和第 3 条决定「统一走workflow」并存的旧出口。README.md 第 301 行 "parallel dispatch" 同样。建议注明它指用户本次明确点名的情况。 |
| P8 | P2 | README.zh-CN.md:157 | B | 「使用方式」流程图里写着「sonnet 并行实现(TDD)+ opus 逐单元评审」,把整条评审链都标成 opus,裁决轮新规则没有体现。README.md 的流程图里对应的一行同样。属于泛指,严重度低。 |
| P9 | P2 | plugins/workflow-en/skills/whats-next/SKILL.md:28 | B | 新句子「Use ultracode ... to implement directly from that spec; unless Progress or the spec records that the user called a halt — in that case ask first」:分号后面单独跟一个 unless 从句,语法上悬空。改成「..., unless ...」或「Exception: ...」更通顺。 |
| P10 | P2 | README.zh-CN.md:225 | B | 第四节标题仍是「批量活走 Workflow,不走裸 Agent」,正文已扩成「批量与并行任务一律走 Workflow」,标题比正文窄。仓库里没有指向这个锚点的链接,改标题不会断链。README.md 第 224 行同样。 |

复核过的检查点:评审 A 14 条、评审 B 14 条(原文见本次 Workflow 的运行记录)。


## 第 1 轮 盲审 — 本机与 dev-toolkit(U1 + U4)(claude-opus-5-5,medium,2 个)

| # | 严重度 | 位置 | 评审者 | 发现 |
|---|---|---|---|---|
| Q1 | P1 | dev-toolkit:plugins/dev-toolkit/skills/stellark-workflow/SKILL.md:94 | A、B | 核心 SKILL.md 的七.6 覆盖段没有改,还是只写「覆盖 brainstorming 结束后唯一可 invoke writing-plans 的规定」。要素 7(点名四处:User Review Gate、bounded 路径停下等批准、HARD-GATE 等)和要素 11(点名 superpowers:dispatching-parallel-agents)都没落实。实际被加载的是这个核心文件,而不是 WORKFLOW.md。七.2 新加了「小改动(bounded 路径)也写小 spec,写完直接做」,七.6 却明确把覆盖范围限定在 writing-plans,读的人会认为 brainstorming 的 HARD-GATE(bounded 必须 STOP 等 explicit yes)仍然有效,两句互相矛盾。另外,本文件的镜像源 WORKFLOW.md:101 已经改成四处覆盖,核心与镜像源对不上。spec 第 5 节要求「做不到不增加就停下报数字」,实现者却没有停下报数字,而是直接跳过了这两条要素。 |
| Q2 | P1 | dev-toolkit:plugins/dev-toolkit/skills/stellark-parallel-do/SKILL.md:38 | A、B | 同一文件里前后说法矛盾(要素 4、12)。第 39 行写「`model`/`effort` 每个 stage 都必须显式写,不许省略」,第 61 行写「本插件口径优先:model/effort 每 stage 显式写」;而相隔 13 行的档位表第 52 行已改成裁决轮「脚本里省略`model`」。两处都没注明裁决轮例外。按第 39 行,写裁决 stage 时会把 model 写死;要是照惯性写 'opus',这一面就又回到了旧规则。spec 第 2 节限定的只是「示例脚本里每个单元挂一个评审」的写法,并没有禁止给这条硬规则加例外说明。 |
| Q3 | P1/P2,conflict | dev-toolkit:plugins/dev-toolkit/skills/stellark-workflow/SKILL.md:21 | A、B | 为了让 token 不增加,核心删了 5 处不在规范文本里的内容:§一主对话职责列表里的「评审裁决、」、§二裁决轮行的「链的最后一轮;」、三.3 括注里的「fable `high`」、七.4 开头的「(拆分与并行调度可调用 `stellark-parallel-do`)」、七.4 评审链括注里的 `opus`。这违反 spec 第 3 节「规范文本之外的句子不动」,也不符合第 5 节「做不到不增加就停下报数字,不硬塞」。删掉「评审裁决」改变了主对话的职责含义:第 19 行同一节仍写着「主对话只读差异裁决」,第 16 行仍写着「汇总与冲突裁决」,第 21 行却不再把评审裁决列为主对话的事,三处说法对不上。(改动前 6534.0,改动后 6533.43,139 行不变,已亲自用 c1-map.md 的公式量过。) |
| Q4 | P2 | dev-toolkit:plugins/dev-toolkit/skills/stellark-workflow/SKILL.md:50 | A | §四「每个 `agent()` 按档位表显式写 `model`+`effort`」没有注明裁决轮的 model 例外。WORKFLOW.md:49 同一句已经加了「(裁决轮例外:省略 `model`,继承主会话模型」,核心和上游写法不一致;要素 4 只能靠「按档位表」间接成立。 |
| Q5 | P2 | dev-toolkit:plugins/dev-toolkit/skills/driving-codex/SKILL.md:68 | A | 「`high` for the verdict round and security verdicts」仍然暗示 codex 会跑裁决轮,和第 109 行刚改的「the verdict round, run on the main conversation's current model」矛盾(要素 12)。这句不是盲审的外部 CLI 写法,不在 spec 第 2 节的保留范围内。 |
| Q6 | P2 | dev-toolkit:plugins/dev-toolkit/skills/stellark-parallel-do/SKILL.md:11 | A | 三层分工句「评审=`opus` agent,核对实现、找 bug、判定验收」,和全局分工表评审行的新写法(盲审、续挖用 opus;裁决轮用主对话当前的模型)不一致,判定验收仍写死给 opus,和第 52 行新改的裁决轮那一格相违(要素 5、12;spec 第 2 节限定了 parallel-do 的改动范围,所以记 P2)。 |
| Q7 | P2 | dev-toolkit:plugins/dev-toolkit/skills/stellark-scaffold/templates/CLAUDE.md.tmpl:99 | A、B | 模板 §7 只把「经用户批准后」改成了「写入后」,没加「小改动(bounded)也写小 spec、写完直接做」(要素 6),也没写覆盖 brainstorming bounded 路径和 HARD-GATE 的说明(要素 7)。用这个模板搭出来的项目,如果没加载全局规则或 stellark-workflow,bounded 改动仍会按 brainstorming 的原样停下等批准。实现者解释说这几条要素没分给模板,但 AC1 写的是「各自适用的面」,模板算不算适用面没有说清,需要裁决。 |
| Q8 | P2 | ~/.claude/CLAUDE.md:43 | B | 新括注「(裁决轮例外:省略 `model`,继承主会话模型。)」后面紧跟的旧半句是「省略 `model` 继承主会话的 Fable、不会落到 opus」,把继承结果写死成 Fable。主对话换成 Opus 时,这半句与第 34 行「是 Opus 就由 Opus 裁决」的例子相冲突,容易被读成裁决轮永远是 Fable。第 3 行标题「Opus 评审」也是同类问题:没说裁决轮按主对话模型走。这两句都不在规范文本内,所以记为 P2,建议改成「继承主会话当前的模型」。 |
| Q9 | P2 | dev-toolkit:WORKFLOW.md:102 | B | 紧挨着新覆盖段(第 101 行,「也覆盖 superpowers:dispatching-parallel-agents…不在一条回复里平行派裸子代理」)的第 102 行写着「用户明确点名要 … / 并行分派时,按点名的方式执行」,核心 SKILL.md:95 也是一样。全局规则第 59 行对应的位置写的是 parallel-do,而 parallel-do 本身走 Workflow。dev-toolkit 写的「并行分派」很容易被读成点名 dispatching-parallel-agents,也就是允许平行派裸子代理,与「统一走 workflow」的边界不清。建议写明指的是 stellark-parallel-do,或者写明用户点名 dispatching-parallel-agents 时属于例外。 |
| Q10 | P2 | dev-toolkit:WORKFLOW.md:147 | B | 按 upstream-map,WORKFLOW.md 是 kit README.zh-CN.md 的镜像。WORKFLOW.md 第 147 行的 whats-next 表已按要素 9 改成「被用户喊停的除外」,kit README.zh-CN.md:345 却还是「spec 是否已获批准拿不准时先问一句」,镜像两边现在不一致。毛病在 U2 那边,这里记下来,方便裁决时统一。 |
| Q11 | P2 | ~/.claude/CLAUDE.md:57 | B | 覆盖段点名了 HARD-GATE、bounded 停下等批准和 User Review Gate,但 brainstorming SKILL.md(6.4.1)另有一节「Anti-Pattern: Too Simple To Need Approval」(第 90~104 行),内容包括「Every path ends with … approving」和「Present, then stop until you hear yes」,也是要求先批准再实现,覆盖段没有点名这一节。模型可能拿这一节当理由,继续在 bounded 路径上停下等批准。这是 spec 3.2 规范文本本身的缺口,WORKFLOW.md:101 也一样;建议加一句「含其 Anti-Pattern 一节与理由表」。 |
| Q12 | P2 | ~/.claude/CLAUDE.md:36 | B | 规则 4 的打回率统计和「评审模型换代时基线清零重采」默认评审模型固定不变。现在裁决轮的模型跟着各会话的主对话变(Fable 或 Opus),同一批单元的裁决可能由不同模型给出,而提交正文只记「实现模型」,不记裁决模型,按评审模型分段统计就做不到了。不在本批规范范围内,作为遗留记录。 |

复核过的检查点:评审 A 14 条、评审 B 14 条(原文见本次 Workflow 的运行记录)。


## 第 1 轮 盲审 — huake(U5)(claude-opus-5-5,medium,2 个)

| # | 严重度 | 位置 | 评审者 | 发现 |
|---|---|---|---|---|
| H1 | P1 | huake-claude:README.md:71 | A、B | Claude 版 README 第 71 行还写着「本插件的开发流程(brainstorming → spec 获批 → ultracode 直接实现)」,和改过的模板与 SKILL 里的「spec 写入后直接实现」矛盾,违反要素 8 和 12,AC6 搜「获批」时会命中这一处,而且它和本批有关。实现者以「README 不在点名文件内」为由没有改。这句要么一起改成「spec 写入 → ultracode 直接实现」,要么由主对话明确接受它暂时留着。 |
| H2 | P2 | huake-claude:plugins/claude-toolkit-engineer/skills/parallel-do/SKILL.md:89 | A、B | 示例脚本里的评审 stage 现在省略了 model(按注释,它是裁决轮,用主对话当前的模型),但第 89 行「每个写入子任务后面必须挂一个 opus 评审 stage」、第 101 行「sonnet 实现 → opus 评审」流水线,以及第 164 行「逐单元评审已经在 workflow 里由 opus agent 做完了」都还说评审由 opus 做,和示例代码不一致(要素 12)。CLAUDE.md.tmpl 第 121 行「每个写入单元后面挂一个 opus 评审 stage」也是同样问题。建议改成「挂一条评审链」,或者括注写明盲审与续挖用 opus、裁决轮用主对话当前的模型。 |
| H3 | P1/P2,conflict | huake-claude:README.md:209 | A、B | 版本号没完全按惯例来。git log 显示两个仓以往每次规则同步都在升 plugin.json 的同一个提交里,往 README 版本说明区加一行「0.x.0 起…(镜像 kit 日期)」,例如 Claude 版 006a912 / 00d28a8,Codex 版 16785aa / 653985a。这次只升了 plugin.json(0.26.0 / 0.14.0),两个 README 都没加 0.26.0 / 0.14.0 的说明行,所以版本号对应改了什么无处可查。Codex 版的对应位置在 huake-codex:README.md 第 83 行之后。 |
| H4 | P1 | huake-claude:plugins/claude-toolkit-engineer/skills/parallel-do/SKILL.md:167 | B | 「修完仍挂 `model: 'opus', effort: 'high'` 复审」没改,还是旧的裁决轮写法。按现在的分流规则,修完 P1 后下一轮是裁决轮(主对话当前的模型 + high),修完 P0 后是续挖轮(opus + medium),opus + high 这个组合两边都对不上。这正是要素 5、12 要清掉的「把裁决轮写死成 opus」的说法,而且和同文件第 80 行、第 87 行的新句矛盾。 |
| H5 | P2 | huake-claude:plugins/claude-toolkit-engineer/skills/scaffold/templates/CLAUDE.md.tmpl:121 | B | 模板里「每个写入单元后面挂一个 opus 评审 stage」没改。它和同一节第 113、119、122 行「裁决轮用主对话当前的模型」放在一起会有歧义(要素 12)。 |
| H6 | P2 | huake-claude:plugins/claude-toolkit-engineer/skills/scaffold/templates/CLAUDE.md.tmpl:97 | B | 生成的项目 CLAUDE.md 是以后会话真正读的规则,但「小改动也写小 spec、写完直接做、不等确认」和覆盖 brainstorming 的 bounded 路径 / HARD-GATE / dispatching-parallel-agents 这几句(要素 6、7、11),在模板里一句都没有,只出现在 scaffold 落盘时给用户的那次汇报里。结果是用这个模板的项目走 bounded 路径时,brainstorming 照样会停下等批准。kit 自己的 workflow 模板也没加,口径是一致的(spec 3.2 对模板只要求改措辞);这条列出来,由主对话判断压缩面要不要补一句。 |

复核过的检查点:评审 A 12 条、评审 B 14 条(原文见本次 Workflow 的运行记录)。

### 第 1 轮分流(主对话)

- 三组都有 P1、没有 P0 → 修复后跑裁决轮。裁决轮按本批的新规则用主对话当前的模型(Fable)+ high。
- 修复内容写进 spec 3.4(a ~ m)。漏改与口径残留(P1、P2、P3、P5、Q2、Q5、Q6、H1、H2、H4、H5 等)直接修;两条 spec 没说清的也定了:脚手架模板加一条「小改动也写小 spec」(P6 / Q7 / H6);dev-toolkit 核心 skill 的覆盖句用压缩版,token 只许不增加,做不到就停下报数字(Q1、Q3)。
- 记为遗留、不在本批改:裁决轮模型跟着主对话变之后,规则 4 按评审模型分段统计打回率做不到了(全局规则第 36 行,Q 组 B 评审提出)——提交正文目前只记实现模型;主对话是 Opus 且外部 CLI 不可用时,dev-toolkit 的三轮都会是 opus,「不许只用 opus 单一模型」做不到(Q4)——属于盲审怎么组成的问题,Tony 还没定。
- 修复轮的档位:U2、U4、U5 的 P1 里有实现时漏改或没按要求停下的,按「退回重跑升 high」;U1、U3 的修复来自 spec 没说清,维持 medium。
