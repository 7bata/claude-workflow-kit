# Spec:发版前检查 + mechanical 固定 low 档 + 档位句补充(Claude Code 2.1.288 对照批次 A / B / H)

日期:2026-10-02
状态:Tony 2026-10-02 圈定「按推荐做」,取证已完成,可直接进入 ultracode
Claude Code 基线:2.1.288
分类:bounded(对已有规则文本与一个已有子代理定义的小改动);按直通流程仍写 spec

## 1. 背景与依据

- 调研稿:`docs/superpowers/research/2026-10-02-cc-288-feature-review.md`(2.1.280→2.1.288 对照,5 主题映射 + 两票盲审)。Tony 圈定 A、B、H 合成一个批次,F 的冒烟并入 B。
- A 的依据:2.1.281 "Added MCP server checks to `claude plugin validate`…" 与同版 "added a `claude plugin validate` warning when a shell-form hook leaves `${CLAUDE_PLUGIN_ROOT}` unquoted";`claude plugin details <name>`:"Show a plugin's component inventory and projected token cost"。本仓 8 个 Claude 插件与仓库根 marketplace 现在 `--strict` 全部通过,但没有任何文档把它写成发版步骤。
- B 的依据:2.1.78 "Added `effort`, `maxTurns`, and `disallowedTools` frontmatter support for plugin-shipped agents";2.1.267 修复该字段在档位被钉住的模型上被忽略;官方 sub-agents 文档 effort 字段写 "Overrides the session effort level"。现有规则句「裸 Agent 工具没有这个参数,派出去的子代理只能继承主会话档位、降不下来」对自带 `effort:` 的子代理类型不成立。
- H 的依据:2.1.251 起 `/effort` 按模型保存;2.1.280 "…no longer apply to newly released models such as Opus 5.5; they start at their default until you pick a level";2.1.284 "Changed Ultracode into its own toggle in `/effort` …: it no longer forces xhigh effort and stays on at any effort level"。本机 settings.json 顶层 `effortLevel: xhigh`、`modelSettings` 里 claude-fable-5-1 为 xhigh,所以「常年挂着 xhigh」对主会话仍成立,结论不变,只补事实。

## 2. 目标覆盖声明

- **覆盖**:目标清单 2026-10-02 行(「最近claude code新版本出了什么新功能…」)里 Tony 圈定的 A(发版清单加 validate 与 details)、B(mechanical 加 `effort: low`,规则句补例外)、H(档位句补半句);F(omitClaudeMd 按需加载)的冒烟结论写进 mechanical 的说明。
- **不覆盖**:
  - C(盲审轮做成命名 workflow)、D(/verify)、G(sonnet 别名复查):Tony 定为先放着。
  - E(`/doctor prompt-audit`):由 Tony 在会话里手动跑,主对话甄别结果,不进本批。
  - 「ultracode 开着时裸 Agent 的 20 并发上限不强制」这句:调研稿列在 H 的相关事实里,Tony 圈定的 H 只是档位句,不扩大范围。
  - huake 两个 engineer 插件:没有 mechanical 子代理、没有全文版规则句;其模板里的压缩句「`effort` 只有 Workflow 的 `agent()` 支持,裸 Agent 工具没这个参数」字面仍然成立,不改。
  - workflow-codex:没有子代理定义与 Workflow 工具,不涉及。
  - dev-toolkit 核心 `skills/stellark-workflow/SKILL.md`:§四已写「插件 `agents/*.md` frontmatter(`model`/`effort`/…)…裸 Agent 按 `subagent_type` 调用即生效」,且有 token 上限(只许不增加),不改。
  - dev-toolkit 已安装副本上的真机冒烟:要等该仓 CI 自动升版并在本机更新插件后才能做,本批只验 kit 的 mechanical。
  - `docs/PLAN.md`「最新发布」那句的陈旧内容:只更新「插件版本」一行,其余不动。
  - 第 1 轮评审记为遗留、本批不改的说法(都偏保守,照着做不会出错):两份 mechanical.md 的 description 与正文、三处脚手架模板里「不自动加载 CLAUDE.md」的说法、全局 CLAUDE.md 档位表规则 3 与 dev-toolkit WORKFLOW.md 里「它不加载 CLAUDE.md」的说法——没有补「子目录规则仍按需加载」;dev-toolkit 核心 SKILL.md 第二节没有补 effort 与档位句(token 上限)。
  - dev-toolkit `hooks/hooks.json` 里两处 `${CLAUDE_PLUGIN_ROOT}` 没加引号(`claude plugin validate` 给出警告,`--strict` 下不通过):第 1 轮评审发现,属于该仓自己的问题,登记为新待办,不在本批改。
  - 全局 CLAUDE.md 第 29 行说 mechanical 是「kit 的 workflow / workflow-en 插件里」的类型,而本机实际启用的是 dev-toolkit 的同名类型:这是本批之前就有的说法,不在圈定范围内,收尾汇报里点明。

## 3. 取证结论(2026-10-02,真机,证据 `docs/reviews/2026-10-02-cc288-smoke-evidence.md`)

临时项目 + 临时插件(三个探针子代理)+ InstructionsLoaded hook 记录载荷,主会话 `--model sonnet --effort high`,嵌套会话串行跑七组。

- **Q1 通过**:frontmatter 写了 `effort: low` 的子代理,hook 载荷 `"effort": {"level": "low"}`;没写的对照组 `{"level": "high"}`(与主会话一致)。原始日志计数:写了 low 的 6 次全是 low,没写的 1 次是 high。
- **Q2**:带 `omitClaudeMd: true` 的子代理看不到根目录 CLAUDE.md 的规则标记(开局不加载,符合预期);但 Read 子目录文件时,该子目录的 CLAUDE.md 被按需加载(`nested_traversal`);Write 新文件时,匹配的 `.claude/rules` 路径规则(`path_glob_match`)与子目录 CLAUDE.md 也被按需加载。Edit 必须先 Read,无法单独归因。结论:`omitClaudeMd` 只屏蔽开局加载,不屏蔽按需加载。
- 取证只覆盖插件自带的子代理类型(插件 `agents/*.md`);`.claude/agents/` 下的用户级 / 项目级定义没有测,规范文本只写测过的范围。
- Workflow `agent()` 的 `opts.effort` 与 frontmatter `effort` 谁优先没有测,官方文档也没写。规则继续要求 Workflow 里显式写 `effort: 'low'`(与 frontmatter 同值),谁优先都不影响结果。

## 4. 规范文本(逐字落实;标点沿用所在文件原有风格;规范文本之外的句子不动)

### 4.1 A — 发版前检查

**README.zh-CN.md**:在 `## License` 之前新增一节:

````markdown
## 维护者:发版前检查

改了任何插件(清单、hook、skill、子代理定义)之后、发版之前,在仓库根目录跑两步,都是只读命令:

1. **校验**——`--strict` 把警告也当失败;末行出现 `ALL PASSED (N plugins)`、且 N 等于插件个数才算过:

   ```bash
   fail=0; n=0
   for p in plugins/*/; do
     [ -d "$p.claude-plugin" ] || continue
     n=$((n+1))
     claude plugin validate "$p" --strict || fail=1
   done
   claude plugin validate . --strict || fail=1
   [ "$fail" = 0 ] && [ "$n" -gt 0 ] && echo "ALL PASSED ($n plugins)" || echo "FAILED"
   ```

2. **常驻 token 成本**——逐个插件看「每个会话固定多占多少 token」,把数字记进 `docs/Progress.md` 当次变更日志。`--plugin-dir` 是全局选项,必须写在 `plugin` 子命令前面:

   ```bash
   for p in plugins/*/; do
     [ -d "$p.claude-plugin" ] || continue
     n=$(basename "$p")
     printf '%s: ' "$n"; claude --plugin-dir "$p" plugin details "$n" 2>&1 | grep "Always-on" || echo "NO Always-on LINE - check this plugin"
   done
   ```

需要 Claude Code 2.1.281 及以上(校验里的 MCP 配置检查与 hook 路径引号检查是这一版加的)。`workflow-codex` 不是 Claude Code 插件(没有 `.claude-plugin` 目录),循环会自动跳过它。
````

**README.md**:在 `## License` 之前新增对应英文节,标题 `## Maintainers: pre-release checks`,两步与两段命令逐条对应(命令块与中文版逐字节相同),末段对应:"Requires Claude Code 2.1.281 or later (that release added the MCP config checks and the hook-path quoting check to validation). `workflow-codex` is not a Claude Code plugin (it has no `.claude-plugin` directory), so the loops skip it automatically."

**docs/PLAN.md**「当前状态」:
- 「插件版本」一行改成各插件清单文件里的实际版本(改完后 workflow / workflow-en 为 `0.15.0`;其余以各自 `plugin.json` 为准,逐个核对后再写)。
- 该行之后新增一条:`- 发版前检查:README「维护者:发版前检查」两步(`claude plugin validate --strict` 全过;`claude plugin details` 的常驻 token 记进 Progress 当次日志)`。

两段命令主对话已在仓库根逐字跑过(2026-10-02,2.1.288):第一段 8 个插件加仓库根全部通过、末行 `ALL PASSED (8 plugins)`;第二段 8 个插件各输出一行 `Always-on`(workflow 约 465、workflow-en 约 442、speak-human 约 181、speak-human-en 约 174、send-to 约 177、send-to-en 约 154、ui-sweep 约 159、ui-sweep-en 约 164 token)。数字不写进 README,由主对话收尾时记进 Progress。实现时若逐字执行的结果与此不符,停下并报告,不自行改写命令。

### 4.2 B — 子代理定义(三份)

`plugins/workflow/agents/mechanical.md`、`plugins/workflow-en/agents/mechanical.md`、dev-toolkit `plugins/dev-toolkit/agents/mechanical.md`:frontmatter 里在 `omitClaudeMd: true` 之后新增一行

```
effort: low
```

正文不动。kit 两个插件的 `plugin.json` 版本 `0.14.0` → `0.15.0`(description 不动)。dev-toolkit 的版本由该仓 CI 自动升,不手改。

### 4.3 B — 规则句(全文版)

**全局 `~/.claude/CLAUDE.md` 第 39 行**,整行改为:

> **按次指定 `effort` 只有 Workflow 脚本的 `agent()` 支持**;裸 Agent 工具没有这个参数,派出去的子代理默认继承主会话档位、降不下来。例外:子代理类型定义(插件 `agents/*.md`)的 frontmatter 写了 `effort:` 的,裸 Agent 按 `subagent_type` 派它时就按该档位跑——`mechanical` 已写 `effort: low`(2026-10-02 冒烟:主会话 high,写了 `effort: low` 的子代理实际 low,没写的继承 high)。所以批量机械活仍优先走 Workflow 编排,别用裸 Agent 分叉。

**README.zh-CN.md 第 227 行**:把行首到「别用裸 Agent 分叉。」为止的部分改为下文,其后的「Workflow 脚本里每个 `agent()` …」原样保留:

> 按次指定 `effort` 只有 Workflow 脚本的 `agent()` 支持;裸 Agent 工具没有这个参数,派出去的子代理默认继承主会话档位、降不下来。例外:子代理类型定义(插件 `agents/*.md`)的 frontmatter 写了 `effort:` 的,裸 Agent 按 `subagent_type` 派它时就按该档位跑——本 kit 的 `mechanical` 已写 `effort: low`。所以批量/并行任务仍一律优先 Workflow 编排,别用裸 Agent 分叉。

**README.md 第 226 行**:把行首到 "don't fork off with a bare Agent." 为止的部分改为下文,其后原样保留:

> Per-call `effort` is only supported by the Workflow script's `agent()`; the bare Agent tool has no such parameter — subagents dispatched that way inherit the main session's tier by default and can't be lowered. Exception: when an agent type's definition (a plugin `agents/*.md` file) sets `effort:` in its frontmatter, a bare Agent call that names it via `subagent_type` runs at that tier — this kit's `mechanical` sets `effort: low`. So batch/parallel tasks should still always go through Workflow orchestration first — don't fork off with a bare Agent.

**dev-toolkit `WORKFLOW.md` 第 49 行**:同 README.zh-CN.md 的改法,其中「本 kit 的 `mechanical`」写成「本仓 dev-toolkit 插件的 `mechanical`」。

### 4.4 B — 模板压缩句

**`plugins/workflow/skills/scaffold/templates/CLAUDE.md.tmpl` 第 124 行**(保持该文件的全角标点与缩进):

> `  - 按次指定 `effort` 只有 Workflow 的 `agent()` 支持，裸 Agent 工具没这个参数（子代理类型定义的 frontmatter 写了 `effort:` 的除外，如 `mechanical` 固定 `low`）→ 批量机械活优先走 Workflow 编排`

**`plugins/workflow-en/skills/scaffold/templates/CLAUDE.md.tmpl` 第 124 行**:

> `  - Per-call `effort` is only supported by Workflow's `agent()` — the bare Agent tool has no such parameter (except agent types whose definition frontmatter sets `effort:`, e.g. `mechanical` is fixed at `low`) → prefer Workflow orchestration for batch mechanical work`

### 4.5 B / F — mechanical 说明段

**全局 `~/.claude/CLAUDE.md` 第 29 行**:把「`mechanical` 是 kit 的 workflow / workflow-en 插件里带 `omitClaudeMd: true` 的子代理类型,不自动加载 CLAUDE.md,省 token(2026-09-19 入表,冒烟验证 agentType+omitClaudeMd 生效)。」改为:

> `mechanical` 是 kit 的 workflow / workflow-en 插件里带 `omitClaudeMd: true` 与 `effort: low` 的子代理类型,开局不加载 CLAUDE.md,省 token(2026-09-19 入表,冒烟验证 agentType+omitClaudeMd 生效)。`omitClaudeMd` 只管开局那次加载:它读写到的目录里有子目录 CLAUDE.md 或带 `paths:` 的 `.claude/rules` 规则时,这些文件仍会按需加载(2026-10-02 冒烟)。

该行其余部分(「只有这两类纯机械 stage 用它;…」)原样保留。

**dev-toolkit `WORKFLOW.md` 第 38 行**:同上改法,保留该行原有的「本仓 dev-toolkit 插件里」说法。

**README.zh-CN.md 第 216 行**:把「其 frontmatter 设了 `omitClaudeMd: true`,会跳过自动加载的 CLAUDE.md,省 token。」改为:

> 其 frontmatter 设了 `omitClaudeMd: true` 与 `effort: low`:开局不加载 CLAUDE.md,省 token;裸 Agent 按 `subagent_type` 派它时也按 `low` 跑。`omitClaudeMd` 只管开局那次加载——它读写到的目录里有子目录 CLAUDE.md 或带 `paths:` 的 `.claude/rules` 规则时,这些文件仍会按需加载。

**README.md 第 215 行**:把 "whose frontmatter sets `omitClaudeMd: true`, so it skips the auto-loaded CLAUDE.md and saves tokens." 改为:

> whose frontmatter sets `omitClaudeMd: true` and `effort: low`: it skips the CLAUDE.md that is auto-loaded at start, which saves tokens, and a bare Agent call that names it via `subagent_type` also runs at `low`. `omitClaudeMd` only covers that start-up load — when a directory it reads or writes in has its own nested CLAUDE.md or a `paths:`-scoped `.claude/rules` rule, those files still load on access.

### 4.6 H — 档位句

**全局 `~/.claude/CLAUDE.md` 第 16 行**:行尾追加:

> 档位按模型分别保存,新出的模型从它自己的默认档起跑;ultracode 是独立开关,Claude Code 2.1.284 起不再强制 xhigh——会话实际挂在哪一档以 `/effort` 为准,不论哪一档,Workflow 里都逐 stage 显式写。

**README.zh-CN.md 第 203 行**与 **dev-toolkit `WORKFLOW.md` 第 25 行**:行尾追加:

> 会话档位按模型分别保存(新出的模型从它自己的默认档起跑),ultracode 是独立开关、不等于 xhigh(Claude Code 2.1.284 起)——会话实际挂在哪一档以 `/effort` 为准,不论哪一档,Workflow 里都逐 stage 显式写。

**README.md 第 202 行**:行尾追加(前面留一个空格):

> The session tier is saved per model (a newly released model starts at its own default), and ultracode is a separate toggle that no longer implies xhigh (since Claude Code 2.1.284) — check `/effort` for the tier a session is actually on; whatever it is, write `effort` explicitly per stage in a Workflow.

行号是 2026-10-02 写 spec 时的位置;实现时以句子内容定位,行号对不上以内容为准。

### 4.7 第 1 轮评审后的修订(2026-10-02;评审链第 1 轮 K1~K4、L2~L4、L8)

**(a) 「同理」半句**——原句保留的「`mechanical` 类型同理」把 `model` 与 `effort` 一并说成继承会话,与新加的 frontmatter `effort: low` 矛盾。四个面改为只对 `model` 说「也一样」,`effort` 另说:

- README.zh-CN.md 第 227 行、dev-toolkit `WORKFLOW.md` 第 49 行:把「省略 `model` 继承主会话模型、不会落到 opus;`mechanical` 类型同理」改为

  > 省略 `model` 继承主会话模型、不会落到 opus,`mechanical` 类型也一样;`mechanical` 的 `effort` 在定义里已写 `low`,脚本里仍显式写 `low`,两处同值

- 全局 `~/.claude/CLAUDE.md` 第 43 行:把「省略 `model` 继承主会话的 Fable、不会落到 opus;`mechanical` 类型同理。」改为

  > 省略 `model` 继承主会话的 Fable、不会落到 opus,`mechanical` 类型也一样;`mechanical` 的 `effort` 在定义里已写 `low`,脚本里仍显式写 `low`,两处同值。

- README.md 第 202 行:把 "an omitted `model` never falls through to opus; the `mechanical` agent type behaves the same" 改为

  > an omitted `model` never falls through to opus, and the same goes for the `mechanical` agent type; `mechanical`'s `effort` is already set to `low` in its definition, and scripts still write `low` explicitly, so the two agree

**(b) README 两段命令块**——改成 4.1 现在的文本(第一段数出校验了几个插件,末行 `ALL PASSED (N plugins)`;第二段拿不到 `Always-on` 行时该行显示 `NO Always-on LINE - check this plugin`)。中文步骤 1 的说明句同 4.1;英文步骤 1 里对应「末行出现 ALL PASSED 才算过」的那半句改为 "the check passes only when the last line reads `ALL PASSED (N plugins)` and N matches the number of plugins"。中英命令块仍须逐字节相同。

**(c) dev-toolkit `README.md` 子代理表**——`dev-toolkit:mechanical` 一行「定义里固定的档位」那一格,由「`omitClaudeMd`,model/effort 由调用方(Workflow `agent()`)指定」改为

  > `omitClaudeMd` / effort low;model 由调用方(Workflow `agent()`)指定

**(d) dev-toolkit 脚手架模板** `plugins/dev-toolkit/skills/stellark-scaffold/templates/CLAUDE.md.tmpl` 里「`effort` 只有 Workflow 的 `agent()` 支持，裸 Agent 工具没这个参数 → 批量机械活优先走 Workflow 编排」那一行:改成与 4.4 中文模板相同的文本(保持该文件的全角标点与缩进)。

## 5. 单元与文件所有权

四个单元的文件互不重叠,可并行。实现 agent 一律不做 git add / commit / push,由主对话在评审后按单元提交。

| 单元 | 组 | 只许改这些文件 |
|---|---|---|
| U1 kit README 与 PLAN | S(sonnet + medium) | `README.zh-CN.md`、`README.md`、`docs/PLAN.md` |
| U2 kit 插件 | O(opus + medium) | `plugins/workflow/agents/mechanical.md`、`plugins/workflow-en/agents/mechanical.md`、两个插件的 `.claude-plugin/plugin.json`、两个 `skills/scaffold/templates/CLAUDE.md.tmpl` |
| U3 本机全局规则 | S(sonnet + medium) | `~/.claude/CLAUDE.md`(主对话已备份到 `~/.claude/CLAUDE.md.bak-20261002-cc288-abh`);第 1 轮评审后追加第 43 行 |
| U4 dev-toolkit | O(opus + medium) | worktree `~/Tony/Proj/Stellark/Platform/dev-toolkit/.worktrees/wip-cc288-abh` 里的 `plugins/dev-toolkit/agents/mechanical.md`、`WORKFLOW.md`;第 1 轮评审后追加 `README.md`(子代理表一格)与 `plugins/dev-toolkit/skills/stellark-scaffold/templates/CLAUDE.md.tmpl`(一行) |

S / O 分组是档位表规则 4 的对照实验(sonnet + medium 对 opus + medium),每个单元首个提交正文记「实现模型:<实际模型 ID>」。

评审两组,各 2 个互不可见的 opus + medium 盲审:公开面(U1 + U2)、私有面(U3 + U4)。本批不触及规则 3 的高风险类别。

## 6. 要素清单(评审逐面核对)

1. A:README 中英各有一节发版前检查,两段命令中英逐字节相同;在仓库根目录逐字执行,第一段末行是 `ALL PASSED (8 plugins)`,第二段每个 Claude 插件输出一行 `Always-on`;PLAN 有对应条目且版本行与各 `plugin.json` 一致。
2. B 定义:三份 mechanical.md frontmatter 都有 `effort: low`,位置在 `omitClaudeMd: true` 之后,正文无改动;kit 两个 `plugin.json` 为 `0.15.0` 且能被 JSON 解析。
3. B 规则句:四个全文面(全局、README 中、README 英、dev-toolkit WORKFLOW.md)都是 4.3 的文本;两份模板是 4.4 的文本;全仓不再有不带例外的「只能继承主会话档位、降不下来」/ "can only inherit the main session's tier"。
4. B / F 说明段:四个面都是 4.5 的文本;「读写到的目录」「按需加载」的说法与取证结论一致(Read 与 Write 实测触发,Edit 未单独归因,文本没有声称 Edit 单独触发)。
5. H:四个面都有 4.6 的追加句;没有改动原句。
6. 公开面(U1、U2 的文件)新增内容里没有内部主机名、组名、仓名。
7. 规范文本之外没有别的改动(diff 只落在点名的行与新增节)。

## 7. 验收条款

- AC1:8 个 Claude 插件目录与仓库根 `claude plugin validate … --strict` 全部通过(改动之后)。
- AC2:README 中英的两段命令从仓库根逐字执行:第一段末行 `ALL PASSED (8 plugins)`,第二段对 8 个 Claude 插件各输出一行 `Always-on`;某个插件拿不到 `Always-on` 行时,该插件那一行显示 `NO Always-on LINE - check this plugin`。
- AC3:kit 中文版 mechanical 的真机冒烟——嵌套会话 `--plugin-dir plugins/workflow --model sonnet --effort high`,裸 Agent 派 `workflow:mechanical` 读一个子目录文件,InstructionsLoaded hook 载荷里该子代理的 effort 为 low;英文版同样验一次(`workflow-en:mechanical`)。嵌套会话串行、每个带 300 秒时限,跑完核对无残留进程。
- AC4:全局 CLAUDE.md 与备份文件的 diff 只有第 16、29、39、43 四行(第 43 行是第 1 轮评审后追加的),行数不变。
- AC5:dev-toolkit worktree 的 diff 只有 `mechanical.md` 加一行与 `WORKFLOW.md` 第 25、38、49 三行,`WORKFLOW.md` 行数不变(153);第 1 轮评审后追加 `README.md` 子代理表一格与脚手架模板一行;`claude plugin validate` 的结果不比改动前差;`claude --plugin-dir <worktree>/plugins/dev-toolkit plugin details dev-toolkit` 的 Agents 里列出 mechanical(validate 不检查 agents 目录,所以加这一步)。
- AC6:第 6 节七条要素全部成立;盲审无 P0 / P1 未闭合。
- AC7(收尾步骤,dev-toolkit 并 main 之后):等该仓 CI 自动升版 → 本机 `claude plugin marketplace update stellark-dev-toolkit` 与 `claude plugin update dev-toolkit@stellark-dev-toolkit` → 在临时项目里不带 `--plugin-dir` 起一个嵌套会话(`--effort high`),裸 Agent 派 `dev-toolkit:mechanical` 读子目录文件,hook 载荷里 effort 为 low。本机实际启用的是 dev-toolkit 插件(kit 的 workflow 插件本机没装),所以全局 CLAUDE.md 第 39 行「`mechanical` 已写 `effort: low`」要到这一步做完才对本机成立;做不完、或冒烟结果不是 low,就在同一次收尾里把全局第 39 行那半句改成带版本条件的说法(dev-toolkit 升到含 `effort: low` 的版本之后才成立),或按备份把这一行退回,并在收尾汇报里写明(裁决轮对 L1 的闭合条件)。
- AC8(只记录,不卡通过):裸 Agent 派 `workflow:mechanical` 且 `model` 指定 haiku 时是否报错、hook 载荷里 effort 是什么。档位表允许 mechanical 用 haiku,取证只测过 sonnet。

## 8. 回滚

- kit、dev-toolkit:`git revert` 对应提交。
- 全局 CLAUDE.md:`cp ~/.claude/CLAUDE.md.bak-20261002-cc288-abh ~/.claude/CLAUDE.md`。这条命令只适用于下一次有人改这个文件之前;之后要回滚就只把第 16、29、39、43 四行按备份改回去,不整文件覆盖(该文件不在 git 里,整文件覆盖会冲掉后来的改动)。
- mechanical 的 `effort: low` 若在某模型上报错或被忽略:删掉那一行即恢复原行为(继承会话档位);Workflow 里的 `opts.effort` 一直显式写着,不受影响。
