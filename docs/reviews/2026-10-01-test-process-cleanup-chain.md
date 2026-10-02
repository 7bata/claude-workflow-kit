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

