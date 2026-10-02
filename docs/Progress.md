# Progress

## 进度总览

| 模块 | 状态 | 备注 |
|---|---|---|
| workflow / workflow-en(方法论 prompt + scaffold/whats-next/sop-generate) | done | 0.14.0;测试启动的进程测完即关、并发前看负载、单元代码启动外部进程时派工 prompt 写明退出要求;omitClaudeMd 机械 agent(agents/mechanical.md)、并发上限 env 文档;进度日志按月归档、评审轮次压进单元提交;需求先复述再动手、worktree 用完即删 + worktree-sweep hook;含目标台账、四点评审纪律、调研内部先行、组件索引三入口、docs-capture 三层 hook(kit/github 面)、main 门禁只拦前端可见改动、截图交付前视觉预审 |
| workflow-codex(Codex CLI 移植版) | done | 0.14.0;测试进程清理、并发前看负载、外部进程退出要求同步;无 hook 机制,auto-scaffold 靠手动 opt-in;omitClaudeMd 判为 Claude 专有、并发对应 `[agents] max_threads` |
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
| docs-capture 英文词表召回窄(approve/ship/stick with 未覆盖,U2 评审记录),按宁漏勿错接受,待实际使用数据再扩 | 2026-08-14 U2 评审 | 低 |

## 变更日志(最新在上)

> 更早的日志按月在 docs/archive/Progress-YYYY-MM.md

### 2026-10-01 — 测试启动的进程测完即关 + 并发前先看负载 + 外部进程必须写退出(workflow/-en/codex 0.14.0,ui-sweep/-en 0.2.1)

起因:Tony 三句需求——测试完要关掉相关进程;测试并发时先看电脑负载,已经很大就把并发调小;Workflow 实现派工 prompt 加一条,项目里有要启动多个无界面浏览器的地方(如 hook-writer)必须写退出进程的代码。查到的事实:hook-writer 2026-09-27 被整体关停,抓取容器里 13 个无界面 Chrome 一直不退出(最久 4 天 18 小时、约 1.9GB),Docker 虚拟机反复内存耗尽,同机另一个项目的 postgres 7 天崩溃 30 次,根因是第三方库的关闭函数出错后无限期等浏览器自己退出、浏览器调用又没有超时;提需求当时本机 10 核、1 分钟负载 31.77、69 个 claude 进程;kit 自带的 ui-sweep 引擎只在开跑时关旧会话,跑完把自己的会话和 Chrome 留在后台。spec:`docs/superpowers/specs/2026-10-01-test-process-cleanup-and-load-design.md`。

三条规则:①测试/验证/截图启动的进程谁启动谁关,失败或中途放弃也关;启动时记 PID / 端口 / 会话名,报告前逐个核对已退出(包装命令带起的子进程一起核对);只关自己启动的,不用 `pkill -f` / `killall` 按名字批量结束,别人留下的残留进程只列出来交给用户。②并行跑测试、压测或开多个并行单元前看 `uptime` 的 1 分钟负载对比核数:超过核数 70% 并发按当前值减半(最少 1),超过核数或可用内存低于 20% 改串行(盲审轮同样可以顺序跑);报告写明负载与实际并发数。③单元代码要启动外部进程(无界面浏览器、子进程、常驻 worker)时,派工 prompt 写明必须实现退出:最长存活时间到点结束整个进程组、关闭先正常后强制且等待有上限、同时存活数有上限、出错/超时/取消/启动失败的路径都关、每次调用带超时、容器加内存与进程数上限,测试覆盖卡住或出错后进程确实退出;评审核对这几条有没有实现和测到。

改动位置:README zh/en 新增「七之四 / 7d」,七.4 / 7.4 加进程约束与评审半句,§四 并发上限段加「开跑前先看负载」;三份 scaffold 模板(质量检查第 7、8 条、红线条、评审条、并发条、禁止事项)、Codex parallel-do、两份机械子代理定义同步。代码:ui-sweep 的 `sweep.mjs`(中英)在会话建立后无论正常结束、失败退出、未捕获异常还是收到 SIGINT / SIGTERM / SIGHUP 都关掉自己的 `ui-sweep` 会话,关闭失败不改退出码、往 stderr 打一行手动关闭提示;smoke 从 24 例加到 35 例;三份 sop-generate 的 `crawl.mjs` 与 `probe-login.mjs` 出错也关浏览器,关闭最多等 10 秒。私有面同批:本机全局 CLAUDE.md(新节 + 直通流程第 2 步 + 并发上限段;改前备份 `~/.claude/CLAUDE.md.bak-20261001-test-process-cleanup`)、dev-toolkit(merge 1204dca;核心 SKILL.md token 6534.29 → 6534.0,细则在新文件 `references/process-exit.md`)、huake claude-toolkit-engineer 0.25.0(merge e8ea537)、codex-toolkit-engineer 0.13.0(merge 8c6c96d)。

验证:两份 smoke 各 35 通过 / 0 失败;真实浏览器(agent-browser 0.27.0,本机临时静态页)跑新引擎,跑完会话列表里没有 `ui-sweep`;同一配置跑改动前的引擎,跑完 `ui-sweep` 会话还在(已手动关掉并核对退出)。测试用的本地静态服务按 PID 关掉、端口释放、临时目录已删。全程按规则②执行:负载 22~37 时所有子代理串行,负载 9.9 时盲审并发减半。

- 不覆盖:没有做「会话结束时自动扫残留进程」的 hook——哪个进程是本会话启动的只有启动方自己知道,hook 只能按名字结束,会误关别的会话的进程。ui-sweep 会话名仍固定为 `ui-sweep`,同一台机器同一时间只能跑一个(SKILL.md 已写明);`crawl.mjs` 与 `probe-login.mjs` 的关闭超时分支只做了语法检查与辅助函数的假对象测试,没在真实浏览器里跑过。
- 对照实验(sonnet+medium 对 opus+medium):S 组 3 个单元退回 1 个,O 组 2 个单元退回 1 个,样本太小不改起跑档;明细在评审链记录末尾。
- 评审 2 轮(kit 面):盲审 4 个(opus medium)——规则文本只有 P2 判通过,代码 1 条 P1(一个用例没测到它声称测的东西)退回;修复后裁决轮(opus high)通过,规则文本续挖轮(集成缝合点)通过。镜像面 2 轮:huake 盲审通过;dev-toolkit 盲审 1 条 P1(为守 token 上限的压缩删掉了登录规则细则的入口),修复后裁决通过。记录:`docs/reviews/2026-10-01-test-process-cleanup-chain.md`。
