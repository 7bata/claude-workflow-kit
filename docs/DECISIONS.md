# Decision Log — claude-workflow-kit

> 条目格式:`## 日期 - 类型(域): 标题` + What/Why/Changes,最新在上。由 `docs/DECISIONS.inbox.md` 的问答草稿消化而来;日常小决定与过程性确认不进本表。

## 2026-10-03 - tooling(mods): workflow-guard 并进内部工具包主插件(改掉同日「只在本机用」的决定;公开 kit 仍不进)

- **What**:本机试用后,workflow-guard 并进内部工具包的主插件(1.11.0 起),所有人更新就有,五个开关默认都开;本机单独装的那份与本地市场卸掉。公开 kit 与 huake 两个工具包仍不放。
- **Why**:Tony 2026-10-03 用过之后说「我觉得mods不错,直接更新到dev-toolkit里面吧」。当初只装本机的顾虑有两条——接口还在早期阶段、出问题会不会连累原有钩子——后一条真机验证过不会(旧版本跳过 mod、mod 写坏时旧式钩子照常),前一条靠「mod 加载失败引擎会跳过它」与五个开关接住。并进主插件而不是另起一个插件,是主对话的判断:市场清单是「全员唯一工具包」,CI 自动升版只管主插件。
- **Changes**:本仓只有 spec、评审链与进度文档;代码与说明在内部工具包。见 Progress 2026-10-03「workflow-guard 并进内部工具包主插件」。

## 2026-10-03 - tooling(mods): Claude Code mods 只在本机用,第一个是 workflow-guard;不进公开 kit 与内部工具包

- **What**:Claude Code 2.1.287 起的 mods(插件里的 TypeScript 钩子模块)先只做本机用途:新建本机仓 `claude-local-mods`(本地插件市场),第一个 mod `workflow-guard` 做 Workflow 开跑前检查、输入框上方状态栏、会话结束关掉本会话自己起的起名浏览器。内置的 You should know 不动,开不开遥测由 Tony 定。现有 shell 钩子不改写成 mod。
- **Why**:mods 的接口还在早期阶段,官方资料写明每个版本都可能变,同步到四处不值得;mod 出错时引擎会跳过它继续跑,只装本机的最坏情况是少一层检查。选这两样是因为当天真实出现过:漏写档位、不带前缀的机械子代理名解析不到、机器负载超过核数、三个启动方已结束的残留浏览器进程。Tony 2026-10-03:「前两个按推荐做吧」。
- **Changes**:本仓只有 spec、评审链与进度文档;代码在本机仓。实现中定下的两条做法:会话结束事件只有约 1.5 秒,关浏览器交给放手的短命进程;没起名的默认会话全机共用,不跟踪也不关。见 Progress 2026-10-03 第三条。

## 2026-10-03 - process(review): 提交里加记裁决模型;内部工具包的评审链不再带外部 CLI

- **What**:① 跑过裁决轮的单元,首个提交正文再记一行「裁决模型:<裁决轮实际运行的模型 ID>」,评审基线按它分段。② 内部工具包的评审链去掉外部 CLI:盲审 2 个 opus(高风险单元 3 个)、默认上限 4 轮,和本仓、本机全局规则同一形态;两个外部 CLI 驱动 skill 保留,只在用户点名时用。原来带外部 CLI 的写法专用的「最多 2 条链、按链撤方」随之取消,改回 4 轮上限是主对话的判断,已告诉 Tony。
- **Why**:裁决轮改成跟随主对话的模型后,提交里只记实现模型,评审模型换代时分不出基线;主对话是 Opus 且外部 CLI 用不了时,三轮都会是 opus,「重要评审不许只用 opus 单一模型」做不到。Tony 2026-10-03:「1. 加上 2. 去掉」。
- **Changes**:README zh/en 规则 4;镜像到本机全局 CLAUDE.md 与内部工具包(1.8.0)。没定的:盲审直接通过的单元没有裁决模型行,要不要再记盲审模型。见 Progress 2026-10-03 第二条。

## 2026-10-03 - process(review): 裁决轮用主对话当前的模型;小改动也写小 spec、写完直接实现;批量与并行任务一律走 Workflow

- **What**:① 评审链最后一轮裁决不再写死 `opus`,改用主对话当前的模型(Workflow 脚本里这一个 stage 省略 `model`,`effort: 'high'`);盲审与续挖仍是 `opus` + `medium`。② brainstorming 的小改动(bounded)路径也写一份小 spec(几段即可),写完直接实现,不在对话里等用户说 yes;覆盖段逐个点名 brainstorming 里要等批准的四处,spike 路径照原样。③ 批量与并行任务一律走 Workflow,不在一条回复里平行派裸子代理;单个子代理的一次性委派不在此列。
- **Why**:2026-10-02 prompt 审计报出三处跨文件说法不一——评审由谁裁决(全局规则写 opus,内部工作流 skill 写 fable 子代理加外部 CLI)、小改动要不要写 spec 与等批准(superpowers 6.3.0 把 brainstorming 分成三条路径、每条都要先获批准,和「spec 写入即授权」的直通流程冲突)、并行派活用裸子代理还是 Workflow。Tony 2026-10-03 逐条拍板:「按照当前这个对话model来当评审裁决」「小改动就写一个小的spec,但是这个就不用让我看了,直接写spec就直接开干」「统一走workflow」。只把裁决轮改成跟随主对话(盲审、续挖不动)是主对话对第 1 条的理解,动手前已告诉 Tony。
- **Changes**:README zh/en、三份脚手架模板、whats-next、scaffold(workflow/-en 0.16.0,codex 0.15.0);镜像到本机全局 CLAUDE.md、dev-toolkit、huake 两个工具包。没定的:裁决轮模型随会话变后按评审模型分段统计怎么做;内部工作流 skill 的盲审要不要保留外部 CLI。见 Progress 2026-10-03。

## 2026-09-28 - process(tiers): Sonnet 5.5 换代——本机把 sonnet 别名钉到 5.5;机械与 low 档 stage 加验证要求;规则 4 补实现模型分段;对照实验 S 组改 medium

- **What**:① 本机 settings.json 加 env `ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-5-5`(本机设置,不进公开 kit;官方把别名切到 5.5 或出下一代时删,已登记复查)。② mechanical 子代理定义自带验证要求(改完跑真实检查、结论来自本次工具输出、范围内做完再报告);不走 mechanical 的 sonnet+low stage 在派工说明里写同样要求。③ 规则 4:实现模型换代按实现模型分段统计、可以跨代比较,每单元首个提交正文记「实现模型:」行(取实际模型 ID,不记别名);评审模型换代才清零、不跨代比较。④ 对照实验改为 sonnet+medium 对 opus+medium,从下一批重新计数,Sonnet 5 那批单独留作参考。
- **Why**:Tony 2026-09-28「更新sonnet 5.5了，你看一下workflow里面需不需要更新」。核查(盲审 2 + 裁决 1):规则只写别名不用改字,但 Claude Code 2.1.284 的 `sonnet` 别名实测仍解析到 claude-sonnet-5(服务端配置);5.5 与 5 同价,官方称 5.5 medium 多数编码评测胜过 5 high、成本不到五分之一,但 low 档可能不跑验证就报告完成、可能凭记忆作答;effort 档位重新标定;cyber/frontier_llm 拒答会自动回落到 Sonnet 5 重跑,按别名记模型会失准。三个选项里 Tony 选全局环境变量、A/B/C 全做、S 组改 medium。
- **Changes**:本机 ~/.claude/settings.json 与全局 CLAUDE.md(规则 4、实验行);kit workflow/-en mechanical 定义与 README zh/en(0.13.1,顺带修英文版计数命令 `^review round`);dev-toolkit mechanical 定义、stellark-workflow、stellark-parallel-do、scaffold 模板、WORKFLOW.md;huake claude-toolkit-engineer parallel-do 与 scaffold 模板(0.24.1)。见 Progress 2026-09-28。

## 2026-09-25 - process(research): 登录相关默认复用组织通用登录库,不进调研与选型(只进私有面;公开 kit 同日撤回)

- **What**:登录/注册、登出、改密/找回密码、会话与令牌、第三方登录、验证码登录、鉴权中间件、登录页等,组织内已有通用登录库的一律直接复用(私有面固定为内部登录库),任何规模都适用,视为 §八 第 0 步已经定下的结果:不调研、不选型、不与外部开源一起比较,Prior art 直接写复用;实现只做接入,不在项目里重写用户表、密码哈希、令牌签发;库缺的能力、语言形态不匹配、存量项目要不要迁都先问用户;用户本次明确要求换方案或自研才例外,原因进 spec;复用后照样登记组件索引的 used_by,接入单元评审仍按三.3 走。
- **Why**:Tony 2026-09-25 拍板「凡是和登录相关的,如果我没特殊要求,直接复用〔内部登录库〕这个仓库」。登录是每个项目都会碰到的通用件,逐项目调研、选型、自研是重复劳动,安全实现质量也随项目波动;该登录库的立项目的就是集中一处、修一次全体受益。
- **Changes**:全局 CLAUDE.md、本机 github-research skill 第 0 步、dev-toolkit(WORKFLOW.md + stellark-workflow 核心与 references,1.5.2)。README zh/en §八/§8 曾同日加入,Tony 当天要求「公开的 kit 不要加」,已恢复原文,公开 kit 不带这条。见 Progress 2026-09-25 两条。

## 2026-09-22 - process(review): 评审编排改为「盲审起步 + 接力续挖 + 裁决收尾」;换代后第一批实现做起跑档对照实验

- **What**:评审不再平行投票,也不是纯链式:首轮 2 个(高风险单元 3 个)互不可见的盲审平行发现、不数票、脚本按 file+line 归并并标 conflict;之后每轮一个 agent 带前面各轮全部发现、先推翻再找漏、换没用过的镜头;链末裁决轮 opus+high,盲审与续挖 medium;分流表与 4 轮上限;修复在评审 stage 外做,链状态落 `docs/reviews/<单元>-chain.md`。同日拍板:Opus 5.5 换代后第一批实现做分组对照(一半 sonnet+high、一半 opus+medium),按组比退回率与 token 再改档位表,实验前起跑档不动。
- **Why**:Tony 先要"一个 agent 评审完、下一个带着前一个的问题继续挖,而不是投票",再问能否同时避开链式(锚定、首轮跑偏)与投票(重复、不能翻案、数票)的短板;三个候选(A 盲审起步 + 接力续挖 / B 每轮先盲后看 / C 纯链式 + 对抗立场)选 A——独立只用于发现,继承只用于深挖与翻案,全程不数票。起跑档:换代前两个项目退回率 46% / 83% 超过规则 4 的 30% 线,但旧数据不跨代比较,所以用一次对照实验产生 5.5 时代的数据。
- **Changes**:README zh/en 二/三/七节、workflow/-en/codex 三份脚手架模板、codex parallel-do §6(kit 0.13.0);镜像到全局 CLAUDE.md、dev-toolkit、huake 两个 engineer 插件。见 Progress 2026-09-22。

## 2026-09-19 - process(workflow): omitClaudeMd 只用在纯机械 stage;AGENTS.md 本批不做

- **What**:`mechanical` 子代理类型(`omitClaudeMd: true`)只用于定位/清单/盘点与批量迁移/重命名/模板化改码两类纯机械 stage,常规实现与全部评审照旧加载 CLAUDE.md;scaffold 本批不生成 AGENTS.md。
- **Why**:省 token 只在不需要项目约定的机械活上安全;评审与实现依赖 CLAUDE.md 的硬规则。AGENTS.md 三种形态(指向 CLAUDE.md / 双份同步 / 按需生成)当时都没有明确需求,按 YAGNI 不做。
- **Changes**:workflow/-en 0.12.0(mechanical agent + 并发上限文档)。见 Progress 2026-09-19。
