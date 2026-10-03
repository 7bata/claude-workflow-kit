# workflow-guard 并进内部工具包主插件(小 spec)

日期:2026-10-03。出处:Tony 用过本机版之后说「我觉得mods不错,直接更新到dev-toolkit里面吧」。

## 1. 目标覆盖声明

覆盖目标清单 2026-10-03「我觉得mods不错,直接更新到dev-toolkit里面吧」一行,并顺带做完本机版留下的下一版事项(「会话结束不关浏览器」的开关、评审留下的四处小问题)。不覆盖:公开 kit(不进)、huake 两个工具包(不进)、试开 You should know。

## 2. Prior art

本机版 `workflow-guard` 0.1.0:spec `2026-10-03-workflow-guard-local-mod-design.md`(第 4 节设计与 4.7、4.8 两轮修订仍然有效,本 spec 只写差异),评审链 `docs/reviews/2026-10-03-workflow-guard-local-mod-chain.md`。代码在本机仓 `~/Tony/Proj/Stellark/Projects/claude-local-mods/plugins/workflow-guard/`(hooks 三个文件约 1250 行,测试 344 条)。

## 3. 放法:并进主插件 `dev-toolkit`,不另起一个插件

理由:市场清单写的是「全员唯一工具包」;CI 自动升版只管主插件;放进去之后所有人更新就有,不用另装。

真机验证过的两件事(2026-10-03,主对话用一个同时带旧式钩子和 mod 的探测插件测的):
- Claude Code 2.1.284(mods 之前的版本):旧式钩子照常运行,mod 被跳过,只多一行「hooks modules are not turned on…」提示。
- 2.1.288 上 mod 文件写坏(解析不了):旧式钩子照常运行,mod 不加载、有一行提示。
所以 mod 出问题不会连累主插件原有的钩子(拦凭据文件、提交门禁等)。

## 4. 改动

### 4.1 搬进来的位置

```
plugins/dev-toolkit/
  .claude-plugin/plugin.json        # 加 "types": "./types/index.d.ts" 与 userConfig 五个开关(version 字段不动)
  hooks/hooks.json                  # 在原有 "hooks" 之外加 "modules": ["./workflow-guard/register.tsx"]
  hooks/workflow-guard/register.tsx
  hooks/workflow-guard/scan.ts
  hooks/workflow-guard/host.ts
  hooks/workflow-guard/README.md    # 它做什么、五个开关、需要的 Claude Code 版本、怎么停用、已知限制
  types/index.d.ts                  # PluginState 契约
  tests/workflow-guard/*.test.ts(x) + helpers.ts
```

### 4.2 因为换了插件名要改的

- `$.state` 的引用与契约改到主插件名下:`{ plugin: 'dev-toolkit', key: 'wgBrowsers' | 'wgOrphans' | 'wgLoad' }`,`types/index.d.ts` 里声明 `interface PluginState { 'dev-toolkit': { wgBrowsers; wgOrphans; wgLoad } }`。
- `$.store` 的键加前缀:`wg:browser:<名>`。
- 拒绝文字、提示与日志的开头写死成 `workflow-guard:`(不再用 `$.plugin.name`,否则会显示成 dev-toolkit)。
- `userConfig` 的键加前缀:`wgCheckEffort`、`wgCheckAgentType`、`wgCheckLoad`(原三个),默认都开。

### 4.3 新增两个开关

- `wgCloseBrowsersAtEnd`(默认开):关掉后会话结束时不交给进程去关浏览器;跟踪、状态栏照常,store 记录留着(下个交互会话会当残留提示出来,不自动关)。
- `wgShowStatusBar`(默认开):关掉后 AbovePrompt 钩子直接 `next(e)`,不起负载定时器;Workflow 检查需要负载时自己现取,不受影响。

### 4.4 本机版评审留下的四处

- (1) 去掉 sh 回落:perl 那次调用被拒或非零退出 → 只记日志,本会话清单与 store 记录都不动(下个会话当残留提示)。于是放手的进程只有 perl 一条路,寿命上限 名字数 × 20 秒 对所有情况成立。
- (2) 会话 id 不跨 `session.end` 缓存:`session.end` 处理完后清掉缓存的会话 id,下次要用时重取(`/clear` 后进程换了新 id)。残留扫描里「加回本会话清单」的条件收紧:记录的 `sessionId` 与当前相同,且记录的 `ownerPid` 为 null、已不在、或就是本进程。
- (3) 残留扫描发现疑似残留或要加回的名字时,不立刻下结论:隔 3 秒(`$.clock.after(3000, ...)`)再取一次会话清单,只对第二次还活着的名字提示或加回(刚退出的会话交出去的 close 约 0.4 秒一个,关完一两秒内名字还在清单里)。
- (4) 交接脚本没法在测试套件里真跑(测试环境没有进程):保留对脚本文本的断言,README 与本 spec 的验收里写明它在真机上验证过(卡住约 41 秒后全部退出;命令不在 PATH 时立刻退出)。

### 4.5 其他

- `.gitignore` 加 `plugins/*/.claude-plugin/types/` 与 `plugins/*/tsconfig.json`(引擎从本人目录加载 mod 时生成)。
- 仓库根 README 的说明、版本说明与 `plugin.json` 的 version 由主对话在合并前写(避免与同时在途的另一个分支冲突):minor 升一档,写明需要 Claude Code 2.1.287 及以上、旧版自动跳过。
- 外部进程约束不变(本机版 spec 4.6 加 4.8 (n)):每次调用带超时;只有一个放手的短命 perl 进程;非交互会话不起定时器。

### 4.6 评审第 1 轮修订(盲审报出 4 条 P1;与前文不一致处以本节为准)

- (a) `/clear` 之后重开同名浏览器要照常记账。4.4 (2) 清掉会话 id 之后,交接时留在 store 里的记录带的是旧会话 id 加本进程的 pid;`isTakenByOther` 把它当成「另一个还在运行的会话占用」而不记账。改:记录的 `ownerPid` 就是本进程(按需取)时,按自己的记录处理——记账并把记录改写成当前会话 id。
- (b) 主插件自己的示例不能被新检查拦下:核心 skill 第二节、`WORKFLOW.md` 机械 stage 那句、脚手架模板里的 `agentType: 'mechanical'` 改成 `'dev-toolkit:mechanical'`(主对话直接改;核心 token 6449.71 → 6453.14,仍低于 6500,没有为这 3 个 token 去压缩别处)。
- (c) 旧版本的说法写准:主对话在 2.1.280 与 2.1.284 上用真实的 mod 文件加两条探测用旧式钩子真机验证过——旧式钩子(会话开始、工具调用前)照常运行,mod 被跳过并有一行提示;2.1.280 的 `claude plugin validate` 会对这个模块报一条错误(旧的静态规则),不影响运行;比 2.1.280 更早的版本没有验证。README 照此写。
- (d) 3 秒复查时重新核对归属:复查时重读每个候选的 store 记录——要加回的,记录的 `sessionId` 仍等于当前会话 id 才加回(不等就跳过,不改写记录);疑似残留的,名字已在本会话清单里、或记录已被改写成当前会话的,就不报。加回时把记录的 `ownerPid` 更新为本进程这一点要有用例断言。
- (e) 关掉残留之后状态要跟上:本会话成功执行了对某个名字的 close,而这个名字在 `wgOrphans` 里 → 从 `wgOrphans` 去掉并删掉它的 store 记录(状态栏不再一直显示「残留 N」)。
- (f) 注释写准:旧式 PreToolUse 钩子或人工拒绝的调用到 mod 这里是 `isError`,不是 `{ deny }`。这种情况下如果同名浏览器恰好活着、store 里又没有它的记录,会被记成本会话的——README 已知限制里写明(少见:要别人用同一个名字、没有记录、而本会话的打开命令又被拦)。
- (g) 回滚步骤写准(`git revert -m 1`;version 冲突时取更高的号)。主对话已直接改 README。
- (h) 测试补齐:(a)(d)(e) 各有用例;测试里的假主机要能让「本进程的 pid 活着」。

## 5. 单元与档位

一个单元 U1,`opus` + `medium`(对照实验 O 组;本机版那个单元是 S 组),TDD:新行为(4.2~4.4)先改 / 补测试再改实现。评审按高风险单元走(所有装了内部工具包的人的每个会话都会加载,且会结束进程):盲审 3 个 `opus` + `high`(正确性、边界、安全与回滚),裁决轮必跑。

## 6. 验收

- AC1 `claude plugin validate plugins/dev-toolkit` 通过,结果不比改前差(原有 2 条 hooks 引号警告);`claude plugin test plugins/dev-toolkit` 全过;本机版 344 条用例除了按 4.2~4.4 改写的,其余原样保留。
- AC2 4.2 的改名有用例守着:state 键、store 键、拒绝文字开头、开关键名。
- AC3 4.3 两个开关各有关与开的用例:关掉 `wgCloseBrowsersAtEnd` 时结束不跑任何 perl、清单与记录都在;关掉 `wgShowStatusBar` 时不画、不起定时器,Workflow 的负载检查仍然生效。
- AC4 4.4 (1)(2)(3) 各有用例:perl 失败后没有任何 sh 调用;`session.end` 之后再记账用的是新的会话 id;加回只在 `ownerPid` 为 null、已不在或是本进程时发生;疑似残留在 3 秒后的第二次清单里不在了就不提示。
- AC5 原有旧式钩子不受影响:`hooks.json` 的 `hooks` 部分逐字不变;原有的冒烟脚本(`plugins/dev-toolkit/hooks/*smoke-test.sh` 与 `tests/` 下已有的)结果不比改前差。
- AC6 真机(主对话做):带着这一版主插件的新会话里,漏写 effort 与 `agentType: 'mechanical'` 的 Workflow 被拦、合规脚本放行;起名浏览器在会话结束后被关;`wgCloseBrowsersAtEnd` 关掉时不关;状态栏抓屏;原有钩子(例如拦凭据文件的那个)照常触发。本机先卸掉本地版 `workflow-guard@tony-local-mods` 再测,避免两份同时生效。
- AC7 回滚路径存在且可执行:`git revert` 合并提交、CI 升版、更新插件即回到没有 mod 的版本;不想回滚时五个开关都能在 `/plugin` 配置菜单里单独关;Claude Code 低于 2.1.287 的机器不受影响。

## 7. 本机的切换

合并、CI 升版后:先 `claude plugin uninstall workflow-guard@tony-local-mods --scope user` 并移除本地市场 `tony-local-mods`,再更新内部工具包插件。本机仓 `claude-local-mods` 不删,README 写明已迁入内部工具包;以后只改内部工具包里的那一份。
