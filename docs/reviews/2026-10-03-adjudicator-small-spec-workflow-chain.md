# 评审链:裁决轮用主对话模型 + 小改动也写小 spec 直接开干 + 并行派活统一走 Workflow

spec:`docs/superpowers/specs/2026-10-03-adjudicator-model-small-spec-workflow-dispatch-design.md`。本文件由主对话维护,每轮结束后追加;下一轮评审 prompt 给本文件路径,轮次计数由本文件继承。

单元与分组(实现模型在首轮实现后补实际模型 ID):U1 本机全局规则(S 组,sonnet + medium);U2 本仓 README 中英(O 组,opus + medium);U3 本仓三个 workflow 插件的模板、whats-next、scaffold 与版本号(S 组,sonnet + medium);U4 内部工具包(O 组,opus + medium);U5 内部工作站 两个工具包(S 组,sonnet + medium)。评审三组,每组 2 个互不可见的 opus + medium 盲审:公开面(U2 + U3)、本机与 内部工具包(U1 + U4)、内部工作站(U5)。裁决轮按本批的新规则用主对话当前的模型(Fable)+ high。本批不属于规则 3 的高风险类别。

执行:2026-10-03 本机 10 核,开跑前 1 分钟负载 7.3(超过 70%,未超核数),实现与盲审都按并发 2 分批跑。

实现模型(取自 Workflow 进度的 model 字段):U1 claude-sonnet-5-5(S);U2 claude-opus-5-5(O);U3 claude-sonnet-5-5(S);U4 claude-opus-5-5(O);U5 claude-sonnet-5-5(S),都是 medium。首个提交:本仓 U3 c359cbc、U2 8a67151;内部工具包 U4 e1242d6;内部工作站 Claude 版 9b45a06、Codex 版 cb0c76e;U1 是本机文件,不在 git 里。


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


## 第 1 轮 盲审 — 本机与内部的几处副本(U1 + U4、U5)(claude-opus-5-5,medium,各 2 个)

这两组的发现明细不在本仓,记录在内部仓库(Q1~Q12 是 U1 + U4 组的发现编号,H1~H6 是 U5 组的,下文沿用)。结论见下面的分流:两组都有 P1、没有 P0。

### 第 1 轮分流(主对话)

- 三组都有 P1、没有 P0 → 修复后跑裁决轮。裁决轮按本批的新规则用主对话当前的模型(Fable)+ high。
- 修复内容写进 spec 3.4(a ~ m)。漏改与口径残留(P1、P2、P3、P5、Q2、Q5、Q6、H1、H2、H4、H5 等)直接修;两条 spec 没说清的也定了:脚手架模板加一条「小改动也写小 spec」(P6 / Q7 / H6);内部工具包 核心 skill 的覆盖句用压缩版,token 只许不增加,做不到就停下报数字(Q1、Q3)。
- 记为遗留、不在本批改:裁决轮模型跟着主对话变之后,规则 4 按评审模型分段统计打回率做不到了(全局规则第 36 行,Q 组 B 评审提出)——提交正文目前只记实现模型;主对话是 Opus 且外部 CLI 不可用时,内部工具包 的三轮都会是 opus,「不许只用 opus 单一模型」做不到(Q4)——属于盲审怎么组成的问题,Tony 还没定。
- 修复轮的档位:U2、U4、U5 的 P1 里有实现时漏改或没按要求停下的,按「退回重跑升 high」;U1、U3 的修复来自 spec 没说清,维持 medium。


## 第 2 轮 修复 + 独立测试 + 裁决(2026-10-03)

执行:开跑前 1 分钟负载 10.0(等于核数),全程串行。修复:U2、U4 claude-opus-5-5 + high;U5 claude-sonnet-5-5 + high;U3、U1 claude-sonnet-5-5 + medium。独立测试:claude-sonnet-5-5 + medium。裁决:三个都省略 model,实际运行在 claude-fable-5-1(主对话当前的模型)+ high——本批新规则的第一次实际使用,继承成立。提交:本仓 f16ecbd(squash 到 8a67151)、d73bb55(squash 到 c359cbc);内部工具包 b7b48ea(squash 到 e1242d6);内部工作站 Claude 版 115681e、Codex 版 6bc71bb。

**独立测试**:T1 通过、T2 通过、T3 通过、T4 通过、T5 未通过、T6 通过、T7 通过、T8 通过、T9 未通过。未通过的两项都指向同一件事:内部工具包 核心 SKILL.md 的 3.4(k) 没有落实(修复 agent 因 token 上限停下并把核心恢复原状)。


**裁决 — 公开面(U2 + U3)**

| # | 成立 | 最终严重度 | 闭合 |
|---|---|---|---|
| P1 | 是 | P1 | 已闭合 |
| P2 | 是 | P1 | 已闭合 |
| P3 | 是 | P2 | 已闭合 |
| P4 | 是 | P2 | 已闭合 |
| P5 | 是 | P2 | 已闭合 |
| P6 | 是 | P1 | 已闭合 |
| P7 | 是 | P2 | 已闭合 |
| P8 | 是 | P2 | 已闭合 |
| P9 | 是 | P2 | 已闭合 |
| P10 | 是 | P2 | 已闭合 |

新发现:
- [P2] plugins/workflow-en/skills/scaffold/templates/CLAUDE.md.tmpl:103 —— 修复轮把主对话职责句里的 "conflict adjudication" 改成了 "conflict resolution"(main 上是 adjudication)。这句不是轮次名,不在 3.4(d) 范围内,违反「规范文本之外的句子不动」;README.md:195 同一句仍是 "conflict adjudication",两个英文面现在用词不一致。含义没变,建议改回,或记为遗留。
- [P2] plugins/workflow/skills/scaffold/templates/CLAUDE.md.tmpl:103 —— 多代理分工一条的标题仍是「ultracode 及其他并行分派一律照此」(英文模板同一行 "ultracode and any other parallel dispatch"),与同一条末尾「批量与并行任务一律走 Workflow 编排」并排,读起来像 Workflow 之外还有别的并行分派。P7 在 README 去掉了同类字眼,模板这里没跟着改。旧句,不改变行为,建议改成「Workflow 并行派活一律照此」或记为遗留。
- [P2] plugins/workflow/skills/scaffold/templates/CLAUDE.md.tmpl:120 —— 新括注后面紧跟原有括注,成了「评审 stage(…裁决轮用主对话当前的模型)(用 `pipeline` 逐条目流过…)」两个括号相连;括注里写的是 `opus`,而同一模板别处都写 `'opus'`(带引号)。英文模板第 120 行也有同样的引号不一致。纯体例。

单元结论:U2:通过;U3:通过。

**裁决 — 本机与 内部工具包(U1 + U4)**

| # | 成立 | 最终严重度 | 闭合 |
|---|---|---|---|
| Q1 | 是 | P1 | 未闭合 |
| Q2 | 是 | P1 | 已闭合 |
| Q3 | 是 | P1 | 未闭合 |
| Q4 | 是 | P2 | 未闭合 |
| Q5 | 是 | P2 | 已闭合 |
| Q6 | 是 | P2 | 已闭合 |
| Q7 | 是 | P2 | 已闭合 |
| Q8 | 是 | P2 | 已闭合 |
| Q9 | 是 | P2 | 未闭合 |
| Q10 | 是 | P2 | 已闭合 |
| Q11 | 是 | P2 | 已闭合 |
| Q12 | 是 | P2 | 已闭合 |

新发现:
- [P2] WORKFLOW.md:38 —— 内部工具包 的 WORKFLOW.md:38 仍写「常规实现(`sonnet`)与全部评审(`opus`)照旧加载 CLAUDE.md」。它的镜像源 kit README.zh-CN.md:216 已是「与所有评审照旧加载」,全局规则 :29 也已去掉「(`opus`)」。3.4(c) 只点名了 README 与全局规则,漏了这个镜像面;结果是同一文件里与 :21、:35 的裁决轮新写法口径不一(要素 5、12),镜像两边也不一致。独立测试 agent 的 T9 没搜到这一句。
- [P2] plugins/内部工具包/skills/driving-codex/SKILL.md:69 —— 修复轮把「`high` for the verdict round and security verdicts」整句换成「`high` for a high-risk unit's blind or dig round」,顺带去掉了安全类评审用 high 这一层。核心档位表把「安全类评审」列在 high 一行,review-chain.md 把「安全类终审」与三.3 高风险单元并列为三路到底;codex 在安全类评审的盲审位上该用哪一档现在没有写。建议写成 a high-risk unit's or a security review's blind or dig round。
- [P2] plugins/内部工具包/skills/内部版-parallel-do/SKILL.md:77 —— 示例脚本的评审 stage 仍是 `{ model: 'opus', effort: 'high', phase: '评审' }`,而 :62 现在写「评审 stage(盲审与续挖 `opus`,裁决轮用主对话当前的模型)」、:85 写修完「跑裁决轮(省略 `model`)」。opus + high 这个组合按新规则既不是盲审(medium)也不是裁决轮(省略 model),照抄骨架的人得到的是由 opus 给出通过 / 不通过的单个 stage。spec 第 2 节把示例脚本列为不覆盖,所以只记 P2;但链文件 H2 记着 内部工作站 版的示例已改成省略 model,两个仓的同一段示例现在不一样,需要主对话定一个口径。
- [P2] docs/reviews/2026-10-03-adjudicator-small-spec-workflow-chain.md:67 —— 第 1 轮分流的遗留项「主对话是 Opus 且外部 CLI 不可用时,〔内部工具包〕 的三轮都会是 opus,『不许只用 opus 单一模型』做不到」标注为 (Q4),但发现表里的 Q4 是核心 §四 缺裁决轮例外,两者不是一回事;这条遗留在表里没有对应编号。追加本轮记录时请改正编号或单列,否则 Q4 会被误读成已按遗留处理。

单元结论:U1:通过;U4:未通过。

**裁决 — 内部工作站(U5)**

| # | 成立 | 最终严重度 | 闭合 |
|---|---|---|---|
| H1 | 是 | P1 | 已闭合 |
| H2 | 是 | P2 | 已闭合 |
| H3 | 是 | P1 | 已闭合 |
| H4 | 是 | P1 | 已闭合 |
| H5 | 是 | P2 | 已闭合 |
| H6 | 是 | P2 | 已闭合 |

新发现:
- [P2] plugins/内部工作站工具包(Claude 版)/skills/parallel-do/SKILL.md:168 —— 「opus 的意见不是圣旨」仍把评审意见统称为 opus 的意见。同一节 164、167 行已写明裁决轮用主对话当前的模型,评审结论可能出自非 opus 的裁决 agent,这里的叫法偏窄(要素 12 的同类残留)。内部工具包 的对应句是「误判可驳回但要说明理由」,不带模型名。建议改成「评审的意见不是圣旨」。不影响行为,记遗留即可。
- [P2] plugins/内部工作站工具包(Claude 版)/.claude-plugin/plugin.json:2 —— 与本批改动无关的既有问题,顺带记录:claude plugin validate plugins/内部工作站工具包(Claude 版) 返回 1,报插件名以「claude-」开头属保留名(Plugin name "〔内部工作站工具包(Claude 版)〕" is reserved)。本批只改了第 3 行版本号,name 没动,origin/main 上同样会报。AC3 只针对 kit 本仓,不影响本单元结论;是否改名交主对话与 Tony 定。

单元结论:U5(内部工作站工具包 Claude 版):通过;U5(内部工作站工具包 Codex 版):通过。


### 第 2 轮分流(主对话)

- U1、U2、U3、U5 通过,新发现都是 P2,记为遗留(清单见 spec 3.5 末条)。
- U4 未通过(Q1、Q3 两条 P1 未闭合,原因是核心 token 上限)。按 spec 3.5 修:主对话已算出一组不超上限的写法(6532.0),派机械子代理照单套用,再测一次、再跑一次裁决轮。计入上限后本链到第 3 轮。
- 更正:第 1 轮分流里「主对话是 Opus 且外部 CLI 不可用时,〔内部工具包〕 的三轮都会是 opus」那条遗留误标成了 (Q4)。它对应的是 Q3 行里评审 B 提的那一点(「异构三方」与「不许只用 opus」在该边界情况下做不到),不是 Q4。Q4 是核心第四节缺裁决轮例外的括注,本轮裁定 P2,因 token 上限记为遗留。


## 第 3 轮 套用 + 独立测试 + 裁决 — U4(2026-10-03)

U4 是内部的一处副本,这一轮的明细不在本仓,记录在内部仓库。结论:Q1、Q3 两条 P1 已闭合,新发现只有 P2,U4 通过。

## 收尾(主对话,2026-10-03)

- 全链结论:五个单元全部通过,没有未闭合的 P0 / P1。本链共 3 轮(盲审 1 轮、裁决 2 轮),在 4 轮上限内。
- 验收条款由主对话在最终状态上重跑:AC2 全局文件与备份都是 111 行,差异只在第 12、14、26、29、34、35、39、43、49、53、57 行;AC3 末行 `ALL PASSED (8 plugins)`;AC4 各仓改动文件都在第 5 节与 3.4 扩大后的范围内;AC5 核心 6534.0 → 6532.0(139 行不变);AC6 剩余命中只有引用 brainstorming 原话的三处、upstream-map 的历史说明、模板标题「其他并行分派」(遗留)与 内部工作站 README 里 parallel-do 的一句功能介绍;AC7 成立。
- 评审轮次已压进单元提交,上文各轮写的提交号是压之前的。压之后:本仓 U3 510a68f、U2 80d3fc0;内部工具包 U4 aa303e0;内部工作站 Claude 版 5b38b5a、Codex 版 ac0bdb6。U1 是本机全局规则,不在 git 里。
- token(取自三次 Workflow 运行的进度记录):实现 5 个 43.8 万;盲审 6 个 65.0 万;修复 5 个 37.7 万;独立测试 2 次 19.0 万;裁决 4 个 47.4 万;套用 0.9 万。合计约 213.7 万。
- 对照实验记录:S 组 U1、U3、U5(claude-sonnet-5-5 + medium,实现各 5.2 万、7.2 万、7.8 万 token);O 组 U2、U4(claude-opus-5-5 + medium,实现各 8.3 万、15.4 万)。五个单元都有修复轮:U3、U4 各两轮,其余各一轮。P1 里一半以上是 spec 自身的缺口或写得不清(模板要不要加小 spec 那条、内部工作站 升版要带 README 说明行、覆盖段要点名的关口);实现漏面的有 U2 第九节一行、U5 README 一句与 parallel-do 一句;U4 为守 token 上限删了不该删的内容。U4 第 2 轮修复由机械子代理(sonnet)照单套用,修复轮换过模型,按规则单列、不归组。本批是规则文字单元、没有测试,不拿来定起跑档。
- 遗留(都是 P2,已登记到 `docs/Progress.md`「待办」表 2026-10-03 的四行)。

