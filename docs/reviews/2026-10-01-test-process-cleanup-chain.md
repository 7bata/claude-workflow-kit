# 评审链:测试的进程清理、并发前看负载、外部进程必须写退出(kit 面)

spec:`docs/superpowers/specs/2026-10-01-test-process-cleanup-and-load-design.md`。本文件由主对话维护,每轮结束后追加;下一轮评审 prompt 给本文件路径,轮次计数由本文件继承。

单元与实现模型:U1 README zh/en(claude-sonnet-5-5,medium,S 组);U2 模板、Codex 并行技能、机械子代理定义(claude-opus-5-5,medium,O 组);U3 ui-sweep 引擎与 sop-generate 脚本(claude-sonnet-5-5,medium,S 组)。评审按两组走:规则文本(U1+U2)、代码(U3)。

执行方式:2026-10-01 本机 10 核、1 分钟负载 24~37,按新规则串行跑(并发 1),盲审各自独立、互相看不到结论。


## 第 1 轮 盲审 — 规则文本(U1+U2)(claude-opus-5-5,medium,2 个)

| # | 严重度 | 位置 | 评审者 | 发现 |
|---|---|---|---|---|
| T1 | P2 | README.zh-CN.md:216 | text-A | README 说 `mechanical` 定义里「自带三条通用要求」并逐条列出,但本批在 plugins/workflow/agents/mechanical.md 里加了两句（检查完就关、只关自己启动的;负载超过核数就串行）,这里的描述没跟着改,已过时。应补上这两条,或改成不写条数的说法。 |
| T2 | P2 | README.md:215 | text-A | 英文 README 描述 mechanical 定义时同样说有 three general requirements 并逐条列出,没有补上本批新加的进程清理和负载两句,与 plugins/workflow-en/agents/mechanical.md 的实际内容不一致。 |
| T3 | P2 | README.md:322 | text-A | 7d 的依据句写的是「(see 7.4)」,而英文 README 别处引用同一步都写「see Section 7.4」（第 197、221 行）;体例不统一,建议改成「see Section 7.4」。 |
| T4 | P2 | README.zh-CN.md:321 | text-B | 七之四第 2 条说负载超过核数就「改成串行(并发 1)」,还适用于「开跑有多个并行单元的 Workflow」;但同一个 prompt 的三.2 和七.4 规定盲审轮必须用 `await parallel()` 平行派 2~3 个评审 agent。负载高时,agent 不知道盲审轮能不能改成顺序跑。改成顺序跑时,只要各评审互相看不到结论,盲审照样成立。应补半句:盲审轮可以改成顺序 await,仍然各自独立。英文版第 320 行 7d item 2 有同样问题。 |
| T5 | P2 | README.zh-CN.md:321 | text-B | T1 要求 agent-browser「一律用自己起名的 --session」,并且「只关自己启动的」;但 kit 自带的 ui-sweep 引擎会话名写死为 'ui-sweep'(sweep.mjs:79)。两个会话同时跑 ui-sweep 时,一方开跑或跑完时的 close 会关掉另一方的会话。T1 的适用范围点名了 ui-sweep 走查,这个边界情况规则里没交代,至少应写明不要同时跑两个 ui-sweep。 |
| T6 | P2 | README.zh-CN.md:321 | text-B | T1 只要求「启动时记下 PID」,再用 `ps -p <PID>` 核对。如果记下的是 `npm run dev`、`npx` 这类包装进程的 PID,包装进程退出后子进程(vite/node、Chrome)可能留成孤儿,`ps -p` 会显示已退出。没有端口的子进程,`lsof` 也查不到,结果误报「测试进程已关」。应写明关的是整个进程组,或核对子进程。英文 7d item 1 同。 |
| T7 | P2 | README.zh-CN.md:321 | text-B | 「只关自己启动的,别的会话的进程都不动」在规则里没有例外,但 spec §1 的起因正是启动它的会话早已结束、父进程为 1 的 agent-browser。按现在的写法,这类无主的残留进程永远没人处理,规则也没要求把它们报告出来。应补一句:发现启动方已结束的残留进程,列出来交给用户决定,不自行结束。 |
| T8 | P2 | README.zh-CN.md:321 | text-B | 「超过核数的 70% 并发数减半」没说从哪个基数减半(测试工具的默认值,还是当前设的并发数)。基数是 1 时减半没有意义;基数是工具默认值时(vitest 默认约为核数),减半后在高负载下仍可能很大。应写明按工具当前或默认并发数减半、最少 1。各模板第 8 条与 parallel-do 同。 |
| T9 | P2 | README.zh-CN.md:321 | text-B | 依据句写「见七.4」,而本节标题是「七之四」,两个号指不同的地方:七.4 指第七节的第 4 步,七之四指这个新小节。读者容易看混,可以改成「见七第 4 步」。英文版第 322 行写「see 7.4」,同一处已有体例是「see Section 3.2」,也不统一。 |
| T10 | P2 | plugins/workflow/agents/mechanical.md:10 | text-B | mechanical 子代理不加载 CLAUDE.md,定义里只写了「uptime 的 1 分钟负载超过核数就串行」,没给取核数的命令(macOS 用 sysctl -n hw.ncpu,Linux 用 nproc)。照着规则干活的 agent 只能自己猜。英文版 plugins/workflow-en/agents/mechanical.md 第 10 行同。各模板第 8 条写了「可用内存低于 20%」,也没给取内存读数的命令。 |
| T11 | P2 | plugins/workflow-codex/skills/parallel-do/SKILL.md:56 | text-B | 同一文件里阈值写法不一致:「并发上限」那条只写「超过核数改串行」,漏了「或可用内存低于 20%」;「边界」那条(第 61 行)写全了。按第 56 行分批的人会漏看内存条件,应补齐。 |

复核过的检查点:

text-A:
- 对照 spec 第 5 节核对了 README.zh-CN.md 七之四第 1、2 条:T1 七个要素、T2 五个要素都在,阈值是 70%、核数、20%
- 对照 README.zh-CN.md 第 4 步七.4 新加的「进程约束」:W1 七个要素、容器上限、依据句都在;括号在「依据…没有超时)→ 每单元完成即派评审链」处正确闭合,原句没被截断;评审那半句也已补上
- 逐条比对 README.md 的 7d 与七之四:中英一一对应,70% / 核数 / 20% 一致;7.4 的 W1、评审半句、§4 并发段那句都有英文对应
- 核对了交叉引用:七之四、7d 在两份 README 里都是真实存在的标题（zh 316 行、en 315 行）;「见七之四第 2 条」和「see 7d, item 2」都指向负载那一条
- 核对了三份模板 §3 的编号:第 7、8 条是新加的两条,红线那条里的「§3 第 7、8 条」和「§3 items 7 and 8」,以及并发上限那条里的「§3 第 8 条」都指得对
- 核对了三份模板里的压缩版:T1 保留了 ③④⑤⑥⑦,T2 保留了 ②③④,W1 七个要素全在;禁止事项里加了一行
- 确认英文模板新增行里没有中文字符;Codex 新增文本里没有 Workflow、agent()、mechanical、Claude 这类说法
- 核对了 Codex parallel-do 步骤 5:并发上限那条加了「分批前先看负载」,边界那条加了 T1、T2、W1 的压缩版,要素齐全
- 核对了两份 mechanical.md 新加的两句:T1 写了「检查完就关、只关自己启动的」,T2 写了「超过核数就串行」,中英对应
- 在公开面新增行里搜索了 hook-writer、hearloop、stellark、huake、gitlab、mac-mini:没有命中
- 在新增行里搜索了 speak-human S5 词库左列的词:唯一一次命中的「台账」来自第 4 步原有的 /goal 文本,不是本批新加的
- 三个 plugin.json 都能被 python json.tool 解析;版本号是 workflow 0.13.1→0.14.0、workflow-en 0.13.1→0.14.0、workflow-codex 0.13.0→0.14.0;两份 marketplace.json 里没有版本字段

text-B:
- 读完 spec 第 3、4、5、6、8 节,对照 §5 要素清单。
- README.zh-CN.md 第 185~351 行:工作流 prompt 整段在 ```markdown 围栏里,新增内容只用了行内反引号,没有新的三反引号,围栏没被破坏。
- README.zh-CN.md 与 README.md 的标题序列:七之一~七之四 和 7a~7d 都是连续编号,没有冲突或跳号;七之四放在七之三和八之间。
- README zh/en 的 T1 七个要素、T2 五个要素、W1 七个要素(含容器上限和依据句)、评审半句、§四并发段末尾那句都在;阈值 70%、核数、20% 中英一致。
- README 新增的依据句里没有 hook-writer、hearloop、主机名或内部仓路径(用的是「一个真实项目的抓取服务」「一台开发机」)。
- 三份模板 §3 原有 1~6 条,新增 7、8 条接着编号,没有跳号;红线条里引用的「§3 第 7、8 条」和并发上限条里引用的「§3 第 8 条」都指向实际条目。
- 模板禁止事项各新增一行;中文模板和 Codex 模板沿用全角标点,与文件原有体例一致。
- 压缩版 T1 保留了 ③④⑤⑥⑦,其中 ⑥「只关自己启动的」在三份模板第 7 条和 parallel-do 边界条里都在,没被压掉;W1 ①~⑦ 在三份模板和 parallel-do 里都在。
- 用 grep 查了 README.md 和 workflow-en 新增行里的 CJK 字符,结果为 0,没夹中文。
- 用 grep 查了 workflow-codex 新增行里的 Workflow / agent() / mechanical / CLAUDE.md / Claude,结果为 0。
- 两份 mechanical.md 末尾都有「检查完就关、只关自己启动的、不用 pkill -f/killall」和「超过核数就串行」,中英对应。
- 版本号:workflow、workflow-en 从 0.13.1 升到 0.14.0,workflow-codex 从 0.13.0 升到 0.14.0;marketplace.json 没有版本字段要同步。
- 新规则与现有条文的冲突:不违背「绝不重启共享服务」(T1 明写共享服务不动);worktree 清理和截图交付规则跟新规则不冲突;Codex 侧 max_threads 的说法保留原样,只在后面接上看负载那句。
- 仓库里没有校验模板或 README 内容的测试脚本,这一项没有测试可核对。

## 第 1 轮 盲审 — 代码(U3)(claude-opus-5-5,medium,2 个)

| # | 严重度 | 位置 | 评审者 | 发现 |
|---|---|---|---|---|
| C1 | P2 | plugins/ui-sweep/skills/ui-sweep/scripts/smoke-test.mjs:421 | code-A | New Case 14 only tests normal finish, STATE_FILE failure exit, a failing close, and --check-config. The uncaught-exception path and the SIGINT/SIGTERM path are untested, yet the sweep.mjs comment and SKILL.md both promise them. I checked both by hand with a fake agent-browser: an ensureBaseline throw ends with status 1 and the last call is close; SIGTERM ends with 143 and the last call is close. So the behavior is right, but nothing in the tests keeps it from breaking later. Suggest adding an ensureBaseline-throws case. The English smoke-test.mjs has the same gap. |
| C2 | P2 | plugins/workflow/skills/sop-generate/scripts/crawl.mjs:398 | code-A | The finally block runs `await browser.close().catch(() => {})` with no time limit. If close hangs, the script hangs too, which is the same failure mode as the hook-writer root cause the spec cites (an unbounded wait for the browser to exit). This meets spec §6 (close on error paths), but it does not match W1's 'bounded wait, then force-kill'. Suggest Promise.race with a timeout, then kill browser.process() (as SIGKILL). The workflow-en and workflow-codex crawl.mjs have the same problem. |
| C3 | P2 | plugins/workflow/skills/sop-generate/scripts/crawl.mjs:398 | code-B | The close in finally is await browser.close().catch(()=>{}), which has no upper bound on the wait. If close hangs, the script hangs forever. This is the same failure as the root cause in spec §1 (the close function waits without limit). Suggest Promise.race with a timeout, then a forced kill of the browser process if needed. The other two crawl.mjs copies (workflow-en line 440, workflow-codex line 399) and probe-login.mjs have the same problem. The try body is also not re-indented, which hurts readability. |
| C4 | P2 | plugins/workflow-codex/skills/sop-generate/scripts/probe-login.mjs:2 | code-A | `const p = await b.newPage()` sits outside the try on the same line as launch. If newPage throws, the finally never runs and the browser launched by launch is not closed. Move newPage inside the try. |
| C5 | P2 | plugins/workflow-codex/skills/sop-generate/scripts/probe-login.mjs:2 | code-B | b.newPage() runs on the same line as launch, outside the try. If newPage fails after a successful launch, the finally never runs and the browser is not closed by the script. Move newPage inside the try so every path after a successful launch closes the browser, matching the crawl.mjs change. |
| C6 | P2 | plugins/ui-sweep/skills/ui-sweep/scripts/sweep.mjs:495 | code-A | With the SIGINT/SIGTERM handlers added, the process now exits with process.exit(130/143) instead of being killed by the signal. A parent process (spawnSync, CI) used to see signal=SIGTERM and now sees status=143, a small change in how it ends. Also, a signal that arrives while the synchronous execFileSync is running is only handled after that call returns (up to 45s). Not a defect, but worth one sentence in a comment. The English sweep.mjs has the same issue. |
| C7 | P2 | plugins/ui-sweep/skills/ui-sweep/scripts/sweep.mjs:495 | code-B | Handlers are registered only for SIGINT and SIGTERM. SIGHUP (terminal closed, or a parent session dropping) still uses Node's default action and exits without emitting 'exit', so the ui-sweep session and Chrome are left running. Suggest adding ['SIGHUP', 129]. The signal paths (exit codes 130/143 and whether close is sent) also have no smoke case; they could be checked with the fake agent-browser by sending SIGTERM after the open call. Same in ui-sweep-en. |
| C8 | P2 | plugins/workflow/skills/sop-generate/scripts/crawl.mjs:200 | code-A | The ~190-line body wrapped in the new try { ... } finally was not re-indented, so the try/finally nesting is hard to read. Same in all three crawl.mjs copies. |
| C9 | P1 | plugins/ui-sweep/skills/ui-sweep/scripts/smoke-test.mjs:469 | code-B | Case 14c says it checks that a failing close does not change the original exit code, but it only runs failCfg, which already exits 1. If closeOwnSession set process.exitCode=1 or threw when close failed, the test would still pass. Fix: run the normal-finish config (sessionCfg) with FAKE_AB_CLOSE_FAIL=1 and assert code 0 plus SWEEP DONE. The same file under ui-sweep-en has the same problem at line 469. |
| C10 | P2 | plugins/ui-sweep/skills/ui-sweep/scripts/sweep.mjs:488 | code-B | closeOwnSession swallows every close failure without a word: ab(...,{ok:true}) returns null, and an execFileSync timeout of 45s only stops the CLI, not Chrome. If close fails or times out, the browser stays alive and nothing reports it. T1 asks to list processes that could not be closed. It should print a line to stderr when close returns null, e.g. 'ui-sweep session close failed, please run agent-browser --session ui-sweep close', without changing the exit code. ui-sweep-en/sweep.mjs has the same issue. |

复核过的检查点:

code-A:
- Read the whole spec docs/superpowers/specs/2026-10-01-test-process-cleanup-and-load-design.md, sections 3-6 and 8
- Checked every exit point in plugins/ui-sweep/skills/ui-sweep/scripts/sweep.mjs: the flag branches (lines 98-429, process.exit(0/1)) all run before the handlers are registered (line 494) and before sessionStarted, so their behavior is unchanged; the only process.exit after the session is built is the STATE_FILE failure in initSession (line 508), which goes through the exit event; normal finish (SWEEP DONE) closes in the exit event when the event loop drains
- Ran node v22 by hand to confirm that the process 'exit' event fires for a top-level await rejection, an uncaught throw, and an unsettled TLA (status 1/1/13), so the uncaught-exception path does close
- With a fake agent-browser in a temp dir (no real browser started), ran zh sweep.mjs: ensureBaseline throwing -> status 1, last call close, 2 closes in total; kill -TERM on the PID of the node I started -> status 143, last call close
- closeOwnSession: sessionClosed makes it run only once; ab is wrapped in try/catch with ok:true, and the exit handler does not change exitCode, so the original exit code is kept (smoke 14c also checks this)
- zh vs en sweep.mjs/smoke-test.mjs: compared the +/- lines of the two git diffs; only comments differ, the logic is identical
- Checked that smoke Case 14a/14b assert closes.length===2 and that the last call is a ui-sweep close (if the cleanup close is removed the count drops to 1 and the test fails); they do not just check the exit code. 14d asserts --check-config output is unchanged and makes no agent-browser call
- Ran node plugins/ui-sweep/skills/ui-sweep/scripts/smoke-test.mjs one after another: 28 passed, 0 failed
- Ran node plugins/ui-sweep-en/skills/ui-sweep/scripts/smoke-test.mjs: 28 passed, 0 failed
- node --check passes on all 8 changed .mjs files (zh/en sweep and smoke, 3 crawl.mjs, probe-login.mjs)
- The try in all three crawl.mjs copies opens right after chromium.launch; the process.exit calls (lines 170/180 etc.) are all before launch; main().catch's process.exit runs only after finally finishes, so error paths do close the browser
- export-state.mjs is unchanged: it uses connectOverCDP to attach to an existing browser, does not launch one, and closes the connection on the no-context branch; there is no unclosed launched process
- The zh/en ui-sweep SKILL.md 'session cleanup' paragraphs match each other (closes automatically, reviewers start a session with their own name and close it when done); the three sop-generate SKILL.md files add 'close when done' at the end of step 3 in the same place
- Both ui-sweep and ui-sweep-en plugin.json go 0.2.0 -> 0.2.1

code-B:
- Read spec docs/superpowers/specs/2026-10-01-test-process-cleanup-and-load-design.md sections 3-6 and 8
- sweep.mjs (zh): closeOwnSession uses a sessionClosed flag so it runs at most once, never calls process.exit itself, and the signal handler's process.exit(code) leads to the exit handler with no recursion
- sweep.mjs ab(): execFileSync has timeout 45000, so a stuck close in the exit handler blocks for at most 45s
- sweep.mjs initSession: sessionStarted is set after the stale-session close and before open, so close is still sent when open succeeds but state load fails and process.exit(1) runs (smoke 14b checks this)
- sweep.mjs: signal handlers are registered after the --check-* branches (lines 342-429), so the flag branches send no close and their output is unchanged (smoke 14d checks this)
- sweep.mjs: restore failure, restore failure after an off-domain click, and ensureBaseline throwing either continue the loop or exit 1, and every case passes through the exit handler
- ui-sweep-en sweep.mjs diff makes the same logic change as the zh copy, with comments translated; the two smoke-test diffs are line-for-line identical
- Ran both smoke tests serially: zh and en each 28 passed, 0 failed; no ui-sweep-smoke-* temp directory left in TMPDIR
- Smoke fake agent-browser: the PATH prefix applies only to the child env, the fake directory sits inside tmp and is removed by finally, the fake script starts no processes, and 14a/14b assert calls.length>0, which proves the fake was used
- Three crawl.mjs copies: try begins after launch succeeds, so a failed launch never reaches finally and there is no undefined-variable reference; there is no process.exit inside the try body that would skip finally; the three copies match; node --check passes
- probe-login.mjs: try/finally added; newPage remains outside the try
- export-state.mjs (identical in zh and en): connects only via connectOverCDP to an existing browser and launches none, so U3 not changing it is reasonable
- SKILL.md (ui-sweep zh/en, sop-generate in all three plugins): wording is consistent between zh and en; plugin.json versions are 0.2.0 -> 0.2.1 in both

## 第 1 轮分流(主对话)

下文的 T1~T11、C1~C10 是上面两张表的发现编号;spec 里的三条规则写作「规则 T1 / 规则 T2 / 规则 W1」。

**规则文本**:无 P0/P1、无 conflict → 判通过。P2 处理:

- 发现 T1、T2(README 对机械子代理的描述还写「三条通用要求」)、T3(英文「see 7.4」体例)、T4(负载高时盲审轮能否顺序跑)、T6(包装命令的 PID)、T7(无主残留进程)、T8(减半的基数)、T10(机械子代理缺取核数的命令)、T11(Codex parallel-do 并发上限条漏内存条件):主对话已在单元首个提交前改掉——规则 T1 补「包装命令带起的子进程一起关、一起核对」「不是自己启动、启动方已结束的残留进程列出来交给用户决定」;规则 T2 补「按当前值减半(没设过按工具默认值,最少 1)」「盲审轮同样可以顺序跑」;模板、parallel-do、机械子代理定义、spec、本机全局 CLAUDE.md 同步。另改一处体例:README 中英七.4 里「;+ **进程约束**」改成「 + **进程约束**」。
- 发现 T5(ui-sweep 会话名写死,两个会话同时跑会互相关掉):交给 U3 修复轮,在 SKILL.md 写明同一台机器同一时间只跑一个 ui-sweep;会话名可配置记为遗留。
- 发现 T9(「见七.4」与小节名「七之四」容易看混):不改,中文 README 全文都用「七.4」指第七节第 4 步(如三.3「见七.4」),保持一致;记为遗留。

**代码(U3)**:1 条 P1——发现 C9(用例 14c 只在本来就退出码 1 的配置上测「关闭失败不改退出码」,测不出问题)→ 退回,修复后跑裁决轮。P2 一并修:C2/C3(三份 crawl.mjs 与 probe-login.mjs 的关闭没有等待上限)、C4/C5(probe-login 的 newPage 在 try 外)、C7(SIGHUP 没处理;信号路径没有用例)、C1(未捕获异常路径没有用例)、C10(关闭失败时没有任何提示)。C8(try 体没有重排缩进)由修复 agent 二选一处理:抽成函数或重排缩进。C6(信号改成以 130/143 退出、同步调用期间信号要等调用返回才处理)写进注释。

修复按退回流程:测试与实现分两个 agent(claude-sonnet 升 high),修完开第 2 轮(裁决,opus high)。

## 第 1 轮修复(U3,claude-sonnet-5-5 high,测试与实现分两个 agent)

- 测试:14c 拆成两条断言(正常跑完的配置加关闭失败 → 退出码 0 且有 SWEEP DONE;失败配置加关闭失败 → 退出码仍 1);新增 14e(关闭失败时 stderr 有手动关闭提示,关闭成功时没有)、14f(未捕获异常路径)、14g(SIGTERM 143、SIGHUP 129,发信号后最后一次调用是 close)、14h(信号用例的子进程都已退出)。实现改之前 33 通过 / 2 失败(SIGHUP 与 stderr 提示,预期失败)。
- 实现:sweep.mjs 加 SIGHUP、关闭失败往 stderr 打一行手动关闭提示、信号说明注释;ui-sweep SKILL.md 写明同一台机器同一时间只跑一个 ui-sweep;三份 crawl.mjs 与 probe-login.mjs 的关闭加 10 秒等待上限(Playwright 的 Browser 对象拿不到子进程 PID,超时后显式结束 node 进程,Playwright 在进程退出时结束浏览器子进程),try 体重排缩进,probe-login 的 newPage 移进 try。两份 smoke 35 通过 / 0 失败。

## 第 2 轮 裁决 — 代码(U3)(claude-opus-5-5,high)

结论:**通过**。无未闭合 P0/P1,无新 P0/P1。

| 发现 | 状态 | 证据 |
|---|---|---|
| C9 | 已闭合 | smoke-test.mjs:472-487 (zh/en byte-identical, cmp passes). 14c now has a second assertion that runs sessionCfg (a normal finish that exits 0) with FAKE_AB_CLOSE_FAIL=1 and asserts code 0 plus SWEEP DONE. Mutation check in a temp copy ($TMPDIR/mutC9.*, deleted afterwards): I added process.exitCode=1 inside closeOwnSession's r===null branch and ran the smoke. Result was 33 passed, 2 failed; the new 14c assertion failed with code=1, and so did 14e. So the test now catches a close failure that leaks into the exit code. |
| C1 | 已闭合 | Case 14f (smoke-test.mjs ~514-524) makes the config's ensureBaseline throw 'smoke-boom'. ensureBaseline is called from restore() at sweep.mjs:527, outside any try, so the top-level await rejects for real. The case asserts code!==0, that stderr contains smoke-boom, that the last call is a ui-sweep close, and that there are 2 closes. It passes in both smokes. |
| C7 | 已闭合 | sweep.mjs:503 (zh) and the matching en line now register ['SIGHUP',129] next to SIGINT/SIGTERM. Case 14g spawns sweep.mjs and polls the fake log until ' wait --load ' appears; the fake writes that log line before it sleeps 3s. It then sends child.kill(signal) by PID and asserts sent && !timedOut && code===143/129 && last call is a close && closes===2. The run is capped at 20s, with a SIGKILL fallback. My runs printed PASS for both SIGTERM and SIGHUP. The test fix agent's red run before the implementation showed SIGHUP failing with code=null, which confirms the case can fail. |
| C10 | 已闭合 | sweep.mjs:492-498 (zh/en). closeOwnSession now keeps r=ab(['close'],{ok:true}). ab() returns null only from its catch branch when ok is set (sweep.mjs:442-450); a successful close returns the stdout string. On null it prints a one-line stderr hint containing 'agent-browser --session ui-sweep close'. The print is wrapped in try and does not touch exitCode. Case 14e asserts code 0 plus the hint on failure, and no hint on success. Both pass. |
| C6 | 已闭合 | Comment added at sweep.mjs:500-502 (zh) and the en equivalent. It covers the 130/143/129 exit codes and says the parent sees an exit code rather than a signal. It also notes that a signal waits for the synchronous execFileSync call to return. (The wording slightly understates the wait; see the new P2.) |
| C2 | 已闭合 | All three crawl.mjs copies (zh :164-183, en :195-215, codex :165-184) add closeBrowserBounded, which runs Promise.race(browser.close(), 10s timer) and clears the timer either way. The finally block calls it (zh :418-420). If close times out, main().then() runs process.exit(process.exitCode ?? 0); the error path still exits 1 from catch after finally. That force-kill claim checks out: in ~/.npm/_npx/.../playwright-core/lib/server/utils/processLauncher.js, line 162 runs addProcessHandlerIfNeeded('exit'), exitHandler kills everything in killSet, and killProcessAndCleanup is only removed from killSet when the process actually closes (:157/:187). So a hung close still leads to a forced kill when the process exits. Comparing zh and codex with diff shows only pre-existing comment differences. |
| C3 | 已闭合 | Same fix as C2 in all three crawl.mjs copies. probe-login.mjs:3-29 has its own closeBounded with a 10s cap and an explicit process.exit(failed?1:0) after a timeout. git diff -w --stat on the sop-generate scripts shows only added lines, so the reindent (C3's readability point) changed no content. |
| C4 | 已闭合 | probe-login.mjs:18-21 now has launch alone on its line, and `const p = await b.newPage()` is the first statement inside the try. Every path after a successful launch reaches the finally. |
| C5 | 已闭合 | Duplicate of C4, closed by the same change (probe-login.mjs:18-29). |
| C8 | 已闭合 | The try body is re-indented in all three copies (crawl.mjs zh :221-418). git diff -w --stat lists only 28/29/28 added lines and 2 removed per file, and none of them are body changes. I scanned the changed lines for an odd number of backticks: none, so no multi-line template literal had its content shifted by the reindent. |
| T5 | 已闭合 | ui-sweep SKILL.md:22 (zh) and ui-sweep-en SKILL.md:22 both now say the session name is fixed as ui-sweep, that only one ui-sweep should run per machine at a time, and that two runs close each other's session. They also mention the stderr hint and SIGHUP. zh and en match sentence for sentence. Making the session name configurable stays an open item, as the triage decided. |

新发现:
- P2 plugins/workflow-codex/skills/sop-generate/scripts/probe-login.mjs:28(correctness)When the script fails and close() also times out, process.exit(1) inside finally discards the pending exception. Only 'probe-login failed' is printed, and the original error (goto or $$eval failure) is lost. Suggest printing the caught error in the catch (or keeping it and printing it before the exit). crawl.mjs does not have this problem, because its catch prints the error after finally.
- P2 plugins/ui-sweep/skills/ui-sweep/scripts/sweep.mjs:500(edge-cases)The new C6 comment says a signal is handled once the current call returns, with 45s as the longest timeout. In fact the JS handler runs only when the code yields to the event loop. Several synchronous ab() calls can run back to back before the next await: in the click loop, fingerprint() then click (sweep.mjs ~649-651) is two calls, so the delay can reach about 90s. Same wording in ui-sweep-en. The comment should say the signal waits for the current run of synchronous calls before the next await.
- P2 plugins/ui-sweep/skills/ui-sweep/scripts/smoke-test.mjs:560(test-quality)Case 14h runs process.kill(pid,0) only after each child's 'close' event, so the child has already exited and been reaped. The check can only fail if the PID gets reused, and it never looks at the fake's grandchild `sleep`. Separately, the fake-script comment at ~436 says only the first `wait --load` sleeps, but every `wait --load` sleeps while FAKE_AB_SLEEP is set. Neither problem weakens 14g. Same in ui-sweep-en (byte-identical).

复核过的检查点:
- Read the spec (sections 3-8) and the chain record for round 1, including the triage
- Read git diff of both sweep.mjs, both smoke-test.mjs, both ui-sweep SKILL.md, all three crawl.mjs (with -w and without) and probe-login.mjs
- zh and en smoke-test.mjs are byte-identical (cmp). The zh/en sweep.mjs diffs have the same logic; only the comments are translated
- zh and codex crawl.mjs differ only in pre-existing comment lines. The en crawl.mjs has the same new code with English messages. No Claude-specific wording was added to the codex copy
- node --check passes for all 8 changed .mjs files
- zh smoke run serially: 35 passed, 0 failed (signal-case child PIDs 21485, 21573)
- en smoke run serially: 35 passed, 0 failed (signal-case child PIDs 22324, 22360)
- After both runs: ps -p shows those PIDs are gone; no ui-sweep-smoke-* dirs in TMPDIR; no leftover fakebin or `sleep 3` processes
- Mutation run (temp copy, deleted afterwards): closeOwnSession setting exitCode=1 makes 14c(normal) and 14e fail (33/2), so 14c now tests what it claims
- The close in the exit handler still runs only once: the sessionClosed flag at sweep.mjs:488-491, and the signal handler only calls process.exit(code), which goes through the single exit listener
- The close-failure hint does not change the exit code: no exitCode write, print wrapped in try. 14c/14e assert code 0
- sessionStarted=true is set before open (sweep.mjs:509), so the signal sent during the first wait --load hits a started session
- ensureBaseline is called outside any try (sweep.mjs:527), so 14f really is an uncaught top-level-await rejection
- crawl.mjs: every process.exit in main is before launch (zh :191/:201). The try starts right after launch. The error path runs finally, then rethrows, then catch exits 1. On the normal path a close-timeout exits with exitCode ?? 0. A close that resolves or rejects within 10s does not set the flag, so normal-path behavior is unchanged
- The playwright exit-handler kill is verified in the local playwright-core processLauncher.js (exit handler plus killSet; the entry is removed only when the process closes)
- Reindent in crawl.mjs: git diff -w shows only additions; no multi-line template literals in the changed lines
- probe-login: when launch fails nothing needs closing; after a successful launch every path goes through finally with the bounded close
- SKILL.md zh/en session-cleanup paragraphs match (SIGHUP, stderr hint, one ui-sweep at a time)
- Acceptance item 4 is met: every end path after the session starts (normal finish, exit(1), uncaught exception, SIGINT/SIGTERM/SIGHUP) closes the session, and the smoke covers normal finish, failure exit, uncaught exception, both signals, and close failure. Acceptance item 5 is met: all three crawl.mjs close the browser on error paths, with a time limit on the close

## 第 2 轮 续挖 — 规则文本(U1+U2)(claude-opus-5-5,medium,镜头:集成缝合点)

结论:**通过**。无 P0/P1。

| 发现 | 状态 | 证据 |
|---|---|---|
| T1 | 已闭合 | README.zh-CN.md:216 now says 「五条通用要求」 and lists both new items (为检查启动的进程检查完就关、只关自己启动的;要并行跑检查先看负载,超过核数就串行). These match the two sentences actually added to plugins/workflow/agents/mechanical.md:10. |
| T2 | 已闭合 | README.md:215 now says 'five general requirements' and the last two clauses match plugins/workflow-en/agents/mechanical.md:10 (shut down only what it started; go serial when load exceeds the core count). |
| T3 | 已闭合 | README.md:322 now reads '(see Section 7.4)', the same as line 221. A related style gap that this fix did not cover is reported as a new P2 under findings ('see 7d'). |
| T4 | 已闭合 | README zh:321 and en:320 both carry the blind-round clause, which says the blind round may run sequentially and stays blind. It matches spec §3 rule T2 word for word: a python exact-substring check found the spec text in README.zh-CN.md. The templates do not carry the clause; that is reported as a new P2 under findings. |
| T5 | 已闭合 | I agree with handing this to U3. The uncommitted U3 working tree adds a line to ui-sweep SKILL.md:22 (zh and en): 「会话名固定为 ui-sweep,同一台机器同一时间只跑一个」 / 'run only one ui-sweep at a time on a machine'. The zh and en lines match each other. That diff is uncommitted, so whether it closes is decided by the U3 verdict round. |
| T6 | 已闭合 | The wrapper-command sentence is in README zh:320 and en:319, in all three templates' item 7, and in the parallel-do boundary bullet. It matches the spec §3 text exactly. |
| T7 | 已闭合 | The leftover-process sentence (list them for the user, do not terminate) is in README zh and en. The three templates' item 7 and parallel-do carry it compressed as 「别人留下的残留进程只列出来报告」 / 'only list and report leftover processes someone else left behind'. It matches the spec §3 and §4 compressed text. |
| T8 | 已闭合 | README zh/en: 「按当前值减半(没设过就按工具默认值算,最少 1)」 / 'halve the current concurrency (if none was set, start from the tool's default; minimum 1)'. Templates item 8 and both parallel-do spots: 「按当前值减半(最少 1)」. Consistent across all faces. |
| T9 | 已闭合 | I agree with not changing it. The Chinese README uses 七.4 for section 7, step 4 elsewhere too (lines 198 and 222), and 七之四 is the subsection heading at line 316, so both references resolve correctly. The English half of T9 was fixed through T3. |
| T10 | 已闭合 | The core-count commands (sysctl -n hw.ncpu / nproc) are now in both mechanical.md files, the three templates' item 8, and parallel-do line 56. The memory-reading command that T10 also mentioned was not added to the compressed faces. That remainder is reported as a new P2 under findings. |
| T11 | 已闭合 | plugins/workflow-codex/skills/parallel-do/SKILL.md:56 now includes 「超过核数或可用内存低于 20% 改串行」, consistent with the boundary bullet at line 61. |

新发现:
- P2 plugins/workflow/skills/scaffold/templates/CLAUDE.md.tmpl:119(integration seams)README 七.4 / 7.4 added a review half-sentence: for units that launch external processes, the reviewer checks that the exit requirements are implemented and tested. The review-stage bullet in all three templates (zh tmpl:119, en tmpl:119, Codex AGENTS.md.tmpl:107 「测试本身每轮必查」) did not get it. The W1 implementation side is in the red-line bullet, but the review side is not, so in a scaffolded project the reviewer prompt does not ask about it. Spec §4 does not list this for the templates, so it is not an acceptance failure.
- P2 plugins/workflow/skills/scaffold/templates/CLAUDE.md.tmpl:120(integration seams)The T4 fix (the blind round may run sequentially under high load and stays blind) went into README zh/en but not into the templates. Template item 8 tells you to go serial when the load exceeds the core count, while the blind-round bullets still say 「平行盲审」 (zh tmpl:120, en tmpl:120, Codex AGENTS.md.tmpl:107 「平行各自验收」). Under high load, an agent working from a scaffolded project faces the same ambiguity T4 described.
- P2 README.md:298(integration seams)In the English README, the new cross-references say 'see 7d' (line 298) and 'see 7d, item 2' (line 228). Existing references to subsections use the 'Section 6c' form (line 138), and T3 already aligned line 322 to 'Section 7.4'. These two should read 'see Section 7d' to match.
- P2 plugins/workflow/skills/scaffold/templates/CLAUDE.md.tmpl:63(integration seams)The remainder of T10: item 8 in all three templates and both spots in parallel-do use the 'available memory below 20%' threshold but give no command for reading memory. README 七之四 gives one (memory_pressure / free -m). The core-count command was added everywhere and the memory one was not, so the compressed faces leave half the threshold without instructions for checking it.

复核过的检查点:
- Spec §3 quoted texts (T1, T2, scope sentence, W1, review half-sentence): a python exact-substring check finds all five verbatim in README.zh-CN.md
- README zh vs en, the new pieces sentence by sentence: wrapper-command sentence, leftover-process sentence, halving base with minimum 1, blind-round sequential clause, the 'basis' sentence, the §4 'check load before kicking off' sentence, the five mechanical requirements, and the W1 graceful-then-forced wait that always returns. All correspond, and the thresholds 70% / core count / 20% match
- README five-requirement description vs both mechanical.md files: the counts and items line up (zh and en)
- Cross-references resolve: 七之四 at zh:316, 7d at en:315, 七.4 means section 七 step 4 (zh:299), Section 7.4 = en:298; the template references §3 第 7、8 条 / §3 items 7 and 8 / §3 第 8 条 point at items 7 and 8 under '## 3. 修改后质量检查' / 'Post-Change Quality Checks' in all three templates
- The three templates' items 7 and 8, red-line bullet, concurrency bullet, and forbidden-list line agree with each other and with spec §4; the Codex template attaches the load check to the parallel-do implementation bullet, line 96, because it has no Workflow concurrency-cap bullet
- Added lines in README.md and plugins/workflow-en: CJK scan finds 0
- Added Codex lines in parallel-do and AGENTS.md.tmpl: no Workflow / agent() / mechanical / Claude / CLAUDE
- Public faces: no hook-writer, hearloop, stellark, huake, gitlab, or mac-mini in the added lines; the S5 lexicon words do not appear in the new rule text (the one 落地 hit is 落地页 in a U3 code comment)
- README in-repo grep for other copies of the step-4 rule text: only README zh/en, the templates, and parallel-do carry it; the plugin.json and marketplace descriptions only list the discipline themes and were not required to change
- T5 follow-through: the uncommitted U3 working tree has the one-ui-sweep-at-a-time note in both ui-sweep SKILL.md files, and the zh/en text matches

## 第 2 轮之后的处理(主对话)

新 P2 共 7 条,改了 6 条,1 条记遗留:

- 代码:probe-login 关闭超时时把原始错误一并打出;sweep.mjs 信号注释改成「等当前这一串同步调用结束、回到下一个 await 才处理」;smoke 里假 agent-browser 的注释改准(每次 `wait --load` 都睡)。遗留:用例 14h 在子进程已回收之后才查 PID,实际查不出问题,也不看假脚本带起的 sleep 孙进程。
- 文本:三份模板的评审那条补「启动外部进程的单元还要核对退出要求有没有实现、有没有测到」;三份模板第 8 条补取内存读数的命令与「盲审轮同样可以顺序跑」;Codex parallel-do 并发上限条补取内存读数的命令;英文 README 两处「see 7d」改成「see Section 7d」;spec §4 压缩版同步。

主对话验证(2026-10-01 23:13~23:20,串行):两份 smoke 各 35 通过 / 0 失败;真实浏览器跑一次新引擎(本机 agent-browser 0.27.0,临时静态页),跑完 `agent-browser session list` 里没有 ui-sweep 会话;同一配置跑改动前的引擎(ba145fd 版),跑完 ui-sweep 会话还在(后台进程 29852),已手动关掉并核对退出;测试用的本地静态服务按 PID 关掉、端口释放、临时目录已删。测试进程已关。

遗留(P2,不再开轮):ui-sweep 会话名固定,不能同时跑两个(SKILL.md 已写明);中文 README「七.4」与「七之四」并存;用例 14h 较弱;crawl.mjs 与 probe-login.mjs 的关闭超时分支没有在真实浏览器里跑过(只做了语法检查与辅助函数的假对象测试)。

链结束:kit 面共 2 轮(盲审 1 轮 + 裁决/续挖 1 轮)。


# 镜像面(dev-toolkit、huake 两个工具包)

单元与实现模型:U4 dev-toolkit(claude-opus-5-5,medium,O 组);U5 huake Claude 版与 Codex 版(claude-sonnet-5-5,medium,S 组)。执行:2026-10-01 23:15 本机 1 分钟负载 9.9(10 核,超过 70% 未超核数),实现串行、盲审并发从 4 减半到 2。


## 第 1 轮 盲审 — U4 dev-toolkit(claude-opus-5-5,medium,2 个)

| # | 严重度 | 位置 | 评审者 | 发现 |
|---|---|---|---|---|
| D1 | P2 | dev-toolkit/plugins/dev-toolkit/skills/stellark-workflow/SKILL.md:77 | dt-A | 核心七.4 的 W1 只保留触发条件和指向 references/process-exit.md,②~⑦(最长存活时间、先正常后强制关闭且等待有上限、同时存活数上限、各失败路径都关、调用带超时、测试覆盖)都不在核心里。这符合 spec §7「核心只留触发条件加指向」,但与 spec §5「压缩版(含核心 SKILL.md)W1 至少保留①~⑦」写法冲突。spec 本身两处矛盾,应在 kit spec 里改成一致(以 §7 为准),否则后面的评审会按 §5 判核心缺要素。 |
| D2 | P2 | dev-toolkit/plugins/dev-toolkit/skills/stellark-workflow/SKILL.md:19 | dt-A | 为抵消 token 增量做的压缩把评审行的「评审不许只用 opus 单一模型、不再平行投票」改成「评审不只用 opus、不平行投票」,禁令语气变成了陈述语气。要素还在,但强制性变弱了;建议保留「不许」二字(只多约 2 个 token,改后仍低于 6534.29)。 |
| D3 | P2 | dev-toolkit/plugins/dev-toolkit/skills/stellark-workflow/SKILL.md:19 | dt-B | §一 评审行把「评审不许只用 opus 单一模型、不再平行投票」压成「评审不只用 opus、不平行投票」。禁止语气「不许」变成了描述语气,禁令强度下降。应保留「不许」。 |
| D4 | P2 | dev-toolkit/plugins/dev-toolkit/skills/stellark-workflow/SKILL.md:52 | dt-A | §四 写「开跑前先看负载(见七之五,references/process-exit.md)」,但核心 SKILL.md 里没有七之五小节(核心的七之四是会话卫生,下一节是 §八),「七之五」只存在于 WORKFLOW.md 和 process-exit.md 的标题里。后面跟着文件路径,还能找到,但光看「见七之五」容易在核心里找不到;建议写成「见 references/process-exit.md 七之五」,与 stellark-parallel-do 的写法一致。 |
| D5 | P2 | dev-toolkit/docs/Progress.md:20 | dt-A | 这是 10 月首条日志,但 9 月(及更早)的条目仍留在主文件里(18 条 2026-08/09 条目,没有 docs/archive/ 目录)。按每月首次收尾归档的规则,应当另起一个 docs: 提交移到 docs/archive/Progress-2026-09.md(kit 已在 beaf3a8 做了)。这属于收尾步骤,不阻塞本单元,记为遗留项。 |
| D6 | P2 | dev-toolkit/docs/Progress.md:20 | dt-B | 这是 10 月第一条变更日志,但主文件里还留着 10 条 2026-09 的条目,docs/archive/ 下也没有 Progress-2026-09.md。按 WORKFLOW.md 七.5,本月首次收尾要把上月日志单独提交一次归档。新条目的位置和体例(放在最上面,分现象/决策/验证结果/归类)本身没问题;归档应在收尾时补上(由主对话做)。 |
| D7 | P1 | dev-toolkit/plugins/dev-toolkit/skills/stellark-workflow/SKILL.md:133 | dt-B | 为压 token,§八 删掉了「细则在 research.md」,也删掉了「不受本节触发条件限制」。这样一来,核心里指向 research.md 的入口只剩句末那一处,而且附带条件「brainstorming 意图明确、提候选方案前」。只读核心的 agent 做不走 brainstorming 的小型登录改动(改密、登出、鉴权中间件)时,就没有入口去读 research.md 里的接入要求:login 子包、不重写用户表/密码哈希/令牌签发、非 Go 后端先问、登记 used_by 的包名。被删的这一处恰好是原来不带条件的入口。应恢复「细则在 research.md」这类不带条件的入口(或等价写法),再到别处压措辞来抵消 token 增量。 |
| D8 | P2 | dev-toolkit/plugins/dev-toolkit/skills/stellark-workflow/SKILL.md:89 | dt-B | GUARD「测试卫生」行新加的负载规则有歧义、缺少可执行信息。(1)「超过 70% 并发减半」没写 70% 是相对核数,也没写「按当前值、最少 1」;(2)只拿到 GUARD 的 agent 不知道怎么查核数和可用内存(sysctl -n hw.ncpu / nproc、memory_pressure / free -m),「可用内存低于 20%」无法照做;(3) 只写了「记会话名」,没写 agent-browser 必须用自己起名的 --session。agent 如果用默认会话再执行 close,会关掉别人共用的默认会话,与「只关自己启动的」相冲突(完整版七之五第 1 条写明了这一点)。建议改成「超过核数 70%」,并补「agent-browser 用自起名 --session」半句。 |
| D9 | P2 | dev-toolkit/plugins/dev-toolkit/skills/stellark-workflow/references/process-exit.md:14 | dt-B | 七.4「进程约束」要求在 GUARD 模板之后再写一遍「测试启动的进程测完即关、并发前先看负载」。但核心 GUARD 的「测试卫生」行已经含这两条(压缩版),照做的主对话会让同一规则在 prompt 里以两种详略不同的措辞出现两次(70% 的表述也不一致)。本文件应说明:本仓 GUARD 已含 T1/T2,这里只需补 W1 的退出要求。 |
| D10 | P2 | dev-toolkit/plugins/dev-toolkit/skills/stellark-workflow/SKILL.md:35 | dt-B | §二 盲审行 effort 列从「都是 medium」压成「(opus 的 effort 与 CLI 的 model_reasoning_effort 同)」。「同」字指代不明:读者可能理解为两者彼此相同(都可以是 high),也可能理解为都等于 medium。应写回「都是 medium」或「同为 medium」。 |
| D11 | P2 | dev-toolkit/plugins/dev-toolkit/skills/stellark-workflow/SKILL.md:94 | dt-B | 七.6 把「因无 plan 失去入口」压成「因此失去入口」,丢掉了原因(没有 plan 文档)。「因此」现在只能回指前半句的「覆盖 brainstorming 规定」,因果关系不准确。 |

复核过的检查点:

dt-A:
- WORKFLOW.md 七之五(第116-123行)与 kit README.zh-CN.md 七之四逐字比对:适用范围句、T1 全文(七要素齐,含 npm/npx 包装进程、pkill -f/killall 禁用、残留进程交给用户)、T2 全文(五要素齐,70%/核数/20%/报告负载与并发数)一致;依据句点名 2026-09-19 与 hook-writer,并指向「见七.4」,七.4 确实存在
- WORKFLOW.md 七.4(第99行)的进程约束与 kit 七.4 逐字一致,W1 七要素与容器上限都在;依据句改成 hook-writer / Docker 虚拟机 / hearloop postgres 的私有面写法;评审半句已补
- WORKFLOW.md §四(第51行)末句与 kit 一致,其中「见七之五第 2 条」指向真实小节;WORKFLOW.md 小节编号是七之一/二/三/五(本仓七之四在核心里是会话卫生,编号顺延的理由写在 upstream-map 与 Progress)
- references/process-exit.md 新文件:七之五全文与 WORKFLOW.md 一致,另加「开跑 Workflow 前先看负载」句;七.4 进程约束全文、hook-writer 依据句、评审半句都在;首行有「何时读」触发句
- 核心 SKILL.md GUARD「测试卫生」行(第89行):原三要素(临时目录/文件自动清理、子进程整组回收、重型用例可跳过并标明)原样保留;T1 ③④⑤⑥⑦ 与 T2 ②③④ 都在
- 核心 SKILL.md 第52、77行两处 references/process-exit.md 指针对应的文件实际存在;七.4 评审括号补了「启动外部进程的还核对退出要求实现了、测到了」
- token:改后 6533.29,改前(git show HEAD)6534.29,没有超过上限
- 逐句核对核心压缩的 word-diff:删掉的「裁决轮由 fable 出 high」「规则 3 单元 high」「主对话只裁决」「主对话用最强模型指挥」「细则在 research.md」在同文件其他位置都有等价表述;§八 删掉的「不受本节触发条件限制」与保留的「任何规模都适用」同义;七之二、台账第3条、七.5 的改写没有丢要素
- references/upstream-map.md:WORKFLOW.md 实际行数 153(改前 144),与表中数字一致;改前 token 6534.29 与实测一致;新增的三行归位表与实际落点相符
- scaffold CLAUDE.md.tmpl:§3 新增第7、8条,红线条、评审条、并发上限条、禁止事项的改动与 kit workflow 模板 diff 逐字一致;§3 确实是「修改后质量检查」;{{ 占位符数量改前改后都是 5;没有出现内部项目名
- agents/mechanical.md 新增两句与 kit workflow/agents/mechanical.md 逐字一致
- stellark-parallel-do/SKILL.md:步骤5开头加了「开跑前先看负载」(T2 ②③④),边界加了 T1/T2/W1 压缩版(W1 七要素齐),没有出现 hook-writer/hearloop
- cmp:ui-sweep 的 sweep.mjs、smoke-test.mjs、SKILL.md、export-state.mjs 与 kit plugins/ui-sweep 定稿逐字节一致
- sop-generate probe-login.mjs 与 kit workflow-codex 定稿逐字节一致;crawl.mjs 与 kit workflow 定稿的差异只有本仓改前就有的 waitForAppReady 300ms 与 landingHref 两处(已用 kit ba145fd 与本仓 HEAD 互相 diff 确认是改前已有的差异),try/finally + closeBrowserBounded + 显式退出码与 kit 一致
- sop-generate/SKILL.md 与 ui-sweep/SKILL.md 新增的「截完即关」「会话收尾」两段已核对
- node --check:sweep.mjs、smoke-test.mjs、crawl.mjs、probe-login.mjs 四个文件都通过
- 串行跑 node plugins/dev-toolkit/skills/ui-sweep/scripts/smoke-test.mjs:35 passed, 0 failed;用 PATH 上的假 agent-browser 隔离,没有启动真实浏览器;信号用例的子进程 57059、57149 已用 ps -p 核对都已退出
- git diff --name-only 里没有任何 plugin.json;改动文件清单与应改文件范围一致

dt-B:
- git status --short:只有点名的 13 个文件被改,外加新文件 references/process-exit.md;没有 plugin.json 被改
- WORKFLOW.md:七之五与 kit README 七之四整段逐行 diff,只有编号和依据句(点名 hook-writer/HAPI)不同;七.4 进程约束与评审半句、§四 并发段末句已核对;WORKFLOW.md 没有七之四(那是核心独有的 delta),编号顺延有意为之,共 153 行
- 核心 SKILL.md:逐句对照 diff。受保护段落未动:取证前置硬规则、两条工具纪律、五.1/五.3/五.4、七之三、[^orch] 脚注都不在 diff 里;GUARD 模板只改了「测试卫生」一行,其余各行和 text 代码围栏完好
- 核心 SKILL.md 的 token 用 c1-map.md 公式实测:改前 6534.29、改后 6533.29,没有增加
- 核心里被压缩的句子逐条核对:前提行、§一 后裁决轮句、§二 省略说明、三.1/三.2 括注、七.2、七.4 /goal 句与「细则同上」、七.5、七.6、七之一、七之二、§八,发现见 findings
- references/process-exit.md 开头有「何时读」行,体例与其余 references 一致;内含七之五全文、七.4 进程约束、评审半句,以及与重型测试并发约束并存的说明
- references/upstream-map.md:行数改为 153,新增归位表,说明了「见七之四 → 见七之五」的对应
- GUARD 新内容与「重型测试并发约束」「不重启任何共享服务」「子进程整组回收」没有逻辑矛盾(只关自己启动的,与不动共享服务一致)
- CLAUDE.md.tmpl:与 kit 模板 diff 的增量一致;{{...}} 占位符种类和个数改前改后 md5 相同;§3 编号 1–8 连续;全角标点体例一致
- agents/mechanical.md 新增两句与 kit 逐字一致(按 spec 只要求 T1 的检查完即关、只关自己启动的,以及 T2 的超过核数串行)
- stellark-parallel-do/SKILL.md:步骤 5 新增「开跑前先看负载」,边界 bullet 与 kit codex 版三条压缩版对照过,与原有 pipeline/重型测试流程不冲突
- ui-sweep 的 sweep.mjs、smoke-test.mjs、SKILL.md 与 kit 定稿 diff 结果完全一致;sop-generate 的 probe-login.mjs 与 kit workflow-codex 一致;crawl.mjs 与 kit 的差异只有本仓原有的两处(300ms 等待、landingHref),try/finally 与有上限的关闭等待已正确移植(看了 git diff -w)
- sop-generate/SKILL.md 的「截完即关」一行与 kit 一致
- docs/Progress.md:新条目在变更日志最上面,体例与相邻条目一致;9 月条目未归档(已列为 P2)

## 第 1 轮 盲审 — U5 huake(claude-opus-5-5,medium,2 个)

| # | 严重度 | 位置 | 评审者 | 发现 |
|---|---|---|---|---|
| H1 | P2 | codex-toolkit-engineer/README.md:83 | hk-A | 0.13.0 的版本说明只写了三条规则,漏了本版唯一的代码改动:sop-generate 的 crawl.mjs 和 probe-login.mjs 出错时也会关浏览器,而且 close 的等待有 10 秒上限。应补半句,例如「sop-generate 采集脚本出错也关浏览器」。 |
| H2 | P2 | codex-toolkit-engineer/README.md:83 | hk-B | 0.13.0 的版本说明只写了三条规则，没提 sop-generate 的 crawl.mjs / probe-login.mjs 改成出错也关浏览器、关闭最多等 10 秒，而这是本版实际的代码行为改动。Claude 版 README 的 0.25.0 说明写到了 ui-sweep 的代码改动，Codex 版缺了对应的一句 |
| H3 | P2 | claude-toolkit-engineer/README.md:208 | hk-A | 0.25.0 的版本说明写了 ui-sweep 引擎跑完自动关会话,但没写 sop-generate 的 crawl.mjs 和 probe-login.mjs 出错也关浏览器(close 等待有上限)这项代码改动。应补上,和实际改动对齐。 |
| H4 | P2 | claude-toolkit-engineer/plugins/claude-toolkit-engineer/skills/parallel-do/SKILL.md:95 | hk-A | 「边界」这条除了加 T1、T2、W1,还新加了生产红线(FORBIDDEN FILES 等)的内容,这不在 spec §7 给 huake 的改动范围内。内容本身无害,也和 kit 的 Codex parallel-do 一致,但属于超范围改动,提交说明里应写明,或者拆出去单独提交。 |
| H5 | P2 | claude-toolkit-engineer/plugins/claude-toolkit-engineer/skills/parallel-do/SKILL.md:95 | hk-B | 新增的「开跑前先看负载」写的是「超过核数 70% 就少开并行单元」，没有给出量化做法；同一文件第 95 行边界条和 Codex 版 parallel-do 都写的是「并发按当前值减半（最少 1）」。两处标准不一样，主对话照这句执行时不知道该少开多少，建议改成「超过核数 70% 并行单元数按当前值减半（最少 1）、用顺序 await 分批」 |
| H6 | P2 | claude-toolkit-engineer/plugins/claude-toolkit-engineer/skills/scaffold/templates/CLAUDE.md.tmpl:97 | hk-B | 这份 Claude 版模板里没有 Workflow 并发上限那一条，所以 kit 接在那条末尾的「开跑前先看一次负载（§3 第 8 条），已高就少开并行单元或分批跑」没有放到别处，主对话开跑前看负载只能靠 §3 第 8 条里「开多个并行单元前先看负载」这半句推出来。Codex 版在 §7 实现那条末尾补了「分批前先看负载（§3 第 7 条）」，建议 Claude 版也在 §7 第 97 行「spec 经用户批准后直接用 ultracode…」末尾补一句「开跑前先看负载（§3 第 8 条），已高就少开并行单元或分批跑」，两版写法保持一致 |

复核过的检查点:

hk-A:
- Claude 版 CLAUDE.md.tmpl:§3 第 7、8 条和 kit 的 workflow CLAUDE.md.tmpl 逐字一致。T1 的要素③④⑤⑥⑦和 T2 的要素②③④都在;红线那条接的 W1 压缩版 7 个要素全有,条号写的是「§3 第 7、8 条」,实际就在 ## 3 修改后质量检查下面(第 62、63 行)。评审那条补上了「启动外部进程的单元还要核对退出要求有没有实现、有没有测到」;禁止事项加了一行,和 kit 一致。huake 模板本来就没有 Workflow 并发上限那条,所以不用接「开跑前先看负载」
- Codex 版 AGENTS.md.tmpl:huake 版没有 ui-sweep 那条,所以新规则编号是第 6、7 条;W1 那条写的「§3 第 6、7 条」和 §7 写的「§3 第 7 条」都指向实际存在的条目(T2 在第 58 行)。文本和 kit 的 workflow-codex 模板一致(kit 是 7、8 条)。盲审那条已补退出要求核对;huake 原来没有红线那条,所以 W1 单独新起了一条「派写入子任务的 prompt 边界里写明进程约束」,要素齐全
- Codex 版 parallel-do/SKILL.md:并发上限处接的看负载那段,以及边界里的 T1、T2、W1,和 kit 的 workflow-codex/parallel-do 一致;kit 版自己也没有评审核测试那一句,所以这里不缺
- Claude 版 parallel-do/SKILL.md:边界里有 T1、T2、W1 的全部要素;评审 agent 那条补了退出要求核对;新加的「开跑前先看负载」这条内容齐全(uptime 对比核数、超过 70% 减半或分批、超过核数或内存低于 20% 改串行)
- ui-sweep:worktree 里的 sweep.mjs、smoke-test.mjs、SKILL.md、export-state.mjs 和 kit 的 plugins/ui-sweep/skills/ui-sweep/ 用 diff 比对完全相同
- sop-generate:Claude 版 crawl.mjs 和 kit 的 workflow 版、Codex 版 crawl.mjs 和 kit 的 workflow-codex 版逐一 diff。剩下的差异只有本批之前就已经分叉的部分(waitForTimeout(300)、landingHref、注释和提示文案);closeBrowserBounded、try/finally、main().then 收尾这几处和 kit 一致。两份 probe-login.mjs 和 kit 的 workflow-codex 版一致;两份 SKILL.md 都加了「截完即关」这一句,和 kit 一致
- node --check:Claude 版的 sweep.mjs、smoke-test.mjs、crawl.mjs、probe-login.mjs,以及 Codex 版的 crawl.mjs、probe-login.mjs,全部通过
- 串行跑了一次 Claude 版的 ui-sweep smoke-test.mjs:35 passed, 0 failed,退出码 0。信号用例的子进程 60816、60890 用 ps -p 查过,都已退出
- plugin.json:claude-toolkit-engineer 是 0.25.0、codex-toolkit-engineer 是 0.13.0,两个文件都能被 JSON.parse 正常解析
- 两个 README 都在版本说明末尾加了一行;两个模板和两个 parallel-do 里没有出现 hearloop、hook-writer 这类内部项目名

hk-B:
- 两个 worktree 各跑了 git status --short：Claude 版只改了点名的 10 个文件（README、plugin.json、parallel-do、scaffold 模板、sop-generate 的 SKILL.md 与 crawl.mjs、probe-login.mjs，ui-sweep 的 SKILL.md、sweep.mjs、smoke-test.mjs），Codex 版只改了点名的 7 个文件，两边都没有新文件，也没有新建 mechanical 子代理
- 在两个 worktree 的 git diff -U0 新增行里查了 hook-writer、hearloop、stellark、gitlab.：都没有出现（gitlab.stellark.io、StellarkTony 只在原有行里，不是本批新增）
- 在 Codex 版 diff 新增行里查了 Workflow、agent()、mechanical、CLAUDE.md、Claude：都没有出现，「盲审的验收 subagent」等说法已改成 Codex 自己的用词
- 在两边新增行里查了兜底、落地、落盘、收口、闭环、链路、抓手、拉齐、沉淀、打回：「打回」只出现在原有句子「测试弱视同打回」里；「落地页」是 crawl.mjs 原有注释被重新缩进后出现在 diff 里，不是新增规则文本
- Claude 版 CLAUDE.md.tmpl 第 7、8 条接在原第 6 条（ui-sweep）后面，编号连续、不冲突；红线条引用的「§3 第 7、8 条」和实际编号一致；禁止事项加了一行
- Codex 版 AGENTS.md.tmpl 原来只有 5 条，新增编为第 6、7 条；§7 引用的「§3 第 7 条」、§8 新增的进程约束条引用的「§3 第 6、7 条」都对得上；盲审那条括号里的补充和 kit 定稿一致
- 两份模板的 diff 都只在已有列表里插入行或在行尾追加，模板占位符、表格、代码围栏都没有被改动
- Codex 版 parallel-do：并发上限条后面接了「分批前先看负载」，边界条接了 T1、T2、W1 压缩版，和原有的 max_threads 默认 6、分批 spawn 的说法不矛盾（kit 版边界条里的生产红线和 TDD 是 Codex 版原来就没有的，不属于本批范围）
- Claude 版 parallel-do：评审条、边界条加了退出核对、T1、T2、W1，新增的「开跑前先看负载」和档位表、pipeline 的说法不冲突
- Claude 版 ui-sweep 的 sweep.mjs、smoke-test.mjs、SKILL.md 和 kit plugins/ui-sweep 定稿逐字节相同（diff 无输出）；smoke 用的是 PATH 上放假 agent-browser，本次没有运行 smoke
- 两边的 probe-login.mjs 和 kit workflow-codex 定稿完全相同；Codex 版 crawl.mjs 和 kit workflow-codex 定稿相比，关浏览器那部分逻辑一致，剩下的差异是原有的（等待一拍、landingHref、MCP 措辞），不是本批新增
- Claude 版 crawl.mjs 用 git diff -w 看过：只加了 try/finally、closeBrowserBounded（最多等 10 秒）、超时后显式退出，其余 366 行变化都是缩进；出错时退出码 1、正常时 0 的路径都能对上
- 对两边改过的 crawl.mjs、probe-login.mjs、sweep.mjs 跑了 node --check，全部通过
- 两边 sop-generate SKILL.md 的「截完即关」那行内容和 kit 一致，只说只关自己启动的
- 版本号：Claude 版 plugin.json 改成 0.25.0、Codex 版改成 0.13.0，两边都没有其他需要同步的 version 字段（只剩 package-lock）；两边 README 的版本说明都加在已有版本说明的最后

## 镜像面第 1 轮分流(主对话)

**U5 huake**:无 P0/P1、无 conflict → 判通过。P2 都在提交前改掉:两个 README 的版本说明补「sop-generate 采集脚本出错也关浏览器、关闭最多等 10 秒」;Claude 版 parallel-do 的「少开并行单元」改成「并行单元数按当前值减半(最少 1)」;Claude 版模板 §7 实现那条接「开跑前先看一次负载」。Claude 版 parallel-do 的边界条顺带补了 kit 已有的生产红线列表(超出本批范围,内容与 kit 一致,提交说明里已写明)。主对话验证:Claude 版 smoke 35 通过 / 0 失败,ui-sweep 两个脚本与 probe-login.mjs 与 kit 定稿逐字节一致。已并入两仓 main(claude-toolkit-engineer 0.25.0、codex-toolkit-engineer 0.13.0)。

**U4 dev-toolkit**:1 条 P1——为了不超核心 SKILL.md 的 token 上限做的压缩,删掉了 §八 登录规则那句里「不受本节触发条件限制」「细则在 research.md」,只读核心的 agent 做小型登录改动时没有入口去读接入要求 → 退回,修复后跑裁决轮。P2 一并修:恢复「不许」「都是 medium」「因无 plan 失去入口」三处被压坏的措辞;GUARD「测试卫生」行写准「超过核数 70%、按当前值减半、最少 1」并补自己起名的会话与取读数的命令;核心 §四 的指向改成在核心里找得到的写法;process-exit.md 说明 GUARD 已含规则 T1/T2;stellark-parallel-do 的评审条补核对退出要求。spec §5 与 §7 对核心 SKILL.md 的要求互相矛盾(一处说 W1 保留七要素、一处说只留触发条件加指向),已把 §5 改成以 §7 为准。该仓 9 月进度日志归档由主对话收尾时另起提交。

