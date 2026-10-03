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
