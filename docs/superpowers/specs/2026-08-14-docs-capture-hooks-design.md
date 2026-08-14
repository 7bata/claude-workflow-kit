# docs-capture:决策/文档采集三层 hook 设计(2026-08-14)

## 1. 背景与目标覆盖声明

stella 符合度审计发现方法论 docs 全靠 Claude 自觉更新;本仓审计报告
`docs/superpowers/research/2026-08-14-docs-auto-update-audit.md` 确认:**写入侧零自动化**,
且 stella portfolio 每 10 分钟轮询 PLAN/Progress——失真会自动扩散成对外错误。

**本次覆盖目标台账条目**(docs/REQUIREMENTS.md):
- ✅ DECISIONS 自动采集(Tony 经 stella 转达的主任务)
- ✅ docs 审计后补齐之「漏更提醒门禁」+「REQUIREMENTS 台账捕获」(Tony 2026-08-14 选项拍板)
- ✅ 「huake/stellark/github/本机四个版本全部更新」(Tony 开场指示)
- ❌ 不覆盖:两套文档契约收敛(kit 八件套 vs stellark starter 六件套)——已登台账,单独批次;
  方案 3 转录后处理(kpi-measure JSONL 解析器路线)——二期,见 §7。

## 2. Prior art(github-research 结论)

- 内部:`kpi-measure-claude-session-jsonl-parser`(二期地基)、send-to 注册 hook(失败静默范式)、
  auto-scaffold hook(默认开 + 标志文件关 + 评测隔离 env var 范式)、dev-toolkit 凭据拦截 hook
  (PreToolUse 范式)。`stella-roadmap-llm-deriver` 与 stella portfolio 是 DECISIONS/PLAN/Progress
  的下游消费方——失真代价的实证。
- 外部:adr-tools(5.6k⭐,停更)/ log4brains(1.5k⭐)管存储展示不管采集;everything-claude-code
  与 madappgang 的 ADR skill 靠模型自觉识别拍板时刻——正是本次要治的病,不采用;Claude Code
  官方 hooks 文档证实 PostToolUse 可拿到工具输入与响应。结论:自研,借鉴 ADR skill 的
  What/Why/Changes 结构与 hook 生态的负载解析手法。

## 3. 三层机制行为规范(即验收条款)

分工原则:**捕获交给机器(忘不掉),鉴别与措辞留给模型(有判断)**。

### 层 1 确定性捕获 — `capture-decisions.sh`(PostToolUse,matcher: AskUserQuestion)

- 每次 AskUserQuestion 完成即触发;从 stdin JSON 抽「日期时间、各问题、候选项标签、
  用户选择、Other/备注原文、session_id 前 8 位」,追加到项目 `docs/DECISIONS.inbox.md`。
- 条目格式:
  ```
  ## <YYYY-MM-DD HH:MM> <sid8>
  **Q**: <question>
  **候选**: <label1> | <label2> | ...
  **选择**: <selected>
  **备注**: <Other/notes 原文;无则省略此行>
  ```
- 仅在方法论项目动作:cwd 位于 git 仓内且 `docs/` 目录存在;否则静默 exit 0。
- 防崩条款:负载解析失败时把原始 JSON 放进 fenced code block 追加到 inbox(数据不丢),
  仍 exit 0;任何错误都不得影响会话(仿 send-to register.sh)。
- inbox **入 git**(拍板原始材料随仓库走;Tony 拍板)。

### 层 2 信号提醒 — `signal-reminder.sh`(UserPromptSubmit)

- 用户消息命中词表 → stdout 注入一行(进入 Claude 上下文):
  「上一条用户消息疑似含 <决策|需求> 信号,按当轮落账规则处理(DECISIONS.inbox 现有 N 条待消化)」。
- 词表外置数据文件:`signals-decision.txt`、`signals-requirement.txt`(每行一个
  grep -E 模式);初版保守取词(决策:就这么定|拍板|就用|改成|方案[A-D一二三]…;
  需求:希望|要能|最好是|得做|别忘…),**宁漏勿错**——漏网由层 3 兜底,误报直接打扰用户。
- 不写文件、不拦截。开关:`~/.claude/.docs-capture-off` 存在即三个 hook 全部静默
  (单标志管全套);评测隔离:env `DOCS_CAPTURE_EVALS_HERMETIC` 非空即静默(仿 auto-scaffold 双开关)。
- 非方法论项目(同层 1 判定)不注入。
- **判定算法(2026-08-14 第三轮修订,依评审处方)**:整条消息先按子句切分
  (。!?;、换行、逗号及英文 .!?;),命中/压制判定**逐子句**执行——某子句命中信号词后,
  仅当**同一子句**含疑问/未定语气(吗、要不要、还没定…)才压制,其他子句的语气词不跨句影响。
  高频裸词根(拍板 / 就按这个X / 必须支持 / 需要新增 / 希望能加 / 一锤定音 / 选定方案 等)
  一律加**宾语枚举或收尾语气锚定**,排除名词性续接(「拍板这个词」「选定方案的评审会」类)。
- **判例所有权分离(硬纪律)**:冒烟测试的正例/陷阱集与词表实现由不同 agent 拥有,
  词表实现者不得增删改判例——防拟合。陷阱集必须含「不含任何压制词」的独立子类(≥20 句);
  正例集必须含多子句真实消息(拍板主句+附带疑问子句)≥8 条。

### 层 3 commit 门禁 — `commit-gate.sh`(PreToolUse,matcher: Bash 且命令含 `git commit`)

- 两项检查(初版范围,后续行做成数据文件渐进补):
  1. `docs/DECISIONS.inbox.md` 存在未消化条目(有 `## ` 级条目)→ 提醒「N 条草稿待消化:
     决策提炼成 What/Why/Changes 进 DECISIONS.md,需求进 REQUIREMENTS 目标台账,噪音删除」;
  2. staged 含源码类文件(非 docs/、非纯配置)但不含 `docs/Progress.md` → 提醒补变更日志。
- **警一次放行语义**:对当前 staged 内容取哈希(如 `git diff --staged | shasum`),
  与状态文件(`.git/docs-capture-warned`,不入版本库)比对——首见即提醒并阻止本次
  commit(输出说明:确认无需补则原样重跑即放行),哈希相同的下一次直接放行。
  验收标准按行为写:同一 staged 内容第一次提示、第二次放行;staged 变了重新计。
- 提示文案用中性工程语言,不出现催促/指责语气,一行说清缺什么、怎么算过。

### 通用

- 三脚本 POSIX sh + jq;jq 缺失时静默退化(exit 0),不装依赖不报错。
- hook 事件名、负载字段以 Claude Code 官方 hooks 文档为准,实现时核对,不凭记忆。

## 4. 文件布局与四面分发

kit workflow 插件为 canonical 源,版本 0.7.0 → 0.8.0(2026-08-14 实测 plugin.json 现值 0.7.0):

```
plugins/workflow/hooks/
  hooks.json            # 增 PostToolUse / UserPromptSubmit / PreToolUse 三段,保留既有 SessionStart 段
  capture-decisions.sh
  signal-reminder.sh
  commit-gate.sh
  signals-decision.txt
  signals-requirement.txt
  docs-capture-smoke-test.sh
```

| 面 | 落法 | 红线 |
|---|---|---|
| github kit | 上述目录 + `workflow-en` 英文文案同步;`workflow-codex` **不移植**(无 hooks 机制,README 注明,维持纪律条款——send-to 先例);双语 README 加节 + 目录树 | 英文 README 漏更曾被打回,列验收 |
| stellark dev-toolkit | 三脚本 + 词表并入 `plugins/dev-toolkit/hooks/`,hooks.json **JSON 合并** | 该文件已有 PreToolUse 凭据拦截段与 SessionStart 三注入,**只增不改不覆盖**;wip 分支 + Tony 门禁 |
| huake claude-toolkit-engineer | 同上并入其 hooks.json;README 能力节 + plugin.json description 更新,版本 bump | speak-human 与 auto-scaffold 并列段保持;skill 计数表不动(hook 非 skill) |
| 本机 | 脚本落 `~/.claude/hooks/`(稳定路径,不指 kit checkout),labs `settings.json` 注册(三 profile 软链共享,改一份全生效) | settings.json 已有 stella-reporter/speak-human/cc-session-register 段,只增不改;只动 hooks 段,不碰 permissions |

## 5. 测试与验收

- `docs-capture-smoke-test.sh`(仿 send-to 10 例):录制/构造 hook JSON 负载喂三脚本,断言
  ①inbox 追加格式正确 ②Other 文本被完整保留 ③非方法论目录零输出 ④解析失败走原始 JSON 兜底
  ⑤词表命中注入、未命中零输出 ⑥关闭标志/评测 env 下三脚本全静默 ⑦门禁首警二放
  ⑧staged 变化后重新警 ⑨inbox 空时门禁检查 1 不响 ⑩jq 缺失静默退化。
- 词表正负判例:≥10 决策句/需求句须命中,≥10 日常句(含"方案讨论"类非拍板句)不得命中;
  **非对称门禁:误触发一票即不达线**(auto-scaffold evals 纪律)。
- 每单元实现完由 opus 评审亲读文件核对,测试弱(只测 happy path / 未覆盖上述验收条款)视同打回。

## 6. 规则联动改动(kit 内)

- `CLAUDE.md.tmpl` §2 文档同步规则表加一行:「DECISIONS.inbox 有草稿 → commit 前消化分流」。
- `DECISIONS.md.tmpl` 头部「自动维护…」改为如实描述:问答框拍板由 hook 自动进 inbox,
  commit 门禁催消化,Claude 提炼成正式条目。
- kit 自身收尾:PLAN.md Spec 索引追行、Progress.md 变更日志、REQUIREMENTS 台账销账。

## 7. 明确不做(Out of scope)

- 两套文档契约收敛、starter 治理(台账在案,单独批次,涉及龙哥共同维护面)。
- 转录后处理二期:会话 JSONL 离线挖决策(kpi-measure 解析器地基),设计约束:按项目路由、
  与 inbox 去重、产出仍走 inbox 消化闸口——留待台账立项。
- ARCHITECTURE/DEPLOYMENT/BUSINESS/MEETINGS 的专属自动化(本次仅靠门禁检查 2 的渐进数据文件预留)。

## 8. 实现单元与派工红线

| 单元 | 内容 | model/effort | 评审 |
|---|---|---|---|
| U1 | kit 三脚本 + 词表 + hooks.json + 冒烟测试(TDD:先写测试) | sonnet/medium | opus/medium |
| U2 | workflow-en 英文同步 | sonnet/low | opus/medium |
| U3 | kit 规则联动 + 双语 README + 版本 bump | sonnet/low | opus/medium |
| U4 | stellark dev-toolkit 并入 | sonnet/medium | **opus/high**(凭据拦截段共存文件) |
| U5 | huake claude-toolkit-engineer 并入 | sonnet/medium | opus/medium |
| U6 | 本机 ~/.claude/hooks + settings.json 注册 | sonnet/medium | **opus/high**(在用 harness 配置) |

派工 prompt 一律附:本 spec 相关节 + FORBIDDEN FILES(各单元只改各自面的文件;U4/U5 对
hooks.json 只增段;U6 只动 settings.json 的 hooks 段)+ 绝不 force push、绝不重启共享服务、
绝不读写生产数据。U1 先行,U2~U6 待 U1 评审通过后并行。
