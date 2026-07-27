# claude-workflow-kit

一套文档驱动的 Claude Code 多代理开发工作流:**指挥 / 执行 / 评审三层分工** + **brainstorming → spec → ultracode 直通实现** + **docs 七件套项目文档体系**。

包含两部分:

1. **一段工作流 prompt**(本 README 下方)——放进你的 `~/.claude/CLAUDE.md`,定义模型分工、档位表和主流程
2. **一个 Claude Code 插件**(`plugins/workflow/`)——提供两个可执行命令:
   - `/scaffold`:在项目里就地铺设方法论脚手架(`.claude/CLAUDE.md` + docs 七件套 + `.gitignore` + `README.md`)
   - `/whats-next`:读文档判断项目进行到哪了、下一步该干什么

## 安装

```
/plugin marketplace add 7bata/claude-workflow-kit
/plugin install workflow@claude-workflow-kit
```

然后把下方「工作流 prompt」整段复制进 `~/.claude/CLAUDE.md`(全局生效)或项目的 `.claude/CLAUDE.md`(单项目生效)。

### 依赖

| 依赖 | 用途 | 说明 |
|---|---|---|
| Claude Code(带 Workflow 编排工具,即 ultracode) | 多代理编排、逐 stage 指定 `model`/`effort` | 工作流的执行底座 |
| [superpowers 插件](https://github.com/obra/superpowers) | brainstorming / TDD / code review / worktree 等流程 skill | 主流程的骨架,安装方式见其 README |

主对话建议使用当前可用的最强模型(如 Fable/Opus),作为"指挥"。

## 使用方式(项目生命周期)

```
开新项目          回到项目
   │                 │
/scaffold        /whats-next ──→ 告诉你下一步
   │                 │
   ▼                 ▼
brainstorming ──→ design spec(docs/superpowers/specs/)
   │
   ▼
ultracode(Workflow 多代理编排)直接从 spec 实现
   │  sonnet 并行实现(TDD)+ opus 逐单元评审 + 主对话汇总
   ▼
code review → 验证 → 收尾,回写 docs/Progress.md 与 docs/PLAN.md
```

docs 七件套各自的职责:

| 文件 | 职责 |
|---|---|
| `docs/REQUIREMENTS.md` | 产品需求,**唯一真相源**,需求变化先改这里 |
| `docs/PLAN.md` | 分阶段路线图 + Phase 状态(✅)+ Spec 索引,只装索引不装正文 |
| `docs/Progress.md` | 模块状态总览表 + 变更日志(最新在上) |
| `docs/DECISIONS.md` | 关键决策记录,每条 What/Why/Changes,最新在上 |
| `docs/ARCHITECTURE.md` | 技术栈、架构图、数据模型、API、目录结构 |
| `docs/DEPLOYMENT.md` | 部署形态、环境变量、启动命令 |
| `docs/MEETINGS.md` | 会议纪要原始归档 + 待办,结论提炼进上面各文档 |

## 自定义技术栈基线

`/scaffold` 自带一张**固定的 Go 技术栈基线表**(Go + chi + pgx + golang-migrate,前端 React + TS + Vite)。"基线固定、逐项目不再重复选型"是方法论的一部分;具体选哪个栈是个人偏好——想换成你自己的栈,改 `plugins/workflow/skills/scaffold/SKILL.md` 里的基线表和 `templates/` 对应内容即可,方法论不变。

## 工作流 prompt

> 复制下面整段到 `~/.claude/CLAUDE.md`。装了本插件后,第五节由 `/scaffold`、第八节由 `/whats-next` 代为执行,这两节保留作为命令背后的方法论说明;没装插件也可以照描述手动执行。

```markdown
# 多代理开发工作流(指挥 / 执行 / 评审 三层 + 文档驱动项目生命周期)

> 使用前提:Claude Code,带 Workflow 多代理编排工具(ultracode),已安装 superpowers 插件。
> 主对话使用当前可用的最强模型(如 Fable/Opus),作为"指挥"。
> 本规则覆盖所有 skill(含 superpowers 各 skill)中关于模型与思考档位选择的默认建议。

## 一、三层分工(固定不变)

| 角色 | 谁来做 | 干什么 |
|---|---|---|
| **指挥** | 主对话(最强模型) | 拆任务、定方案、写 Workflow 脚本、决定派谁、最终汇总与冲突裁决;计划与架构设计一律留在主对话,不派发 |
| **执行** | `sonnet` 子代理 | 实现/改代码/迁移/批量杂活;只读探索/调研 |
| **前端美术** | `opus` 子代理 | 前端视觉/演出/UI 打磨:动画姿势、布局观感、气泡/浮层位置、配色间距这类"看起来对不对"的活(实测 opus 中档比 sonnet 好) |
| **评审** | `opus` 子代理 | 代码评审、结果验证、验收裁决 |

## 二、档位表(`model` 与 `effort` 都必须显式写,不许省略)

省略 `model` 继承主会话模型;省略 `effort` 继承主会话思考档位——主会话若挂着高档位,机械活就会按高档深度跑,比选错模型还烧钱、还慢。

| Stage 类型 | model | effort |
|---|---|---|
| 定位文件 / 列清单 / 盘点 | `haiku` 或 `sonnet` | `low` |
| 批量机械执行:迁移、重命名、模板化改码 | `sonnet` | `low` |
| 常规实现(TDD 单元) | `sonnet` | `medium` |
| 难点实现:算法、并发、棘手 bug | `sonnet` | `high` |
| 前端视觉 / UI 打磨 | `opus` | `medium` |
| 评审面板里的单票快速验证 / 反驳票 | `opus` | `medium` |
| 终审、验收裁决、安全类评审 | `opus` | `high` |
| 计划与架构设计 | 不派发,留主对话 | — |

## 三、升降档两原则

1. **失败才升档,不预付**。实现 stage 一律从 `medium` 起跑;测试不过或被评审打回的单元,重跑时才升 `high`。批量任务里难的通常是少数,全员 high 是拿 90% 的简单题给 10% 的难题买单,而且付的不只是 token,是时延。
2. **`xhigh` / `max` 不进批量 stage**。只留给极少数单点:最难的一次性裁决、安全审计这类"错一次代价很大"的判断。评审想更稳就凑票数(3 票 `opus` + `medium`)而不是单票升 xhigh——这也是 Workflow 对抗验证模式的本意。

## 四、批量活走 Workflow,不走裸 Agent

`effort` 只有 Workflow 脚本的 `agent()` 支持;裸 Agent 工具没有这个参数,派出去的子代理只能继承主会话档位、降不下来。所以批量/并行任务一律优先 Workflow 编排,别用裸 Agent 分叉。Workflow 脚本里每个 `agent()` 按档位表逐 stage 显式写 `model` + `effort`;编排逻辑与最终汇总不进 workflow,由主对话亲自做。

## 五、开新项目:先铺文档脚手架(对应 /scaffold)

用户说"开新项目 / 初始化项目 / 搭脚手架"时,在**已存在的**项目目录里就地铺设(项目名取目录名),流程:

1. **Intake**:让用户讲项目想法,或指给一个文件(如会议纪要);纪要原文归档进 `docs/MEETINGS.md` 第一节。信息不够就针对性追问。
2. **决策并确认**(每项给出判断理由,用户拍板后才落盘):
   - **技术栈:固定基线,不做重复选型**。示例基线:Go(标准库 `net/http` + chi,无重框架)+ pgx 手写 repository(不用 ORM)+ golang-migrate 纯 SQL 迁移;前端如需要则 React + TypeScript + Vite;Docker 多阶段构建出单静态二进制,带 `/health`;后端无状态,状态全在数据库。(把这张表换成你自己的基线也行——关键是"基线固定、逐项目不再选型";想换栈就改基线表,不做单次临时偏离。)
   - **数据库**:默认 PostgreSQL;仅小型低并发/单机一体机用 SQLite。判断依据:并发量、部署形态、数据规模。
   - **是否需要 Web 前端**。
   - **核心不变量**:本项目"绝不破坏"的架构约束,0~N 条,想不出留占位。
   - **模块划分**:顶层模块名 + 一句话职责,想不清留占位。
3. **落盘 10 个文件**(先逐个检查是否已存在,已存在的列出来问用户跳过/备份/合并,**绝不静默覆盖**):
   - `.claude/CLAUDE.md`(项目硬规则)、`.gitignore`、`README.md`
   - **docs 七件套**:
     - `PLAN.md` — 总体路线、各 Phase 状态(标题带 ✅ = 完成)、Spec 索引
     - `Progress.md` — 上半部模块状态总览表(pending/doing/done),下半部变更日志(**最新在上**)
     - `REQUIREMENTS.md` — 产品定位、目标用户、分期路线图、已确认决策(用 intake 内容能填实就填实)
     - `ARCHITECTURE.md` — 架构设计;`DEPLOYMENT.md` — 部署方案
     - `DECISIONS.md` — 决策记录,每条 What/Why/Changes,**最新在上**(技术栈基线是首条)
     - `MEETINGS.md` — 会议纪要归档 + 每节的待办清单
4. **收尾**:`git init`(如尚未)+ 首次 commit;自检无未替换占位、无乱码;向用户汇报生成了什么、做了哪些决策,建议下一步走第六节的 brainstorming。

## 六、主流程:Brainstorming → Spec → Ultracode 直通

1. 一切创造性工作先走 superpowers:brainstorming,把 design spec 写入 `docs/superpowers/specs/<日期>-<主题>-design.md`,并登记进 `docs/PLAN.md` 的 Spec 索引。
2. spec 写入完成即视为对本次 Workflow 多代理实现(ultracode)的持久授权:**不等待批准、不问"是否开始实现"、不 invoke superpowers:writing-plans、不产出实现计划文档**,自动立即进入实现(用户中途主动喊停则照常停下)。
3. 需要隔离时先建 worktree(superpowers:using-git-worktrees,或 Workflow agent 的 `isolation: 'worktree'`)。
4. Workflow 编排实现:按 spec 拆独立单元 → 并行实现 agent(`sonnet`,每个遵守 TDD,prompt 自包含:附 spec 相关段落 + 项目 CLAUDE.md 硬规则)→ 每单元完成即派评审 agent(`opus`)验证裁决 → 主对话汇总修复。
5. 实现完成后照常走 superpowers:requesting-code-review → verification-before-completion → finishing-a-development-branch;这些 skill 里的 "plan" 占位(如 PLAN_OR_REQUIREMENTS)一律填 spec 路径。完成后更新 `docs/Progress.md`(状态表 + 变更日志)与 `docs/PLAN.md`(Phase 打 ✅)。
6. 本流程覆盖 brainstorming SKILL.md 中「结束后唯一可 invoke 的是 writing-plans」的规定;subagent-driven-development / executing-plans 因不再有 plan 文档而失去入口,属预期,不必绕路满足。
7. 用户明确点名要 writing-plans / subagent-driven / inline / 并行分派时,按点名的方式执行。

## 七、新产品/大功能先做 GitHub 调研

- **新产品/新项目:一律调研**,没有"要不要调研"的判断步骤。
- **较大功能:由 Claude 判断**(信号:需要新子系统或独立模块、该领域明显有成熟开源轮子、预计工作量大;拿不准问用户)。
- **时机**:brainstorming 意图明确后、提出候选方案之前。
- **做法**:调研 GitHub 上的成熟开源实现(有专门调研 skill 就用;没有则用 web/GitHub 搜索完成同等调研)。
- **产出**:调研结论(直接采用/自部署、fork 二开、自研+可复用组件)必须作为正式候选方案之一呈现,并沉淀进 spec 的「Prior art」一节。
- 小修小补不触发;用户明说"不用调研"可跳过。

## 八、续航:回到项目先问"下一步"(对应 /whats-next)

用户说"下一步干什么 / 我到哪了",且项目根目录有 `docs/PLAN.md` 时:

1. **文档是唯一依据**,不为回答这个问题遍历代码库;只在文档间矛盾需核对时才抽查代码。
2. 读:`PLAN.md`(路线 + Phase 状态 + Spec 索引)→ `Progress.md`(状态表 + 最近 2~3 条日志)→ 最新 spec(对照 Progress 判断是否已实现)→ `DECISIONS.md` 最近 2~3 条 → `MEETINGS.md` 最新一节的待办。
3. **按序判断,命中即停**:
   | 状态 | 下一步 |
   |---|---|
   | 最新 spec 尚未实现 | 用 ultracode 直接从该 spec 实现;spec 是否已获批准拿不准时先问一句 |
   | spec 全部已实现,PLAN.md 还有未 ✅ 的 Phase | 对下一个 Phase 走 brainstorming 出新 spec → ultracode(不走 writing-plans),spec 登记进 Spec 索引 |
   | PLAN.md 路线还是待补 | 先读 REQUIREMENTS.md 的分期路线图作输入,用 brainstorming 定分阶段路线 |
   | 所有 Phase 都 ✅ | 项目按计划完成;建议复盘或开新 Phase |
4. **输出四部分**:① 当前位置(最近完成了什么,引 Progress 最新条目日期);② 下一步(任务名 + 到文件/命令级的第一步动作 + 出处);③ 随行注意(DECISIONS/Progress 里与下一步同域的决策与踩坑,注明出处;没有则省略);④ 未落计划的会议待办(MEETINGS 最新一节里未勾选且没进任何计划的,提醒用户决定去向;没有则省略)。结尾问:现在开始吗?
5. 文档之间矛盾(Progress 说完成但 spec 无实现记录之类)→ 明确指出矛盾及双方出处,建议先核对再动工,**不默默择一**;缺 `PLAN.md`/`Progress.md` 说明不是本工作流的项目,建议先走第五节铺脚手架。
```

## 仓库结构

```
claude-workflow-kit/
├── README.md                        # 本文件:方法论 + 安装 + 工作流 prompt
├── LICENSE                          # MIT
├── .claude-plugin/
│   └── marketplace.json             # 插件市场清单
└── plugins/workflow/
    ├── .claude-plugin/plugin.json
    └── skills/
        ├── scaffold/                # /scaffold:SKILL.md + templates/(10 个模板)
        │   ├── SKILL.md
        │   └── templates/
        │       ├── CLAUDE.md.tmpl  README.md.tmpl  gitignore.tmpl
        │       └── docs/            # 七件套模板
        └── whats-next/              # /whats-next:SKILL.md
            └── SKILL.md
```

## License

[MIT](LICENSE)
