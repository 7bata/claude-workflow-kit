# 评审链:workflow-guard 并进内部工具包主插件

spec:`docs/superpowers/specs/2026-10-03-workflow-guard-into-dev-toolkit-design.md`。内部工具包分支 `wip/workflow-guard-mod`,单元首个提交 b1be6d0(变基后;实现模型 claude-opus-5-5 + medium,对照实验 O 组),另有主对话的两个提交(README 与版本号;示例里的调用名与版本说明)。按高风险单元走。

实现:搬位置、改名、两个新开关、本机版留下的三处修复;377 个测试全过(本机版 344 − 5 条 sh 回落用例 + 4 + 34),`claude plugin validate` 结果与改前相同(2 条原有警告),类型检查通过,原有冒烟脚本结果与 main 相同。约 17.2 万 token。

## 第 1 轮:盲审(3 个 opus + high,并行;机器负载 5 / 10 核;各自重跑了 validate 与 test)

| # | 位置 | 级别 | 发现 | 谁报的 |
|---|---|---|---|---|
| Y1 | `register.tsx:171` | P1 | 4.4 (2) 清掉会话 id 后,`/clear` 之后重开同名浏览器被当成「别的会话占用」而不记账;结束时不关、状态栏不显示。测试的假主机里本进程 pid 默认不算活着,所以没测出来 | 安全与集成 |
| Y2 | 核心 `stellark-workflow/SKILL.md:39`、`WORKFLOW.md:38` | P1 | 主插件自己的示例写 `agentType: 'mechanical'`,照抄会被新检查拒绝(不装 mod 时这个写法本来也解析不到) | 安全与集成 |
| Y3 | 脚手架模板 `CLAUDE.md.tmpl:130` | P1 | 同上,而且会写进每个新项目的 CLAUDE.md | 安全与集成 |
| Y4 | `hooks.json` 的 modules | P1 | 「旧版自动跳过、旧式钩子照常」只在 2.1.284 上验证过;2.1.280 的 `plugin validate` 对这个模块报错并判整个 hooks.json 失败,运行时会不会连旧式钩子一起丢没验证 | 安全与集成 |
| Y5 | `register.tsx:350` | P2 | 3 秒复查只看名字还在不在,不重新核对记录归属:窗口内被别的会话接管的名字仍会被加回并改写记录;本会话自己接管的仍被报成残留 | 三位都报 |
| Y6 | `devtoolkit.test.ts:262` | P2 | 加回时把记录的 `ownerPid` 更新为本进程没有用例断言 | 正确性 |
| Y7 | `register.tsx:484` | P2 | 注释说「deny = 确实没跑」,但旧式钩子拒绝的调用到这里是 isError;同名浏览器恰好活着又没有记录时会被记成本会话的 | 边界 |
| Y8 | `register.tsx:216` | P2 | 残留提示让用户「告诉 Claude 去关」,关掉之后记录不删、`wgOrphans` 不更新,状态栏整个会话都显示「残留 1」(本机版就有) | 边界 |
| Y9 | mod 的 README:72 | P2 | 回滚步骤没写 `-m 1` 与版本号要往前走 | 安全与集成 |

三位都核对通过的点:`scan.ts`、`host.ts` 与本机版一字未改,`register.tsx` 的差异都能归到 spec 4.2~4.4;`hooks.json` 的 hooks 部分与主干逐字相同;搬过来的用例没有被削弱,删掉的只有 sh 回落那组;每次外部调用带超时;只有一个放手的 perl 进程;非交互会话不起定时器;没有发现会误拦合规脚本的新情况;parallel-do 的示例骨架不受影响。

分流:有 P1 → 修复后裁决。主对话的处理:
- Y4 真机验证(2.1.280 与 2.1.284,真实 mod 文件加两条探测用旧式钩子):旧式钩子照常运行,mod 被跳过,只多一行提示;2.1.280 只有 `plugin validate` 这条静态检查会报错。结论:放法不用改,README 写准验证过的范围。
- Y2、Y3 主对话直接改三处示例(核心 token 6449.71 → 6453.14),Y9 直接改 README;提交 a 见分支。
- Y1、Y5、Y6、Y7、Y8 进修复轮(spec 4.6 (a)(d)(e)(f)(h)):测试与实现分开两个 agent(opus + high)。

补记(Y4 的验证用的是什么):探测插件用的是工作分支里真实的 `plugin.json`(含 `types` 与五个 `userConfig` 开关,插件名 dev-toolkit)、真实的 `types/index.d.ts` 与 `hooks/workflow-guard/` 三个文件;`hooks.json` 换成两条探测用的旧式钩子(SessionStart、PreToolUse 各写一个标记文件)加真实的 `modules` 一行。2.1.280 与 2.1.284 上两条旧式钩子都运行了,输出里有「hooks module not loaded: hooks modules are not turned on for installed plugins in this process」。

## 修复(测试与实现分开两个 agent,都是 claude-opus-5-5 + high)

测试 agent 补了 12 条用例(7 条在旧实现上失败),假主机加了「本进程的 pid 活着」的开关;实现 agent 改了 `isTakenByOther`(记录的 pid 是本进程就按自己的记录处理)、`confirmLeftovers`(复查时重读记录、核对会话 id)、新增 `dropClosedOrphan`(成功关掉残留后从名单与记录里去掉),注释与已知限制写准;改写了 1 条与 4.6 (d) 冲突的旧用例(理由:同一模块实例里那个名字还在本会话清单)。389 条全过。提交压进单元首个提交。约 22.7 万 token。

副作用与处理:主对话用 2.1.280 / 2.1.284 的二进制做兼容性探测时没有换配置目录,旧版把「mods 关闭」写进了当前配置档的缓存,之后 `claude plugin test` 报「hooks modules are turned off in this process」;修复轮的两个 agent 用临时配置目录绕过,裁决 agent 没能跑测试。主对话用当前版本联网启动一次后恢复,自己重跑 `claude plugin test`:389 过 0 败。mod 的 README 已写上这条注意事项。

## 第 2 轮:裁决(省略 model,实际运行在 claude-fable-5-1,high;高风险单元必跑)

Y1~Y9 全部闭合;核心 token 实算 6453.14,低于 6500;`hooks.json` 的 hooks 部分与主干逐字相同;回滚步骤可执行。结论:**通过**。(裁决没能跑测试,用逐条手工走查代替;主对话事后重跑确认 389 条全过。)新发现都是 P2:

- mod 自己的 README 版本范围没按 4.6 (c) 同步、「五个开关全关等于停用」说过头——主对话已直接改。
- Y4 的验证用的清单内容记录里没写——已补记在上面。
- `/clear` 交出去没关成的浏览器,记录带的是本进程的 pid,同一进程里后续会话不会提示,要换一个进程才提示(本机版就这样)。
- 3 秒复查的加回只重新核对会话 id、不重新核对启动进程;两个进程恢复同一个会话 id 且落在 3 秒窗口里才会出现。
- 没有总开关。

## 真机核对(AC6,主对话做,合并前,Claude Code 2.1.288)

先卸掉本机单独装的 `workflow-guard@tony-local-mods` 与本地市场。嵌套 `claude -p --plugin-dir <工作分支>/plugins/dev-toolkit`:漏写 effort 的 Workflow 被拦(「workflow-guard: Workflow 没有运行,请先改:第 2 行的 agent() 没写 effort…」);`agentType: 'mechanical'` 被拦并给出 `dev-toolkit:mechanical`;写 `agentType: 'dev-toolkit:mechanical'` 的合规脚本放行并跑完;主对话开的一个与 Workflow 子代理开的一个起名浏览器,会话结束后 4 秒内都不在会话清单里,没有残留进程。没做真机核对的:`wgCloseBrowsersAtEnd` 关掉时不关(只有测试)。安装后的核对见 Progress。

链共 2 轮(盲审、裁决)。用量合计约 97 万 token:实现 17.2 万、盲审 3 个 39.3 万、修复(测试 + 实现)22.7 万、裁决 17.7 万。实现与修复 claude-opus-5-5,盲审 claude-opus-5-5,裁决 claude-fable-5-1。

