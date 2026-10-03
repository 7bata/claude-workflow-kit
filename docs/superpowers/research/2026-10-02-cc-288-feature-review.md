# Claude Code 2.1.280 → 2.1.288 新功能对照(2026-10-02)

起因:Tony 问「最近 claude code 新版本出了什么新功能,你觉得可以加到这个 workflow 里的?」,随后把本机升到 2.1.288。上次对照是 2026-09-19(审到 2.1.278,采纳 omitClaudeMd 机械子代理与并发上限 env,AGENTS.md 被 YAGNI),所以本次范围是 2.1.280 → 2.1.288(2.1.279 不存在)。

## 方法

- 资料:官方 CHANGELOG(`anthropics/claude-code/CHANGELOG.md`,8174 行),范围内 Added/Changed/Improved/Removed 共 320 行(滤掉 IDE 与读屏),涉及子代理 / hook / 插件 / skill / 权限的 Fixed 共 217 行;官方文档 workflows / sub-agents / skills / memory / plugins 页;本机 `claude --help`、`claude plugin --help`、settings.json(只读)。
- 编排:一个 Workflow,5 个主题各 1 个 `sonnet` + `medium` 调查员做「是否已在 kit / 怎么加 / 要镜像哪几面」映射,每主题 2 个互不可见的 `opus` + `medium` 评审盲审(镜头:事实核对 / 价值契合)。15 个 agent,约 111 万 token,4.6 分钟,无失败。机器负载开跑前 5.6(10 核)、内存余 38%。
- 盲审结果:40 条发现里 19 条被评审 adjust 或 refute(非 P2)。推翻的主要是「本机测不到 plugin details」(其实是 `--plugin-dir` 要放在子命令前面)、「userConfig 会让四个 profile 配置分裂」(各 profile 的 settings.json 是软链到同一个文件)、「2.1.284 起拒答回落不再固定上一代」(那条只对钉了 Opus 的会话生效,本机钉的是 Sonnet)。下面的结论已按盲审修正。

## 结论总表

| # | 候选 | 版本 | 建议 | 代价 | 一句话 |
|---|---|---|---|---|---|
| A | `claude plugin validate --strict` + `claude plugin details` 进发版清单 | 2.1.281 / 2.1.139 | **采纳** | S | 两条只读命令,今天就能防插件清单、路径、引号类低级事故,并给每个插件一个 token 成本数字 |
| B | `mechanical` 子代理 frontmatter 加 `effort: low` | 2.1.78(2.1.267、2.1.288 修复) | 考虑,先冒烟 | S + 1 次冒烟 | 裸 Agent 派 mechanical 时也按 low 跑;规则第 39 行「裸 Agent 降不下来」要补例外 |
| C | 评审链盲审轮做成插件自带的命名 workflow | 文档确认(插件 `workflows/` 目录) | 考虑,先出 spec | M | 固化「2~3 个 opus 盲审 + 按 file+line 归并 + 标 conflict」这一段;分流与裁决仍留主对话 |
| D | `verify` skill 提交前自动提示 | 2.1.286 | 考虑,先一次性实测 | S | 不发模板;在项目里跑一次内置 `/verify` 生成自维护配方,CLAUDE.md.tmpl 补一句 |
| E | `/doctor prompt-audit` 审 CLAUDE.md、skill、agent 的过期写法 | 2.1.283 | 考虑,先手动跑一次 | S | 不能非交互跑(已试 `claude -p`,无输出);Tony 在会话里跑一次,结果当线索,用过一两次再决定要不要写进规则 4 |
| F | omitClaudeMd 的省 token 效果是否被 2.1.288 按需加载打折 | 2.1.288 | 只做冒烟 | 1 次冒烟 | Write/Edit 时子代理也会按需加载子目录 CLAUDE.md 与 `.claude/rules`;09-19 只验了开局不加载 |
| G | sonnet 别名复查 | — | 考虑 | S | 2.1.285→288 没有别名改动的新证据;只是升级后再测一次,须放在对照实验两批之间 |
| H | 规则第 16 行「常年挂着 xhigh」补半句事实 | 2.1.284 / 2.1.251 / 2.1.280 | 顺手并入下次规则修订 | S | 前提已核实仍成立(settings.json effortLevel xhigh);ultracode 不再等于 xhigh,effort 按模型保存 |

其余候选建议不做,理由见「不做的项」。

## 各候选详情

### A. validate --strict 与 plugin details 进发版清单(采纳)

- 证据:2.1.281 "Added MCP server checks to `claude plugin validate`: it reports `.mcp.json` entries that would be silently dropped at load, undeclared `${user_config.*}` references, and insecure URLs";同版 "added a `claude plugin validate` warning when a shell-form hook leaves `${CLAUDE_PLUGIN_ROOT}` unquoted";2.1.283 补了 outputStyles/themes/monitors/lspServers 路径检查。`claude plugin details <name>`:"Show a plugin's component inventory and projected token cost"。
- kit 现状:hooks.json 六处都已加引号;本机实跑 `claude plugin validate <path> --strict` 对 workflow、workflow-en、speak-human、speak-human-en、send-to、send-to-en、ui-sweep、ui-sweep-en 与仓库根 marketplace 全部通过。但 README、docs/PLAN.md、Progress 都没有把 validate 写成发版步骤。
- 实测 token 成本(`claude --plugin-dir plugins/<p> plugin details <p>`,注意 `--plugin-dir` 要放在 `plugin` 子命令前面):workflow 常驻约 465 tok(scaffold 调用约 6.8k、sop-generate 4.1k、whats-next 1.7k、mechanical 400);speak-human 181(调用 8.4k);send-to 177(调用 10.1k);ui-sweep 159(调用 8.2k)。hook 标注 "harness-only — no model context cost"。四个插件常驻合计约 980 tok。
- 做法:README zh/en 与 docs/PLAN.md 加一段「发版前」:`for p in plugins/*; do [ -d $p/.claude-plugin ] && claude plugin validate $p --strict; done; claude plugin validate . --strict`,再对每个插件跑一次 details 把常驻 token 记进 Progress。可选:包一个 smoke 脚本。
- 风险:几乎没有;`--strict` 把警告当错误,以后 plugin.json 加未识别字段会变红,这正是目的。

### B. mechanical 加 `effort: low`(考虑,先冒烟)

- 证据:2.1.78 "Added `effort`, `maxTurns`, and `disallowedTools` frontmatter support for plugin-shipped agents";2.1.267 "Fixed `effort:` frontmatter on custom commands, skills, and subagents being ignored on models whose default effort is still pinned";官方 sub-agents 文档 effort 字段写 "Overrides the session effort level";2.1.243 起 `/tasks` 与子代理详情直接显示每个子代理实际的模型与 effort。盲审纠正:2.1.288 那条 "Fixed agent teams: a plugin-defined agent spawned by name now runs with its own ... effort" 修的是 agent teams,不能当裸 Agent 的证据。
- kit 现状:`plugins/workflow/agents/mechanical.md` frontmatter 只有 name / description / omitClaudeMd / tools;全局 CLAUDE.md 第 39 行与 README 第 227 行写「裸 Agent 工具没有这个参数,派出去的子代理只能继承主会话档位、降不下来」——对自带 `effort:` 的子代理类型这句已不成立。
- 做法:mechanical.md(workflow 与 workflow-en,镜像 dev-toolkit 与 huake)加一行 `effort: low`;Workflow 里 `opts.effort` 照旧显式写(值与 frontmatter 相同,谁优先都不影响结果);冒烟一次:裸 Agent `subagent_type: mechanical` 在 xhigh 会话里派一个探针,`/tasks` 看实际 effort。通过后第 39 行补例外:「带 `effort:` frontmatter 的子代理类型(如 mechanical)裸派也按声明档位跑」。
- 取舍:frontmatter 写死 low 后 mechanical 不能按 stage 升档;但 mechanical 只服务两类纯机械 stage,档位表对它们本来就定 low,「失败才升档」在这两类上基本不触发。haiku 是否接受 effort 只在真派 haiku 时再测。
- 文档没写 Workflow `opts.effort` 与 frontmatter 谁优先(model 有顺序:按次传入 > frontmatter > 环境变量 > 会话;effort 没写)。

### C. 盲审轮做成插件命名 workflow(考虑,先出 spec)

- 证据:官方 workflows 文档 "Distribute a workflow in a plugin: Place the script in a `workflows/` directory at the plugin root, or point to a different location with the `workflows` manifest field. Plugin workflows are namespaced by the plugin name ... runs as `/acme-tools:release-audit`";"A saved workflow can accept input through the `args` parameter";对命名的插件 workflow 首次运行可选 "Yes, and don't ask again"。官方 claude-security 插件已经这么做(`workflows/scan.js`,plugin.json 无 workflows 字段)。首次版本 changelog 没查到。
- kit 现状:评审链(盲审 2~3 + 续挖 + 裁决 + 按 file+line ±3 归并 + conflict 标记)只在全局 CLAUDE.md 规则 2 与 README 用文字描述,每次由主对话临时手写脚本;plugins/workflow 下没有 workflows/ 目录。
- 做法(盲审缩小后的版本):只固化「盲审 + 归并 + 标 conflict」这一段:`plugins/workflow/workflows/review-blind.js`,args 传 `{unit, files, specPath, chainFile, n: 2|3, effort: 'medium'|'high', lenses}`,脚本内 `parallel()` 跑 n 个 `opus` 评审(统一 schema `findings[{file,line,severity,claim,lens}]`),纯 JS 做归并(file 用仓库相对路径、line 取起始行、±3 视为同一位置、无行号按 file + claim 前 40 字、同位置结论相反或严重度不同标 conflict),返回 `{merged, conflicts}`。分流(通过 / 裁决 / 修复后续挖)与裁决轮仍由主对话决定——这样不违反 CLAUDE.md 第 43 行「编排逻辑与最终汇总不进 workflow」。调用变成 `workflow('workflow:review-blind', {...})` 或 `/workflow:review-blind`。
- 取舍:评审链跨多次运行(修复后再开一次接原链),命名 workflow 只覆盖一段,链文件 docs/reviews 仍由主对话追加;多一个漂移面(脚本 + 规则 2 + README zh/en + dev-toolkit + huake,改规则要动 6 处);workflow-codex 没有 Workflow 工具,无法对应;脚本里不能读写文件、不能用 Date.now()。收益取决于每月跑多少次评审链——本仓 docs/reviews 只有 1 个链文件,stella 等项目应更多,定之前先数一下。
- 冒烟:临时目录建最小插件(plugin.json + workflows/hello.js),`claude --plugin-dir` 加载,确认 `/<plugin>:<name>` 出现、`Workflow({name})` 能调、args 能传、脚本内 agent() 的 model/effort/agentType 生效。

### D. `verify` skill(考虑,先一次性实测)

- 证据:2.1.286 "Improved commit guidance: when your project or user skills include one named `verify`, Claude is now told to run it right before committing, except for docs-only and tests-only commits";skills 文档:"The recipe that `/verify` records at your repo root is a project skill, so it counts. The bundled `/verify` and `/simplify`, plugin skills, and skills from your claude.ai account don't count"(不能带 `disable-model-invocation: true`);2.1.205 "Fixed project verify skills being rewritten on every session instead of only when a documented command changed"(内置 `/verify` 会生成并自维护项目级 verify skill);2.1.215 "Claude no longer runs the `/verify` and `/code-review` skills on its own"。
- kit 现状:scaffold 只产出 .claude/CLAUDE.md、docs/*、.gitignore、README.md、data/.gitkeep,没有 .claude/skills/;commit-gate hook 只管 docs 消化,不跑测试。
- 做法:不发模板(插件 skill 不算数;模板配方会过期,还要多四份维护)。两条便宜路线:① 项目有测试命令后跑一次内置 `/verify`,它生成的项目级配方算数且随命令变化自动重写——在 CLAUDE.md.tmpl 的验证段与 whats-next 补一句;② 用户级 `~/.claude/skills/verify` 写一份通用配方(按项目 CLAUDE.md / Makefile 找测试命令,再核对测试进程已关),本机所有项目一次生效,但不随 kit 分发。
- 风险:评审链的 `squash!` 修复提交多数是源码改动,每次都会提示跑 verify,拖慢时延;`includeGitInstructions` 关掉就整体失效;Workflow 子代理里 commit 是否收到提示未知。
- 实测:临时仓库放一个项目级 verify skill,新会话提交一个源码改动看是否先跑 verify;docs-only 提交看是否豁免;Workflow 子代理里提交看是否也被提示。测完关掉启动的进程。

### E. `/doctor prompt-audit`(考虑,先手动跑一次)

- 证据:2.1.283 "Added `/doctor prompt-audit` (also `/checkup prompt-audit`) to audit your CLAUDE.md files, skills, agents and commands for prompting patterns written for older models";同版 "stale paths, stale commands and contradicting instruction files now lead the report, and thinking keywords that Claude Code documents are kept"。
- 本次实测:`claude doctor --help` 只有 `-h`;`env -u CLAUDECODE claude -p "/doctor prompt-audit"` 退出码 0、无任何输出——内置命令在 `-p` 里不运行,所以不能在 CI 或脚本里跑,只能在会话里敲。
- 对应规则:档位表规则 4「经验校准有保质期……主力模型换代后失效待验」只规定复盘打回率与 token,没有「审提示词本身是否过期」这一步。全局 CLAUDE.md 111 行 / 31KB,其中 22 行超过 400 字符;CLAUDE.md.tmpl 145 行 / 21KB。
- 做法:Tony 在本仓会话里跑一次 `/doctor prompt-audit`,结果由主对话甄别(它按「旧模型写法」判定,可能建议删掉有意保留的强约束措辞,照单全收会削弱规则),记进 Progress;用过一两次再决定要不要写进规则 4(与 AGENTS.md 被 YAGNI 同理:一年做一两次的事先别进规则)。

### F. omitClaudeMd 按需加载冒烟(只做冒烟)

- 证据:2.1.288 "Fixed path-scoped `.claude/rules` and nested CLAUDE.md files not loading when Write or Edit creates or changes a file in their scope (previously only Read loaded them)";2.1.288 "Fixed the InstructionsLoaded hook omitting agent_id and agent_type when a subagent's file access loads a rule or nested CLAUDE.md"——说明子代理访问文件时也会按需加载。
- 疑点:omitClaudeMd 文档只说屏蔽开局自动加载的 user / project / local CLAUDE.md;目标项目有子目录 CLAUDE.md 或 `.claude/rules` 时,mechanical 批量改文件会不会把它们加载进来,09-19 的冒烟没测(当时只验了开局 NORULE)。
- 做法:临时项目放一个子目录 CLAUDE.md,用 InstructionsLoaded hook(2.1.288 起载荷带 agent_id / agent_type / effort)记录,派 mechanical 去 Edit 那个子目录里的文件,看 hook 有没有记到加载。结果写进规则里 mechanical 那一行。

### G. sonnet 别名复查(考虑)

- 2.1.285→2.1.288 没有任何一行说别名解析改了;2.1.284 的 "now the default Sonnet model on the Anthropic API" 是 09-28 实测时就有的旧文字(当时 2.1.284 上 sonnet 别名仍解析到 claude-sonnet-5),且限定 Anthropic API,本机是 claude.ai 登录。
- 做法:只是升到 2.1.288 后再测一次(一次性子代理 transcript 的 model 字段);删 env 钉必须放在对照实验两批之间,删前删后都按实测模型 ID 核对,否则同一批会混进两代模型。更新 docs/DECISIONS.md 的复查项。
- 另:2.1.288 "Changed the client-side auto mode classifier to ignore an `ANTHROPIC_DEFAULT_SONNET_MODEL` pin that names Claude Sonnet 5.5 or Opus 5.5" 只在 auto mode 下起作用,本机是 bypass,不受影响。settings.json 第 16 行 `"model": "claude-fable-5-1"` 是完整 ID,2.1.287 的 Fable 别名修复不影响它;改不改成别名是 Tony 本机偏好,不属 kit。

### H. 规则第 16 行前提补半句(顺手并入下次修订)

- 核实:~/.claude/settings.json 顶层 `effortLevel: xhigh`,`modelSettings` 里 claude-fable-5-1 为 xhigh、claude-fable-5 为 low、claude-opus-5-5 没有条目。所以「我常年挂着 xhigh」对主会话(Fable 5.1)成立,规则结论「逐 stage 显式写 effort」不变。
- 要补的事实:2.1.284 "Changed Ultracode into its own toggle in `/effort` ...: it no longer forces xhigh effort and stays on at any effort level"(但 `claude --effort ultracode` 启动仍会同时设 xhigh);2.1.251 起 effort 按模型保存;2.1.280 "an effort level saved before `/effort` became per-model to no longer apply to newly released models such as Opus 5.5; they start at their default until you pick a level";2.1.287 "automatic model switches after a flagged message to keep your current effort level instead of the new model's default"。
- 另一条相关事实(官方 workflows 文档):ultracode 开着时,裸 Agent 的并发子代理上限(默认 20,`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`,2.1.217 起)不再强制,Large workflow 警告也不显示——与「并发前先看负载」互补,可在并发上限那段补一句。
- 价值低、成本 S,不单独开改动。

## 不做的项(附修正后的理由)

- **Claude Mods(2.1.287)与内置 "You should know" 旁观 mod**:kit 四个 shell hook 工作正常;改成 mod 要带 TS 依赖与 ≥2.1.287 版本门槛,还多出 workflow-en 与 dev-toolkit 两份镜像;"You should know" 需要 telemetry 开着,本机 settings.json 没开。DECISIONS.inbox 待消化条数做成状态条也不省 token、不防事故,commit-gate 已在 commit 前挡住。与 AGENTS.md 同属「有了没坏处但没人用」。
- **插件 userConfig + `claude plugin configure`(2.1.285)替代 touch 文件开关**:真实代价是两套开关要兼容并存,外加 README、SKILL、smoke、evals 四五处联动;调查员原先的「四个 profile 配置分裂」理由不成立——labs/long/tech 的 settings.json 软链到同一个文件,touch 文件能共享是因为 hook 里写死 `$HOME/.claude`。
- **拆 `.claude/rules` 路径条件规则**:kit 的规则绑定动作(派子代理、commit、截图)不绑定文件路径,`paths:` 触发不了;文档明说 `@path` 导入不省上下文;可路径化的段不到 5%。真要瘦身是删段,见 E。
- **迁到 `claude plugin eval`(2.1.269)**:还在 early access;默认会把 HTML 报告发布到 claude.ai(`--help` 原话 "already the default when your account supports it",试点必须 `--no-publish`,speak-human 的案例来自 Tony 真实抉择);每个用例默认跑 3 次、两臂合计 6 个 claude 子进程;历史分数断档;近一个月 evals 没有改动需求,也没有「自建脚本测不到真实触发」的事故。记为跟踪项。
- **/code-review `--max-findings`(2.1.288)当评审链第三票**:2.1.215 起它不再自动运行;是会话内 skill,Workflow agent 能否稠定调用未验;评审链已有异构外部评审(codex / cwcode)。
- **`--bare` 用于评测隔离(2.1.286)**:需要 API key,不读 OAuth,本机是 claude.ai 登录;run_evals.py 本来就用 HERMETIC 环境变量关 hook、把规则拼进 prompt,与 --bare 不冲突但也不需要。若要更严的隔离,2.1.248 的 `--restricted`(不需要 API key、忽略用户设置)是替代。
- **后台命令时限写进规则**:2.1.285 加时限(默认 30 分钟、最长 2 小时),三个版本后 2.1.288 改成只在无人值守会话生效、终端无上限——变化太快,规则正文已要求「谁启动谁关」,不写版本行为。
- **WorktreeCreate / WorktreeRemove hook(2.1.50)强制 worktree 位置与清理**:Stop hook worktree-sweep 已够用。
- **跨会话(T4)八项全部不单独改**,下次改 send-to 时顺手带上:① 2.1.285 `claude --resume <id> "prompt"` 会把 prompt 当对方用户本人的下一轮输入投进后台会话,绕过 held 门、无发件人标识,风险与 ping_peer force 同类,应明写禁止作投递路径;② 2.1.284 "Fixed sessions launched without the `SendMessage` tool (such as by Claude Desktop)…"——桌面应用起的会话没有 SendMessage,send-to 的 L1–L3 用不了,应直接走文件交接;③ 2.1.288 held 消息的送达通知现在会说「未送达并点名会话」,但「通知异步、没收到也不许断言没被挂起」仍成立,不放松;④ 全局 CLAUDE.md「HAPI 跨会话传话规则」四条无一过时。
- **auto mode 成为默认(2.1.283/284/285)**:本机 `permissions.defaultMode: bypassPermissions`,不受影响;但 kit 是公开发布的,没设 defaultMode 的 kit 用户从 2.1.284 起默认进 auto mode,send-to 写的「权限模式类别不一致就挂起」对他们更容易碰到——记在这里,不改规则。
- **规则 4「拒答还会自动回落到上一代」不改**:2.1.284 的「API 自选回落目标」只对用 `ANTHROPIC_DEFAULT_OPUS_MODEL` / `modelOverrides` 钉了 Opus 的会话生效,本机钉的是 Sonnet;2.1.286 "retries once on the previous model of the same tier" 反而证明原句在本机仍成立。前提:本机 settings.json `switchModelsOnFlag: true`,这不是无条件行为。
- 其余(`attribution: false`、`CLAUDE_CODE_DISABLE_WEB_FETCH`、sandbox 项目设置不能放宽、API 重试上限合并、`claude --desktop`、`/btw`、`maxProseWidth` 等)与 kit 无关。

## 自动受益,无需改动(值得知道)

- 2.1.286 修好 `isolation: 'worktree'` 的子代理首次读文件时把项目 CLAUDE.md 再加载一遍——直通流程用 worktree 隔离的实现 agent 每个少吃一份 CLAUDE.md。
- 2.1.286 Workflow 子代理连接中断几分钟后不再从原 prompt 重跑;2.1.288 子代理与非交互会话在中途超时后从部分响应继续——都减少重复烧 token。
- 2.1.285 脚本里稍后才 await(或不 await)的失败 `agent()` / `parallel()` / `pipeline()` 不再当成未处理的 promise rejection 结束整个后台会话——能解释早期评审链中途断掉的情况。
- 2.1.283 "Fixed dynamic workflows started during a model fallback running every agent on the fallback model instead of retrying the configured model"——**对照实验里早于 2.1.283 的批次,「实现模型」行可能整批偏到回落模型**,实验记录里应注一句;2.1.285 `/cost` 与 SDK modelUsage 在拒答回落后不再记错模型。
- 2.1.288 PreToolUse hook 匹配失败或输入无法序列化时改为阻止调用;commit-gate.sh 遇坏 JSON 时 exit 0 放行,两层语义一致,不用改。

## 顺带发现(未入候选,记一句)

- 官方 workflows 文档:Workflow 子代理的提示缓存默认只保 5 分钟(主对话是 1 小时);`subagentPromptCacheTtl: 1h` 可改成 1 小时,但 1 小时缓存写入按更高价计费;同一轮 fan-out 里相同模型 / effort / agentType / tools / schema / cwd 的 agent 共享前缀缓存,`CLAUDE_CODE_WORKFLOW_PREFIX_STAGGER_MS`(默认 5000)控制等待首个 agent 建缓存的时间。对 kit 的盲审轮(2~3 个同构 opus agent)天然有利——这是保持盲审 agent 同 model / 同 effort / 同 schema 的又一个理由。
- `claude plugin details` 需要 `claude --plugin-dir <path> plugin details <name>`(全局选项放子命令前面);`claude -p` 不执行 `/doctor` 这类内置命令。

## 待 Tony 定

A 建议直接做;B / C / D / E / F / G / H 由 Tony 圈定。圈定后按直通流程走 brainstorming → spec → ultracode(A、B、H 可合并成一个小批次;C 单独出 spec;D / E / F 先做一次性实测再定)。
