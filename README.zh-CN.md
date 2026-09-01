# claude-workflow-kit

[English](README.md) | 中文

一套文档驱动的 Claude Code 多代理开发工作流:**指挥 / 执行 / 评审三层分工** + **brainstorming → spec → ultracode 直通实现** + **docs 八件套项目文档体系**。

包含两部分:

1. **一段工作流 prompt**(本 README 下方)——放进你的 `~/.claude/CLAUDE.md`,定义模型分工、档位表和主流程
2. **一个 Claude Code 插件**(`plugins/workflow/`)——提供三个可执行命令,外加三项能力:
   - `/scaffold`:在项目里就地铺设方法论脚手架(`.claude/CLAUDE.md` + docs 八件套 + `.gitignore` + `README.md`)
   - `/whats-next`:读文档判断项目进行到哪了、下一步该干什么
   - `/sop-generate`:给已部署的 Web 应用生成带截图的中文业务 SOP(操作手册)
   - **目标台账**:对话里说过的需求当轮落进 `docs/REQUIREMENTS.md` 的收件箱节,brainstorming 开工对账、收尾销账、`/whats-next` 报未销账项——治「说过的需求做着做着就忘了」
   - **docs-capture**:三条常驻 hook 让决策日志不再靠自觉——问答框每次拍板确定性落进 `docs/DECISIONS.inbox.md`,自由文本的决策/需求措辞触发软提醒,commit 门禁催消化草稿(见下方「docs-capture」一节)
   - 外加一个常驻能力:**auto-scaffold**——新会话开局自动认出"用户要做个新东西",无声建目录 + git 仓 + 脚手架(默认开启,可 opt-out;见下方「新项目自动铺设」一节)

## 安装

```
/plugin marketplace add 7bata/claude-workflow-kit
/plugin install workflow@claude-workflow-kit
```

本仓库提供两个插件变体,**装其中一个**即可:

- `workflow@claude-workflow-kit` — 中文输出(本 README)
- `workflow-en@claude-workflow-kit` — 英文输出

两者的 skill 共用 `/scaffold`、`/whats-next` 命令名,同时安装会互相冲突——按你要的输出语言二选一。

然后把下方「工作流 prompt」整段复制进 `~/.claude/CLAUDE.md`(全局生效)或项目的 `.claude/CLAUDE.md`(单项目生效)。

### 依赖

| 依赖 | 用途 | 说明 |
|---|---|---|
| Claude Code(带 Workflow 编排工具,即 ultracode) | 多代理编排、逐 stage 指定 `model`/`effort` | 工作流的执行底座 |
| [superpowers 插件](https://github.com/obra/superpowers) | brainstorming / TDD / code review / worktree 等流程 skill | 主流程的骨架,安装方式见其 README |

主对话建议使用当前可用的最强模型(如 Fable/Opus),作为"指挥"。

## 附赠插件:speak-human

让 Claude 说人话、会提问。规则从 548 次真实 AskUserQuestion 抉择记录里挖出来(67% 照选 / 16% 吸收后自造答案 / 12% 拒绝转聊天):提问前自检清单(先用工具核实前提、交代为什么问/现状/影响、黑话逐个带解释、不硬造二选一——留组合位、一轮一个决策点、视觉决策给真预览)+ 三条表达纪律(语言跟随用户、全域黑话带解释、叙述禁文件名流水账)。

```
/plugin install speak-human@claude-workflow-kit      # 中文版
/plugin install speak-human-en@claude-workflow-kit   # 英文版(二选一,别都装)
```

- **按需**:任意会话里 `/speak-human` 手动触发。
- **常驻**:`touch ~/.claude/.speak-human-always` —— SessionStart hook 每个会话自动注入规则;删掉该文件即关闭。
- **自带评测**(`plugins/speak-human/evals/`):37 个脱敏真实失败案例(29 verified + 8 unverified) + 逐条判分标准 + 基线 vs 带 skill 对比跑分脚本(`run_evals.py`),改规则可以回归验证,不靠感觉。

## 附赠插件:send-to

`/send-to 会话名 要转达的内容` —— 把消息转达给本机另一个 Claude Code 会话,基于跨会话消息功能(Claude Code v2.1.224+,macOS/Linux;发消息本身没有内置斜杠命令,这正是本插件存在的原因)。它定死了几件事:

- **会话名模糊匹配**:自动生成的会话名多是「目录名-两位后缀」(如 `myapp-ec`),只输 "myapp" 也能对上;零命中或多个命中时把在线会话列表亮出来问你,不替你猜。
- **消息强制自包含**:对方会话没有你这边的任何上下文,转达必须带上背景、实质内容(分支、提交、路径)和期望动作,禁止"按我们刚才说的"。
- **如实汇报投递状态**:"已发送"不会被吹成"对方已收到";两个会话权限模式不一致时消息会在对方端挂起等批准,skill 会把挂起状态如实转告。
- **跨 profile 不可见但可直发,身份注册表认人**:跨会话发现按 profile 隔离(每个会话只在自己 profile 的注册表登记)——另一个 profile 开的窗口在 `ListAgents` 里互相看不见,但 `SendMessage` 带显式 `uds:` 地址可跨账号直达(2026-08-10 受控实验定谳),不再是边角料式的最后手段。为解决"看到 socket 也认不出是谁"的窘境,`send-to` 插件的 SessionStart hook 会把本会话身份(项目名、账号、profile、启动时间、启动命令行)自愿注册进共享的身份注册表,零命中时先读注册表按四级阶梯(`ListAgents` → 身份注册表直发 → 现行地址来源阶梯 → 文件交接)找目标,能唯一认出目标就直发不必绕弯。**这条 hook 要在每个 profile 都装并生效,才能注册该 profile 的会话**——少装一个 profile,那个 profile 的窗口就只能靠地址阶梯或文件交接被找到。注册默认开启,`touch ~/.claude/.cc-session-registry-off` 即全局停用(删除该文件恢复)。文件交接降级(自包含交接文件 + 一行粘贴指令,由用户亲手贴进目标窗口)退回真正的最后兜底,只在四级阶梯全部落空时触发。

```
/plugin install send-to@claude-workflow-kit      # 中文版
/plugin install send-to-en@claude-workflow-kit   # 英文版(二选一,别都装)
```

## 附赠插件:ui-sweep

SOP 截图前,或改完一批 UI 后做回归扫描,把全站可交互元素系统性点一遍——`vercel-labs/agent-browser`(Rust CLI,自带 Chrome for Testing,a11y 快照带元素引用)驱动 + 自研通用化遍历引擎:登录态注入 → 按项目 `sweep.config.mjs` 编制的屏清单逐屏跑 → 每屏恢复现场、逐元素点击观察、八分类记账(状态变化 / 无反应 / 弹窗被驳回 / 点击异常 / 页面异常 / 拦截名单 / 定位丢失 / 出域拉回)→ 产出 JSONL 台账 + 每屏截图 + 报告。

- **配置外置**:`node sweep.mjs <path>/sweep.config.mjs` 吃项目的 `ROOT`/`SCREENS`(必填)+ `DENY_EXTRA`/`ensureBaseline`/`OUT`(可选),缺必填项立即报错退出,不静默空跑。
- **安全边界**:默认拦截名单(吊销/删除/退出/logout/revoke/归档/清除/重置/发送/保存/上传等)项目只能通过 `DENY_EXTRA` 叠加、不能削减;破坏性按钮只记不点;`confirm`/`prompt` 一律驳回,不产生真实写入;出域防护双层:`--allowed-domains` 限显式导航(点击驱动的跳转拦不住,引擎已实测并接管会话生命周期),可靠层是引擎逐击域名校验——出域记 `left-domain` 并当场拉回;只用于自家或已获授权的站点。
- **`--strict` 模式**:每击必恢复现场,治"同屏状态累积掩盖后续点击变化"的假阳性;默认关(全量跑慢约一倍),初跑用默认、对 dead 清单复核用 `--strict`。
- **孤儿功能对账(可选)**:遍历只能查「有按钮点了没反应」,查不到「功能实现了但前端根本没入口」——后者要靠对账。config 里给 `INVENTORY`(后端 API + 前端路由清单,由 Claude 按项目技术栈现场生成)后,引擎在遍历中采集实际触发的请求,与清单求差集,产出 `unreachable`(疑似没入口)/ `broken-entry`(入口在但 4xx/5xx)/ `exempt`(webhook 等预期无入口)三类结论;配四类假阳性判读指南(权限/数据状态/拦截名单/覆盖不全)与真孤儿三条件。**不配 `INVENTORY` 时此功能静默关闭,行为与不开完全一致。**

```
/plugin install ui-sweep@claude-workflow-kit      # 中文版
/plugin install ui-sweep-en@claude-workflow-kit   # 英文版(二选一,别都装)
```

## 附赠插件:Codex CLI 版工作流

同一套文档驱动工作流,面向 OpenAI Codex CLI 的移植版:`plugins/workflow-codex/`(打包成 `.codex-plugin/plugin.json`,不是 Claude Code 插件——按你的 Codex CLI 版本对应的 skill/插件加载机制安装)。它以 `AGENTS.md` 取代 `.claude/CLAUDE.md`,共五个 skill:

- `scaffold`:铺设方法论脚手架(`AGENTS.md` + docs 八件套 + `.gitignore` + `README.md`)
- `whats-next`:读文档判断下一步该干什么
- `sop-generate`:给已部署的 Web 应用生成带截图的中文业务 SOP
- `parallel-do`:把一个步骤拆成独立子任务,分波 spawn 并行 Codex subagent 执行——这个 skill 是 Codex 独有的,补的是 Claude Code 原生多代理编排工具在 Codex 侧缺失的能力
- `speak-human`:让 Codex 提问与表达遵守说人话纪律——移植自下方「附赠插件:speak-human」的同一套 P1~P9/S1~S4 规则,常驻方式改为写入 `~/.codex/AGENTS.md`(见该 skill 文件末尾「常驻安装」一节的脚本)

`workflow-codex` 不含 auto-scaffold(说一句要做新东西就自动建目录铺脚手架)的随装自动生效——Codex CLI 没有会话开局 hook 机制,插件装上不会像 Claude Code 版那样自动触发。想要同款效果,需按 `scaffold` skill 文件末尾「Auto 模式与常驻安装(可选)」一节手动 opt-in:把判定规则片段写进 `~/.codex/AGENTS.md`(附幂等安装/卸载脚本,可反复跑不重复追加)。

### 安装 workflow-codex

```
git clone <本仓库地址> ~/claude-workflow-kit
codex plugin marketplace add ~/claude-workflow-kit
codex plugin add workflow-codex@claude-workflow-kit
```

市场清单已在仓库的 `.agents/plugins/marketplace.json`,`marketplace add` 指向 clone 到本地后的仓库根目录即可发现它(尚未实测 `marketplace add` 直接指向 git 地址的用法,故不在此推荐)。

### 运行模式(必读)

Codex 默认沙箱 `workspace-write` 把 `.git` 排除在可写范围外,`git init` / `git commit` 都会报 `Operation not permitted`;本工作流每个操作都要原子 commit,因此必须先给 `.git` 写权限。`read-only` 模式完全跑不了。以下两个方案均已实测通过:

1. **推荐(窗口最小,实测通过 `git init` 与 `git commit` 两种场景)**:保持 `workspace-write`,只把本项目的 `.git` 加进可写根——

   ```
   codex -s workspace-write -c 'sandbox_workspace_write.writable_roots=["/abs/path/to/项目/.git"]'
   ```

   或写进 `~/.codex/config.toml`(可放在按项目切换的 profile 里):

   ```toml
   [sandbox_workspace_write]
   writable_roots = ["/abs/path/to/项目/.git"]
   ```

   该路径在 `.git` 尚不存在时也有效(用空目录实测 `git init -b main` + 首个 commit 均退出 0),scaffold 首次铺设同样适用。

2. **一次性/容器/CI 环境**可用更粗的开关:`codex -s danger-full-access`;非交互批跑用 `codex exec --dangerously-bypass-approvals-and-sandbox`。仅在自己信任的项目目录里用。

开工前先跑一句自检,能过再开始,别等 scaffold 落到一半才发现:

```
git commit --allow-empty -m probe && git reset --hard HEAD~1
```

### Codex 版与 Claude 版的口径差异

- **spec 落哪**:Codex 侧没有 superpowers 插件,design spec 落 `docs/specs/YYYY-MM-DD-<主题>-design.md`,不用下面 Claude 版口径的 `docs/superpowers/specs/`
- **并行实现靠谁**:spec 定稿后的并行实现由 `parallel-do` 承担,不是下面的 ultracode / Workflow 多代理编排工具
- **改技术栈基线改哪**:改 `plugins/workflow-codex/skills/scaffold/SKILL.md` 与其 `templates/`,不是下面「自定义技术栈基线」指向的 `plugins/workflow/`
- **没有 docs-capture hooks**:六之二描述的决策/需求三层捕获(`AskUserQuestion` → `DECISIONS.inbox.md`、信号词提醒、commit 门禁)未移植到这里——依赖 Claude Code 的 hooks 机制,Codex CLI 没有。纪律照旧成立(决策/需求落档别蒸发),Codex 这边靠约定维持,不靠自动化。

## 使用方式(项目生命周期)

> 以下路径与编排工具为 **Claude 版口径**;Codex 版见上「Codex 版与 Claude 版的口径差异」。

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

docs 八件套各自的职责:

| 文件 | 职责 |
|---|---|
| `docs/REQUIREMENTS.md` | 产品需求,**唯一真相源**,需求变化先改这里;含「目标台账(收件箱)」节,收对话/会议里冒出的需求 |
| `docs/BUSINESS.md` | 业务档案:业务事实(系统出现之前怎么做、业务规则),业务规则变化先改这里 |
| `docs/PLAN.md` | 分阶段路线图 + Phase 状态(✅)+ Spec 索引,只装索引不装正文 |
| `docs/Progress.md` | 模块状态总览表 + 变更日志(最新在上) |
| `docs/DECISIONS.md` | 关键决策记录,每条 What/Why/Changes,最新在上 |
| `docs/ARCHITECTURE.md` | 技术栈、架构图、数据模型、API、目录结构 |
| `docs/DEPLOYMENT.md` | 部署形态、环境变量、启动命令 |
| `docs/MEETINGS.md` | 会议纪要原始归档 + 待办,结论提炼进上面各文档 |

## 自定义技术栈基线

> 以下路径为 **Claude 版口径**;Codex 版见上「Codex 版与 Claude 版的口径差异」。

`/scaffold` 自带一张**固定的 Go 技术栈基线表**(Go + chi + pgx + golang-migrate,前端 React + TS + Vite)。"基线固定、逐项目不再重复选型"是方法论的一部分;具体选哪个栈是个人偏好——想换成你自己的栈,改 `plugins/workflow/skills/scaffold/SKILL.md` 里的基线表和 `templates/` 对应内容即可,方法论不变。

## 工作流 prompt

> 复制下面整段到 `~/.claude/CLAUDE.md`。装了本插件后,第六节由 `/scaffold`、第九节由 `/whats-next` 代为执行,这两节保留作为命令背后的方法论说明;没装插件也可以照描述手动执行。

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

## 三、升降档四原则

1. **失败才升档,不预付**。实现 stage 一律从 `medium` 起跑;测试不过或被评审打回的单元,重跑时才升 `high`。批量任务里难的通常是少数,全员 high 是拿 90% 的简单题给 10% 的难题买单,而且付的不只是 token,是时延。
2. **`xhigh` / `max` 不进批量 stage**。只留给极少数单点:最难的一次性裁决、安全审计这类"错一次代价很大"的判断。评审想更稳就凑票数(3 票 `opus` + `medium`)而不是单票升 xhigh,**且各票必须用不同镜头:正确性 / 安全 / 边界与异常数据,不许三票复读同一个 prompt——同质票共享盲区,票数不等于置信度**。这也是 Workflow 对抗验证模式的本意。评审的编排分两种,按任务性质选:**平行多票**(上面的 3 票不同镜头,各票独立、互不可见)适合验收裁决与正确性确认;**链式接力**适合诊断、根因分析、排障——每轮评审的 prompt 显式附上一轮的结论与已被否决的假设,让本轮在前人基础上往深挖,而不是从零重投。平行票每票从零开始,抓不到"上一轮结论本身算错了"这类自我纠错,链式抓得到;链式的收敛标准建议用"连续两轮无新发现"。链式轮与轮是继承关系,不算凑票数。
3. **后果覆盖难度**。凡触及不可逆操作或高爆炸半径的单元——数据迁移、删除/覆写数据、鉴权与权限、支付、对外发布——无论实现档位多低,评审一律 `opus` + `high`,评审检查项必须包含"回滚路径存在且可执行"。实现档位照旧按难度走,贵的只是验证。红线同样要**前置到实现侧**:派实现 agent 时就把生产红线写进每个 prompt(见七.4),不能只靠评审兜底。
4. **经验校准有保质期**。档位表里的经验性结论(opus 前端、medium 起跑等)均视为有日期的校准,主力模型换代后失效待验:用会话用量数据复盘——medium 起跑的打回率 <5% 考虑下探 `low`,>30% 说明起跑档太低。凭数据改表,不凭手感。

## 四、批量活走 Workflow,不走裸 Agent

`effort` 只有 Workflow 脚本的 `agent()` 支持;裸 Agent 工具没有这个参数,派出去的子代理只能继承主会话档位、降不下来。所以批量/并行任务一律优先 Workflow 编排,别用裸 Agent 分叉。Workflow 脚本里每个 `agent()` 按档位表逐 stage 显式写 `model` + `effort`;编排逻辑与最终汇总不进 workflow,由主对话亲自做。

## 五、Git 分支与备份策略

1. **分支即推**:日常开发一律在 feature/wip 分支进行,开工先切/建分支(worktree 流程自动满足);每次 commit 后立即 `git push` 当前分支到远端,无需确认(无 upstream 时用 `-u` 建立)——这就是实时异地备份。
2. **main 门禁**(只拦用户在前端看得出来的改动):merge 进 main(或直接在 main 上 commit)前先判一次——这次改动用户在前端能不能看出/测出差别?**能**(前端代码改动,或后端逻辑变化会改变前端交互/展示行为)→ 必须先获用户确认。**不能**(用户没法在前端测试的:纯后端内部实现与重构、文档、后端测试、脚本、CI、依赖升级、接口行为不变的改动)→ 直接合并并 push main,无需确认,合并后向用户报告一句。两类合并后都照旧删除已合并的远端 feature 分支;拿不准就按"能"处理,先问;直接在 main 上 commit 仍先按规则 1 切分支,本条只管要不要确认。本条覆盖 finishing-a-development-branch 的 Step 4 三选项菜单——判定为"不能"时不弹菜单,直接合并并继续收尾。门禁只设在用户能亲手验证的地方,其余改动用户本来就无从核对,问了只是打断。
3. **无远端兜底**:仓库没有 remote(或分支没有 upstream)时,首次 commit 后提醒用户建远端,避免"自动 push"静默失效。

## 六、开新项目:先铺文档脚手架(对应 /scaffold)

用户说"开新项目 / 初始化项目 / 搭脚手架"时,在**已存在的**项目目录里就地铺设(项目名取目录名),流程:

1. **Intake**:让用户讲项目想法,或指给一个文件(如会议纪要);纪要原文归档进 `docs/MEETINGS.md` 第一节,其中的业务事实另提炼进 `docs/BUSINESS.md`。信息不够就针对性追问。除判断技术栈/DB 外,**按 7 格模型追问业务上下文**(用于填实 `docs/BUSINESS.md`;信息不足的格留占位、不逼问、不卡流程):① 目标与现状手工流程(没系统之前谁、怎么做、痛点在哪);② 输入:交易数据(有无真实样本文件);③ 输入:参考/配置数据(对照表、规则表、允许值);④ 加工流程(输入怎么变成输出);⑤ 输出(产出什么、给谁,有无期望样例);⑥ 业务铁律与异常(绝不能错的规则、意外情况怎么办);⑦ 人工介入与反馈(谁复核、能改什么、要不要被系统记住)。
2. **决策并确认**(每项给出判断理由,用户拍板后才落盘):
   - **技术栈:固定基线,不做重复选型**。示例基线:Go(标准库 `net/http` + chi,无重框架)+ pgx 手写 repository(不用 ORM)+ golang-migrate 纯 SQL 迁移;前端如需要则 React + TypeScript + Vite;Docker 多阶段构建出单静态二进制,带 `/health`;后端无状态,状态全在数据库。(把这张表换成你自己的基线也行——关键是"基线固定、逐项目不再选型";想换栈就改基线表,不做单次临时偏离。)
   - **数据库**:默认 PostgreSQL;仅小型低并发/单机一体机用 SQLite。判断依据:并发量、部署形态、数据规模。
   - **是否需要 Web 前端**。
   - **核心不变量**:本项目"绝不破坏"的架构约束,0~N 条,想不出留占位。
   - **模块划分**:顶层模块名 + 一句话职责,想不清留占位。
3. **落盘 11 个文件**(先逐个检查是否已存在,已存在的列出来问用户跳过/备份/合并,**绝不静默覆盖**):
   - `.claude/CLAUDE.md`(项目硬规则)、`.gitignore`、`README.md`
   - **docs 八件套**:
     - `PLAN.md` — 总体路线、各 Phase 状态(标题带 ✅ = 完成)、Spec 索引
     - `Progress.md` — 上半部模块状态总览表(pending/doing/done),下半部变更日志(**最新在上**)
     - `REQUIREMENTS.md` — 产品定位、目标用户、分期路线图、已确认决策(用 intake 内容能填实就填实)+ 目标台账(收件箱)节
     - `BUSINESS.md` — 业务档案:系统出现之前怎么做、业务规则、输入输出样本登记(用 7 格追问收集的内容填实)
     - `ARCHITECTURE.md` — 架构设计;`DEPLOYMENT.md` — 部署方案
     - `DECISIONS.md` — 决策记录,每条 What/Why/Changes,**最新在上**(技术栈基线是首条)
     - `MEETINGS.md` — 会议纪要归档 + 每节的待办清单
4. **收尾**:`git init`(如尚未)+ 首次 commit;自检无未替换占位、无乱码;向用户汇报生成了什么、做了哪些决策,建议下一步走第七节的 brainstorming。

### 六之一、新项目自动铺设(auto-scaffold)

面向不会敲 `/scaffold`、脑中没有"项目=文件夹"意识的纯 vibe coding 用户:插件装好后,新会话开局静默注入一条判定规则——用户在描述"要做一个新东西"(而不是问问题/改现有代码)、当前目录又不在任何 git 仓库且没有 `docs/`/`.claude/` 时,自动建目录 + `git init` + 走 `/scaffold` 的 Auto 模式铺好八件套,只回一行话告知路径就继续干活,不停下等确认。**判定原则是宁漏勿错**:拿不准是不是新项目就不触发,照常干活;目标目录里已经有同名文件就立即降级为交互模式,绝不静默覆盖。

- **关闭**:`touch ~/.claude/.auto-scaffold-off` 即全局 opt-out(hook 检测到就不再注入规则)。
- **换根目录**:`~/.claude/workflow-projects-root` 文件写入你想要的根路径,不写则默认 `~/Projects`。
- **判定 evals**:`plugins/workflow/evals/`(`cases.jsonl` + `run_evals.py` + `rubric.md`),覆盖触发/不触发两类判例(共 15 条:trigger 6 条、no_trigger 9 条;降级路径由单独的冒烟测试覆盖,不在本 evals 集合内)。
- **opt-out 后仍可手动触发**:`touch` 关闭标志只是关掉自动静默建项目;`/scaffold` 命令本身照常可用,手动敲或按描述触发都不受影响。
- **已有 git 仓内不注入**:会话所在目录已在 git 仓内时,hook 不再注入本规则(判定条件 2 本就不会触发,省上下文)。

### 六之二、决策/需求随口一说别蒸发(docs-capture)

问答框拍板、随口提的需求,对话一翻页就容易消失——这是一套三层 hook,层层兜底,每层补上一层漏不到的地方:

1. **层 1 确定性捕获**(`PostToolUse`,matcher `AskUserQuestion`):脚手架项目内每次 `AskUserQuestion` 问答框选了选项或填了自由文本,hook 就把原始问答逐字追加进 `docs/DECISIONS.inbox.md`——不摘要、不判断,原文照存,不给转述留漏损空间。目录外(无 `docs/` 的非方法论项目)静默不动。
2. **层 2 信号提醒**(`UserPromptSubmit`,设计上宁滥勿漏):按决策词表/需求词表(`signals-decision.txt` / `signals-requirement.txt`)扫每句输入;第三份词表 `signals-veto.txt` 存疑问/未定语气(吗、要不要、还没定),同子句内命中即压制——遇到误报要调教的就是这个文件。命中就提醒"这句像是决策/需求,建议落档",不拦截。故意选高召回而非高准确率——这层是软提醒,不是门禁,误触发的代价只是一行噪音,不是卡住输入。
3. **层 3 commit 门禁**(`PreToolUse`,matcher:Bash 命令含 `git commit`):`git commit` 放行前查两条——①`docs/DECISIONS.inbox.md` 是否还有未消化草稿(`## ` 级条目);②本次 staged 改动是否碰了源码却没碰 `docs/Progress.md`。任一条命中就警告。放行判据是「同一份 staged 内容警一次,不是永久警」:对 staged diff 取哈希,与上次警告的哈希比对——内容不变时首次拦截、原样重跑即放行(并不真的检查 inbox 是否已被消化,原样重跑本身就是清警的动作)。

三层合起来把"用户说了一嘴、对话翻篇就没了"变成"总归落在盘里、commit 前必被看一眼"——层 1 保底捕获,层 2 补住 `AskUserQuestion` 框以外的口头表达,层 3 是发布前最后一道闸。

- **关闭**:三层共用一个总开关——`touch ~/.claude/.docs-capture-off` 即三层全部静默(没有逐层单独关的开关);评测隔离场景把 env var `DOCS_CAPTURE_EVALS_HERMETIC` 设成任意非空值。各层在缺依赖时各自静默退化(比如缺 `jq` 会直接 exit,不报错)。
- **只消化不代笔**:`docs/DECISIONS.inbox.md` 是原始缓冲区,不是事实源——见 `CLAUDE.md.tmpl` 的「文档同步规则」表:决策提炼进 `docs/DECISIONS.md`,需求类条目转入 `docs/REQUIREMENTS.md` 目标台账,噪音直接删除。
- **不移植进 workflow-codex**:Codex CLI 没有承载这三层的 hooks 机制;"落档别蒸发"的纪律照旧成立,只是在 Codex 那边靠约定维持,不靠自动化(见「附赠插件:Codex CLI 版工作流」一节的对应说明)。

## 七、主流程:Brainstorming → Spec → Ultracode 直通

1. 一切创造性工作先走 superpowers:brainstorming,把 design spec 写入 `docs/superpowers/specs/<日期>-<主题>-design.md`,并登记进 `docs/PLAN.md` 的 Spec 索引。开工前先读 `docs/REQUIREMENTS.md` 目标台账里状态为 open 的未销账项,把与本次相关的列给用户;spec 须含「目标覆盖声明」——本次覆盖台账哪几条、明确不覆盖哪几条及原因。
2. spec 写入完成即视为对本次 Workflow 多代理实现(ultracode)的持久授权:**不等待批准、不问"是否开始实现"、不 invoke superpowers:writing-plans、不产出实现计划文档**,自动立即进入实现(用户中途主动喊停则照常停下)。
3. 需要隔离时先建 worktree(superpowers:using-git-worktrees,或 Workflow agent 的 `isolation: 'worktree'`)。
4. Workflow 编排实现:先输出 3~5 行**开工摘要**(拆了几个单元、各自 model/effort 档位、预估规模),**不等待确认直接开跑**——摘要只是给用户一个看得见的打断窗口。开工摘要末尾附一行现成可贴的目标命令:`/goal "完成 <批次/spec 名>" until "<spec 验收条款要点或本批覆盖的台账条目>全部满足"`——`/goal` 是 Claude Code 会话级内置命令(每轮自动评估完成条件,防长会话做着做着跑偏),不跨会话,跨批次的持久性靠目标台账。随后按 spec 拆独立单元 → 并行实现 agent(`sonnet`,每个遵守 TDD,prompt 自包含:附 spec 相关段落 + 项目 CLAUDE.md 硬规则 + **生产红线与文件所有权**——FORBIDDEN FILES(本单元不许碰的文件/目录点名列出)、绝不重启共享服务、绝不读写生产数据、禁止 force push 与任何丢弃改动的历史改写、只改分给本单元的文件)→ 每单元完成即派评审 agent(`opus`)验证裁决,评审除核对实现外必须核对**测试本身**(是否覆盖 spec 对应验收条款、是否只测 happy path),测试弱视同打回,被打回的单元重跑时测试与实现分开派两个 agent → 主对话汇总修复。评审报告一律**报差异不报摘要**:只报与上一轮、与其他票不同的新发现与推翻项,禁止"检查了一遍没问题"式复述;无新发现就写明"无新发现"并列出复核过的检查点。评审编排按任务选:验收裁决用平行多镜头票,诊断/根因/排障用链式接力(每轮 prompt 附上一轮结论与被否决的假设,连续两轮无新发现才收,见三.2)。
5. 本批改动涉及 UI(前端页面/交互)时,进 code review 前先跑一次 ui-sweep 做交互回归扫描(全站可交互元素系统性点一遍),把 dead(点了没反应)/page-error/left-domain 清单带进验收;真缺陷逐条真浏览器复核后才定罪,假阳性(状态累积、同步 prompt 堵塞、当前态按钮)按 skill 的判读指南定性。纯后端/文档批次跳过。实现完成后照常走 superpowers:requesting-code-review → verification-before-completion → finishing-a-development-branch;这些 skill 里的 "plan" 占位(如 PLAN_OR_REQUIREMENTS)一律填 spec 路径。完成后更新 `docs/Progress.md`(状态表 + 变更日志)与 `docs/PLAN.md`(Phase 打 ✅),同时销账目标台账——本批覆盖到的条目状态改 done 并附证据(commit/截图/spec 条款),把实现过程中新冒出的目标登记进台账。本批若造出了**别的项目能拿去用的成型件**(通用中间件/数据管线/LLM 客户端/部署模板/解析器等,非业务专属逻辑),收尾时登记进你组织的组件索引(§八 第 0 步查的那份;没有就从一份 YAML 清单起步,字段建议 slug/name/capability/repo/path/how_to_integrate/maturity/since/used_by),**必须核实真实路径后才写**,登记完推回索引所在仓。这与「第 0 步内部先行」构成闭环:一个管查、这个管造——索引只有人查没人写,三个月后就会退化成过期清单。
6. 本流程覆盖 brainstorming SKILL.md 中「结束后唯一可 invoke 的是 writing-plans」的规定;subagent-driven-development / executing-plans 因不再有 plan 文档而失去入口,属预期,不必绕路满足。
7. 用户明确点名要 writing-plans / subagent-driven / inline / 并行分派时,按点名的方式执行。

### 七之一、安全加固类工作的措辞规范

安全/加固类的 spec、派工 prompt、代码注释、commit message,一律用中性工程语言描述**系统做什么**——输入校验、频率限制、会话过期、权限收紧——而不是"防什么人、挡什么行为"。确需记录威胁场景时,写进面向人的项目文档(`DECISIONS.md` / `BUSINESS.md`),不进派工 prompt 与代码注释。原因:带对抗性叙述的消息可能被内容安全分类器整条拦截,导致 spec 回炉重写、被迫换模型——这是多场真实会话反复踩中的坑。这是措辞工程,不是隐瞒:同一个加固动作,按"系统行为"描述同样表达得完整。

### 七之二、需求当轮落账(目标台账登记规则)

对话中用户表达的需求、期望或不满——哪怕只有一句话——**当轮**登记进 `docs/REQUIREMENTS.md` 的「目标台账」(日期+原话+出处),并回一行「已记入目标台账」。拿不准算不算需求就按 open 登记,宁滥勿漏;**不登记视同没听见,禁止**。会议纪要、用户反馈里的需求类条目同样先落台账再升格;行动项(要做的事)照旧进 PLAN/spec,不入台账。

## 八、新产品/大功能先做 GitHub 调研

- **新产品/新项目:一律调研**,没有"要不要调研"的判断步骤。
- **较大功能:由 Claude 判断**(信号:需要新子系统或独立模块、该领域明显有成熟开源轮子、预计工作量大;拿不准问用户)。
- **时机**:brainstorming 意图明确后、提出候选方案之前。
- **第 0 步:内部先行(硬步骤)**:先查**自己组织内部**有没有现成可复用件——组件索引、内部代码托管(如自建 GitLab)上的既有项目/模块;内部命中的候选与外部开源候选**同台呈现**给用户拍板,不得因为"是内部的"就默认优先或默认排除。内部索引不可用时如实记录后继续外部调研,不阻塞。
- **做法**:调研 GitHub 上的成熟开源实现(有专门调研 skill 就用;没有则用 web/GitHub 搜索完成同等调研)。
- **产出**:调研结论(直接采用/自部署、fork 二开、自研+可复用组件)必须作为正式候选方案之一呈现,并沉淀进 spec 的「Prior art」一节。
- 小修小补不触发;用户明说"不用调研"可跳过。
- **定期校对**:组件索引每季度或换代节点做一次全量校对:补漏(新造未登记的)、清失效(路径已删/项目已归档的标注或移除)、核对 maturity 是否仍属实。索引长期不校对会退化成过期清单,查了等于没查。

## 九、续航:回到项目先问"下一步"(对应 /whats-next)

用户说"下一步干什么 / 我到哪了",且项目根目录有 `docs/PLAN.md` 时:

1. **文档是唯一依据**,不为回答这个问题遍历代码库;只在文档间矛盾需核对时才抽查代码。
2. 读:`PLAN.md`(路线 + Phase 状态 + Spec 索引)→ `Progress.md`(状态表 + 最近 2~3 条日志)→ 最新 spec(对照 Progress 判断是否已实现)→ `DECISIONS.md` 最近 2~3 条 → `MEETINGS.md` 最新一节的待办 → `REQUIREMENTS.md` 目标台账里状态为 open 的未销账项。
3. **按序判断,命中即停**:
   | 状态 | 下一步 |
   |---|---|
   | 最新 spec 尚未实现 | 用 ultracode 直接从该 spec 实现;spec 是否已获批准拿不准时先问一句 |
   | spec 全部已实现,PLAN.md 还有未 ✅ 的 Phase | 对下一个 Phase 走 brainstorming 出新 spec → ultracode(不走 writing-plans),spec 登记进 Spec 索引 |
   | PLAN.md 路线还是待补 | 先读 REQUIREMENTS.md 的分期路线图作输入,用 brainstorming 定分阶段路线 |
   | 所有 Phase 都 ✅ | 项目按计划完成;建议复盘或开新 Phase |
4. **输出五部分**:① 当前位置(最近完成了什么,引 Progress 最新条目日期);② 下一步(任务名 + 到文件/命令级的第一步动作 + 出处);③ 随行注意(DECISIONS/Progress 里与下一步同域的决策与踩坑,注明出处;没有则省略;若最近一批改动动过 UI 且 Progress 里没有 ui-sweep 走查记录,在此提示一句:建议补跑一次交互回归扫描,没有则省略、不强推));④ 未落计划的会议待办(MEETINGS 最新一节里未勾选且没进任何计划的,提醒用户决定去向;没有则省略);⑤ 未销账目标(REQUIREMENTS.md 目标台账里状态为 open 的条目逐条列出,挂账超 7 天的置顶标注;没有则省略)。结尾问:现在开始吗?
5. 文档之间矛盾(Progress 说完成但 spec 无实现记录之类)→ 明确指出矛盾及双方出处,建议先核对再动工,**不默默择一**;缺 `PLAN.md`/`Progress.md` 说明不是本工作流的项目,建议先走第六节铺脚手架。
```

## 仓库结构

```
claude-workflow-kit/
├── README.md                        # 英文 README(默认门面)
├── README.zh-CN.md                  # 本文件:方法论 + 安装 + 工作流 prompt
├── LICENSE                          # MIT
├── .claude-plugin/
│   └── marketplace.json             # 插件市场清单(注册八个插件)
└── plugins/
    ├── workflow/                    # 中文输出插件
    │   ├── .claude-plugin/plugin.json
    │   ├── hooks/                   # auto-scaffold 常驻规则(hooks.json + inject.sh + auto-scaffold.md)+ docs-capture(capture-decisions.sh、signal-reminder.sh、commit-gate.sh、signals-decision.txt、signals-requirement.txt、signals-veto.txt、docs-capture-smoke-test.sh)
    │   ├── evals/                   # auto-scaffold 判定 evals:cases.jsonl + run_evals.py + rubric.md + .gitignore(out/、__pycache__/)
    │   └── skills/
    │       ├── scaffold/            # /scaffold:SKILL.md(含 Auto 模式节)+ templates/(11 个模板)
    │       │   ├── SKILL.md
    │       │   └── templates/
    │       │       ├── CLAUDE.md.tmpl  README.md.tmpl  gitignore.tmpl
    │       │       └── docs/        # 八件套模板
    │       ├── whats-next/          # /whats-next:SKILL.md
    │       │   └── SKILL.md
    │       └── sop-generate/        # /sop-generate:SKILL.md + references/ + scripts/
    │           ├── SKILL.md
    │           ├── references/      # runbook-template.md(网络不可达时的降级交付模板)
    │           └── scripts/         # crawl.mjs(原生 Playwright 降级采集脚本)
    ├── workflow-en/                 # 英文输出插件(结构同 workflow,含同款 hooks/)
    ├── workflow-codex/               # OpenAI Codex CLI 移植版(五个 skill,无 Claude Code 插件清单)
    │   ├── .codex-plugin/plugin.json
    │   └── skills/
    │       ├── scaffold/            # 铺 AGENTS.md + 八件套(无 CLAUDE.md.tmpl)
    │       ├── whats-next/
    │       ├── sop-generate/
    │       ├── parallel-do/         # Codex 专属:把一步拆给多个 Codex subagent 并行执行
    │       └── speak-human/         # 说人话纪律 Codex 移植版,常驻靠写入 ~/.codex/AGENTS.md
    ├── speak-human/                 # 中文版 speak-human 插件:hooks/ + skills/ + evals/
    ├── speak-human-en/              # 英文版 speak-human 插件(结构同 speak-human)
    ├── send-to/                     # 中文版 send-to 插件:跨会话消息转达
    │   ├── .claude-plugin/plugin.json
    │   ├── hooks/                   # SessionStart 注册 hook:把本会话身份写进共享身份注册表
    │   └── skills/send-to/SKILL.md  # 目标模糊匹配 + 消息自包含硬规则 + 投递状态如实汇报
    ├── send-to-en/                  # 英文版 send-to 插件(结构同 send-to)
    ├── ui-sweep/                    # 中文版 ui-sweep 插件:agent-browser 驱动的 UI 全量交互遍历
    │   ├── .claude-plugin/plugin.json
    │   └── skills/ui-sweep/
    │       ├── SKILL.md             # 环境自检→登录态注入→屏清单编制→跑引擎→结果判读→产报告
    │       ├── scripts/             # sweep.mjs(通用化遍历引擎)+ export-state.mjs(登录态导出)
    │       └── references/          # report-template.md(报告骨架)
    └── ui-sweep-en/                 # 英文版 ui-sweep 插件(结构同 ui-sweep,scripts 与中文版逐字节一致)
```

## License

[MIT](LICENSE)
