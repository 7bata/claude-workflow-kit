# Decision Log — claude-workflow-kit

> 条目格式:`## 日期 - 类型(域): 标题` + What/Why/Changes,最新在上。由 `docs/DECISIONS.inbox.md` 的问答草稿消化而来;日常小决定与过程性确认不进本表。

## 2026-10-05 - process(workflow): 对照 superpowers 6.4.1 后改四处,其余不吸收

- **What**:①七.6 点名 6.4.1 重写后的 HARD-GATE 整段,spec 写入就是对其后全部阶段的授权;②多个单元并行实现时实现 agent 只跑定向用例,全量由主对话按顺序跑(优先于 TDD skill 的收尾全量要求);③评审判据加一句:spec 没写到的行为按使用者的合理预期判;④spec 必备内容加一节「容易漏的输入与失败情形」。
- **Why**:6.4.1 新增的几句与「spec 写完直接实现」正面相反,新版 TDD 会让并行的实现 agent 同时各跑一遍全量——这两处以本规则为准(Tony:「按照我们自己workflow的规则」)。③④是 6.4.1 里 Tony 认为值得吸收的两条;其余做法(评审结果加「搁置不判的事项」等)Tony 定不加。
- **Changes**:README 中英、三份脚手架模板(workflow/-en 0.18.0,codex 0.17.0);镜像到本机全局规则与内部的几处副本。见 Progress 2026-10-05。

## 2026-10-03 - process(review): 裁决轮改回固定用 opus

- **What**:评审链的裁决轮固定 `opus` + `high`,脚本里显式写 `model: 'opus'`;不再用「主对话当前的模型」。提交正文的「裁决模型」一行保留。
- **Why**:主对话用最高档模型时,每个单元的裁决都落在它上面,消耗太大(Tony 2026-10-03 定;「用主对话当前的模型」只实行了不到一天)。保留「裁决模型」一行是因为 `opus` 别名解析到哪一代由服务端决定,换代仍要看得出来。
- **Changes**:README 中英、workflow 与 workflow-en 的脚手架模板(0.17.0);镜像到本机全局规则与内部的几处副本。见 Progress 2026-10-03。

## 2026-10-03 - process(test): 并发前看 CPU 占用,负载平均值只作退回

- **What**:并行之前判断机器忙不忙,改看实际 CPU 占用(1 秒采样,取最后一条 CPU 行):超过 70% 并发减半,超过 90% 或可用内存低于 20% 串行。`uptime` 的负载平均值只在取不到 CPU 读数时使用。
- **Why**:负载平均值数的是排队的任务。实测一台 10 核、600 多个进程的机器,负载平均值约 10 时 CPU 实际占用只有 43%~53%,按「负载超过核数就串行」会把半闲的机器判成跑满。
- **Changes**:README 中英、三份脚手架模板、两份 mechanical 定义、codex 的 parallel-do(workflow/-en 0.17.0,codex 0.16.0);镜像到本机全局规则与内部的几处副本。见 Progress 2026-10-03。

## 2026-10-03 - docs(public): 本仓的记录文档只用中性叫法

- **What**:`docs/` 里不出现内部域名、内网地址、带用户名的本机路径、组名、同事的名字、内部工具包与内部项目的名字;要提到时用「内部工具包」「内部项目管理系统」「某内部项目」「同事」这类叫法。只涉及内部的批次,细节记在内部仓库。
- **Why**:本仓是公开仓库,`docs/` 也是公开的;这些名字对公开读者没有用处。
- **Changes**:`docs/` 下约 30 个文件;README 与 `plugins/` 无改动;提交历史不改写。见 Progress 2026-10-03。

## 2026-10-03 - tooling(mods): Claude Code mods 相关的工具不进公开 kit

- **What**:基于 Claude Code mods(插件里的 TypeScript 钩子模块,2.1.287 起)做的工具只在内部使用,公开 kit 不放;现有 shell 钩子不改写成 mod。
- **Why**:mods 的接口还在早期阶段,官方资料写明每个版本都可能变;公开 kit 要对更宽的版本范围保持可用。
- **Changes**:本仓无改动;细节记在内部仓库。

## 2026-10-03 - process(review): 提交里加记裁决模型

- **What**:跑过裁决轮的单元,首个提交正文再记一行「裁决模型:<裁决轮实际运行的模型 ID>」,评审基线按它分段。
- **Why**:裁决轮改成跟随主对话的模型后,提交里只记实现模型,评审模型换代时分不出基线。Tony 2026-10-03:「加上」。
- **Changes**:README zh/en 规则 4;镜像到本机全局规则与内部工具包。没定的:盲审直接通过的单元没有裁决模型行,要不要再记盲审模型。见 Progress 2026-10-03「提交里加记裁决模型」。同一批里内部工具包的评审链也做了调整,记录在内部仓库。

## 2026-10-03 - process(review): 裁决轮用主对话当前的模型;小改动也写小 spec、写完直接实现;批量与并行任务一律走 Workflow

- **What**:① 评审链最后一轮裁决不再写死 `opus`,改用主对话当前的模型(Workflow 脚本里这一个 stage 省略 `model`,`effort: 'high'`);盲审与续挖仍是 `opus` + `medium`。② brainstorming 的小改动(bounded)路径也写一份小 spec(几段即可),写完直接实现,不在对话里等用户说 yes;覆盖段逐个点名 brainstorming 里要等批准的四处,spike 路径照原样。③ 批量与并行任务一律走 Workflow,不在一条回复里平行派裸子代理;单个子代理的一次性委派不在此列。
- **Why**:2026-10-02 prompt 审计报出三处跨文件说法不一——评审由谁裁决(全局规则写 opus,内部工作流 skill 写 fable 子代理加外部 CLI)、小改动要不要写 spec 与等批准(superpowers 6.3.0 把 brainstorming 分成三条路径、每条都要先获批准,和「spec 写入即授权」的直通流程冲突)、并行派活用裸子代理还是 Workflow。Tony 2026-10-03 逐条拍板:「按照当前这个对话model来当评审裁决」「小改动就写一个小的spec,但是这个就不用让我看了,直接写spec就直接开干」「统一走workflow」。只把裁决轮改成跟随主对话(盲审、续挖不动)是主对话对第 1 条的理解,动手前已告诉 Tony。
- **Changes**:README zh/en、三份脚手架模板、whats-next、scaffold(workflow/-en 0.16.0,codex 0.15.0);镜像到本机全局 CLAUDE.md、内部工具包、内部工作站 两个工具包。没定的:裁决轮模型随会话变后按评审模型分段统计怎么做;内部工作流 skill 的盲审要不要保留外部 CLI。见 Progress 2026-10-03。

## 2026-09-28 - process(tiers): Sonnet 5.5 换代——本机把 sonnet 别名钉到 5.5;机械与 low 档 stage 加验证要求;规则 4 补实现模型分段;对照实验 S 组改 medium

- **What**:① 本机 settings.json 加 env `ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-5-5`(本机设置,不进公开 kit;官方把别名切到 5.5 或出下一代时删,已登记复查)。② mechanical 子代理定义自带验证要求(改完跑真实检查、结论来自本次工具输出、范围内做完再报告);不走 mechanical 的 sonnet+low stage 在派工说明里写同样要求。③ 规则 4:实现模型换代按实现模型分段统计、可以跨代比较,每单元首个提交正文记「实现模型:」行(取实际模型 ID,不记别名);评审模型换代才清零、不跨代比较。④ 对照实验改为 sonnet+medium 对 opus+medium,从下一批重新计数,Sonnet 5 那批单独留作参考。
- **Why**:Tony 2026-09-28「更新sonnet 5.5了，你看一下workflow里面需不需要更新」。核查(盲审 2 + 裁决 1):规则只写别名不用改字,但 Claude Code 2.1.284 的 `sonnet` 别名实测仍解析到 claude-sonnet-5(服务端配置);5.5 与 5 同价,官方称 5.5 medium 多数编码评测胜过 5 high、成本不到五分之一,但 low 档可能不跑验证就报告完成、可能凭记忆作答;effort 档位重新标定;cyber/frontier_llm 拒答会自动回落到 Sonnet 5 重跑,按别名记模型会失准。三个选项里 Tony 选全局环境变量、A/B/C 全做、S 组改 medium。
- **Changes**:本机 ~/.claude/settings.json 与全局 CLAUDE.md(规则 4、实验行);kit workflow/-en mechanical 定义与 README zh/en(0.13.1,顺带修英文版计数命令 `^review round`);内部工具包 mechanical 定义、内部版-workflow、内部版-parallel-do、scaffold 模板、WORKFLOW.md;内部工作站工具包(Claude 版) parallel-do 与 scaffold 模板(0.24.1)。见 Progress 2026-09-28。

## 2026-09-25 - process(research): 登录相关默认复用组织通用登录库,不进调研与选型(只进私有面;公开 kit 同日撤回)

- **What**:登录/注册、登出、改密/找回密码、会话与令牌、第三方登录、验证码登录、鉴权中间件、登录页等,组织内已有通用登录库的一律直接复用(私有面固定为内部登录库),任何规模都适用,视为 §八 第 0 步已经定下的结果:不调研、不选型、不与外部开源一起比较,Prior art 直接写复用;实现只做接入,不在项目里重写用户表、密码哈希、令牌签发;库缺的能力、语言形态不匹配、存量项目要不要迁都先问用户;用户本次明确要求换方案或自研才例外,原因进 spec;复用后照样登记组件索引的 used_by,接入单元评审仍按三.3 走。
- **Why**:Tony 2026-09-25 拍板「凡是和登录相关的,如果我没特殊要求,直接复用〔内部登录库〕这个仓库」。登录是每个项目都会碰到的通用件,逐项目调研、选型、自研是重复劳动,安全实现质量也随项目波动;该登录库的立项目的就是集中一处、修一次全体受益。
- **Changes**:全局 CLAUDE.md、本机 github-research skill 第 0 步、内部工具包(WORKFLOW.md + 内部版-workflow 核心与 references,1.5.2)。README zh/en §八/§8 曾同日加入,Tony 当天要求「公开的 kit 不要加」,已恢复原文,公开 kit 不带这条。见 Progress 2026-09-25 两条。

## 2026-09-22 - process(review): 评审编排改为「盲审起步 + 接力续挖 + 裁决收尾」;换代后第一批实现做起跑档对照实验

- **What**:评审不再平行投票,也不是纯链式:首轮 2 个(高风险单元 3 个)互不可见的盲审平行发现、不数票、脚本按 file+line 归并并标 conflict;之后每轮一个 agent 带前面各轮全部发现、先推翻再找漏、换没用过的镜头;链末裁决轮 opus+high,盲审与续挖 medium;分流表与 4 轮上限;修复在评审 stage 外做,链状态落 `docs/reviews/<单元>-chain.md`。同日拍板:Opus 5.5 换代后第一批实现做分组对照(一半 sonnet+high、一半 opus+medium),按组比退回率与 token 再改档位表,实验前起跑档不动。
- **Why**:Tony 先要"一个 agent 评审完、下一个带着前一个的问题继续挖,而不是投票",再问能否同时避开链式(锚定、首轮跑偏)与投票(重复、不能翻案、数票)的短板;三个候选(A 盲审起步 + 接力续挖 / B 每轮先盲后看 / C 纯链式 + 对抗立场)选 A——独立只用于发现,继承只用于深挖与翻案,全程不数票。起跑档:换代前两个项目退回率 46% / 83% 超过规则 4 的 30% 线,但旧数据不跨代比较,所以用一次对照实验产生 5.5 时代的数据。
- **Changes**:README zh/en 二/三/七节、workflow/-en/codex 三份脚手架模板、codex parallel-do §6(kit 0.13.0);镜像到全局 CLAUDE.md、内部工具包、内部工作站 两个 engineer 插件。见 Progress 2026-09-22。

## 2026-09-19 - process(workflow): omitClaudeMd 只用在纯机械 stage;AGENTS.md 本批不做

- **What**:`mechanical` 子代理类型(`omitClaudeMd: true`)只用于定位/清单/盘点与批量迁移/重命名/模板化改码两类纯机械 stage,常规实现与全部评审照旧加载 CLAUDE.md;scaffold 本批不生成 AGENTS.md。
- **Why**:省 token 只在不需要项目约定的机械活上安全;评审与实现依赖 CLAUDE.md 的硬规则。AGENTS.md 三种形态(指向 CLAUDE.md / 双份同步 / 按需生成)当时都没有明确需求,按 YAGNI 不做。
- **Changes**:workflow/-en 0.12.0(mechanical agent + 并发上限文档)。见 Progress 2026-09-19。
