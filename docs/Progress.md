# Progress

## 进度总览

| 模块 | 状态 | 备注 |
|---|---|---|
| workflow / workflow-en(方法论 prompt + scaffold/whats-next/sop-generate) | done | 0.18.1;盘点行改 haiku 首选(2026-10-07);对照 superpowers 6.4.1 改四处(2026-10-05):七.6 点名新版 HARD-GATE 整段、并行实现时全量测试由主对话按顺序跑、评审判据「spec 没写到的行为按使用者的合理预期判」、spec 加一节「容易漏的输入与失败情形」;评审链裁决轮固定 `opus` + `high`(2026-10-03 同日由「用主对话当前的模型」改回)、并发前先看 CPU 占用、小改动也写小 spec 且写完直接实现、批量与并行任务一律走 Workflow;mechanical 子代理定义固定 `effort: low`(裸 Agent 派它也按 low 跑)、README 加「维护者:发版前检查」两步;测试启动的进程测完即关、并发前看负载、单元代码启动外部进程时派工 prompt 写明退出要求;omitClaudeMd 机械 agent(agents/mechanical.md)、并发上限 env 文档;进度日志按月归档、评审轮次压进单元提交;需求先复述再动手、worktree 用完即删 + worktree-sweep hook;含目标台账、四点评审纪律、调研内部先行、组件索引三入口、docs-capture 三层 hook(kit/github 面)、main 门禁只拦前端可见改动、截图交付前视觉预审 |
| workflow-codex(Codex CLI 移植版) | done | 0.17.0;评审判据与 spec 加一节同步(2026-10-05);spec 写入后直接实现、小改动也写小 spec 的措辞同步;测试进程清理、并发前先看 CPU 占用、外部进程退出要求同步;无 hook 机制,auto-scaffold 靠手动 opt-in;omitClaudeMd 判为 Claude 专有、并发对应 `[agents] max_threads` |
| speak-human / -en(提问与表达纪律 + evals) | done | 0.7.0 / 0.6.0;S1~S6(含 S6 更新日志式汇报);evals 43 条合成案例 |
| send-to / -en(跨会话消息 + 身份注册 hook) | done | 0.4.1;uds 直发为标准路径,四级阶梯 |
| ui-sweep / -en(UI 交互走查 + 孤儿对账) | done | 0.2.1;引擎跑完(含失败退出、收到信号)自动关掉自己的浏览器会话;引擎 smoke 35 例,三入口接进主流程 |
| 进度文档层(PLAN/Progress) | done | 2026-08-13 补;此前只有 README + spec + git 历史 |

## 待办

| 事项 | 来源 | 优先级 |
|---|---|---|
| ui-sweep 中英两份文档里导出登录态的命令缺 `node`,脚本文件又没有可执行权限,照文档执行会报权限错误 | 2026-10-04 对照 superpowers 6.4.1 时查出 | 中 |
| 对照 superpowers 6.4.1 批次的评审遗留(K4~K7、L6):七.4「各单元实现返回后按顺序跑」可读成等全部返回;顺序跑全量出现失败怎么办没写;「HARD-GATE 整段」含 Spike 那一行、句末才说 spike 照原样;模板漏「或派一个 agent 串行跑」;「容易漏」的条目没法用测试覆盖或跨单元时怎么办没写 | 2026-10-05 评审链 | 低 |
| README 仓库结构树漏 `docs/` 与 `.agents/`;`speak-human-en` 标注「结构同 speak-human」但实际无 `evals/` | 2026-08-13 发布把关 | 低 |
| 内部版 CI 令牌 `内部工具包-ci-bot` **2027-04-20 到期**,到期后 auto-bump 会再次全红 | 2026-08-13 修 auto-bump 时建 | 到期前 |
| Phase 4 方向未定 | — | 待规划 |
| 本机 docs-capture 双重注册风险:内部工具包 1.3.0 插件版将来在本机拉取后,与 settings.json 直接注册二存一(内部工具包 README 已写注意) | 2026-08-14 U6 评审 | 拉取插件版时 |
| Claude Code 2.1.288 对照里先放着的三项:C 盲审轮做成插件命名 workflow(先统计各项目评审链月跑次数,再单独出 spec)、D `/verify` 一句话(等下一个有测试命令的新项目实测)、G sonnet 别名复查(放对照实验两批之间) | 2026-10-02 调研稿 | 时机到了再做 |
| prompt 审计的建议改法:2026-10-03 Tony「按照推荐改」,已采纳四个(本机全局规则的机械子代理调用名、两处固定回复句;sop-generate 用户级副本同步成插件版);44 个里另有 2 个上一批已处理,其余 38 个只让文字更短、不改行为,没有采纳(其中 4 个属第三方 skill,上游一更新就被覆盖)。采纳后本仓与内部工具包里的镜像句(固定回复句「已记入目标台账」、不带前缀的调用名)要不要跟着改,等 Tony 定 | 2026-10-02 prompt 审计 | 等 Tony |
| 2026-10-03 批次遗留(都是 P2):中英脚手架模板「多代理分工」标题里还有「其他并行分派」;中文模板一处两个括注相连、`opus` 带不带引号不统一 | 2026-10-03 评审链 | 低 |
| prompt 审计采纳后还没跟着改的镜像句:本仓 README 与模板里的固定回复句「已记入目标台账」、本仓 README 与模板里不带前缀的 `agentType: 'mechanical'`(内部工具包里的已改;本机全局规则已是新写法) | 2026-10-02 prompt 审计 | 等 Tony 定 |
| 2026-10-03 第二批遗留(都是 P2):英文 README 规则 4 新句用 adjudication round,其余处叫 verdict round;「裁决模型」行只记裁决轮,盲审直接判通过的单元没有这一行、盲审与续挖的 opus 换代也不反映(下次复盘时定要不要再记盲审模型) | 2026-10-03 评审链 | 低 |
| 内部工作站 的 Claude 版插件名以 `claude-` 开头,`claude plugin validate` 判为保留名并返回失败(本批之前就有;改名会影响已安装的人) | 2026-10-03 评审链 | Tony 2026-10-03:先不管 |
| 本仓 README 中英与脚手架模板写的 `agentType: 'mechanical'` 不带插件名前缀;workflow 插件里它的注册名实测是 `workflow:mechanical` / `workflow-en:mechanical`,不带前缀在本机实测解析不到,要核对后改 | 2026-10-02 prompt 审计 | 中 |
| 内部工具包四处按原文执行会出错的地方(两个不可逆操作的确认步骤用交互式 read、生产状态 skill 把人指到测试环境的部署命令、缺令牌时提示用一个做不到这件事的命令、一个自己承认会失败的示例);本机杂项:speak-human 全文开局被注入两次、28 个 lark skill 是失效软链接 | 2026-10-02 prompt 审计 | 中 |
| 2026-10-02 批次遗留(都是 P2):README.md 第 202 行 "mechanical work" 紧挨 mechanical 类型的说明,容易误读;「N 等于插件个数」没写清是带 `.claude-plugin` 的 8 个;mechanical 定义的 description 与三处模板里「不自动加载 CLAUDE.md」没补「子目录规则仍按需加载」;「裸 Agent 派 mechanical 按 low 跑」对 haiku 不适用(该模型不接收档位) | 2026-10-02 评审链 | 低 |
| 内部工具包 `hooks/hooks.json` 两处 `${CLAUDE_PLUGIN_ROOT}` 没加引号(validate 有警告,`--strict` 不通过) | 2026-10-02 评审链 L12 | 低 |
| 2026-10-03 第三批遗留(都是 P2):mechanical 那一句没写 `top` 取不到读数时怎么办;模板与 parallel-do 的一行写法没带「没设过就按工具默认值算」;Linux 逐核显示、busybox 的 top、逗号小数点的语言环境下取不到 `%Cpu(s)` 行(有退回办法,Linux 没实测);内存读数取不到时没有规定 | 2026-10-03 评审链 | 低 |
| docs 换成中性叫法后的遗留(都是 P2):内部仓库的提交号与版本号未逐条删;三份 spec 的回滚命令里备份文件位置是占位说法;非原话处〔〕标注不统一 | 2026-10-03 评审链 | 低 |
| docs-capture 英文词表召回窄(approve/ship/stick with 未覆盖,U2 评审记录),按宁漏勿错接受,待实际使用数据再扩 | 2026-08-14 U2 评审 | 低 |

## 变更日志(最新在上)

### 2026-10-07 — Haiku 5.5 发布:档位表盘点行改 haiku 首选(workflow/-en 0.18.1)

- 背景:Haiku 5.5 当天发布,1M 上下文、支持 effort(4.5 不接收)、提示 ≤100K 时 $0.10/$0.50(4.5 是 $1/$5)。本机 Claude Code 2.1.292 的 `haiku` 别名实测仍落到 4.5,2.1.293 的编译模型目录才指向 5.5;本机已升级并用 `claude -p --model haiku` 复验。别名由各版本二进制编译的目录决定,不随新模型发布当天自动变。
- 改动:「定位文件 / 列清单 / 盘点」行改成 `haiku`(首选;出错才换 `sonnet`),派工句写明盘点类用 haiku、批量机械执行类用 sonnet,README 中英各加一段说明(≤100K 档便宜 20 倍、2.1.293 起别名才到 5.5、更早版本写完整型号);两份脚手架模板同步。「批量机械执行」行保持 sonnet,对照实验 Tony 未选。
- 同批(不在本仓):本机全局规则与内部工具包四处同步(核心文件受字数上限,压成「败则 sonnet」);内部项目管理系统(生产仓与 3.0 分支)与内部用量统计工具的模型价格表补 Opus 5.5 / Haiku 5.5 行(三处都已并 main,生产仓由 Tony 定直接上线),用量统计工具另补 Sonnet 5.5 / Fable 5.1 并撤销 Sonnet 5 的涨价行(官方 2026-10-07 取消)。
- 评审:盲审 2 轮 + 裁决(opus high)通过;遗留 P2 见 `docs/reviews/2026-10-07-haiku55-chain.md`。spec `docs/superpowers/specs/2026-10-07-haiku-55-inventory-row-and-price-tables-design.md`。
- 实现模型:claude-fable-5-1(主对话直接改);裁决模型:claude-opus-5-5。
- 提交历史:本仓两条评审 squash! 提交没压进单元提交——压缩前工作区里有钩子追加的未提交改动,rebase 没跑起来就合并了;main 不改写历史,就这样留着,统计退回率时按「评审第」行数照样数得到。内部工具包那边压缩正常。

> 更早的日志按月在 docs/archive/Progress-YYYY-MM.md

### 2026-10-05 — 对照 superpowers 6.4.1 改四处规则(workflow/-en 0.18.0,codex 0.17.0)

起因:superpowers 升到 6.4.1。2026-10-04 先做了一次只读对照(5 个 agent 对照、2 个逐条核对),Tony 定了改四处:「那就把1和2改一下,按照我们自己workflow的规则,目前我们已有的这个规则挺好的」「这两点加上吧,我觉得挺好的」。

- 七.6:改写 brainstorming 批准关口的那一条点名 6.4.1 重写后的 HARD-GATE 整段(按路径列出的批准、同段三句英文原话),写明 spec 写入就是对其后全部阶段的授权。
- 七.4:多个单元并行实现时同一时间只允许一个单元跑全量或重型测试;派工 prompt 写明实现 agent 收尾只跑本单元的定向用例或 -short,并写明这一条优先于 TDD skill 的收尾全量要求;全量由主对话在实现返回后按顺序跑、结果交给评审。
- 七.4:评审判据——spec 没写到的行为,按使用者的合理预期判(说的是已实现的行为在 spec 没点名的输入或情形下的表现,不是 spec 没要求做的功能)。
- 七.1:spec 必备内容加一节「容易漏的输入与失败情形」(最多五条,每条在负责的单元里补一个测试;查过没有就写明)。
- 改动:README 中英、workflow 与 workflow-en 的脚手架模板(四条都有)、Codex 模板(后两条)。小 spec 两份:`docs/superpowers/specs/2026-10-05-superpowers-641-approval-gates-and-full-suite-design.md`、`docs/superpowers/specs/2026-10-05-review-criterion-and-easy-to-miss-section-design.md`;文字由脚本按替换清单套用(清单在同目录)。本机全局规则与内部的几处副本同步改。
- 评审:单元一(前两条)盲审 2 个(opus medium)全是 P2,判通过,改了 3 处;单元二(后两条)盲审 2 个全是 P2,内部副本有 1 条 P1(压缩句丢了要素),修复后裁决(claude-opus-5-5,high)通过。评审链 `docs/reviews/2026-10-05-superpowers-641-chain.md`。遗留见上面「待办」表。
- 没做:对照时列出的其余几条(评审结果加「搁置不判的事项」等)按 Tony 的决定不加;ui-sweep 文档那一处没有改(记在「待办」表)。

### 2026-10-03 — 评审链的裁决轮改回固定用 opus(workflow/-en 0.17.0)

起因:同日早些时候把裁决轮改成了「用主对话当前的模型」。Tony:「把审查模型放回opus吧,fable消耗量太大了,默认主模型为审查模型不太行」——主对话用最高档模型时,每个单元的裁决都落在它上面。

- 规则(小 spec `docs/superpowers/specs/2026-10-03-adjudication-round-back-to-opus-design.md`):裁决轮固定 `opus` + `high`,脚本里显式写 `model: 'opus'`,不随主对话的模型变。提交正文的「裁决模型」一行保留(`opus` 别名解析到哪一代由服务端决定)。同一批的另外两条规则(小改动也写小 spec、并行派活走 Workflow)不变。
- 改动:README 中英第三节与七.4(各约 8 处)、workflow 与 workflow-en 的脚手架模板(各 5 处)。Codex 版没有这条写法。本机全局规则与内部的几处副本同步改。
- 评审:与下一条同一个单元,盲审 2 个(opus medium)无 P0 / P1,判通过。评审链 `docs/reviews/2026-10-03-cpu-usage-and-opus-adjudication-chain.md`。

### 2026-10-03 — 并发前先看 CPU 占用,不再用负载平均值当依据(workflow/-en 0.17.0,codex 0.16.0)

起因:Tony 指出「负载计算不太准」,随后定「改成先看 CPU占用」。实测一台 10 核、600 多个进程的机器:`uptime` 的 1 分钟负载平均值约 10 时,CPU 实际占用只有 43%~53%——负载平均值数的是排队的任务,不是 CPU 用了多少。

- 规则(小 spec `docs/superpowers/specs/2026-10-03-cpu-usage-before-concurrency-design.md`):并行之前取 1 秒 CPU 采样(macOS `top -l 2 -n 0 -s 1`、Linux `top -bn2 -d1`,取最后一条 CPU 行,占用 = 100 − idle);超过 70% 并发按当前值减半,超过 90% 或可用内存低于 20% 串行;`uptime` 的负载平均值只在 `top` 取不到读数时才用。
- 改动:README 中英七之四第 2 条全文与三处短句;三份脚手架模板;两份 mechanical 定义;codex 的 parallel-do。章节标题「测试的进程清理与并发负载」没改名。
- 评审:spec 第一版把短写法写成「取最后一行」,在内部副本上先被盲审查出(照字面取到的是磁盘统计),改成「取最后一条 CPU 行」后本仓才实现。本仓单元盲审 2 个(opus medium)无 P0 / P1,4 条 P2(1 条已改,3 条记入「待办」表)。评审 1 轮:英文 mechanical 定义的减号统一。
- 对照实验:本批实现单元都是 sonnet + medium(规则文字改动,没有分组)。

### 2026-10-03 — 记录文档里的内部标识换成中性叫法

起因:Tony 问公开仓库里有没有写进内部的东西,核对后定「清了」。

- 做法(小 spec `docs/superpowers/specs/2026-10-03-docs-neutral-wording-design.md`):用脚本按固定对照,把 `docs/` 里的内部域名、内网地址、带用户名的本机路径、组名、同事的名字与账号编号、内部工具包与内部项目的名字、内部组件名统一换成中性叫法;Tony 原话引用里被替换的词用〔〕标注;一份文件名带内部项目名的 spec 改了名;三份评审记录里整段只讲内部副本的章节换成一句结论(原文存在内部仓库)。README 与 `plugins/` 没有改动;已推送的提交历史不改写。
- 规模:约 30 个文件、900 多处替换。
- 评审:盲审 2 个(opus medium)6 条 P1(4 类内部组件名与工具名没换、一个通用默认路径被误换、一段证据里的 JSON 被换坏)→ 修复 → 裁决(claude-fable-5-1)又查出 1 条 P1(一位同事的名字)→ 修复 → 再裁决(claude-opus-5-5)通过。评审链 `docs/reviews/2026-10-03-docs-neutral-wording-chain.md`。评审 3 轮。
- 以后:往本仓写记录直接用中性叫法;只涉及内部的批次不在本仓留细节。

### 2026-10-03 — 内部工具包的几批改动(本仓无改动)

同一天还做了几批只涉及内部工具包与本机的事(一个本机小工具、内部技能的同步、收尾规则的一处指向)。它们与公开 kit 无关,spec、评审记录与进度细节记在内部仓库,不放在本仓。本仓当天的实际改动只有下面一条里的规则 4(加记裁决模型)。

### 2026-10-03 — 提交里加记裁决模型

起因:上一批留给 Tony 的几件事里,有一条是「裁决轮的模型随会话变之后,按评审模型分段统计做不到」,Tony 答复「加上」。

- 规则(小 spec `docs/superpowers/specs/2026-10-03-adjudication-model-line-drop-external-cli-design.md`):跑过裁决轮的单元,首个提交正文在「实现模型:」之外再记一行「裁决模型:<裁决轮实际运行的模型 ID>」,评审基线按它分段。
- 改动:本仓 README 中英规则 4 各一句;本机全局规则与内部工具包里的同一句同步改。插件没有改动。
- 评审:盲审 2 个(opus medium)对本仓单元无发现;裁决(省略 model,实际运行在 claude-fable-5-1,high)通过,两条 P2 记入「待办」表。评审链 `docs/reviews/2026-10-03-adjudication-model-line-drop-external-cli-chain.md`。新规则当批就用上。
- 同一批里还有几处只涉及内部工具包与本机的改动,记录在内部仓库。
- 遗留:见「待办」表。

### 2026-10-03 — 裁决轮用主对话当前的模型 + 小改动也写小 spec 直接实现 + 并行派活统一走 Workflow(workflow/-en 0.16.0,codex 0.15.0)

起因:2026-10-02 prompt 审计报出三处跨文件说法不一,Tony 逐条拍板:「按照当前这个对话model来当评审裁决」「小改动就写一个小的spec,但是这个就不用让我看了,直接写spec就直接开干」「统一走workflow」。

- 规则(spec `docs/superpowers/specs/2026-10-03-adjudicator-model-small-spec-workflow-dispatch-design.md`):① 评审链只有最后一轮裁决改用主对话当前的模型(脚本里这一个 stage 省略 `model`、`effort: 'high'`;主对话是 Fable 就由 Fable 裁决,是 Opus 就由 Opus 裁决),盲审与续挖仍是 `opus`;② brainstorming 的小改动(bounded)路径也写一份小 spec,写完直接实现、不等用户确认,覆盖段逐个点名 brainstorming 里要等批准的四处(writing-plans 交接、User Review Gate、bounded 停下等批准、HARD-GATE 含「Too Simple To Need Approval」一节),spike 路径照原样;③ 批量与并行任务一律走 Workflow,不在一条回复里平行派裸子代理(单个子代理的一次性委派不在此列),点名覆盖 superpowers:dispatching-parallel-agents。
- 改动:README 中英第一、二、三、四、七节,第九节 whats-next 表与使用方式流程图;三份脚手架模板(Codex 版只做第 ② 条的措辞)、whats-next、scaffold 汇报句、PLAN 模板;三个插件版本号。
- 镜像:本机全局 CLAUDE.md 11 行(备份 `改前备份文件`);内部工具包(WORKFLOW.md、核心 内部版-workflow 及其 review-chain / upstream-map、parallel-do、whats-next、scaffold 与模板、driving-codex;核心 token 6534.0 → 6532.0);内部工作站 Claude 版 0.26.0、Codex 版 0.14.0(README 各加一行版本说明)。四处都已并 main;内部工具包 由 CI 升到 1.7.5,本机插件已更新,已装的核心 skill 与仓库一致。
- 验收(主对话在最终状态上重跑):全局文件与备份都是 111 行,差异只在点名的 11 行;README 发版前检查第一段末行 `ALL PASSED (8 plugins)`;各仓改动文件都在 spec 点名范围内;旧说法(「获批」「fable 裁决」「异构三方」「opus 评审 stage」「并行分派」)的剩余命中只有引用原话、历史说明与下面登记的遗留。新规则当批就用上了:四个裁决 agent 都省略 model,实际运行在 claude-fable-5-1。全程没有启动服务或浏览器,测试进程已关。
- 编排:三次 Workflow 运行、23 个 agent、约 213.7 万 token(实现 5 个 43.8 万;盲审 6 个 65.0 万;修复 5 个 37.7 万;独立测试 2 次 19.0 万;裁决 4 个 47.4 万;套用 0.9 万)。机器负载 5~10(10 核),实现与盲审并发 2,修复之后全部顺序跑。评审链 `docs/reviews/2026-10-03-adjudicator-small-spec-workflow-chain.md`。
- 对照实验:S 组 U1、U3、U5(claude-sonnet-5-5 + medium),O 组 U2、U4(claude-opus-5-5 + medium)。五个单元都有修复轮(U3、U4 各两轮);P1 里一半以上是 spec 自身的缺口或写得不清,U4 第 2 轮修复换成机械子代理、单列不归组。本批是规则文字单元、没有测试,不拿来定起跑档。
- 内部工具包 核心 skill 的 token 上限这次卡了两轮:修复 agent 两次都按要求停下报数字。最后的做法是主对话自己按该仓公式在草稿上算好一组「恢复被删内容 + 另两句换短说法」的精确替换清单,交机械子代理照单套用。
- 遗留:见「待办」表 2026-10-03 的四行。

评审 2 轮:第 1 轮(盲审 6 个)——README 第九节 whats-next 一行与流程图漏改、脚手架模板缺「小改动也写小 spec」一条、内部工作站 README 的版本说明行与开发流程句漏改、parallel-do「修完仍挂 opus high 复审」、内部工具包 核心为守 token 上限删了不该删的内容。第 2 轮(裁决)——内部工具包 核心按上限重排(恢复被删内容、覆盖段换成压缩句、另两句换短说法);英文模板一处超范围改词改回。

### 2026-10-02 — 仓库目录搬到另一个上级目录下

Tony 要求把本仓搬到本机另一个上级目录下。搬前检查:目标无重名、同一磁盘、仓库干净、只有一个 worktree,没有软链接、定时任务、别的仓库或配置写死旧路径。搬后核对:提交号、远端、工作区状态不变,8 个插件 `--strict` 校验全过。Claude 的项目状态按路径存放:记忆目录已挪到新路径对应的状态目录,旧位置留软链接,新旧路径开的会话共用一份记忆;旧会话记录留在旧路径对应的状态目录。

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
- 镜像:本机全局 CLAUDE.md 第 16、29、39、43 行(备份 `改前备份文件`);内部工具包(mechanical 定义、WORKFLOW.md 三行、README 子代理表一格、脚手架模板一行;并 main 后 CI 升到 1.7.4,本机插件已更新)。内部工作站 两个 engineer 插件没有 mechanical 子代理、模板压缩句字面仍成立,不改;workflow-codex 不涉及。
- 验收:README 两段命令从仓库根逐字执行,第一段末行 `ALL PASSED (8 plugins)`;kit 两份 mechanical 真机冒烟均为 low(主会话 high);本机已装的 `内部工具包:mechanical`(1.7.4)真机冒烟为 low;haiku 实测不报错(该模型不接收档位)。测试进程已关。
- 发版前检查第二步的数字(常驻 token,Claude Code 2.1.288):workflow 约 465、workflow-en 约 442、speak-human 约 181、speak-human-en 约 174、send-to 约 177、send-to-en 约 154、ui-sweep 约 159、ui-sweep-en 约 164。
- 编排:取证 1 个 agent(5.6 万 token);实现 4 个单元 + 盲审 4 个(57.7 万);修复 3 个 + 独立测试 1 个 + 裁决 2 个(39.0 万)。评审链 `docs/reviews/2026-10-02-cc288-abh-chain.md`。
- 对照实验:S 组 U1、U3(claude-sonnet-5-5),O 组 U2、U4(claude-opus-5-5)。有修复轮的是 U1、U3、U4,原因都是 spec 缺口或部署时序,没有一条是实现偏离 spec;样本太小,不改起跑档。
- 不覆盖与遗留:见上面「待办」表新增的五行。

评审 1 轮:同一句里保留的「mechanical 类型同理」与新例外矛盾(四个面);发版前检查两段命令的两个边界;内部工具包 README 子代理表漏改。

### 2026-10-01 — 测试启动的进程测完即关 + 并发前先看负载 + 外部进程必须写退出(workflow/-en/codex 0.14.0,ui-sweep/-en 0.2.1)

起因:Tony 三句需求——测试完要关掉相关进程;测试并发时先看电脑负载,已经很大就把并发调小;Workflow 实现派工 prompt 加一条,项目里有要启动多个无界面浏览器的地方(如 某内部项目)必须写退出进程的代码。查到的事实:某内部项目 2026-09-27 被整体关停,抓取容器里 13 个无界面 Chrome 一直不退出(最久 4 天 18 小时、约 1.9GB),Docker 虚拟机反复内存耗尽,同机另一个项目的 postgres 7 天崩溃 30 次,根因是第三方库的关闭函数出错后无限期等浏览器自己退出、浏览器调用又没有超时;提需求当时本机 10 核、1 分钟负载 31.77、69 个 claude 进程;kit 自带的 ui-sweep 引擎只在开跑时关旧会话,跑完把自己的会话和 Chrome 留在后台。spec:`docs/superpowers/specs/2026-10-01-test-process-cleanup-and-load-design.md`。

三条规则:①测试/验证/截图启动的进程谁启动谁关,失败或中途放弃也关;启动时记 PID / 端口 / 会话名,报告前逐个核对已退出(包装命令带起的子进程一起核对);只关自己启动的,不用 `pkill -f` / `killall` 按名字批量结束,别人留下的残留进程只列出来交给用户。②并行跑测试、压测或开多个并行单元前看 `uptime` 的 1 分钟负载对比核数:超过核数 70% 并发按当前值减半(最少 1),超过核数或可用内存低于 20% 改串行(盲审轮同样可以顺序跑);报告写明负载与实际并发数。③单元代码要启动外部进程(无界面浏览器、子进程、常驻 worker)时,派工 prompt 写明必须实现退出:最长存活时间到点结束整个进程组、关闭先正常后强制且等待有上限、同时存活数有上限、出错/超时/取消/启动失败的路径都关、每次调用带超时、容器加内存与进程数上限,测试覆盖卡住或出错后进程确实退出;评审核对这几条有没有实现和测到。

改动位置:README zh/en 新增「七之四 / 7d」,七.4 / 7.4 加进程约束与评审半句,§四 并发上限段加「开跑前先看负载」;三份 scaffold 模板(质量检查第 7、8 条、红线条、评审条、并发条、禁止事项)、Codex parallel-do、两份机械子代理定义同步。代码:ui-sweep 的 `sweep.mjs`(中英)在会话建立后无论正常结束、失败退出、未捕获异常还是收到 SIGINT / SIGTERM / SIGHUP 都关掉自己的 `ui-sweep` 会话,关闭失败不改退出码、往 stderr 打一行手动关闭提示;smoke 从 24 例加到 35 例;三份 sop-generate 的 `crawl.mjs` 与 `probe-login.mjs` 出错也关浏览器,关闭最多等 10 秒。私有面同批:本机全局 CLAUDE.md(新节 + 直通流程第 2 步 + 并发上限段;改前备份 `改前备份文件`)、内部工具包(merge 1204dca;核心 SKILL.md token 6534.29 → 6534.0,细则在新文件 `references/process-exit.md`)、内部工作站工具包(Claude 版) 0.25.0(merge e8ea537)、内部工作站工具包(Codex 版) 0.13.0(merge 8c6c96d)。

验证:两份 smoke 各 35 通过 / 0 失败;真实浏览器(agent-browser 0.27.0,本机临时静态页)跑新引擎,跑完会话列表里没有 `ui-sweep`;同一配置跑改动前的引擎,跑完 `ui-sweep` 会话还在(已手动关掉并核对退出)。测试用的本地静态服务按 PID 关掉、端口释放、临时目录已删。全程按规则②执行:负载 22~37 时所有子代理串行,负载 9.9 时盲审并发减半。

- 不覆盖:没有做「会话结束时自动扫残留进程」的 hook——哪个进程是本会话启动的只有启动方自己知道,hook 只能按名字结束,会误关别的会话的进程。ui-sweep 会话名仍固定为 `ui-sweep`,同一台机器同一时间只能跑一个(SKILL.md 已写明);`crawl.mjs` 与 `probe-login.mjs` 的关闭超时分支只做了语法检查与辅助函数的假对象测试,没在真实浏览器里跑过。
- 对照实验(sonnet+medium 对 opus+medium):S 组 3 个单元退回 1 个,O 组 2 个单元退回 1 个,样本太小不改起跑档;明细在评审链记录末尾。
- 评审 2 轮(kit 面):盲审 4 个(opus medium)——规则文本只有 P2 判通过,代码 1 条 P1(一个用例没测到它声称测的东西)退回;修复后裁决轮(opus high)通过,规则文本续挖轮(集成缝合点)通过。镜像面 2 轮:内部工作站 盲审通过;内部工具包 盲审 1 条 P1(为守 token 上限的压缩删掉了登录规则细则的入口),修复后裁决通过。记录:`docs/reviews/2026-10-01-test-process-cleanup-chain.md`。
