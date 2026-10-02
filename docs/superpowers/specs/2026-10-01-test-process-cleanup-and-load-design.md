# 测试的进程清理、并发前看负载、外部进程必须写退出 — 设计

日期:2026-10-01
来源:Tony 本会话三句需求(目标清单 2026-10-01 三行)

## 1. 背景与依据

三件事实,都是本机查到的:

1. **进程没人关**。2026-10-01 22:28 本机有两个 agent-browser 后台进程,一个已存活 1 天 11 小时、父进程是 1(启动它的会话早已结束)。kit 自带的 ui-sweep 引擎 `sweep.mjs` 只在**开跑时**关一次旧会话(`initSession` 里的 `ab(['close'])`),跑完打印 `SWEEP DONE` 就退出,自己起的 `ui-sweep` 会话和 Chrome 留在后台。
2. **负载已高还在加并发**。2026-10-01 22:32 本机 10 核,`uptime` 1 分钟负载 31.77,69 个 claude 进程,另有别的会话在跑 vitest 与 go test。2026-09-19 已经出过一次过载事故(44 个会话加残留进程,HAPI hub 连不上)。
3. **代码里启动的浏览器不退出**。内部项目 hook-writer 于 2026-09-27 被整体关停(该仓 `docs/Progress.md` 2026-09-27、提交 ba9c6cb):抓取容器里 13 个无界面 Chrome 常驻,最久 4 天 18 小时、合计约 1.9GB,Docker 虚拟机(4GB 内存)反复内存耗尽,同机另一个项目的 postgres 7 天崩溃 30 次。根因:第三方库的关闭函数出错后无限期等浏览器自己退出、从不强制结束;浏览器调用又没有超时,54 次调用挂住 1~90 小时。修法是补丁自己管浏览器:最长存活时间到点结束整个进程组、关闭先正常后强制且等待有上限、同时最多 2 个、容器加内存与进程数上限。

## 2. 目标覆盖声明

覆盖目标清单 2026-10-01 三行(测试完关进程;并发前看负载;启动多个浏览器的代码必须写退出)。

不覆盖:2026-09-28 那条 open(sonnet 别名环境变量到期复查)与本批无关。不做自动化 hook(例如会话结束时自动扫残留进程):判断「哪个进程是本会话启动的」目前只能靠启动方自己记录,hook 拿不到这份记录,硬做只能按名字结束进程,会误关别的会话的进程。

Prior art:小规则改动,不触发调研。

## 3. 三条规则(规范文本)

下面是**公开面**的规范文本(kit README、模板用;称呼用「用户」,不出现内部项目名)。私有面(本机全局 CLAUDE.md、dev-toolkit)内容相同,只是依据句点名 hook-writer / hearloop、称呼按该文件原有写法。各面可以按该文件的体例压缩,但 §5 的要素一条都不能丢。

### 规则 T1 — 测试启动的进程,测完即关

> **测试启动的进程,测完即关**:为测试/验证/截图启动的开发服务器、mock 服务、无界面浏览器(agent-browser 会话和它带起的 Chrome、Playwright)、临时容器、后台 watch,谁启动谁关;测试失败、超时、中途放弃也要关。启动时记下 PID / 端口 / 会话名(agent-browser 一律用自己起名的 `--session <名字>`,结束时 `agent-browser --session <名字> close`),报告完成前按这份记录逐个核对(`ps -p <PID>`、`lsof -i :<端口>`),确认都已退出,报告里写一句「测试进程已关」,关不掉的列出来并说明原因。用 `npm` / `npx` 这类包装命令启动的,记下的 PID 只是包装进程,它带起的子进程要一起关、一起核对(按端口或进程组)。**只关自己启动的**:不按名字批量结束进程(`pkill -f`、`killall node`、`killall "Google Chrome"` 这类一律不用),别的会话的进程、共享服务、用户自己开的浏览器都不动;发现不是自己启动、启动方又已经结束的残留进程,列出来交给用户决定,不自行结束。

### 规则 T2 — 并发前先看负载

> **并发前先看负载**:并行跑测试、压测、多个浏览器同时截图,以及开跑有多个并行单元的 Workflow 之前,先看机器负载——`uptime` 的 1 分钟负载对比核数(macOS `sysctl -n hw.ncpu`,Linux `nproc`),内存看 `memory_pressure`(macOS)或 `free -m`(Linux)。1 分钟负载超过核数的 70%,并发数按当前值减半(没设过就按工具默认值算,最少 1);超过核数,或可用内存低于 20%,改成串行(并发 1)或等负载降下来再跑。调小的是测试工具自己的并发参数(`go test -p` / `-parallel`、vitest `--maxWorkers`、playwright `--workers`、压测的并发数)和同时跑测试的单元数;Workflow 里的做法是少开并行单元、用顺序 `await` 分批(评审的盲审轮同样可以改成顺序跑——各评审互相看不到结论,盲审照样成立),派工 prompt 写明本单元测试可用的并发数。报告里写明看到的负载和实际用的并发数。

T1、T2 的适用范围句(放在两条之前):

> 跑测试、验证、截图、ui-sweep 走查都适用;主对话、实现 agent、评审 agent 都要守,派工 prompt 里写明(`mechanical` 子代理不加载 CLAUDE.md,更要写)。

### 规则 W1 — 单元代码要启动外部进程时,派工 prompt 写明必须实现退出

写进「Workflow 编排实现」那一步(README 七.4 / 全局 CLAUDE.md 直通流程第 2 步)实现 agent 的 prompt 清单,紧跟在「生产红线与文件所有权」之后:

> + **进程约束**——测试启动的进程测完即关、并发前先看负载(见七之四);单元代码要启动外部进程时(无界面浏览器如 agent-browser / Chrome / Playwright、子进程、常驻 worker,尤其是同时或反复启动多个的),写明必须实现退出:每个进程有最长存活时间、到点结束整个进程组;关闭先正常关、不行就强制结束,等待有上限、任何情况都返回;同时存活的数量有上限;出错、超时、取消、启动失败的路径都要关;对外部进程的每次调用带超时;跑在容器里的再加内存与进程数上限;测试要覆盖「卡住或出错后进程确实退出」。依据:一个真实项目的抓取服务里 13 个无界面 Chrome 一直不退出(最久 4 天多、约 1.9GB),容器虚拟机反复内存耗尽,同机另一个项目的数据库 7 天崩溃 30 次,服务被整体停掉——根因是关闭函数出错后无限期等浏览器自己退出、从不强制结束,浏览器调用又没有超时

同一步里评审那句同步补半句:

> 评审除核对实现外必须核对**测试本身**(是否覆盖 spec 对应验收条款、是否只测 happy path;启动外部进程的单元还要核对上面几条退出要求有没有实现、有没有测到)

## 4. 各面落点

| 面 | 文件 | 改什么 | 谁做 |
|---|---|---|---|
| 本机全局 | `~/.claude/CLAUDE.md`(不在 git,改前备份 `CLAUDE.md.bak-20261001-test-process-cleanup`) | 新节「测试的进程清理与并发负载」(T1、T2);直通流程第 2 步加 W1 与评审半句;并发上限那段加一句「开跑前先看负载」 | 主对话 |
| kit README | `README.zh-CN.md`、`README.md` | 新增「七之四、测试的进程清理与并发负载」(英文 7d;T1、T2 加适用范围句,末尾一句依据:不点名内部项目);七.4 加 W1 与评审半句;§四 并发上限段末尾加一句「开跑前主对话先看一次负载(见七之四第 2 条),已高就少开并行单元或分批跑,不调高上限」 | U1 |
| kit 模板 | `plugins/workflow/skills/scaffold/templates/CLAUDE.md.tmpl`、`plugins/workflow-en/…/CLAUDE.md.tmpl`、`plugins/workflow-codex/skills/scaffold/templates/AGENTS.md.tmpl` | 「修改后质量检查」加两条(T1、T2 压缩版);多代理分工里「派实现 agent 的 prompt…必须点名生产红线」那条末尾接 W1 压缩版;并发上限那条末尾接「开跑前先看负载」;「禁止事项」加一行「测试启动的进程测完不关」 | U2 |
| kit Codex | `plugins/workflow-codex/skills/parallel-do/SKILL.md` | 步骤 5「边界」那条接 T1、T2、W1 压缩版;并发上限处接「分批前先看负载」 | U2 |
| kit 机械子代理 | `plugins/workflow/agents/mechanical.md`、`plugins/workflow-en/agents/mechanical.md` | 通用要求段末尾加两句:为检查启动的进程检查完就关、只关自己启动的;要并行跑检查先看 `uptime`,1 分钟负载超过核数就串行 | U2 |
| kit 版本号 | `plugins/workflow/.claude-plugin/plugin.json`、`workflow-en` 同名文件、`plugins/workflow-codex/.codex-plugin/plugin.json` | 0.13.1 → 0.14.0(workflow、workflow-en);0.13.0 → 0.14.0(workflow-codex) | U2 |
| kit ui-sweep | `plugins/ui-sweep/skills/ui-sweep/`、`plugins/ui-sweep-en/skills/ui-sweep/` | 见 §6 | U3 |
| kit sop-generate | `plugins/workflow/skills/sop-generate/`、`workflow-en`、`workflow-codex` 三份 | 见 §6 | U3 |
| dev-toolkit | 见 §7 | 镜像 | U4(kit 评审通过后) |
| huake 两个工具包 | 见 §7 | 镜像 | U5(kit 评审通过后) |

模板里的压缩版(中文;英文版对应翻译,Codex 版把 Workflow 说法换成该文件自己的并行说法):

- 质量检查新增两条:
  - `测试、验证、截图启动的进程(开发服务器、mock 服务、无界面浏览器、临时容器)测完即关,失败或中途放弃也要关;启动时记下 PID / 端口 / 会话名,报告完成前逐个核对已退出(npm / npx 这类包装命令带起的子进程一起关、一起核对);只关自己启动的,不用 pkill -f / killall 按名字批量结束,别人留下的残留进程只列出来报告`
  - `并行跑测试、压测或开多个并行单元前先看负载(uptime 的 1 分钟负载对比核数,核数 macOS 用 sysctl -n hw.ncpu、Linux 用 nproc):超过核数 70% 并发按当前值减半(最少 1),超过核数或可用内存低于 20% 改串行;报告写明负载与实际并发数`
- 红线那条末尾接:`;测试启动的进程测完即关、并发前先看负载(§3 第 7、8 条);单元代码要启动外部进程(无界面浏览器、子进程、常驻 worker)时写明必须实现退出:最长存活时间到点结束整个进程组、关闭先正常后强制且等待有上限、同时存活数有上限、出错/超时/取消/启动失败的路径都关、每次调用带超时、容器加内存与进程数上限,测试覆盖卡住或出错后进程确实退出`(条号以该模板实际编号为准)
- 禁止事项新增:`测试启动的进程测完不关(开发服务器、浏览器、容器;失败路径同样要关),或按名字批量结束进程`

## 5. 要素清单(评审逐面核对)

T1 七个要素:①范围含测试/验证/截图;②举例含开发服务器、无界面浏览器、容器;③失败或放弃也要关;④启动时记录 PID/端口/会话名;⑤报告前核对已退出;⑥只关自己启动的;⑦不按名字批量结束进程。

T2 五个要素:①触发场景含并行测试与开多个并行单元;②看 `uptime` 1 分钟负载对比核数;③超过 70% 减半;④超过核数(或内存低于 20%)串行;⑤报告写明负载与实际并发数。

W1 七个要素:①触发条件是单元代码启动外部进程(举例含无界面浏览器);②最长存活时间、到点结束整个进程组;③关闭先正常后强制、等待有上限;④同时存活数有上限;⑤出错/超时/取消/启动失败路径都关;⑥调用带超时;⑦测试覆盖出错后进程确实退出。容器上限与依据句在完整版(README、全局、WORKFLOW.md)必须有,压缩版可省依据句。

完整版(全局 CLAUDE.md、kit README zh/en、dev-toolkit WORKFLOW.md)要素必须全。压缩版(模板、parallel-do、核心 SKILL.md)允许压缩措辞,T1 至少保留 ③④⑤⑥⑦,T2 至少保留 ②③④,W1 至少保留 ①②③④⑤⑥⑦。机械子代理定义只要求 T1 的「检查完就关、只关自己启动的」与 T2 的「超过核数就串行」。

## 6. U3:ui-sweep 引擎跑完关会话;sop-generate 核对

**ui-sweep(`sweep.mjs`,中英两份,改法相同)**:

- 会话建立之后,引擎无论怎么结束都要关掉自己的 `ui-sweep` 会话:正常跑完(`SWEEP DONE` 之前或之后)、会话建立后的 `process.exit(1)` 分支、未捕获异常、收到 SIGINT / SIGTERM。做法建议:一个 `sessionStarted` 标志加统一的收尾函数(`ab` 是同步调用,可以在 `process.on('exit')` 里用);关闭失败不改变原退出码。
- `--check-config` 等在建会话之前就退出的旗标分支不建会话,也不应多出一次 close 调用以外的副作用(保持现有输出不变)。
- 不加「保留会话」的开关。`SKILL.md` 相应说明:引擎跑完自动关会话;人工复核真缺陷时另起一个自己起名的会话,复核完 `agent-browser --session <名字> close`。
- `smoke-test.mjs` 增加用例:会话建立后正常结束会发出 close;会话建立后的失败退出也会发出 close;建会话之前退出的分支不受影响。现有用例全部保持通过。smoke 现在怎么隔离真实浏览器就沿用那套办法(例如 PATH 上放一个记录参数的假 `agent-browser`);确实只能靠真实浏览器才测得到的,报告里写明哪条没测到。
- `export-state.mjs`:读一遍,如果它启动了浏览器或会话而出错路径不关,按同样原则补上;没有就不动,报告里写一句核对结论。
- 版本号 `plugins/ui-sweep/.claude-plugin/plugin.json` 与 `ui-sweep-en` 同名文件 0.2.0 → 0.2.1。

**sop-generate(三份:workflow、workflow-en、workflow-codex)**:

- `scripts/crawl.mjs`:`browser.close()` 现在只在正常路径末尾;改成出错也会关(try/finally 或等价写法),三份一致。`probe-login.mjs`(workflow-codex 有)同样核对。
- `SKILL.md`:在截图流程结束处加一句——截图用的 agent-browser 会话与为截图启动的应用进程,截完即关(T1),只关自己启动的。

## 7. 镜像(kit 评审通过后做,文本以 kit 定稿为准)

**dev-toolkit**(`~/Tony/Proj/Stellark/Platform/dev-toolkit`,worktree 放它的 `.worktrees/`;不改 version,CI 自动升):

- `WORKFLOW.md`:完整版 T1、T2 新小节(编号取该文件下一个空号,别与已有「七之四」冲突)、七.4 加 W1(可点名 hook-writer 依据)、§四 并发段加「开跑前先看负载」。
- `plugins/dev-toolkit/skills/stellark-workflow/SKILL.md`:核心压缩版。**有 token 上限**:按 `docs/reviews/2026-09-23-slim-c/c1-map.md` 的公式算,改后不得高于改前。GUARD 模板现有「测试卫生:临时目录/文件自动清理;子进程整组回收;重型用例可跳过并标明」一行,在这一行上改写并入 T1(测试启动的服务/浏览器测完即关、只关自己启动的)与 T2(并发前看负载);W1 细则放 `references/`(新文件或并入现有),核心只留触发条件加指向;用别处等量压缩抵消增量,压缩不得丢要素。
- `references/upstream-map.md`:归位表补本批三条,核心句数与 WORKFLOW.md 行数跟着改。
- `plugins/dev-toolkit/skills/stellark-scaffold/templates/CLAUDE.md.tmpl`、`plugins/dev-toolkit/agents/mechanical.md`、`plugins/dev-toolkit/skills/stellark-parallel-do/SKILL.md`:同 kit 对应文件。
- `plugins/dev-toolkit/skills/ui-sweep/`、`sop-generate/`:同 §6(以 kit 定稿的代码为准)。

**huake**(`~/Tony/Proj/Stellark/Platform/claude-toolkit-engineer`、`codex-toolkit-engineer`;手动升版本号并在各自 README 版本记录加一行):

- claude 版:`skills/scaffold/templates/CLAUDE.md.tmpl`(质量检查两条、红线条接 W1、禁止事项一行)、`skills/parallel-do/SKILL.md`、`skills/ui-sweep/`、`skills/sop-generate/`(同 §6)。没有 mechanical 子代理,不加。
- codex 版:`skills/scaffold/templates/AGENTS.md.tmpl`、`skills/parallel-do/SKILL.md`、`skills/sop-generate/`(同 §6);没有 ui-sweep。
- huake 面不点名 stellark 内部项目(用公开面的依据句)。

## 8. 验收条款

1. 全局 CLAUDE.md、kit README zh/en 三处完整版里,T1、T2、W1 要素(§5)全部在;README 英文版与中文版逐条对应,阈值数字一致(70%、核数、20%)。
2. 三份 scaffold 模板、Codex parallel-do、两份 mechanical 定义按 §4 加好,压缩版保留 §5 规定的最少要素;英文模板不夹中文,Codex 版不出现 Claude 专有说法(Workflow `agent()`、`mechanical`)。
3. 公开面(本仓 `README*`、`plugins/`)不出现 hook-writer、hearloop 及任何内部主机名/仓路径。
4. `sweep.mjs`(中英)会话建立后的所有结束路径都会关 `ui-sweep` 会话;smoke 测试新增用例覆盖正常结束与失败退出两条路径并通过,原有用例全过。
5. 三份 `crawl.mjs` 出错路径也关浏览器。
6. 版本号按 §4、§6 升好;`docs/Progress.md`、`docs/PLAN.md` Spec 索引更新;目标清单三行改 done 并附证据。
7. dev-toolkit 核心 SKILL.md 的 token 数不高于改前;镜像面要素齐全。
8. 新增规则文本不使用 speak-human S5 词库左列的词(兜底、落地、收口、闭环、链路等),引用既有章节名除外。

## 9. 回滚

- 全局 CLAUDE.md:`cp ~/.claude/CLAUDE.md.bak-20261001-test-process-cleanup ~/.claude/CLAUDE.md`。
- kit / dev-toolkit / huake 两仓:各自 `git revert -m 1 <merge sha>`;手动管版本号的插件回滚时版本号继续往上加。dev-toolkit 回滚后等 CI 升版再更新本机插件。
