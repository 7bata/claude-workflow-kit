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
