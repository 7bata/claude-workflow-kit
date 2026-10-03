# 评审链:本机 mod workflow-guard(U1)

spec:`docs/superpowers/specs/2026-10-03-workflow-guard-local-mod-design.md`。代码仓:本机 `~/Tony/Proj/Stellark/Projects/claude-local-mods`(暂无远端),分支 `wip/workflow-guard-v1`,首个提交 aa022a2。

实现:claude-sonnet-5-5 + medium(对照实验 S 组),TDD;`claude plugin validate` 通过,`claude plugin test` 123 过 0 败;用 npx 临时装的 tsc 类型检查 0 错误。约 17.8 万 token。

## 第 1 轮:盲审(2 个 opus + medium,顺序跑;各自重跑了 validate 与 test)

两位都把所有发现标为 P2。主对话合并后的清单(R = 正确性镜头,E = 边界镜头):

| # | 位置 | 发现 | 谁报的 | 主对话定级 |
|---|---|---|---|---|
| W1 | `host.ts` 无会话名记为 default | 默认会话全机共用,本会话结束时会关掉别的会话正在用的浏览器 | R、E | P1(违反「只关自己启动的」,属 spec 4.2 的缺口) |
| W2 | `host.ts` 切段 | heredoc 正文里以 agent-browser 开头的行被当成真调用,可能记下并关掉别的会话的浏览器 | E | P1(同上) |
| W3 | `register.tsx:300` | 只看 `deny` 不看 `isError`:失败的 close 也把名字从清单与 store 删掉,浏览器无声泄漏;失败或被下层拒绝的打开照样记账 | R、E(测试缺口) | P1(漏关且不报残留,与 4.3 / 4.4 的目的相反) |
| W4 | `host.ts:147` | 带值选项的值被当成子命令(`--profile /p close` 记成打开) | R、E | P2 |
| W5 | `host.ts:151` | `--session "$NAME"` 记下字面量,关不掉也不报残留 | R、E | P2 |
| W6 | `host.ts:115` | `timeout 30 agent-browser`、`npx agent-browser@x`、`$(...)`、子 shell、`bash -c` 不认 | E | P2 |
| W7 | `register.tsx:220` | `session.start` 串行等多条命令,卡住时首个提示被拖 25 秒以上 | R | P2 |
| W8 | `register.tsx:163` | 结束时逐个 close 没有总时长上限 | E | P2 |
| W9 | `register.tsx:229` | 定时器只在 `session.start` 起,模块重载后状态栏一直显示旧负载 | E | P2 |
| W10 | `register.tsx:149` | `close --all` 漏删同一条命令里刚写入的 store 记录 | E | P2 |
| W11 | `scan.ts:238` | 名叫 agent 的对象 / 类方法定义被当成调用,合规脚本被拦;`foo . agent(` 也算 | E | P2 |
| W12 | `scan.ts:82` | 关键字后的正则字面量被读成除号,扫描器抛错后整次检查放行 | E | P2 |
| W13 | `host.ts:4` | 负载解析不认逗号小数 | E | P2 |
| W14 | 测试 | 缺:被拒 / 出错的 Bash 不记账;关键字后的正则;名叫 agent 的方法;很窄的状态栏;「不是文本」用例没走到出错路径 | R、E | P2(随修复补齐) |
| W15 | `register.tsx:108` | 第 2 项检查假设不带前缀的 `mechanical` 解析不到,但本批没有重新验证 | E | P2(放进 AC8) |

两位都核对通过的点:4.1 判定表逐行;出错放行的每条路径;多项违规合并成一条;结束时只遍历本会话的清单;残留只提示不关;每条外部命令都带超时;非交互会话不起定时器;没有常驻进程;状态栏两个界面;断言检验的是行为。

分流:主对话把 W1、W2、W3 定为 P1(盲审标 P2,定级理由见表)→ 修复后裁决。spec 加 4.7 修订 (a)~(m),AC8 加一步。修复按打回流程:测试与实现分开两个 agent(sonnet + high),先补测试再改实现。

## 修复(第 1 轮之后;测试与实现分开两个 agent,都是 claude-sonnet-5-5 + high)

测试 agent 补了 151 条用例(共 274 条,其中 112 条在旧实现上失败),改写了 2 条与 4.7 (b) 矛盾的旧用例、删了 1 条没走到出错路径的旧用例;实现 agent 没动测试,274 条全过,`claude plugin validate` 通过,类型检查通过。提交 1ae1e3a(压进 aa022a2)。约 30.5 万 token。主对话真机确认了 W15:不带 mod 时 `agentType: 'mechanical'` 的 Workflow 在本机报 `agent type 'mechanical' not found`。

## 第 2 轮:裁决(省略 model,实际运行在 claude-fable-5-1,high)

W1~W14 全部闭合;W1、W2、W3 定为 P1 的判断成立(W2 偏严但可接受)。修复没有削弱原有用例。结论:**不通过**,新发现:

| # | 位置 | 级别 | 发现 |
|---|---|---|---|
| X1 | `register.tsx:169` | P1 | 接口声明写明 `session.end` 整条链只有约 1.5 秒,到点在途的 `$` 调用被中止。逐个 close(每个 15 秒、总上限 30 秒)在真机上会被切断,「会话结束关掉自己起的浏览器」只对一个且关得快的浏览器成立。测试全过是因为测试套件的根 next 不计时 |
| X2 | `register.tsx:341` | P1 | 4.7 (a) 对打开一侧矫枉过正:`isError` 涵盖命令跑了一部分的情况(后一步超时、被打断),浏览器已起来却没记账,结束时不关、下个会话也不提示。属 spec 的决定,不是实现偏差 |
| X3 | `host.ts:170` | P2 | 切段不认 shell 注释,注释里的命令被记账或把后面的真调用吞掉 |
| X4 | `register.tsx:158` | P2 | 记账不看 store 里已有记录的归属,会接管别的会话正在用的名字并在结束时关掉 |
| X5 | `host.ts:36` | P2 | 可用名字允许以 `-` 开头(`--session --all`),结束时的 close 可能被读成 `close --all` |
| X6 | `register.tsx:219` | P2 | 恢复的会话:上个进程留下的同 `sessionId` 记录既不报也不关;没见过 `session.start` 的模块实例 `ownerPid` 一直是 null |

分流:裁决轮报出新 P1 → 修复后再裁决(计入上限,下一轮是第 3 轮)。主对话真机量了 close 耗时(约 0.4 秒)与会话清单的真实格式,spec 加 4.8 修订 (n)~(u):X1 改成交给放手的短命进程去关;X2 改成出错时以会话清单的实际情况为准;X3~X6 一并修。

## 修复(第 2 轮之后;测试与实现分开两个 agent,都是 claude-sonnet-5-5 + high)

测试 agent 按 4.8 补用例、改写了与 4.8 矛盾的旧用例(共 344 条,53 条在旧实现上失败);实现 agent 只改了一处测试输入(状态栏用例里的会话清单换成真实格式,断言没动),344 条全过,`claude plugin validate` 通过,类型检查通过;它还用假的 agent-browser 把交接脚本真跑了一遍。提交 8cca482(压进单元提交)。约 24.8 万 token。

## 第 3 轮:裁决(省略 model,实际运行在 claude-fable-5-1,high;镜头:回滚与可逆性、集成缝合点)

X1~X6 全部闭合,没有削弱与 4.8 无关的用例。结论:**通过**。新发现都是 P2,记遗留:

- sh 回落这条路没有寿命上限(perl 不存在且某个 close 卡住时,后台子 shell 会一直留着);本机有 /usr/bin/perl,要两个少见情况叠加才出现。
- `/clear` 之后会话 id 没刷新,配合「加回自己的记录」只比会话 id:在另一个终端恢复 `/clear` 之前的会话时,可能把还在运行的进程正在用的浏览器加进自己的清单并在结束时关掉。
- 交出去的 close 与下一个会话的残留扫描之间没有协调:退出后几秒内就开的新会话可能看到名字还在清单里,弹一条假的残留提示。
- 交接脚本本身没有被测试真正执行过(只断言文本里有关键词)——已由主对话在下面的真机核对里补上。

## 真机核对(AC8,主对话做,2026-10-03,Claude Code 2.1.288,agent-browser 0.27)

- 不带 mod:`agentType: 'mechanical'` 的 Workflow 报 `agent type 'mechanical' not found`(W15 的前提成立)。
- 交接脚本直接跑:关闭命令卡住(假的 agent-browser 睡 600 秒)、两个名字 → perl 立即返回,约 41 秒后进程全部退出(每个 20 秒被结束);PATH 里没有 agent-browser → 立即退出;都没有残留进程。
- 嵌套 `claude -p --plugin-dir`:漏写 effort 的 Workflow 被拦,文字是「第 2 行的 agent() 没写 effort…」;`agentType: 'mechanical'` 被拦并给出 `dev-toolkit:mechanical`;合规的顺序脚本放行并跑完;主对话开的三个起名浏览器(其中一个的命令以非零退出码结束)加 Workflow 子代理里开的一个,会话结束后 3 秒内四个都不在会话清单里,没有残留进程(说明 Workflow 子代理里的 Bash 调用也触发 `tool.call`)。
- 交互会话(tmux 抓屏):状态栏显示「负载 5.28/10 · 内存空闲 42%」;开一个起名浏览器后显示「负载 5.88/10 · 内存空闲 36% · 浏览器 1(wg-ac8-band)」;`/exit` 后 5 秒内浏览器已关。
- 跨会话记录文件在 `~/.claude/plugins/store/` 下,四个 profile 共用(plugins 目录是软链接)。
- 安装后(不带 `--plugin-dir` 的新会话):漏写 effort 的 Workflow 同样被拦。
- 核对用的浏览器、tmux 会话、临时目录与测试留下的记录文件都已清掉。

链共 3 轮(盲审、裁决、裁决),未到上限。用量合计约 131 万 token:实现 17.8 万、盲审 2 个 23.8 万、第 1 次修复(测试 + 实现)30.5 万、裁决 17.6 万、第 2 次修复 24.8 万、裁决 16.3 万。实现与修复都是 claude-sonnet-5-5,盲审 claude-opus-5-5,裁决 claude-fable-5-1。
