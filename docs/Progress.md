# Progress

## 进度总览

| 模块 | 状态 | 备注 |
|---|---|---|
| workflow / workflow-en(方法论 prompt + scaffold/whats-next/sop-generate) | done | 0.16.0;评审链裁决轮用主对话当前的模型、小改动也写小 spec 且写完直接实现、批量与并行任务一律走 Workflow;mechanical 子代理定义固定 `effort: low`(裸 Agent 派它也按 low 跑)、README 加「维护者:发版前检查」两步;测试启动的进程测完即关、并发前看负载、单元代码启动外部进程时派工 prompt 写明退出要求;omitClaudeMd 机械 agent(agents/mechanical.md)、并发上限 env 文档;进度日志按月归档、评审轮次压进单元提交;需求先复述再动手、worktree 用完即删 + worktree-sweep hook;含目标台账、四点评审纪律、调研内部先行、组件索引三入口、docs-capture 三层 hook(kit/github 面)、main 门禁只拦前端可见改动、截图交付前视觉预审 |
| workflow-codex(Codex CLI 移植版) | done | 0.15.0;spec 写入后直接实现、小改动也写小 spec 的措辞同步;测试进程清理、并发前看负载、外部进程退出要求同步;无 hook 机制,auto-scaffold 靠手动 opt-in;omitClaudeMd 判为 Claude 专有、并发对应 `[agents] max_threads` |
| speak-human / -en(提问与表达纪律 + evals) | done | 0.7.0 / 0.6.0;S1~S6(含 S6 更新日志式汇报);evals 43 条合成案例 |
| send-to / -en(跨会话消息 + 身份注册 hook) | done | 0.4.1;uds 直发为标准路径,四级阶梯 |
| ui-sweep / -en(UI 交互走查 + 孤儿对账) | done | 0.2.1;引擎跑完(含失败退出、收到信号)自动关掉自己的浏览器会话;引擎 smoke 35 例,三入口接进主流程 |
| 进度文档层(PLAN/Progress) | done | 2026-08-13 补;此前只有 README + spec + git 历史 |

## 待办

| 事项 | 来源 | 优先级 |
|---|---|---|
| README 仓库结构树漏 `docs/` 与 `.agents/`;`speak-human-en` 标注「结构同 speak-human」但实际无 `evals/` | 2026-08-13 发布把关 | 低 |
| 内部版 CI 令牌 `dev-toolkit-ci-bot` **2027-04-20 到期**,到期后 auto-bump 会再次全红 | 2026-08-13 修 auto-bump 时建 | 到期前 |
| Phase 4 方向未定 | — | 待规划 |
| 本机 docs-capture 双重注册风险:dev-toolkit 1.3.0 插件版将来在本机拉取后,与 settings.json 直接注册二存一(dev-toolkit README 已写注意) | 2026-08-14 U6 评审 | 拉取插件版时 |
| Claude Code 2.1.288 对照里先放着的三项:C 盲审轮做成插件命名 workflow(先统计各项目评审链月跑次数,再单独出 spec)、D `/verify` 一句话(等下一个有测试命令的新项目实测)、G sonnet 别名复查(放对照实验两批之间) | 2026-10-02 调研稿 | 时机到了再做 |
| prompt 审计的建议改法:2026-10-03 Tony「按照推荐改」,已采纳四个(本机全局规则的机械子代理调用名、两处固定回复句;sop-generate 用户级副本同步成插件版);其余 38 个只让文字更短、不改行为,没有采纳(其中 4 个属第三方 skill,上游一更新就被覆盖)。采纳后本仓与内部工具包里的镜像句(固定回复句「已记入目标台账」;不带前缀的调用名,见下面一行)要不要跟着改,等 Tony 定 | 2026-10-02 prompt 审计 | 等 Tony |
| 内部工具包 parallel-do 的示例脚本仍是单个 `opus` + `high` 的评审 stage,要不要换成评审链(huake 版示例已省略 model,两边不一样) | 2026-10-03 评审链 | 等 Tony 定 |
| 2026-10-03 批次遗留(都是 P2):中英脚手架模板「多代理分工」标题里还有「其他并行分派」;中文模板一处两个括注相连、`opus` 带不带引号不统一;内部工作流核心 skill 第四节标题与「显式写 model+effort」后的裁决轮例外括注没改(当时 token 上限放不下;同日去掉外部 CLI 后核心降到 6449.71,已有余量,下次动内部工具包时补上);huake parallel-do「opus 的意见不是圣旨」;本机全局规则标题与几处「主对话(Fable)」字样 | 2026-10-03 评审链 | 低 |
| 内部工具包里的 workflow-guard 遗留(都是 P2):没有总开关(五个开关全关后残留扫描与提示照常);`/clear` 交出去没关成的浏览器在同一进程里不会被提示;3 秒复查加回时不重新核对启动进程;旧式钩子拒绝的打开命令遇上同名、无记录、活着的浏览器会被记成本会话的;「会话结束不关浏览器」开关的真机行为只有测试;比 2.1.280 更早的 Claude Code 没验证 | 2026-10-03 评审链 | 低 |
| 本机仓 `claude-local-mods` 已被内部工具包里的那一份取代(README 已注明),目录还在;要不要删等 Tony 定 | 2026-10-03 | 等 Tony 定 |
| prompt 审计采纳后还没跟着改的镜像句:本仓 README 与模板里的固定回复句「已记入目标台账」、本仓 README 与模板里不带前缀的 `agentType: 'mechanical'`(内部工具包里的三处已随 workflow-guard 那一批改成 `dev-toolkit:mechanical`;本机全局规则已是新写法) | 2026-10-02 prompt 审计 | 等 Tony 定 |
| 收尾时「要别人做的事」指向的遗留(都是 P2):全局规则与内部工具包 WORKFLOW 七.5 的新半句没有点明这类事不进收尾清单、非交互会话不建(细则在 stella3 skill);stella3 skill「批次收尾」「提交代码之后」两节与提交后提醒钩子的提示语没有指向「要别人做的事」一节 | 2026-10-03 评审链 | 低 |
| 2026-10-03 第二批遗留(都是 P2):英文 README 规则 4 新句用 adjudication round,其余处叫 verdict round;「裁决模型」行只记裁决轮,盲审直接判通过的单元没有这一行、盲审与续挖的 opus 换代也不反映(下次复盘时定要不要再记盲审模型);内部工具包 README 的 1.1.0 历史说明仍写「异构评审票」;review-chain 七之一(甲)缩短后,外部 CLI 包装 agent 的两条回报纪律没有去处 | 2026-10-03 评审链 | 低 |
| Stella 记录子代理语言规定的遗留(都是 P2):批次收尾「新冒出」的新建标题算子代理自己组织(用中文)还是清单原文没说清;「原因不改写」比 examples 里精简原因的样例更严;项目的当前判断、阻塞方等自由文本字段没点名 | 2026-10-03 评审链 | 低 |
| huake 的 Claude 版插件名以 `claude-` 开头,`claude plugin validate` 判为保留名并返回失败(本批之前就有;改名会影响已安装的人) | 2026-10-03 评审链 | Tony 2026-10-03:先不管 |
| 本仓 README 中英与脚手架模板写的 `agentType: 'mechanical'` 不带插件名前缀;workflow 插件里它的注册名实测是 `workflow:mechanical` / `workflow-en:mechanical`,不带前缀在本机实测解析不到,要核对后改 | 2026-10-02 prompt 审计 | 中 |
| 内部工具包四处按原文执行会出错的地方(两个不可逆操作的确认步骤用交互式 read、生产状态 skill 把人指到测试环境的部署命令、缺令牌时提示用一个做不到这件事的命令、一个自己承认会失败的示例);本机杂项:speak-human 全文开局被注入两次、28 个 lark skill 是失效软链接 | 2026-10-02 prompt 审计 | 中 |
| 2026-10-02 批次遗留(都是 P2):README.md 第 202 行 "mechanical work" 紧挨 mechanical 类型的说明,容易误读;「N 等于插件个数」没写清是带 `.claude-plugin` 的 8 个;mechanical 定义的 description 与三处模板里「不自动加载 CLAUDE.md」没补「子目录规则仍按需加载」;「裸 Agent 派 mechanical 按 low 跑」对 haiku 不适用(该模型不接收档位) | 2026-10-02 评审链 | 低 |
| dev-toolkit `hooks/hooks.json` 两处 `${CLAUDE_PLUGIN_ROOT}` 没加引号(validate 有警告,`--strict` 不通过) | 2026-10-02 评审链 L12 | 低 |
| docs-capture 英文词表召回窄(approve/ship/stick with 未覆盖,U2 评审记录),按宁漏勿错接受,待实际使用数据再扩 | 2026-08-14 U2 评审 | 低 |

## 变更日志(最新在上)

> 更早的日志按月在 docs/archive/Progress-YYYY-MM.md

### 2026-10-03 — workflow-guard 并进内部工具包主插件(内部工具包 1.11.1)

起因:Tony 用过本机版之后说「我觉得mods不错,直接更新到dev-toolkit里面吧」。

- 放法(spec `docs/superpowers/specs/2026-10-03-workflow-guard-into-dev-toolkit-design.md`):并进主插件,不另起一个插件——市场清单是「全员唯一工具包」,CI 自动升版只管主插件,所有人更新就有。新旧版本兼容真机验证过:Claude Code 2.1.280 与 2.1.284 上旧式钩子照常运行、mod 被跳过;2.1.288 上 mod 写坏时旧式钩子照常。
- 相对本机版的变化:状态与存储键改到主插件名下;新增两个开关(会话结束不关浏览器、不显示状态栏),连同三项检查共五个,默认都开;去掉 sh 回落(放手的进程只有 perl 一条路);`/clear` 后重取会话 id;残留扫描 3 秒后复查;关掉残留后状态栏与记录跟上。同批把内部工具包核心 skill、工作流说明、脚手架模板里不带前缀的 `agentType: 'mechanical'` 改成 `'dev-toolkit:mechanical'`(照抄会被新检查拦下,不装 mod 这个写法本来也解析不到)。
- 评审(链 `docs/reviews/2026-10-03-workflow-guard-into-dev-toolkit-chain.md`,按高风险单元):盲审 3 个(opus high)报 4 条 P1、5 条 P2;修复(测试与实现分开)后裁决(claude-fable-5-1)通过,新 P2 记遗留。389 个测试,`claude plugin validate` 通过,原有钩子配置逐字不变。
- 真机核对(主对话做):合并前用工作分支里的整个主插件——两类违规脚本被拦、`dev-toolkit:mechanical` 放行、两个测试浏览器在会话结束后 4 秒内关掉;合并、CI 升到 1.11.1、本机更新后,新会话里拦截生效,tmux 抓屏状态栏「负载 3.39/10 · 内存空闲 40%」。本机单独装的那份与本地市场已卸掉,本机现在只有内部工具包里的这一份。核对用的浏览器、tmux 会话、临时目录都已清,测试进程已关。
- 副作用与处理:主对话用旧版二进制做兼容性探测时没有换配置目录,旧版把「mods 关闭」写进了本机 tech 配置档的缓存(约 20 分钟),用当前版本联网启动一次后恢复;以后旧版探测用临时配置目录(已写进 mod 的 README 与记忆)。
- 编排:三次 Workflow 运行、7 个 agent、约 97 万 token。机器负载 3~6(10 核),盲审并行、其余顺序。对照实验:O 组 1 个单元(claude-opus-5-5 + medium),退回 1 轮;4 条 P1 里 1 条是实现回归(`/clear` 后重开同名不记账),2 条是 spec 没查主插件自己的示例,1 条是验证范围没说清。与上一个 S 组单元(退回 2 轮)合起来各只有一个单元,仍不足以定起跑档。
- 遗留:见「待办」表(总开关等 P2;公开 kit 的调用名前缀与回复句镜像仍等 Tony 定)。

### 2026-10-03 — 本机 mod workflow-guard(Workflow 开跑前检查 + 状态栏 + 会话结束关浏览器);内部工具包的 stella3 skill 同步到原稿最新版

起因:Tony 问「新更新的mods,还有插件you should know,我们有什么能利用到的地方吗」,看过六项候选后说「前两个按推荐做吧」。同一时段 stella 窗口转来 stella3 skill 的同步请求。

- mod(spec `docs/superpowers/specs/2026-10-03-workflow-guard-local-mod-design.md`,含真机探测结果与两轮修订):代码不在本仓,在本机新仓 `~/Tony/Proj/Stellark/Projects/claude-local-mods`(本地插件市场 `tony-local-mods`,暂无远端),已装到本机(用户级,四个 profile 共用,新开的会话加载)。三样功能:① Workflow 开跑前检查——`agent()` 没写 effort、子代理类型名解析不到、机器负载超过核数(或可用内存低于 20%)还用并行写法,开跑前拒绝并说明原因,检查自己出错一律放行;② 输入框上方状态栏——负载 / 核数、内存空闲、本会话开着的起名浏览器、启动方已结束的残留浏览器;③ 会话结束时把本会话开的起名浏览器交给一个放手的短命进程去关(每个最多 20 秒)。不做的:后台进程数(接口里没有清单)、没起名的默认会话(全机共用,不跟踪也不关)。
- 评审(链 `docs/reviews/2026-10-03-workflow-guard-local-mod-chain.md`):盲审两位 16 条都标 P2,主对话把三条(关到别的会话的浏览器、失败的关闭被当成成功)定为 P1;第 2 轮裁决不通过,报出两条新 P1(接口声明里会话结束只有约 1.5 秒,逐个等关闭会被切断;上一轮「出错不记账」定得太宽);第 3 轮裁决通过。裁决都运行在 claude-fable-5-1。344 个测试,`claude plugin validate` 通过,类型检查通过。
- 真机核对(主对话做):两类违规脚本被拦、合规脚本放行;四个测试浏览器(含 Workflow 子代理开的、命令出错但已起来的)在会话结束后 3 秒内关掉;关闭命令卡住时放手的进程约 41 秒后自己退出;状态栏在 tmux 里抓屏确认;安装后的新会话里拦截生效。核对用的浏览器、tmux 会话、临时文件都已清,测试进程已关。
- 编排:mod 三次 Workflow 运行、9 个 agent、约 131 万 token。机器负载 5~16(10 核),全程顺序跑。对照实验:S 组 1 个单元(claude-sonnet-5-5 + medium),退回 2 轮;两轮的 P1 里实现缺陷只有一条(失败的关闭被当成成功),其余都是 spec 的缺口(默认会话共用、heredoc、会话结束时限没查接口、修订矫枉过正)。本批没有 O 组单元,单看不足以定起跑档。
- stella3 同步(小 spec `docs/superpowers/specs/2026-10-03-stella3-skill-sync-design.md`,链 `docs/reviews/2026-10-03-stella3-skill-sync-chain.md`):内部工具包的副本从 9 月 29 日起落了四批原稿改动,用三方合并一次带齐(要别人做的事先复述确认、运维信息、取消阶段与下一检查点、待办视图),只保留本仓自己的一处差异;盲审只有 P2,通过;插件 1.9.1,本机已更新并在新会话里核对。
- 追加:Tony 确认状态栏样子没问题;全局规则直通流程第 3 步补了「要别人做的事按 stella3 skill「要别人做的事」一节办——先复述、我确认后建成对方的待办」(Tony「加」),内部工具包 WORKFLOW 七.5 同步改;盲审 2 个只有 P2,通过(链 `docs/reviews/2026-10-03-closing-hand-to-other-pointer-chain.md`)。
- 追加:stella 窗口转来第二次同步(原稿加了撤回完成 / 删除待办,工具已上线)。三方合并进内部工具包副本,因涉及删除按高风险单元评审:3 个盲审共 15 条全 P2,裁决(claude-fable-5-1)通过;已并主干,插件 1.10.1,本机已更新。真机核对:建一条测试待办后要求删除,先复述、回「写」后才删。本机全局规则里「写错了我在网页改」经 Tony 点头改成会话里也能撤回与删除(备份 `~/.claude/CLAUDE.md.bak-20261003-undo-delete`)。评审留给原稿的 10 条小问题已转给 stella 窗口。约 49.3 万 token。链 `docs/reviews/2026-10-03-stella3-skill-sync-chain.md`「第二次同步」一节。
- 遗留:见「待办」表新增的几行。

### 2026-10-03 — 提交里加记裁决模型 + 内部工作流 skill 的盲审去掉外部 CLI + 采纳 prompt 审计四个改动块

起因:上一批留给 Tony 的几件事,他逐条答复:「1. 加上 2. 去掉 3. 先不管 4. 关 5. 有哪些审计的改动? 6. 这个仓库对应的不就是claude workflow kit吗?你再看看」,看过审计清单后又说「两个进程你关一下,然后这个里面的审计,你按照推荐改吧」。

- 规则(小 spec `docs/superpowers/specs/2026-10-03-adjudication-model-line-drop-external-cli-design.md`):① 跑过裁决轮的单元,首个提交正文在「实现模型:」之外再记一行「裁决模型:<裁决轮实际运行的模型 ID>」,评审基线按它分段;② 内部工具包的评审链回到与本仓相同的形态(盲审 2 个 opus、高风险单元 3 个、默认上限 4 轮),外部 CLI 不再是评审链的一方,两个驱动 skill 保留、只在用户点名时用。
- 改动:本仓 README 中英规则 4 各一句;本机全局规则同一句(备份 `~/.claude/CLAUDE.md.bak-20261003-adjudicator-model-line`);内部工具包的 WORKFLOW.md 规则 4、核心 skill 六处、review-chain 细则重写、对照表、两个驱动 skill、README、parallel-do 档位表一行,版本升到 1.8.0。核心 token 6532.0 → 6449.71,已低于 6500。huake 两个工具包只有压缩句,不动。
- 审计:四个改动块套用到本机(全局规则三处,备份 `~/.claude/CLAUDE.md.bak-20261003-audit-g24-g25`;sop-generate 用户级副本的 SKILL.md 与两个脚本同步成插件版,旧版备份在审计目录)。其余 38 个没有采纳。
- 评审:盲审 2 个(opus medium,顺序跑)同报 2 条 P1(codex 驱动 skill 正文还把它写成评审链一方;核心一处括注还指向已删掉的撤方与链数上限)、2 条 P2;修复后裁决(省略 model,实际运行在 claude-fable-5-1,high)两个单元都通过,新 P2 四条记入「待办」表。评审链 `docs/reviews/2026-10-03-adjudication-model-line-drop-external-cli-chain.md`。新规则当批就用上:两个单元的提交正文都记了「裁决模型:claude-fable-5-1」。
- 编排:两次 Workflow 运行、5 个 agent、约 41.6 万 token。机器 1 分钟负载 11~13(10 核),全程顺序跑。对照实验不计入(规则文字单元,没有测试)。
- 其他:三个残留的 agent-browser 进程(连同带起的无界面浏览器)按 Tony 的话关掉,它们都不是本会话启动的;huake 插件名的保留名问题按 Tony 说的先不管;本仓在 Stella 里对应项目「Claude Workflow Kit」,上一批说没有对应项目是错的,这次收尾补更新待办。本批没有启动服务或浏览器,测试进程已关。
- 追加(同一分支):Tony 在 hapi 窗口说「更新stella的为啥是英文,调成中文的」,由该窗口转来。内部工具包的 Stella 记录子代理定义加一条语言规定:给用户的话与自己组织后写进 Stella 的文字一律用中文,别人给的原文(用户原话、批次清单条目、已有待办标题、工具返回的原文、人名与专有名词)照原样。盲审一位判 P1、一位判 P2(与「用户原话直接用」没写清谁优先),改写后裁决通过(claude-fable-5-1);3 个 agent 约 22.3 万 token。原稿在 stella 仓,已通知那边写回。
- 遗留:见「待办」表(镜像句要不要跟着改、parallel-do 示例脚本、四条 P2、语言规定的三条 P2)。

### 2026-10-03 — 裁决轮用主对话当前的模型 + 小改动也写小 spec 直接实现 + 并行派活统一走 Workflow(workflow/-en 0.16.0,codex 0.15.0)

起因:2026-10-02 prompt 审计报出三处跨文件说法不一,Tony 逐条拍板:「按照当前这个对话model来当评审裁决」「小改动就写一个小的spec,但是这个就不用让我看了,直接写spec就直接开干」「统一走workflow」。

- 规则(spec `docs/superpowers/specs/2026-10-03-adjudicator-model-small-spec-workflow-dispatch-design.md`):① 评审链只有最后一轮裁决改用主对话当前的模型(脚本里这一个 stage 省略 `model`、`effort: 'high'`;主对话是 Fable 就由 Fable 裁决,是 Opus 就由 Opus 裁决),盲审与续挖仍是 `opus`;② brainstorming 的小改动(bounded)路径也写一份小 spec,写完直接实现、不等用户确认,覆盖段逐个点名 brainstorming 里要等批准的四处(writing-plans 交接、User Review Gate、bounded 停下等批准、HARD-GATE 含「Too Simple To Need Approval」一节),spike 路径照原样;③ 批量与并行任务一律走 Workflow,不在一条回复里平行派裸子代理(单个子代理的一次性委派不在此列),点名覆盖 superpowers:dispatching-parallel-agents。
- 改动:README 中英第一、二、三、四、七节,第九节 whats-next 表与使用方式流程图;三份脚手架模板(Codex 版只做第 ② 条的措辞)、whats-next、scaffold 汇报句、PLAN 模板;三个插件版本号。
- 镜像:本机全局 CLAUDE.md 11 行(备份 `~/.claude/CLAUDE.md.bak-20261003-adjudicator`);dev-toolkit(WORKFLOW.md、核心 stellark-workflow 及其 review-chain / upstream-map、parallel-do、whats-next、scaffold 与模板、driving-codex;核心 token 6534.0 → 6532.0);huake Claude 版 0.26.0、Codex 版 0.14.0(README 各加一行版本说明)。四处都已并 main;dev-toolkit 由 CI 升到 1.7.5,本机插件已更新,已装的核心 skill 与仓库一致。
- 验收(主对话在最终状态上重跑):全局文件与备份都是 111 行,差异只在点名的 11 行;README 发版前检查第一段末行 `ALL PASSED (8 plugins)`;各仓改动文件都在 spec 点名范围内;旧说法(「获批」「fable 裁决」「异构三方」「opus 评审 stage」「并行分派」)的剩余命中只有引用原话、历史说明与下面登记的遗留。新规则当批就用上了:四个裁决 agent 都省略 model,实际运行在 claude-fable-5-1。全程没有启动服务或浏览器,测试进程已关。
- 编排:三次 Workflow 运行、23 个 agent、约 213.7 万 token(实现 5 个 43.8 万;盲审 6 个 65.0 万;修复 5 个 37.7 万;独立测试 2 次 19.0 万;裁决 4 个 47.4 万;套用 0.9 万)。机器负载 5~10(10 核),实现与盲审并发 2,修复之后全部顺序跑。评审链 `docs/reviews/2026-10-03-adjudicator-small-spec-workflow-chain.md`。
- 对照实验:S 组 U1、U3、U5(claude-sonnet-5-5 + medium),O 组 U2、U4(claude-opus-5-5 + medium)。五个单元都有修复轮(U3、U4 各两轮);P1 里一半以上是 spec 自身的缺口或写得不清,U4 第 2 轮修复换成机械子代理、单列不归组。本批是规则文字单元、没有测试,不拿来定起跑档。
- dev-toolkit 核心 skill 的 token 上限这次卡了两轮:修复 agent 两次都按要求停下报数字。最后的做法是主对话自己按该仓公式在草稿上算好一组「恢复被删内容 + 另两句换短说法」的精确替换清单,交机械子代理照单套用。
- 遗留:见「待办」表 2026-10-03 的四行。

评审 2 轮:第 1 轮(盲审 6 个)——README 第九节 whats-next 一行与流程图漏改、脚手架模板缺「小改动也写小 spec」一条、huake README 的版本说明行与开发流程句漏改、parallel-do「修完仍挂 opus high 复审」、dev-toolkit 核心为守 token 上限删了不该删的内容。第 2 轮(裁决)——dev-toolkit 核心按上限重排(恢复被删内容、覆盖段换成压缩句、另两句换短说法);英文模板一处超范围改词改回。

### 2026-10-02 — 仓库目录搬到 Stellark/Projects 下

Tony 要求把本仓从 `~/Tony/Proj/claude-workflow-kit` 搬到 `~/Tony/Proj/Stellark/Projects/claude-workflow-kit`。搬前检查:目标无重名、同一磁盘、仓库干净、只有一个 worktree,没有软链接、定时任务、别的仓库或配置写死旧路径。搬后核对:提交号、远端、工作区状态不变,8 个插件 `--strict` 校验全过。Claude 的项目状态按路径存放:记忆目录已挪到新路径对应的状态目录,旧位置留软链接,新旧路径开的会话共用一份记忆;旧会话记录留在旧路径对应的状态目录。

### 2026-10-02 — prompt 审计(`/doctor prompt-audit`,只出报告与建议改法,没有改文件)

起因:2.1.288 对照里的 E 项,Tony 在会话里敲了 `/doctor prompt-audit`。范围是本项目会话会加载的 Claude Code 配置文字,共 123 个文件:本机全局规则、用户级 skill、账号同步的 skill、四个插件自带的 skill 与子代理定义。目标模型 Claude Fable 5.1。

- 做法:10 个扫描员逐文件对照内置审计指南(9 个 sonnet medium 加 1 个 opus medium 查跨文件冲突,约 115 万 token);4 个 opus medium 逐条回到原文复核(全局规则两位互不可见),另实测了一次子代理类型名解析(约 45 万 token)。扫描员报 141 条,复核推翻 3 条、改写 15 条的替换文本、补报 4 条。
- 结果:旧模型脚手架、退役模型名、含糊措辞、身份套话都是 0 命中;账号同步的 14 个 skill 全部干净。问题集中在三类——规则里的历史叙述与「相对旧版本」的说法、跨文件冲突与失效的交叉引用、内部工具包里几处按原文执行会出错的步骤。
- 最要紧的三条:全局规则里机械子代理的调用名 `agentType: 'mechanical'` 在本机解析不到(实测报 not found,带插件名前缀才行);评审由谁裁决有两套互相冲突的规则同时加载;superpowers 6.3.0 的 brainstorming 分成三条路径后,全局的覆盖说明只管到其中一条。
- 产出:完整报告、逐块的原文与替换文本、两份差异文件放在本机私有目录(含内部运维细节,不进本仓)。建议改法共 44 块(全局规则 27、用户级 skill 17),插件与同步文件只报告。
- 对本仓的后续:README 中英与脚手架模板里不带前缀的 `agentType: 'mechanical'` 要核对后改;全局规则采纳哪些改动块定了之后,README 里的对应句再跟着改。见「待办」表新增的三行。

### 2026-10-02 — Claude Code 2.1.288 对照:发版前检查 + mechanical 固定 low 档 + 档位句补充(workflow/-en 0.15.0)

起因:Tony 问「最近 claude code 新版本出了什么新功能,你觉得可以加到这个 workflow 里的」,随后升到 2.1.288。上次对照是 2026-09-19(审到 2.1.278)。

- 调研:2.1.280→2.1.288 共 320 行新功能、217 行相关修复;5 个主题各 1 个 sonnet medium 调查员 + 2 个互不可见的 opus medium 盲审,15 个 agent 约 111 万 token,盲审修正 19 条。研究稿 `docs/superpowers/research/2026-10-02-cc-288-feature-review.md`,候选 A~H。Tony「按推荐做」:A、B、H 一个批次,F 的冒烟并入 B,E 由 Tony 手动跑,C、D、G 先放着。
- 取证(真机):插件子代理定义 frontmatter 写了 `effort: low` 的,主会话 high 时裸 Agent 派它实际按 low 跑,没写的继承 high;`omitClaudeMd` 只屏蔽开局加载,子代理读写到的子目录 CLAUDE.md 与带 `paths:` 的规则仍按需加载。证据 `docs/reviews/2026-10-02-cc288-smoke-evidence.md`。
- 改动(spec `docs/superpowers/specs/2026-10-02-cc288-validate-effort-frontmatter-design.md`):README 中英新增「维护者:发版前检查」两步(`claude plugin validate --strict` 全过并数出插件个数;`claude plugin details` 看每个插件的常驻 token);两份 mechanical 定义加 `effort: low`;规则句改成「按次指定 effort 只有 Workflow 的 agent() 支持」,补「定义里写了 effort 的子代理类型,裸 Agent 派它也按该档位跑」的例外(README 中英、两份脚手架模板);mechanical 说明补「omitClaudeMd 只管开局那次加载」;档位句补「按模型分别保存、ultracode 不等于 xhigh、以 /effort 为准」。
- 镜像:本机全局 CLAUDE.md 第 16、29、39、43 行(备份 `~/.claude/CLAUDE.md.bak-20261002-cc288-abh`);dev-toolkit(mechanical 定义、WORKFLOW.md 三行、README 子代理表一格、脚手架模板一行;并 main 后 CI 升到 1.7.4,本机插件已更新)。huake 两个 engineer 插件没有 mechanical 子代理、模板压缩句字面仍成立,不改;workflow-codex 不涉及。
- 验收:README 两段命令从仓库根逐字执行,第一段末行 `ALL PASSED (8 plugins)`;kit 两份 mechanical 真机冒烟均为 low(主会话 high);本机已装的 `dev-toolkit:mechanical`(1.7.4)真机冒烟为 low;haiku 实测不报错(该模型不接收档位)。测试进程已关。
- 发版前检查第二步的数字(常驻 token,Claude Code 2.1.288):workflow 约 465、workflow-en 约 442、speak-human 约 181、speak-human-en 约 174、send-to 约 177、send-to-en 约 154、ui-sweep 约 159、ui-sweep-en 约 164。
- 编排:取证 1 个 agent(5.6 万 token);实现 4 个单元 + 盲审 4 个(57.7 万);修复 3 个 + 独立测试 1 个 + 裁决 2 个(39.0 万)。评审链 `docs/reviews/2026-10-02-cc288-abh-chain.md`。
- 对照实验:S 组 U1、U3(claude-sonnet-5-5),O 组 U2、U4(claude-opus-5-5)。有修复轮的是 U1、U3、U4,原因都是 spec 缺口或部署时序,没有一条是实现偏离 spec;样本太小,不改起跑档。
- 不覆盖与遗留:见上面「待办」表新增的五行。

评审 1 轮:同一句里保留的「mechanical 类型同理」与新例外矛盾(四个面);发版前检查两段命令的两个边界;dev-toolkit README 子代理表漏改。

### 2026-10-01 — 测试启动的进程测完即关 + 并发前先看负载 + 外部进程必须写退出(workflow/-en/codex 0.14.0,ui-sweep/-en 0.2.1)

起因:Tony 三句需求——测试完要关掉相关进程;测试并发时先看电脑负载,已经很大就把并发调小;Workflow 实现派工 prompt 加一条,项目里有要启动多个无界面浏览器的地方(如 hook-writer)必须写退出进程的代码。查到的事实:hook-writer 2026-09-27 被整体关停,抓取容器里 13 个无界面 Chrome 一直不退出(最久 4 天 18 小时、约 1.9GB),Docker 虚拟机反复内存耗尽,同机另一个项目的 postgres 7 天崩溃 30 次,根因是第三方库的关闭函数出错后无限期等浏览器自己退出、浏览器调用又没有超时;提需求当时本机 10 核、1 分钟负载 31.77、69 个 claude 进程;kit 自带的 ui-sweep 引擎只在开跑时关旧会话,跑完把自己的会话和 Chrome 留在后台。spec:`docs/superpowers/specs/2026-10-01-test-process-cleanup-and-load-design.md`。

三条规则:①测试/验证/截图启动的进程谁启动谁关,失败或中途放弃也关;启动时记 PID / 端口 / 会话名,报告前逐个核对已退出(包装命令带起的子进程一起核对);只关自己启动的,不用 `pkill -f` / `killall` 按名字批量结束,别人留下的残留进程只列出来交给用户。②并行跑测试、压测或开多个并行单元前看 `uptime` 的 1 分钟负载对比核数:超过核数 70% 并发按当前值减半(最少 1),超过核数或可用内存低于 20% 改串行(盲审轮同样可以顺序跑);报告写明负载与实际并发数。③单元代码要启动外部进程(无界面浏览器、子进程、常驻 worker)时,派工 prompt 写明必须实现退出:最长存活时间到点结束整个进程组、关闭先正常后强制且等待有上限、同时存活数有上限、出错/超时/取消/启动失败的路径都关、每次调用带超时、容器加内存与进程数上限,测试覆盖卡住或出错后进程确实退出;评审核对这几条有没有实现和测到。

改动位置:README zh/en 新增「七之四 / 7d」,七.4 / 7.4 加进程约束与评审半句,§四 并发上限段加「开跑前先看负载」;三份 scaffold 模板(质量检查第 7、8 条、红线条、评审条、并发条、禁止事项)、Codex parallel-do、两份机械子代理定义同步。代码:ui-sweep 的 `sweep.mjs`(中英)在会话建立后无论正常结束、失败退出、未捕获异常还是收到 SIGINT / SIGTERM / SIGHUP 都关掉自己的 `ui-sweep` 会话,关闭失败不改退出码、往 stderr 打一行手动关闭提示;smoke 从 24 例加到 35 例;三份 sop-generate 的 `crawl.mjs` 与 `probe-login.mjs` 出错也关浏览器,关闭最多等 10 秒。私有面同批:本机全局 CLAUDE.md(新节 + 直通流程第 2 步 + 并发上限段;改前备份 `~/.claude/CLAUDE.md.bak-20261001-test-process-cleanup`)、dev-toolkit(merge 1204dca;核心 SKILL.md token 6534.29 → 6534.0,细则在新文件 `references/process-exit.md`)、huake claude-toolkit-engineer 0.25.0(merge e8ea537)、codex-toolkit-engineer 0.13.0(merge 8c6c96d)。

验证:两份 smoke 各 35 通过 / 0 失败;真实浏览器(agent-browser 0.27.0,本机临时静态页)跑新引擎,跑完会话列表里没有 `ui-sweep`;同一配置跑改动前的引擎,跑完 `ui-sweep` 会话还在(已手动关掉并核对退出)。测试用的本地静态服务按 PID 关掉、端口释放、临时目录已删。全程按规则②执行:负载 22~37 时所有子代理串行,负载 9.9 时盲审并发减半。

- 不覆盖:没有做「会话结束时自动扫残留进程」的 hook——哪个进程是本会话启动的只有启动方自己知道,hook 只能按名字结束,会误关别的会话的进程。ui-sweep 会话名仍固定为 `ui-sweep`,同一台机器同一时间只能跑一个(SKILL.md 已写明);`crawl.mjs` 与 `probe-login.mjs` 的关闭超时分支只做了语法检查与辅助函数的假对象测试,没在真实浏览器里跑过。
- 对照实验(sonnet+medium 对 opus+medium):S 组 3 个单元退回 1 个,O 组 2 个单元退回 1 个,样本太小不改起跑档;明细在评审链记录末尾。
- 评审 2 轮(kit 面):盲审 4 个(opus medium)——规则文本只有 P2 判通过,代码 1 条 P1(一个用例没测到它声称测的东西)退回;修复后裁决轮(opus high)通过,规则文本续挖轮(集成缝合点)通过。镜像面 2 轮:huake 盲审通过;dev-toolkit 盲审 1 条 P1(为守 token 上限的压缩删掉了登录规则细则的入口),修复后裁决通过。记录:`docs/reviews/2026-10-01-test-process-cleanup-chain.md`。
