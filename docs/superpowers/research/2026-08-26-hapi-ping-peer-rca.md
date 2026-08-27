# 根因说明:HAPI `ping_peer` 会把「本地模式」的目标会话强制切到 remote,顺手杀掉它的 Claude 进程

日期:2026-08-26 · 排查范围:只读,未改任何项目代码,未重启任何服务 · 证据原文:`docs/superpowers/research/2026-08-26-hapi-ping-peer-evidence.txt`(本仓 claude-workflow-kit;/tmp 下另有同名副本) · 本版已按三票 opus 反驳式核验(代码路径 / 日志时间线 / 规避建议)修订,修订处标「核验修订」

## 一句话结论

`ping_peer`(MCP 工具)和 `hapi ping-peer`(命令行)走的是同一条路:把消息 POST 到 hub 的 `/api/sessions/<目标>/messages`,hub 把它当成**网页端发来的用户消息**转给目标会话的 hapi 进程;目标会话如果正处在**本地模式**(终端里跑着交互式 Claude Code),hapi 会立刻执行"本地 → remote 切换":对交互式 Claude 的进程树发 SIGTERM,再用 Claude Agent SDK 以 `--resume` 起一个 remote 模式的新进程去处理这条消息。**被杀的是目标会话,不是发起方**;仍挂在 Claude 进程树上的后代(Workflow、子代理、后台 shell)一起被杀,MCP 连接断开后由新进程重连。

"resumes if inactive" 指的是另一回事:目标会话**离线**时,先 POST `/api/sessions/<目标>/resume` 让 runner 在对方机器上把它拉起来再发消息。这一步同样只作用于目标,与发起方无关;两次事故里目标都在线,这一步没执行(`resumed=false`)。(核验修订)它也不是"无害":拉起来的 agent 沿用对方原来的权限设置(可能就是 bypass)、无人看管地执行你这条消息;目标是已归档会话时归档标记会被清掉。

send-to 技能与此无关:它走的是 Claude Code 原生 `SendMessage`(`uds:/tmp/cc-socks/<pid>.sock`),不经过 hub,复现 T5 里对本地模式目标验证不会触发切换。

## 时间线(两次事故,均来自 `~/.hapi/logs` 原文)

会话对应关系:

| 窗口 | HAPI session | Claude session | hapi CLI pid / 日志 |
|---|---|---|---|
| 主窗口(askthestalks) | `e1f36ddc-…` | `08b5be7a-…` | 33470 / `2026-08-26-17-30-30-pid-33470.log` |
| 子窗口 | `9d9403d2-…` | `d8b2c509-…` | 10348 / `2026-08-26-18-05-45-pid-10348.log` |

**事故 1 — 18:10:36 主窗口切 remote,触发者是子窗口的 `ping_peer`**

```
子窗口  18:10:35.989  [hapiMCP] ping_peer: e1f36ddc
主窗口  18:10:36.022  [loop] User message received with permission mode: bypassPermissions ...
主窗口  18:10:36.025  [local]: doSwitch
主窗口  18:10:36.025  [ClaudeLocal] Abort signal received, killing process tree (pid=33486) with SIGTERM
主窗口  18:10:36.173  User message pushed to queue: text="来自 askthestalks 子窗口(session 9d9403d2 …" meta={sentFrom:"webapp", deliveryMode:"queue"}
主窗口  18:10:37.161  [ClaudeLocal] Child exited (code=143, signal=null, aborted=true)
主窗口  18:10:37.173  [Session] Mode switched to remote
主窗口  18:10:38.45x  SDK stream: task_notification ×2 —— 就是那两个 Workflow(wf_b9ec9b1f-3be "round5-frontend" / wf_b4cf2cdc-70c "round5-backend-money")的 "No completion record was found for background workflow … from the previous session" 通知
主窗口  18:10:59.140  [remote]: Switching to local mode via double space   ← 你在终端按了双空格
主窗口  18:10:59.194  [Session] Mode switched to local → Spawning claude with args: ["--resume","08b5be7a-…", …]
```

**事故 2 — 18:13:44 子窗口切 remote,触发者是主窗口的 `ping_peer`**

```
主窗口  18:13:44.220  [hapiMCP] ping_peer: 9d9403d2
子窗口  18:13:44.239  [loop] User message received …
子窗口  18:13:44.240  [local]: doSwitch
子窗口  18:13:44.241  [ClaudeLocal] Abort signal received, killing process tree (pid=10388) with SIGTERM
子窗口  18:13:44.940  Child exited (code=143)
子窗口  18:13:44.944  [Session] Mode switched to remote
子窗口  18:14:35.395  [Session] Mode switched to local → claude --resume d8b2c509-…
```

要纠正一点你的描述:主窗口**自己**调用 `ping_peer` 那次(18:13:44)没有让主窗口切 remote——主窗口自 hapi 接管(17:30:30)以来只切过一次,就是 18:10:36 被子窗口 ping 的那次(在此之前 Claude 会话 08b5be7a 已在 hapi 之外裸跑了约 3 小时,那段时间日志管不着);18:13:44 切 remote 的是**子窗口**。你在 18:17:14 说的"给子窗口发消息的时候又复现了",复现在子窗口那边。

(核验修订)来源排除:把两个会话全天 642 条消息的 meta 全扫一遍,`sentFrom=webapp` 的只有 2 条——e1f36ddc seq 505(子窗口这条 ping)和 9d9403d2 seq 41(主窗口那条 ping),其余用户消息全是 `sentFrom=cli`(你在终端敲的"继续"等)。没有网页/手机端来源。两个窗口的 transcript 里 `SendMessage`、`ListAgents` 的 tool_use 都是 0 次,Skill 调用主窗口 2 次(brainstorming、ui-sweep)、子窗口 0 次,没有 send-to。

## 机制(代码路径,源码在 `~/Tony/Proj/Stellark/Projects/hapi-long`,分支 feat/merge-long-fork)

1. 发起方:`cli/src/modules/pingPeer/pingPeer.ts` `pingPeer()` —— 换 JWT(POST /api/auth)→ `GET /api/sessions` 按前缀找目标 → 目标 `active=false` 才 `POST /api/sessions/:id/resume` 并等它上线 → 发送前再 `GET /api/sessions/:id` 复核一次(防 409 竞态)→ `POST /api/sessions/:id/messages {text}`。MCP 工具(`cli/src/claude/utils/startHappyServer.ts:294`)和命令行(`cli/src/commands/pingPeer.ts`)都调这个函数。全程只发 HTTP,不碰本进程。(核验修订)**没有"不能 ping 自己"的校验**:`list_peers` 会过滤掉调用方(`startHappyServer.ts:383`),`pingPeer()` 不会(`pingPeer.ts:480-483`),前缀写成自己的会话 id 就会把自己切 remote、杀掉自己的 claude。
2. hub:`hub/src/web/routes/messages.ts:121` 起的路由,第 174 行打上 `sentFrom: 'webapp'`,`engine.sendMessage()` 推给目标会话的 hapi CLI(顺带记 queued/activity 标记)。对在线目标没有任何"抢占"逻辑;两次事故 hub 日志都是 `POST /api/auth → GET /api/sessions → GET /api/sessions/<id> → POST /api/sessions/<id>/messages 200`,无 `/resume`。(核验修订)对**离线但 wake-eligible** 的目标,这条路由不返回 409 而是交给唤醒编排,可能返回 202 `{ok:true, wake:'queued'}`——`pingPeer` 只认 `ok===true`,会报"已发送",消息其实只是排在队列里。
3. 目标方(本地模式):`cli/src/claude/runClaude.ts:337` 打印 "User message received",同一 handler 末尾 `:485` 入队;`cli/src/modules/common/launcher/BaseLocalLauncher.ts:94-96` 注册了 `queue.setOnMessage(() => doSwitch())`,任何入队消息都触发 `doSwitch` → `abortController.abort()` → `cli/src/utils/spawnWithAbort.ts:68` "killing process tree with SIGTERM"。(核验修订)进程树是 `pgrep -P` 递归枚举的一次性快照(`cli/src/utils/process.ts:125-142`),每个 pid 先 SIGTERM、最多等 2 秒不死就 SIGKILL(`:181-204`);已脱离父子关系的后代(double fork、setsid、父 shell 先退出)不在快照里,不会被杀,会变孤儿。随后 `Mode switched to remote` → `cli/src/claude/claudeRemote.ts:160-183` 用 Claude Agent SDK `query({ resume: <id> })` 起新进程(ps 里那串 `claude --output-format stream-json …` 是 SDK 自己加的)处理消息 → 终端显示 "📱 Press space to switch to local mode" → 双空格后 `Mode switched to local`,再起交互式 `claude --resume <id>`。
4. 这是 HAPI 的设计行为,文档写明(`docs/guide/how-it-works.md:211-214` "Local → Remote: Receive a message from phone/web → Session automatically switches to remote mode")。`ping_peer` 的工具描述(`shared/src/sessionCitation.ts:28-32`)只写了 "resumes if inactive",没写"目标在本地模式会被强制切换并杀进程"。`deliveryMode: queue/steer` 对 claude 类会话没有区别(cli 侧只有 `cli/src/pi/runPi.ts:1104` 引用)。
5. 目标若**已经**在 remote 模式,消息只是入队交给现有 remote 进程处理,不杀进程(remote 模式没有任何 `setOnMessage` 注册;复现 T4 验证)。
6. 版本:事故发生时二进制是 0.27.2;18:23:57 另一个窗口把 hub/runner/二进制换成了 0.29.0(不是本次排查做的),复现在 0.29.0 上。(核验修订)0.27.2 的二进制已被覆盖,"两版逻辑一致"是从两次事故日志行与复现日志行逐字相同推断的,不是直接核对。

## 对三个现象的解释

1. **两个 Workflow 失去完成记录**:Workflow 跑在交互式 Claude 进程里,18:10:36 进程树被 SIGTERM;`--resume` 后 Claude Code 对"上个进程退出时还在跑的任务"报 "No completion record was found for background workflow "<名字>" from the previous session …"。复现 T1 里一条 `sleep 600` 后台 shell 得到同一模板的通知("… for this background shell command …")。
2. **MCP 工具断开又重连**:(核验修订)这条只有你的观察,日志和 transcript 里没有留痕("MCP server disconnected" 全库只在你 18:18 写给排查窗口的那段话里出现)。机制上说得通:hapi 的 MCP 服务是 hapi CLI 进程里的 HTTP 服务(主窗口是 `127.0.0.1:54539`,17:30:30 起没重启过),死的是 Claude 进程这一端,新进程起来后重新连上。
3. **更早一次重启(主窗口没调 ping_peer)**:就是 18:10:36 那次——子窗口在 18:10:35.989 对主窗口调了 `ping_peer`(它按你的要求"向主窗口报备并问一件事")。

## 排除的假设

| 假设 | 结论 | 依据 |
|---|---|---|
| send-to 技能导致 | 排除 | 两个窗口都没调过它;它的通道(原生 SendMessage)在复现 T5 中对本地模式目标不触发切换,hapi 只把它显示成 "⇄" 事件(`cli/src/claude/claudeLocalLauncher.ts:36-59`) |
| hub 侧 session 抢占 / resume 了发起方 | 排除 | hub 对在线目标只做转发;`/resume` 没被调用;发起方日志除 `[hapiMCP] ping_peer:` 外无任何切换记录;复现 T2 发起方进程 pid 不变。唯一能"自伤"的口子是把自己的 id 当目标(见机制 1) |
| runner 重启牵连 | 排除 | 事故时刻(18:10:36 / 18:13:44)runner 日志无事件;runner 不管理终端起的会话进程。(核验修订)事故之后 18:15:57 runner 连报三次 `claude agents --json` 超时 SIGKILL,18:16:03 被停、18:24:00 才回来——都晚于事故 |
| 18:23:57 hub 重启 | 排除 | 晚于两次事故;主窗口也在 18:23:57 断连 1.3 秒后重连(33470 日志 7846-7847 行),与事故无关 |

## 复现记录(2026-08-26 18:26:22–18:35:13,两个一次性会话,已清理)

环境:tmux 里各起一个 `hapi --dangerously-skip-permissions`,工作目录 `/tmp/hapi-repro/X`、`/Y`;启动环境去掉了本会话继承的 `CLAUDECODE/CLAUDE_*/HAPI_SESSION_ID`,并设 `HAPI_API_URL=http://100.100.144.81:3006` 让 runner 身份校验通过(`Runner identity match: true`,runner 未重启)。Claude Code 2.1.246,hapi 0.29.0。(核验修订)同机同时还有 runner 起的别的会话在跑(18:28:52 e18ed57a、18:28:59 cwcode、18:32:56 9755e48a),与 X/Y 不同会话,不影响下面的因果。表里的子进程 pid 来自当时的 ps 快照,事后只能核对被杀的 81559/82042 两个。

| 会话 | HAPI session | Claude session | hapi pid | 交互式 claude pid |
|---|---|---|---|---|
| X | `980ba46d-…`("Sleep 600 background task") | `1033a216-…` | 81538 | 81559 |
| Y | `280f3f9b-…`("MCP hapi ping peer") | `0dc390e2-…` | 81999 | 82042 |

**T1:Y → X(X 本地模式,带后台任务)**
- 步骤:X 里输入 "Use the Bash tool with run_in_background=true to run exactly this command: sleep 600. Then reply STARTED." → 18:28:17 `sleep 600` pid 90960 起来。Y 里输入 "Call the MCP tool mcp__hapi__ping_peer with sessionIdPrefix=980ba46d and message=\"REPRO-T1 ping from Y\"."
- 结果原文:
  ```
  T1 pre:  18:28:56 X-claude-pid=81559 alive=yes; sleep600 alive=yes
  Y  18:29:03.959 [hapiMCP] ping_peer: 980ba46d
  X  18:29:03.980 [loop] User message received with permission mode: bypassPermissions ...
  X  18:29:03.982 [local]: doSwitch
  X  18:29:03.982 [ClaudeLocal] Abort signal received, killing process tree (pid=81559) with SIGTERM
  X  18:29:04.055 User message pushed to queue: "text": "REPRO-T1 ping from Y"  "sentFrom": "webapp", "deliveryMode": "queue"
  X  18:29:04.734 [ClaudeLocal] Child exited (code=143, signal=null, aborted=true)
  X  18:29:04.741 [Session] Mode switched to remote
  X  18:29:06.711 stream message #15 type=system subtype=task_notification  task_id b5ig0145c status "stopped"
       summary "No completion record was found for this background shell command from the previous session. It may h…"
  T1 post: 18:29:27 X-claude-pid=81559 alive=no; sleep600(90960) alive=no; Y-claude-pid=82042 alive=yes
  X 终端:「📱 Press space to switch to local mode • Ctrl-C to exit」
  Y 日志新增只有那一行 ping_peer,无 doSwitch。
  ```

**T4:Y → X(X 已在 remote 模式)**
- 结果:X 的 remote 子进程 95993 存活;X 日志 `18:29:57.903 User message received` → `Thinking state changed` → `result #3 received`,**没有** doSwitch / Abort / Child exited。说明只有"本地 → remote"这一步会杀进程。

**X 回本地**:18:30:41 双空格 → `[remote]: Switching to local mode via double space` → `Mode switched to local` → `Spawning claude with args: ["--resume","1033a216-…"]`,新 pid 5332(再次弹出信任目录提示)。

**T3:只读对照,`hapi inspect-peer 280f3f9b --limit 5`(目标 Y 本地模式)**
- 结果:正常打印 sessionId/name/active=true/lifecycle=running/最近消息;Y 的 claude 82042 存活;Y 日志无任何 "User message received"/doSwitch。

**T2:X → Y(反向,看发起方)**
- 步骤:X 里输入 "Call the MCP tool mcp__hapi__ping_peer with sessionIdPrefix=280f3f9b and message=\"REPRO-T2 ping from X\"."
- 结果原文:
  ```
  T2 pre:  18:31:27 X-claude(local) pid=5332 alive=yes; Y-claude pid=82042 alive=yes
  X  18:31:33.635 [hapiMCP] ping_peer: 280f3f9b          ← X 日志新增仅此一行
  Y  18:31:33.652 [loop] User message received …
  Y  18:31:33.654 [local]: doSwitch
  Y  18:31:33.654 [ClaudeLocal] Abort signal received, killing process tree (pid=82042) with SIGTERM
  Y  18:31:34.664 Child exited (code=143)
  Y  18:31:34.667 [Session] Mode switched to remote
  T2 post: 18:31:58 X-claude pid=5332 alive=yes; Y-claude pid=82042 alive=no
  X 终端正常显示 DONE 继续待命;Y 终端变成 remote 模式提示;Y 新子进程 9381(SDK 起的 stream-json 进程)
  ```

**T5:X → Y,改用 Claude Code 原生 SendMessage(send-to 技能的通道)**
- 步骤:Y 双空格回本地(新 pid 15209,socket `/tmp/cc-socks/15209.sock`);X 里输入 "ToolSearch select:SendMessage, then SendMessage to=uds:/tmp/cc-socks/15209.sock message=\"REPRO-T5 native SendMessage from X. No reply needed.\""
- 结果:X 显示 `“REPRO-T5 native message” → uds:/tmp/cc-socks/15209.sock` 并回 DONE;Y 终端直接收到并回复"收到 X 的 REPRO-T5 消息(原生 SendMessage)…";`T5 post: X pid=5332 alive=yes; Y pid=15209 alive=yes`;两边 hapi 日志都没有 "User message received"/doSwitch(hapi 全程不参与)。只验证了目标处于**本地模式**的情况。

清理:两会话 `/exit`(18:35:13),tmux server 已杀,`/tmp/hapi-repro` 已删,无残留 `sleep 600`/claude 进程;hub 数据库里留下两条非活动会话行(`980ba46d` "Sleep 600 background task"、`280f3f9b` "MCP hapi ping peer"),可在网页端归档。

## 能避免的用法(立即可执行)

1. **只是想看对方状态/最近对话**:用 `mcp__hapi__inspect_peer` 或 `hapi inspect-peer <id>`;`list_peers` 同样。对方的进程和终端都不动(它们只发 GET;首次会 POST /api/auth 换一枚 4 小时的 JWT)。
2. **要把消息送进一个正在终端里工作的窗口(本地模式)**:
   - 首选 Claude Code 原生 `SendMessage`,按 send-to 技能的阶梯找地址:同 profile 的用 `ListAgents` 按名字发;不同 profile(你的主窗口在默认配置、子窗口在 labs 配置,互相看不见)先读身份注册表 `/tmp/cc-session-registry/`(两个窗口都有条目),认对人再对 `uds:` 地址发;不许拿 pid 盲发。T5 验证不会重启对方。边界:两边权限模式类别不同时消息会在对方那里挂起等批准,只能说"已发送";目标处于 remote 模式时这条路未验证。
   - 或者写成一个文件,由你复制路径贴到对方窗口,零风险。
3. **`ping_peer` / `hapi ping-peer` 只对已经在 remote 模式(网页/手机端控制,或 runner 起的)的会话用**,这种情况下它只入队、不杀进程(T4)。(核验修订)对**离线**会话用它 = 在对方机器上按对方原来的权限设置起一个无人看管的 agent 去执行你这条消息,已归档的会话会被拉活;返回"已发送"也可能只是排进了唤醒队列。要唤醒别人的会话前先想清楚。
4. 对本地模式窗口不用 `ping_peer`,没有"确认对方没在跑任务就可以"的例外——`inspect_peer` 看不出对方有没有 Workflow 在跑(`thinking` 只反映当下是否在推理)。真要这么做只能由你本人在明知后果(终端切 remote、进行中的任务丢、要按双空格回来;对话历史不丢)下亲自决定,Claude 不得自行选择;send-to 技能与全局规则均按此执行。
5. 凡是人开着的终端窗口一律不 ping;现在的工具看不出对方是终端模式还是网页模式(`inspect_peer` 不显示 `controlledByUser`,`list_peers` 只有 id/active/flavor/名字)。

## 要不要提 issue

**要。** 建议先提到自己的 fork(hapi-long,gitlab.stellark.io),再视情况提到上游 tiann/hapi(上游同样有 `ping_peer`,代码里引用了 tiann/hapi#1143、#1195)。可直接粘的标题与正文(已按核验修订):

> **`ping_peer` / `hapi ping-peer` silently kills the target's interactive agent (and in-flight background work) when the target is in local mode; no self-target guard**
>
> `ping_peer` posts to `/api/sessions/:id/messages` with `sentFrom: 'webapp'`. For a target in local (terminal) mode this triggers the documented local→remote switch (`BaseLocalLauncher` `queue.setOnMessage → doSwitch`), which SIGTERMs the interactive Claude process tree (`pgrep -P` snapshot, SIGKILL after 2 s per pid). Everything still attached to that tree — Workflows, background shells, subagents — is lost; Claude Code reports "No completion record was found … may have been running when the previous Claude Code process exited" on resume. The tool description only says "resumes if inactive"; nothing warns that an *active* local-mode target will be restarted. `pingPeer()` also does not exclude the caller's own session id (unlike `list_peers`), so a prefix matching yourself kills your own session. For an *inactive* target, `resume` spawns an unattended agent on the target machine with the session's stored permission mode and clears the hibernated marker; a wake-eligible inactive target returns 202 `{ok:true, wake:'queued'}` which the CLI reports as success.
>
> Repro (two `hapi --dangerously-skip-permissions` terminals X/Y, hapi 0.29.0, Claude Code 2.1.246): X runs `sleep 600` in background; Y calls `ping_peer` → X log: `User message received` → `[local]: doSwitch` → `killing process tree (pid=…) with SIGTERM` → `Child exited (code=143)` → `Mode switched to remote`; X's background shell is dead and the resumed process emits the "No completion record" task notification. Initiator Y is unaffected. Same log lines on 0.27.2 in production logs.
>
> Proposals: (1) document the behavior in the MCP description and `hapi ping-peer --help`; (2) in `pingPeer()`, fetch `GET /api/sessions/:id` (the hub already returns `agentState.controlledByUser`; the CLI type just drops it) and refuse when `active && controlledByUser` unless `force: true` — note `controlledByUser` is not cleared on exit, so `active` must be part of the predicate; also refuse `sessionId === client.sessionId`; treat 202/`wake:'queued'` as "queued", not "sent"; (3) expose `mode=local|remote` and `claudeSessionId` in `inspect_peer` (client-only change) and, if the hub adds them to `SessionSummary`, in `list_peers`; (4) optionally, for same-machine claude targets in local mode, deliver through Claude Code's native messaging socket (`/tmp/cc-socks/<pid>.sock`; hapi spawns claude directly so it knows the pid) — trade-offs: undocumented Claude Code protocol, and such messages would not appear in hub history (web/phone can't see them); (5) longer term, let a local-mode session *queue* a hub message and show a terminal notice instead of switching.

## 顺带发现(与本次根因无关,记录备查)

- (核验修订)每次在终端启动 `hapi`,runner 会两步来回重启:交互式 hapi 先把 launchd 管的 runner 停掉、自己起一个(apiUrl=`http://localhost:3006`、没有 workspace roots,并以此身份注册机器),约 0.8 秒后 launchd 的正牌 runner(apiUrl=`http://100.100.144.81:3006`、workspace roots=/Users/tbata/Tony/Proj)起来再把它停掉。原因是 `cli/src/runner/controlClient.ts:180` 解析 apiUrl 时 settings.json 没有 `apiUrl` 字段。设了 `HAPI_API_URL=http://100.100.144.81:3006` 就不重启。对 runner 起的会话有没有影响未验证(它们是 runner 的子进程)。
- (核验修订)主窗口 hapi 33470 从 17:30:32 到 18:10:36 每秒报一次 `[FILE_WATCHER] ENOENT`,盯的是 resume 选择器切换前那个瞬时会话(90bae865)的 transcript,没有随 17:30:37 切到 08b5be7a 而更新监视目标,日志被撑到 1.2 MB;不是事故成因(事故走消息队列,不走文件监视)。
- (核验修订)每次 runner 起来都先报 `[ACP] Process error ENOENT spawn agent` 并重试;18:15:57 runner 10392 连报三次 `[WORKER ROSTER] Failed to list background agents`(`claude agents --json` 超时 SIGKILL)。
- labs 配置的 SessionStart hook 指向不存在的 `/Users/tbata/Proj/Stellark/Projects/speak-human/hooks/inject.sh`,每个新会话都报一次非阻塞错误(记忆里已有"旧 hook 路径别修要删"的备注)。
- 18:23:57 有另一个窗口把 hub/runner/`hapi-stellark` 二进制换到了 0.29.0——不是本次排查做的;包括主窗口在内的所有会话在那个时刻经历了一次 hub 断连重连。
