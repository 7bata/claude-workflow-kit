# auto-scaffold:新项目自动铺设 — 设计 spec

日期:2026-08-11
状态:已获用户逐节批准(触发机制、规则正文、Auto 模式、分发面矩阵、验收方案共四节,两轮确认)
来源:stella 路线图窗口转达的用户指派——让"新建项目"总是自动铺脚手架,落 claude-workflow-kit,同步 stellark vibe / huake / 开源各面

## 1. 背景与目标

非工程用户(典型如 Will)纯 vibe coding:开会话说需求、AI 就干,脑中没有"项目=
文件夹"的意识——不建文件夹、不敲 `/scaffold`、不管 git。结果项目没有 docs,
stella 路线图(读各项目 docs/REQUIREMENTS、DECISIONS、PLAN、Progress 生成主管级
路线图)无料可读。

**目标**:把"认出新项目并铺设脚手架"做成**注入会话的 AI 行为**——AI 从用户的
需求句自己认出"这是个新项目",无声建好文件夹 + git 仓 + 脚手架 docs;脚手架里的
CLAUDE.md 自带自维护闭环(每操作 → 补文档 + 原子 commit + push),铺下去之后由
用户会话里的 AI 持续维护 docs,用户全程不需要懂任何概念。

**非目标**:
- 存量缺 docs 项目的回填(另有窗口负责,本设计明确不顺手补铺);
- 改变 DECISIONS / PLAN / Progress 三件模板的格式(stella 解析依赖现状格式;
  若未来要改,先知会 stella 窗口);
- 改动现有手动 `/scaffold` 交互流程(Auto 模式是并列入口,手动流程一字不动)。

## 2. Prior art

- 机制空间由 Claude Code 自身扩展点(hook / skill / CLAUDE.md)限定,无外部轮子
  可借;通用脚手架器(yeoman / cookiecutter 一类)解决的是"怎么铺",本仓
  scaffold skill 已具备,本次新增的是"怎么自动认出来",故按全局规则判定不触发
  GitHub 先行调研(用户未异议)。
- 仓内先例:speak-human 插件的 SessionStart hook 注入(`hooks/hooks.json` +
  `inject.sh` 剥 frontmatter 注入正文),含评测隔离环境变量的防污染解法,直接复用。

## 3. 方案选型(已拍板)

**方案 A:常驻 hook 注入判定规则 + scaffold 增 Auto 模式 + 触发描述扩词。**
落选:B(只扩 skill description——触发概率性,对不会敲命令的用户漏触发风险高;
superpowers 自身都需 hook 强制模型用 skill)、C(写各机器全局 CLAUDE.md——不可
分发、无版本管理)。

关键取舍:
- **默认开启、可 opt-out**(`touch ~/.claude/.auto-scaffold-off` 全局关闭)。与
  speak-human 的 opt-in 相反,理由即动机本身:目标用户不会去开开关,装插件即
  视为选择进入方法论。误触发防线放在保守判定上,不放在开关上。
- **宁漏勿错**:拿不准就不触发,照常干活;绝不错建垃圾文件夹。

## 4. 注入规则正文(hook 注入内容,~40 行)

落盘为 `plugins/workflow/hooks/auto-scaffold.md`,注入时原样输出(无 frontmatter
可剥则直接 cat)。正文定稿:

```markdown
# auto-scaffold:新项目自动铺设

## 判定(三条全满足才触发)
1. 用户在描述"要做一个新的东西"——新产品/工具/网站/系统,
   而不是:问问题、闲聊、改现有代码、在现有项目里加功能;
2. 当前目录不在任何 git 仓库内(git rev-parse --git-dir 失败),
   且当前目录没有 docs/ 或 .claude/(不是已铺过的项目);
   例外:当前目录就是用户家目录 $HOME 本身时,~/.claude 是 Claude 自己的
   配置目录、不算项目标记——$HOME 不是 git 仓即视为满足本条;
3. 本次对话尚未为这个需求建过项目。

拿不准算不算新项目时:不触发,照常干活——宁可漏建,不可错建垃圾文件夹。
用户明说"不用建项目/就在这儿改"时:不触发。
已有仓库但缺 docs 的存量项目:不归本规则管,不要顺手补铺。

## 触发后动作(静默执行,全程不追问、不发选项)
1. 从需求句提炼英文 kebab-case 项目名(如"记账小工具"→ expense-tracker);
2. 定项目根:~/.claude/workflow-projects-root 文件存在则以其内容为根,
   否则默认 ~/Projects;创建 <根>/<项目名>/ 并进入;
   - <根>/<项目名>/ 已存在:不复用、不覆盖,视同"拿不准"——本次不自动
     建项目,一行说明后就地继续干活;
   - 创建或写入失败(含用户拒绝授权):不重试;已建出的空目录删掉,
     不留残目录;一行说明"没能自动建项目,先就地干活",照常继续;
3. 按 scaffold skill 的「Auto 模式」铺设(技术栈走基线不询问;能从
   用户需求句填实的填实,其余留模板占位;git init + 初始 commit 含在内);
4. 一行话告知:"已建项目 <名> 于 <路径>,这个需求后续都在里面做"——
   说完直接继续干用户真正要的活,不停下等确认。

## 关闭
touch ~/.claude/.auto-scaffold-off 即全局关闭(hook 检测到就不注入)。
```

hook 配置(`plugins/workflow/hooks/hooks.json`)与 speak-human 同款:
SessionStart,matcher `startup|resume|clear|compact`,timeout 5,调 `inject.sh`。
`inject.sh` 防御:opt-out 标志存在 → 静默退出;规则文件缺失 → 静默退出;评测
隔离环境变量 `AUTO_SCAFFOLD_EVALS_HERMETIC` 非空 → 静默退出;当前目录已在
git 仓内 → 静默退出(判定条件 2 永远不满足,注入纯属上下文浪费)。

2026-08-11 终审修订:HOME 豁免、同名目录条款、失败分支、git 仓早退(评审
Important #1/#4)。

## 5. scaffold skill 增「Auto 模式」

在 `plugins/workflow/skills/scaffold/SKILL.md` 增一节,并列于现有交互流程:

- **跳过**步骤 2 的 intake 追问与七格业务追问、步骤 3 的 AskUserQuestion 确认;
- 数据库默认 PostgreSQL;需求句有明显信号(单机/离线/纯命令行)才走既有
  SQLite / CLI 分支,判断理由自动写进 `docs/DECISIONS.md`;
- `docs/REQUIREMENTS.md` 用需求句填实一句话定位与初版需求;`docs/BUSINESS.md`
  七格全留占位注释(后续会话自然补);`docs/MEETINGS.md` 空骨架;
- 步骤 4 冲突保护简化:Auto 模式只应在新建空目录里跑,检测到任何 EXISTS 文件
  → **立即降级为交互模式**(绝不静默覆盖,fail-safe);
- 步骤 5 收尾(git init -b main + 初始 commit + 占位/乱码自检)原样执行;收尾
  汇报压缩为一行;
- skill frontmatter description 扩词:补"用户描述要做一个新产品/工具/网站且
  当前不在项目目录"触发场景(与 hook 规则互为冗余,不互斥)。

## 6. 分发面矩阵

| 分发面 | 改动 |
|---|---|
| 开源 zh `plugins/workflow/` | 新增 hooks 三件(hooks.json / inject.sh / auto-scaffold.md);scaffold SKILL.md 加 Auto 模式节 + description 扩词;plugin.json 版本升、description 提自动铺设;marketplace.json 同步 |
| 开源 en `plugins/workflow-en/` | 同上全套英文版;**双语两份 README 都要加节 + 目录树**(历史上英文 README 漏更被评审打回,列入验收清单) |
| stellark vibe `dev-toolkit-vibe`(plugins/vibe/) | 同款 hook;规则正文中执行器换为 `/stellark-setup` 静默路径:slug 当 `$ARGUMENTS` 传入,其余字段沿用其 schema 默认值;stellark-setup 加 auto 模式小节(语言选择之外不发任何问题)。vibe 仓本机无 checkout:临时 clone,动手前先 fetch 快进(CI 有 [auto-bump] 提交)。共享 skill 只进 vibe 不进 engineer(叠装规则) |
| huake `claude-toolkit-engineer` | 同款 hook + scaffold Auto 节;README「包含的 N 个 skill」计数与表格、plugin.json description 同步 |
| codex `plugins/workflow-codex/` | **不做自动触发**(Codex CLI 无 SessionStart hook 机制);README 注明原因,附一段可手动粘进全局 AGENTS.md 的规则片段供 opt-in |

## 7. 验收方案

1. **正向冒烟**:干净临时目录(HOME 隔离)模拟说"我想做个记账小工具"→ 目录按
   slug 建立、11 件 + `data/.gitkeep` 落盘、`grep -rl '{{'` 干净、无乱码、初始
   commit 存在、REQUIREMENTS 被需求句填实、告知只有一行。
2. **反例冒烟**(宁漏勿错,三条):现有 git 仓内说同样的话 → 不触发;"帮我修个
   bug" → 不触发;"就在这个文件夹里改" → 不触发。
3. **降级冒烟**:目标目录预放同名 README.md → Auto 模式降级为交互模式,不静默
   覆盖。
4. **轻量判定 evals**:仿 speak-human evals 基建,判例集 15 条(jsonl + 判分
   脚本,含 HOME 根目录触发与同名目录不触发两条终审补例),hermetic 环境变量
   隔离评测子进程。
5. **hook 卫生**:opt-out 标志、规则文件缺失、hermetic 变量、已在 git 仓内
   四种情况下 inject.sh 均静默安全退出。

## 8. 实施顺序

1. wip 分支上开源 zh 主实现(hooks 三件 + Auto 模式节)+ evals;
2. 开源 en 镜像 + 双语 README;
3. 冒烟与 evals 验收;
4. 评审 + 用户确认后并入 main;
5. 传播:stellark vibe(临时 clone)→ huake → codex README 片段;
6. 回执 stella 窗口(doc 格式未动,可放心解析)。
