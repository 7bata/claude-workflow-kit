# workflow-guard:本机 mod(Workflow 开跑前检查 + 状态栏 + 会话结束关浏览器)

日期:2026-10-03。出处:Tony 问「新更新的mods,还有插件you should know,我们有什么能利用到的地方吗」,看过六项候选后说「前两个按推荐做吧」。

## 1. 目标覆盖声明

覆盖目标清单 2026-10-03「前两个按推荐做吧」一行。不覆盖:试开 You should know(Tony 自己决定开不开遥测)、评审链面板、把现有 shell 钩子改写成 mod、工具输出遮密钥(都在候选表里标了不做或先不做)。只装在 Tony 本机,不进本仓插件,也不进内部工具包。

## 2. Prior art

mods 是 Claude Code 2.1.287 才加的,没有可复用的现成实现;规模小,没有做 GitHub 调研。参考资料只有本机内置的 `plugin-authoring` skill:`reference.md`、`examples/`(band.tsx、tool-call.ts、pane.tsx)、`types/claude-code.d.ts`(约 2 万行,按名字 grep)。

## 3. 真机探测结果(2026-10-03,2.1.288,嵌套 `claude -p --plugin-dir`,主对话做)

- `--plugin-dir` 的 mod 在 `-p` 会话里会加载;`session.start`(`isInteractive: false`、`surface: null`)与 `session.end`(`reason: "other"`)都触发。
- `agent.offer` 每轮对每个已注册的子代理类型各触发一次,`e.agent` 是注册名。本机 8 个:`claude`、`dev-toolkit:docs-extractor`、`dev-toolkit:mechanical`、`dev-toolkit:stella-recorder`、`Explore`、`general-purpose`、`Plan`、`statusline-setup`。
- `tool.call` 对主对话的 Bash、Agent、Workflow 都触发(主对话 `agentId` 缺省);Agent 工具派出的子代理里的 Bash 也触发,带 `agentId`。Workflow 的输入键是 `script`(另有 `scriptPath`、`name`、`args`、`resumeFromRunId`),Bash 是 `command`、`run_in_background`。
- 钩子返回 `{ deny: "..." }` 时调用不执行,模型收到这段文字作为出错结果。
- `claude plugin validate` 的硬规定:接收 `$` 的辅助函数必须是文件顶层的函数声明(或绑定到函数的顶层 const),不能定义在 `register` 里面;`$` 在调用处一律写成 `$.名词.方法(...)`。
- 没探测到的:Workflow 里的子代理的 Bash 调用是否也触发 `tool.call`(类型文件说 workflow 的 agent 带 `agentId`);放在验收里真机核对。

## 4. 设计

仓库:`~/Tony/Proj/Stellark/Projects/claude-local-mods`(新建,本地 git,暂无远端),同时是本地插件市场 `tony-local-mods`。mod 目录 `plugins/workflow-guard/`:

```
.claude-plugin/marketplace.json            # 仓库根:市场清单,列 workflow-guard
plugins/workflow-guard/
  .claude-plugin/plugin.json               # name、version 0.1.0、description、author、types
  hooks/hooks.json                         # { "modules": ["./register.tsx"] }
  hooks/register.tsx                       # 钩子模块
  hooks/scan.ts                            # 纯函数:脚本扫描(不碰 $)
  hooks/host.ts                            # 纯函数:解析 uptime / memory_pressure / agent-browser 命令行
  types/index.d.ts                         # PluginState 契约
  tests/*.test.ts(x)                       # claude plugin test
  README.md                                # 装、更新、停用、三项检查各拦什么
```

### 4.1 Workflow 开跑前检查(`tool.call`,matcher `{ tool: 'Workflow' }`)

脚本文本取 `e.script`;没有而有 `e.scriptPath` 时用 `$.fs.read` 读;只有 `name`(预置 workflow)时直接放行。

`scan.ts` 是一个小扫描器:跳过字符串(单引号、双引号、模板字符串含 `${}`)、行注释、块注释,只在代码层面找调用。三项检查:

1. **漏写档位**。找每个代码层面的 `agent(` 调用(前面不是 `.` 或标识符字符),按括号配平取参数:
   - 只有一个参数 → 违规。
   - 第二个参数是对象字面量:顶层有 `effort` 键(`effort:` 或简写 `effort`)→ 通过;顶层有展开 `...` → 判断不了,通过;否则违规。
   - 第二个参数不是对象字面量(变量、函数调用)→ 判断不了,通过。
   违规 → deny,点名行号:「第 N 行的 agent() 没写 effort(省略会继承会话档位)。每个 agent() 显式写 effort;裁决轮可以省 model,不能省 effort。」
2. **子代理类型名解析不到**。`agent.offer` 钩子把见过的注册名收进一个集合(只读 `e.agent`,原样 `next(e)`)。对每个对象字面量里的 `agentType: '<字面量>'`:集合非空、字面量不在集合里、且集合里有以 `:<字面量>` 结尾的名字 → deny:「第 N 行 agentType '<x>' 解析不到;本机注册名是 '<全名>'。」集合为空,或没有后缀匹配 → 放行(不猜)。
3. **负载超过核数还要并行**。脚本代码层面出现 `parallel(` 或 `pipeline(` 时才查:`sysctl -n hw.ncpu`(Linux 回落 `nproc`,结果在模块里缓存)、`uptime`(解析 macOS 的 `load averages: a b c` 与 Linux 的 `load average: a, b, c`)、`memory_pressure`(解析 `System-wide memory free percentage: N%`;命令不存在或失败就当不知道)。1 分钟负载 > 核数,或可用内存 < 20% → deny:「机器 1 分钟负载 X,超过 N 核(或:可用内存 M%,低于 20%)。把 parallel() / pipeline() 改成顺序 await,或等负载降下来再跑。」负载在核数的 70% 到 100% 之间 → 放行,`$.ui.toast`「负载 X/N 偏高,并发按减半」。

多项违规合并成一条 deny,一项一行,开头带 `$.plugin.name`。**出错一律放行**:整段检查包在 try/catch 里,读文件失败、命令失败或超时、扫描器抛错,都 `next(e)`,并 `$.ui.log` 记一行原因;负载取不到就跳过第 3 项。检查逻辑永远不改写 `e`。

`userConfig`(`plugin.json`):`checkEffort`、`checkAgentType`、`checkLoad` 三个布尔开关,默认都开;给 Tony 在 `/plugin` 的配置菜单里单独关某一项用。

### 4.2 浏览器会话跟踪(`tool.call`,matcher `{ tool: 'Bash' }`)

先 `await next(e)`,调用没被拒绝时再解析 `e.command`(`host.ts` 的纯函数):按 `;`、`&&`、`||`、`|`、换行切段,取含 `agent-browser` 的段;会话名来自 `--session <名>`、`--session=<名>` 或段首的 `AGENT_BROWSER_SESSION=<名>`,都没有记为 `default`。段里有 `close` 子命令 → 从「本会话开着的浏览器」里去掉该名(`close --all` 清空);否则加入。主对话与子代理的调用都算本会话的。

状态放 `$.state`(契约 `types/index.d.ts`):`browsers: string[]`、`orphans: string[]`、`load: { load1: number; ncpu: number; memFree: number | null } | null`。同时写 `$.store`(跨会话):键 `browser:<名>`,值 `{ sessionId, ownerPid, at }`;关掉后删除。`ownerPid` 在 `session.start` 时取一次(`$.process.run(['sh','-c','echo $PPID'])`),取不到就存 null。

### 4.3 会话结束时关掉自己起的浏览器(`session.end`,任何 reason,含 `/clear`)

对「本会话开着的浏览器」里的每个名字,顺序执行 `agent-browser --session <名> close`(`timeoutMs: 15000`)。成功 → 删 `$.store` 记录;失败或超时 → 记录留着(下个会话会当残留报出来),继续下一个。全程不抛错,最后 `next(e)`。只关本会话自己记录的名字,不按名字批量结束进程,不碰别的会话的记录。

### 4.4 残留提示(`session.start`,只在 `e.isInteractive` 时)

读 `$.store` 里所有 `browser:*` 记录,`agent-browser session list`(`timeoutMs: 5000`)取现在还活着的会话名:记录的名字已不在活着的清单里 → 删记录;还活着、`sessionId` 不是当前会话、且 `ownerPid` 为 null 或 `kill -0 <pid>` 失败 → 记入 `orphans`。有残留就 `$.ui.toast`「发现 N 个启动方已结束的浏览器会话:a、b。没有自动关,要关告诉 Claude。」**不自动关**(全局规则:不是自己启动、启动方已结束的残留进程交给 Tony 决定)。

### 4.5 状态栏(`ui.render`,matcher `{ component: 'AbovePrompt' }`)

`e.props.hasSurvey` 为真时 `next(e)`。否则画一行:`负载 5.8/10 · 内存空闲 34% · 浏览器 2(shot-a、shot-b) · 残留 1`。没有的项不画(内存取不到、浏览器 0 个、残留 0 个)。负载 > 核数用警示色加粗,70%~100% 用提醒色,其余 `dimColor`。元素从 `$.ui.resolve(e)` 取,不假设某个界面;宽度按 `e.props.bodyColumns`,放不下时先省掉浏览器名字清单、只留个数。

负载刷新:`session.start` 且 `e.isInteractive` 时立刻刷新一次,再 `$.clock.every(30000, ...)`;上一次还没跑完就跳过这一次;`-p` 等非交互会话不起定时器。刷新写 `$.state` 的 `load`,读它的状态栏自动重画。

### 4.6 外部进程约束

mod 自己起的外部命令只有:`sysctl` / `nproc`、`uptime`、`memory_pressure`、`sh -c 'echo $PPID'`、`kill -0`、`agent-browser session list`、`agent-browser --session <名> close`。每次调用都带 `timeoutMs`(查询类 5000,close 15000),都是一次性命令,不留常驻进程;同一时刻最多一个刷新在跑;任何失败、超时、取消都被接住并返回。

### 4.7 评审第 1 轮修订(以本节为准,与 4.1~4.6 不一致处按本节)

实现时已做、认可的两处偏离:`scriptPath` 与 `script` 同时给时 `scriptPath` 优先(Workflow 工具自己的规定);`session`(含 `session list`)、`help`、`--help`、`--version` 这类不起浏览器的子命令不记账。

- (a) 只在调用成功时记账:`ran.deny === undefined` 且 `ran.isError !== true`。失败或被拒的打开不加入;失败的 close 不移除(名字与 store 记录都留着)。
- (b) 没写会话名的调用不记账、不在结束时关、状态栏不计入:agent-browser 的默认会话全机共用,关它可能关掉别的会话正在用的浏览器。README 已知限制写明。
- (c) 会话名不匹配 `^[A-Za-z0-9._:-]+$`(含 `$`、反引号等要 shell 展开的写法)→ 判断不了,不记账,`$.ui.log` 记一行。
- (d) 切段前去掉 heredoc 正文(`<<`、`<<-`,定界符带不带引号都算),正文里的行不当命令。
- (e) 子命令判定要跳过带值选项的值。带值选项的清单按 `/tmp/agent-browser-help.txt`(本机 `agent-browser --help` 的输出)整理;清单外的 `--opt` 按不带值处理。
- (f) 认得常见包装写法:段首的 `timeout <n>`、`env A=B`、`command`、`exec`、`nohup`、`npx [-y] agent-browser[@版本]`;`$(...)`、反引号、`( ... )` 里的命令;`bash -c "..."` / `sh -c '...'` 引号内的文本再解析一层。
- (g) `close --all`:以应用完这条命令各段之后的清单为准,把本会话记录的名字全部从 `$.state` 与 `$.store` 去掉(含同一条命令里刚加入的)。
- (h) 4.3 加总时长上限:开始关浏览器后超过 30 秒就不再发起新的 close,剩下的记录留在 store。
- (i) `session.start` 不等残留扫描与首次刷新:取 `ownerPid` 之后,残留扫描与首次负载刷新用 `$.clock.after(0, ...)` 放到后面跑,`session.start` 立即 `next(e)`。残留扫描里 `kill -0` 最多查 20 条记录,多出来的当作判断不了(不算残留、不删)。
- (j) 定时器在模块重载后要能重新起来:AbovePrompt 的 `ui.render` 钩子里,发现本模块实例还没起定时器就起(这个钩子只在交互界面触发)。
- (k) 扫描器:`agent(...)` 的右括号后紧跟 `{` 的是方法定义,不算调用;`.` 与 `agent` 之间有空白也算成员调用,不算;`return`、`typeof`、`case`、`in`、`of`、`void`、`throw`、`yield`、`await`、`delete`、`do`、`else` 后面的 `/` 按正则字面量读。
- (l) 负载解析接受逗号小数(macOS `load averages: 4,80 6,16 8,12`,Linux `load average: 0,52, 0,48, 0,40`)。
- (m) 测试补齐:(a)~(l) 各有用例;状态栏在很窄的宽度(如 12 列)下不抛错、有合理输出;原来「不是文本」那条用例换成真的走到出错路径的输入。

## 5. 单元与档位

一个单元 U1(整个 mod 连同测试、市场清单、README),`sonnet` + `medium`(对照实验 S 组),TDD:先写 `tests/`,`claude plugin test` 看失败,再实现。评审:2 个 `opus` + `medium` 盲审(负载高时顺序跑)→ 按分流修复 / 裁决(省略 model,high)。

## 6. 验收

- AC1 `claude plugin validate plugins/workflow-guard` 通过(只允许非错误级提示);`claude plugin test plugins/workflow-guard` 全过。
- AC2 测试覆盖 4.1 三项检查各自的拦与放:只有一个参数的 `agent()`、对象字面量缺 `effort`、有 `effort`、简写、展开、变量做第二参数、字符串或注释里出现 `agent(`;`agentType: 'mechanical'` 在集合含 `dev-toolkit:mechanical` 时被拦、集合为空时放行、全名放行;有 `parallel(` 且负载超核数被拦、可用内存低被拦、没有并行写法放行、负载 70%~100% 放行并提示;`scriptPath` 读文件;只有 `name` 放行。
- AC3 出错放行有测试:`uptime` 失败或超时、`$.fs.read` 失败、扫描器遇到括号不配平的脚本,Workflow 调用都照常放行。
- AC4 4.2 的解析有测试:`--session a`、`--session=a`、环境变量写法、无会话名、同一条命令里先开后关、`close --all`、命令里只是提到 agent-browser 字样的 echo(按段解析,出现在引号里的不算)。
- AC5 4.3 有测试:会话结束时逐个 close;某个 close 失败或超时时不抛错、其余照关、失败的记录留在 store。
- AC6 4.4 有测试:残留只提示不关;已不存在的记录被清掉;当前会话自己的不算残留。
- AC7 状态栏在 terminal 与 desktop 两个界面上都能挂载(测试里循环两个界面),各项有无对应画或不画。
- AC8 真机(主对话做,嵌套 `claude -p --plugin-dir`):先在不带 mod 的会话里确认用 `agentType: 'mechanical'` 的 Workflow 在本机确实报解析不到(不成立就把第 2 项检查默认关掉);漏写 effort 的 Workflow 被拦且文字点名行号;写 `agentType: 'mechanical'` 被拦并给出 `dev-toolkit:mechanical`;合规的顺序脚本放行并真的跑起来;Workflow 里的子代理跑 Bash 时 `tool.call` 触发与否记录在案;一个真实的 `agent-browser --session wg-probe` 在会话结束后已不在 `agent-browser session list` 里。交互会话里状态栏的实际样子用 tmux 抓屏贴给 Tony 看。
- AC9 4.6 每条外部命令调用都带 `timeoutMs`;没有常驻进程;非交互会话不起定时器。

## 7. 安装与回滚

评审通过、AC8 做完后由主对话安装:`claude plugin marketplace add ~/Tony/Proj/Stellark/Projects/claude-local-mods`,`claude plugin install workflow-guard@tony-local-mods --scope user`。四个 profile 共用一个插件目录,装一次都生效,新开的会话才加载。

回滚:`claude plugin disable workflow-guard@tony-local-mods --scope user`(立刻停用,新会话不再加载);要彻底去掉再 `claude plugin uninstall`。mod 出错时引擎会跳过它继续跑,最坏情况是少了这层检查。

## 8. 已知限制

- 状态栏只在终端和桌面端画;HAPI 网页和手机上看不到,检查与关浏览器不受影响。
- 会话被强制杀掉时 `session.end` 不触发,浏览器关不了,只能靠下个会话的残留提示。
- 第 1 项检查对经变量或包装函数传入的参数判断不了,按放行处理。
- 没起名的 agent-browser 会话(默认会话)不跟踪也不关;会话名要靠 shell 展开才知道的(`$NAME`)也不跟踪。按全局规则,浏览器一律用自己起名的 `--session <名字>`。
- 「本会话开着的后台进程数」这次不做:mod 接口里没有后台任务的清单,靠猜会不准。
