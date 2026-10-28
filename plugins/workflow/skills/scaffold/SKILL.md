---
name: scaffold
description: 在当前项目目录里铺设方法论脚手架（CLAUDE.md + docs 八件套 + .gitignore + README）。后端技术栈固定为 Go（版本基线见 skill 内表格），数据库由 Claude 按项目意图判断。用户说"搭脚手架/初始化项目/开新项目/scaffold"时触发；用户描述要做一个新产品/工具/网站且当前不在项目目录时也触发（auto 模式，配合 auto-scaffold 常驻规则）。
allowed-tools: Bash, Read, Write, Glob, AskUserQuestion
---

# /scaffold

在**已存在的**项目目录里就地铺设方法论脚手架。**全程默认中文输出**（技术标识符保持英文）。

模板位于本 skill 的 `templates/` 子目录。用 Glob/Read 读模板时，基于调用时给出的本 skill base directory（"Base directory for this skill"）下的 `templates/`，不要写死绝对路径。

## 技术栈基线（固定，不做选型）

后端技术栈**固定为 Go**，版本与选型统一采用以下基线（固定基线是本方法论的一部分：逐项目不再重复选型；想换栈就修改本表，而不是单次临时偏离）：

| 组件 | 选型 / 版本 | 说明 |
|---|---|---|
| 后端语言 | Go 1.25（`golang:1.25-alpine` 编译） | 标准库 `net/http` + chi 路由，无重量级框架 |
| DB 访问 | pgx（手写 repository） | 不用 ORM、不用 sqlc，`internal/repo` 直接写类型化 SQL |
| 迁移 | golang-migrate | 纯 SQL 版本化迁移（`NNNN_*.up.sql / down.sql`） |
| 校验/序列化 | `encoding/json` + go-playground/validator | 请求/响应 schema 校验 |
| 前端（如需要） | React + TypeScript + Vite | `node:20-alpine` 仅用于构建阶段 |
| 运行镜像 | `alpine:3.20` | Docker 多阶段构建，单静态二进制，`/health`（存活，恒 200，容器健康检查探它）与 `/health/ready`（就绪，可选；开了就把切换前探的路径改成它） |
| 日志 | 标准库结构化日志（Go 用 `log/slog` 的 JSON handler；其它栈用等价的 JSON 行日志库）写 stdout | 按 `.claude/CLAUDE.md` 第 4 节的日志契约；完整表格与验收清单在 `docs/ARCHITECTURE.md`「日志契约」一节 |
| 目录结构 | `backend/cmd/server` 入口 + `backend/internal/{config,db,repo,handlers,service,model,middleware}` | Go 社区惯例；前端在 `frontend/src` |

后端服务保持**无状态**（状态全在数据库），为多副本水平扩展留余地。

## SQLite 分支（步骤 3 选了 SQLite 时的具体替代）

上面基线表默认 PostgreSQL（pgx + golang-migrate + postgres 容器/实例）。步骤 3 若判断选 **SQLite**（小型低并发 / 单机一体机场景），DB 访问层与迁移工具按以下替换，Go 版本、校验库、运行镜像、目录结构（`backend/internal/{db,repo}` 等目录名不变，只是里面的实现换了）不变——不是"酌情调整"，按此执行：

| 组件 | SQLite 替代 |
|---|---|
| DB 访问 | `database/sql` + `modernc.org/sqlite`（纯 Go 驱动，无 cgo，`CGO_ENABLED=0` 直接编译；不用需要 cgo 的 `mattn/go-sqlite3`） |
| 迁移 | golang-migrate 的 `sqlite`（modernc，纯 Go）驱动，migrations 仍是 `NNNN_*.up.sql/down.sql`；不用 cgo 版 `sqlite3` 驱动；无迁移框架依赖时也可退化为启动时执行嵌入的建表 SQL（`embed.FS` 内一份 `schema.sql`），小项目够用 |
| 数据文件 | 单文件落 `data/{{PROJECT_NAME}}.db`（复用本 skill 落盘的 `data/` 目录），不建 PG 容器/实例 |
| 并发注意 | 打开 `_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)`，写路径避免长事务持锁 |

**占位符联动**：`{{TECH_STACK}}` 里 `pgx + golang-migrate` 替换为 `database/sql (modernc.org/sqlite) + golang-migrate (sqlite driver)`；`{{DATABASE}}` 填 `SQLite`。

**`docs/DECISIONS.md.tmpl` 预置首条会自相矛盾，必须改**：第 9 行 What「后端 Go 1.25（net/http + chi + pgx + golang-migrate），数据库 {{DATABASE}}」里的 `pgx + golang-migrate` 若不改，`{{DATABASE}}` 填 `SQLite` 后渲染成「…pgx + golang-migrate…数据库 SQLite」，同一句自相矛盾；落盘前把这半句换成 `database/sql (modernc.org/sqlite) + golang-migrate (sqlite driver)`。再按下文「`docs/DECISIONS.md` 追加一条记录选 SQLite 的理由」写一条独立条目。

**`docs/ARCHITECTURE.md.tmpl` 里第 1/3/6 节的 `pgx`/`BIGSERIAL`/`TIMESTAMPTZ`/`pgxpool` 是正文硬编码、不是占位符**（该模板未做数据库分支占位符化）。落盘生成 `docs/ARCHITECTURE.md` 后，选了 SQLite 就必须手工按下表改写这几处，否则文档会与实际技术栈冲突，且照着 `BIGSERIAL`/`TIMESTAMPTZ` 写 DDL 在 SQLite 里会直接建表失败：

| 位置 | PostgreSQL 原文 | SQLite 改写为 |
|---|---|---|
| 第 1 节「DB 驱动 / 查询」行 | `pgx（手写 repository）` | `database/sql + modernc.org/sqlite（手写 repository）` |
| 第 3 节表设计约定 | `id BIGSERIAL PK`、`created_at/updated_at TIMESTAMPTZ` | `id INTEGER PRIMARY KEY AUTOINCREMENT`、`created_at/updated_at TEXT`（ISO8601 字符串，SQLite 无原生 TIMESTAMPTZ 类型） |
| 第 6 节目录结构注释 | `pgx 连接池` / `pgxpool 连接池` / `手写 pgx repository` | 对应改为 `database/sql (modernc.org/sqlite) 连接` / `手写 repository` |

`docs/DECISIONS.md` 追加一条记录选 SQLite 的理由（步骤 3 已要求）。

本 skill 落盘范围是 11 个通用文件，SQLite 分支不改变落盘文件数量；除上表要求手工改写 `docs/ARCHITECTURE.md` 正文、`docs/DECISIONS.md.tmpl` 预置首条外，其余文件只改变技术选型占位符取值。

## CLI / 无网络服务分支（步骤 3 判定为纯 CLI / 批处理时的具体替代）

上面基线表默认对外提供 HTTP 接口（`net/http + chi` + `/health`（存活）与可选的 `/health/ready`（就绪）+ 容器运行）。步骤 3 若判定项目是**纯 CLI / 批处理**（无 HTTP 接口、不监听端口），按以下替换，不是"酌情调整"，按此执行：

| 组件 | CLI 替代 |
|---|---|
| `{{TECH_STACK}}` | `Go 1.25 标准库 CLI + <DB 访问栈>`（`<DB 访问栈>` 按上面基线表或 SQLite 分支取值），不写 `net/http + chi` |
| 目录结构 | `backend/cmd/<binary>` 入口 + `backend/internal/{cli,core,db,repo,model}`；不建 `handlers/`、`middleware/` |
| `docs/ARCHITECTURE.md` | 第 1 节删掉路由/HTTP 接口行；第 6 节目录结构注释同步为 `cmd/<binary>` + `internal/{cli,core,db,repo,model}`，不出现 `handlers`/`middleware` |
| `docs/DEPLOYMENT.md` | 部署形态写「单二进制，`CGO_ENABLED=0 go build`，无容器/端口/健康检查」；不写 `alpine` 运行镜像与 `/health` |
| 日志契约 | 纯 CLI 没有 HTTP：不写 `http request` 行，不做 `/health`、`/health/ready`；`service start` 不带 `addr`；`service stop`、作业行、外部调用行照契约写；铺出来的 `docs/ARCHITECTURE.md` 5.1 验收清单第 2、6 条与 `docs/DEPLOYMENT.md`「上线后核对」里 `http request`、`/health` 两条划掉，其余保留；生成的 `CLAUDE.md` 第 4 节与 `docs/ARCHITECTURE.md` 5.1 正文里的 `http request`、健康检查两条标成「本项目无 HTTP，不适用」，版本注入改用 `-ldflags` 或构建信息里的 vcs 修订（无 Dockerfile） |

## 非代码产出分支（步骤 3 第 0 条选了「非代码产出」时）

培训、PPT、讲义、报告、方案文档这类没有代码的交付物也当仓库管：材料逐版留档，每版一次提交。选了这个类型，上面的技术栈基线、SQLite 分支、CLI 分支都不适用；步骤 3 第 1~5 条不问、汇报写「不适用」，步骤 2 的 7 格追问换成下面的追问，步骤 4 改用下面的清单。

1. **Intake 追问**（代替 7 格业务模型）：产出是什么（讲义 / PPT / 报告 / 方案）、给谁（受众）、分几个单元（讲 / 章 / 期）、谁交付、首版截止日；信息不够留占位，不逼问。
2. **落盘**（模板目录 `templates/noncode/`，8 个文件 + 1 个占位）：`.claude/CLAUDE.md`、`AGENTS.md`（与 CLAUDE.md 同文，给 Codex 读；改规则时两份一起改）、`README.md`、`.gitignore`、`docs/PLAN.md`、`docs/Progress.md`、`docs/REQUIREMENTS.md`、`docs/DECISIONS.md`，以及 `材料/.gitkeep`。冲突保护同代码项目（已存在的列出来问，不静默覆盖）。**不生成** Dockerfile、CI 配置、`.env.example`、`docs/ARCHITECTURE.md`、`docs/DEPLOYMENT.md`、`docs/BUSINESS.md`、`docs/MEETINGS.md`，也不建 `data/.gitkeep`。占位符：`{{PROJECT_NAME}}`、`{{ONE_LINER}}`、`{{DATE}}`、`{{AUDIENCE}}`（受众）、`{{DELIVERABLES_BLOCK}}`（交付物清单，intake 填不出就留 `<!-- 待补：交付物清单 -->`）。
3. **目录约定**（已写进模板，CLAUDE.md / AGENTS.md / README 三处一致）：`材料/` 放交付物本体，按单元分子目录，培训类单元内再分 `发给学员/`、`讲师用/`、`源文件/`（其他类型按产出物分子目录，README 写清），仓里只留每个文件的最新版，历史版本靠 git 历史，不另存 `v2.3 存档/` 这类目录，也不进 zip；`docs/` 是四件套，`Progress.md` 是**版本日志**（每出一版加一行「版本 | 日期 | 改了什么 | 提交」，最新在上；项目进展据此一眼看清；首次那一行的提交列写「首次提交」，之后每行写该版 tag 名，不打 tag 的先留空、提交后补短 sha 随下一次提交带上）；`README.md` 有项目一句话、受众、目录说明与「网盘链接」表（文件名 | 版本 | 链接 | 日期）。
4. **仓内硬规则**（CLAUDE.md / AGENTS.md 同文，模板已写）：每出一版就提交一次，提交说明写「<类型>: <单元或文件> vN——改了什么」（类型用 docs / chore / fix），不许把几版攒成一次提交，提交前 `docs/Progress.md` 版本日志先加一行、与材料一起提交；单个文件超过 20 MB（视频、录音、大 PDF、大图包）不进 git，放团队网盘或对象存储、在 README「网盘链接」表登记，仓里只留链接，提交前跑 `find . -path ./.git -prune -o -type f -size +20M -print`（误把大文件或个人信息提交了：还没 push 的用 `git rm --cached <文件>` 再 `git commit --amend`；已 push 的要改写历史并通知所有协作者；误提交的密码、令牌先作废换新，改写历史收不回已被拉取的值，所以提交前先查）；不写密码、令牌、学员与客户的个人信息进仓，示例用虚构数据并标明「虚构」；分支即推，要给别人看的版本标 git tag（`v1`、`v2`……）；打 tag 后 `git push origin vN`（`git push` 默认不推 tag）；仓库还没有远端时先建远端，建好前 push 失败不算提交失败；本项目没有代码、测试与部署，Workflow、评审链、TDD、日志契约不适用，要用 AI 改材料照常在本仓里做、改完按上面提交。
5. **收尾**：首次提交只 add 落盘清单，目录里既有的文件先列给用户看（做法见步骤 5）；汇报加一行「类型：非代码产出（材料 / docs 四件套；不生成 CI 与部署）」；首次提交说明用「chore: 初始化非代码产出项目骨架（材料 / docs 四件套）」；`docs/PLAN.md` Phase 0 标 ✅ 的规则同代码项目。

## 步骤 1：确认项目名与目录

```bash
basename "$PWD"
```
取当前文件夹名为项目名。确认当前目录就是要铺设的项目根目录。

## 步骤 2：Intake — 收集项目意图

向用户说明并收集：

> 把这个项目的想法 / 会议总结讲给我，或指给我一个文件（如纪要 `*.md`），我据此判断技术栈、数据库、核心不变量和模块划分。

- 用户给文件路径 → 用 Read 读它；若是**会议纪要**，落盘时将原始内容归档进 `docs/MEETINGS.md` 第一节，其中的**业务事实**另提炼进 `docs/BUSINESS.md`（原先全部归 REQUIREMENTS 的提炼职责，现按事实/决定拆分）
- 用户口述 → 用对话内容
- 信息不足以判断时，**针对性追问**（不要泛泛）

- intake 明显是培训 / 讲义 / PPT / 报告这类没有代码的产出时，步骤 3 推荐「非代码产出」类型，追问改用「非代码产出分支」的第 1 条，不用下面的 7 格

在判断技术栈/DB 之外，**按以下 7 格追问业务上下文**（用于填实 `docs/BUSINESS.md`；信息不足的格留占位注释，不逼问、不卡流程）：

1. 目标与现状手工流程 —— 没系统之前谁、用什么工具、一步步怎么做，痛点在哪
2. 输入：交易数据 —— 每次都变的数据是什么，有没有真实样本文件
3. 输入：参考/配置数据 —— 对照表、规则表、允许值，有没有现成文件
4. 加工流程 —— 输入怎么变成输出
5. 输出 —— 产出什么、给谁、什么样，有没有期望输出样例
6. 业务铁律与异常 —— 绝不能错的规则，意外情况怎么处理
7. 人工介入与反馈 —— 谁复核、能改什么、改的结果要不要被系统记住

## 步骤 3：决策并确认

基于 intake，向用户列出以下各项 + 给理由，用 AskUserQuestion 让用户确认/修改：

0. **项目类型** —— **代码项目**（默认，下面第 1~5 条照常）/ **非代码产出**（培训、PPT、讲义、报告、方案文档等没有代码的交付物）。先**单独**用一次 AskUserQuestion 问（只问这一问，默认代码项目）；intake 明显是培训 / 讲义 / PPT / 报告的，推荐非代码产出并说明理由。选了非代码产出，第 1~5 条不问、汇报写「不适用」，改按上面「非代码产出分支」执行；选了代码项目，第 1 条只陈述、第 2~5 条合成第二次 AskUserQuestion 确认
1. **后端技术栈** —— **固定为 Go，不询问、不选型**（见开头「技术栈基线」表格）。只向用户**陈述**将采用该基线；若用户主动要求换栈，视为修改本 skill 的信号，提醒其更新基线表而非本次临时偏离
2. **数据库**：
   - **默认 PostgreSQL**（有并发 / 大多数场景；Go 侧用 pgx + golang-migrate，见基线表）
   - **仅小型低并发 / 单机一体机用 SQLite**（如 mac mini appliance）——选中则按上面「SQLite 分支」执行
   - 判断依据：并发量、部署形态（云 vs 单机）、数据规模
3. **是否需要 Web 前端**：需要则按基线 React + TypeScript + Vite；纯 API / CLI 项目则无 frontend 目录。判定为纯 CLI / 批处理（无 HTTP 接口、不监听端口）时，按上面「CLI / 无网络服务分支」执行
4. **核心不变量**：本项目「绝不破坏」的架构约束，0~N 条。想不出就留占位
5. **模块划分**：顶层模块名 + 一句话职责。想不清就留占位

把每项的**判断理由**说出来，由用户拍板。确认后才落盘。

## 步骤 4：落盘（带冲突保护）

先列出将写入的 11 个目标文件（类型为非代码产出时改用「非代码产出分支」第 2 条的清单：8 个文件 + `材料/.gitkeep`，模板在 `templates/noncode/`，不建 `data/.gitkeep`），**逐个检查是否已存在**：

```bash
for f in .claude/CLAUDE.md docs/PLAN.md docs/Progress.md docs/ARCHITECTURE.md docs/DEPLOYMENT.md docs/REQUIREMENTS.md docs/BUSINESS.md docs/DECISIONS.md docs/MEETINGS.md .gitignore README.md; do
  test -e "$f" && echo "EXISTS: $f"
done
```

类型为非代码产出时，循环里的清单换成 `.claude/CLAUDE.md AGENTS.md README.md .gitignore docs/PLAN.md docs/Progress.md docs/REQUIREMENTS.md docs/DECISIONS.md 材料`。

- 有 `EXISTS` 的 → 列出来问用户：跳过 / 备份改名（`.bak`）/ 手动合并。**绝不静默覆盖**
- 无冲突的 → 继续

对每个模板：Read 模板内容 → 替换占位符 → Write 到目标路径。占位符替换表：

| 占位符 | 值来源 |
|---|---|
| `{{PROJECT_NAME}}` | 步骤 1 文件夹名 |
| `{{ONE_LINER}}` | intake 提炼的一句话定位 |
| `{{DATE}}` | `date +%F` |
| `{{TECH_STACK}}` | 固定基线：`Go 1.25（net/http + chi）+ pgx + golang-migrate`；选 SQLite 时按「SQLite 分支」替换；纯 CLI / 批处理时按「CLI / 无网络服务分支」替换，不写 `net/http + chi`；有前端时追加 `；前端 React + TypeScript + Vite（Node 20 构建）` |
| `{{DATABASE}}` | 步骤 3 数据库 |
| `{{INVARIANTS_BLOCK}}` | 步骤 3 核心不变量；无则 `<!-- 待补：本项目核心不变量 -->` |
| `{{MODULES_BLOCK}}` | 步骤 3 模块划分；无则 `<!-- 待补：模块划分 -->` |
| `{{CODE_CONVENTIONS_BLOCK}}` | 按基线生成的 Go 代码约定（Go 1.25、gofmt、error 显式处理并 wrap、`cmd/` + `internal/` 布局、依赖最小化）；有前端时追加 TS 约定（strict 模式、组件按页面分目录）；日志按契约写：slog JSON、每请求一行访问日志、作业行、外部调用行、`/health` 正文（模板里 `CLAUDE.md.tmpl` 第 4 节已内置日志契约固定块，此占位符不重复写） |
| `{{AUDIENCE}}` | intake「给谁」；填不出留 `<!-- 待补：受众 -->` |
| `{{DELIVERABLES_BLOCK}}` | intake 的交付物清单；填不出留 `<!-- 待补：交付物清单 -->` |

模板路径映射：`templates/docs/X.md.tmpl` → `docs/X.md`；`templates/gitignore.tmpl` → `.gitignore`；`templates/CLAUDE.md.tmpl` → `.claude/CLAUDE.md`；`templates/README.md.tmpl` → `README.md`。另建空目录占位 `data/.gitkeep`。(data/.gitkeep 是清单外的占位文件,物理文件总数 = 清单数 + 1,自检时按此对账)非代码产出：`templates/noncode/docs/X.md.tmpl` → `docs/X.md`，`templates/noncode/CLAUDE.md.tmpl` → `.claude/CLAUDE.md`，`templates/noncode/AGENTS.md.tmpl` → `AGENTS.md`，`templates/noncode/README.md.tmpl` → `README.md`，`templates/noncode/gitignore.tmpl` → `.gitignore`；另建 `材料/.gitkeep`。

**内容预填**（不只替换占位符，能填实的就填实）：

- `docs/REQUIREMENTS.md`：用 intake 提炼内容尽量填实（产品定位、目标用户、分期路线图、已确认决策）；填不了的保留待补注释；模板自带「目标台账（收件箱）」节，落盘时保留空表格即可，不追问
- `docs/BUSINESS.md`：用 7 格追问收集到的内容按对应节填实（目标与现状流程、输入输出、加工流程、业务铁律、人工介入……）；填不了的格保留模板自带的待补注释
- `docs/MEETINGS.md`：intake 来自会议纪要时，把原始纪要归档为第一节；否则保留空骨架
- `docs/DECISIONS.md`：模板自带「Go 基线」首条；步骤 3 若有其他重要拍板（如数据库选 SQLite 的理由），各追加一条 What/Why/Changes
- 非代码产出：`docs/REQUIREMENTS.md` 填产出定位、受众、交付物清单（模板节名如此，没有产品定位 / 目标用户 / 分期路线图）；`docs/DECISIONS.md` 模板自带首条是「材料按代码仓管理」而不是技术栈基线；BUSINESS / MEETINGS 不生成，上面关于它们的两条不适用。

## 步骤 5：收尾

类型为非代码产出时，下面 `git commit -m` 的说明改为「chore: 初始化非代码产出项目骨架（材料 / docs 四件套）」。并且不用代码块里的 `git add -A`：首次提交只 add 落盘清单——逐个文件 `git add .claude/CLAUDE.md AGENTS.md README.md .gitignore docs/PLAN.md docs/Progress.md docs/REQUIREMENTS.md docs/DECISIONS.md 材料/.gitkeep`；add 之前先跑 `find . -path ./.git -prune -o -type f -size +20M -print` 列出目录里已有的大文件，再用 `git -c core.quotePath=false status --porcelain --untracked-files=all` 列出不在落盘清单里的既有文件，两张清单都给用户看过、按仓内硬规则处理（大文件放网盘留链接、含个人信息的不进仓）之后，才按版把它们提交进去。

```bash
set -e
git rev-parse --git-dir >/dev/null 2>&1 || git init -b main
git add -A
git commit -m "chore: 初始化项目脚手架"
git rev-parse HEAD >/dev/null 2>&1 && echo "初始 commit 已产生 ✓" || { echo "⚠ 仓库未建立/未提交，停止"; exit 1; }
```

初始 commit 校验通过后，把 `docs/PLAN.md` 的 Phase 0 标题改为 `## Phase 0：环境与脚手架 ✅ <date +%F 的结果>`；校验未通过则保持原样并在标题后追加 `（未纳入版本控制，待补 git 提交）`。

落盘后**自检**：
```bash
grep -rl '{{' .claude docs README.md 2>/dev/null && echo "⚠ 有未替换占位" || echo "占位全部替换 ✓"
LC_ALL=C grep -rl $'\xef\xbf\xbd' .claude docs README.md 2>/dev/null && echo "⚠ 有乱码" || echo "无乱码 ✓"
```

类型为非代码产出时，两条自检命令的扫描范围加上 `AGENTS.md`：`grep -rl '{{' .claude AGENTS.md docs README.md`，乱码那条同样加。

向用户汇报：生成了哪些文件、技术栈/DB 决策、下一步建议（`/brainstorming` 开始设计——spec 写入后直接 ultracode 实现；小改动也写一份小 spec（几段即可），写完直接做）。

类型为非代码产出时，汇报加一行「类型：非代码产出（材料 / docs 四件套；不生成 CI 与部署）」，技术栈 / DB 决策写「不适用」。

若项目推进中沉淀出可复用的组件/模块（不是本次落盘范围，是给未来的提醒）：**若团队维护组件索引库，登记之**，方便其他项目调研时发现并复用。

## Auto 模式（被 auto-scaffold 常驻规则触发时）

与上面的手动交互流程**并列**，手动流程一字不动。被 auto-scaffold hook 静默触发时，走本节，全程不追问、不发选项：

- **跳过步骤 2 的 intake 追问与七格业务追问、跳过步骤 3 的 AskUserQuestion 确认**——不停下等用户回答，直接用需求句里已有的信息判断；
- **项目类型不问**：需求句明显是培训 / 讲义 / PPT / 报告这类没有代码的产出，走「非代码产出分支」（同样静默，`{{AUDIENCE}}` 与交付物清单能从需求句填的填、填不出留替换表里的待补注释）；拿不准按代码项目——宁可多铺几份代码项目的文档，不可把代码项目铺成材料仓；
- **数据库默认 PostgreSQL**；只有需求句里出现单机 / 离线 / 纯命令行这类明显信号时，才走步骤 3 已有的 SQLite 分支或 CLI 分支，判断理由照常写进 `docs/DECISIONS.md`（步骤 4「内容预填」里对 `docs/DECISIONS.md` 的要求原样适用）；
- `docs/REQUIREMENTS.md` 用需求句直接填实一句话定位与初版需求；`docs/BUSINESS.md` 七格**全部**留模板自带的待补占位注释（不追问，留给后续会话自然补）；`docs/MEETINGS.md` 保持空骨架；
- 步骤 4 的冲突保护在 Auto 模式下简化为 fail-safe：Auto 模式只应在新建空目录里跑，一旦扫到任何 `EXISTS` 文件——**不问跳过/备份/合并，立即降级为交互模式**，绝不静默覆盖；
- 步骤 5 的收尾（`git init -b main` + 初始 commit + 占位符与乱码自检）原样执行；执行完的收尾汇报压缩为一行；
- Auto 是手动流程之外的并列入口，不替代、不改写上面任何步骤的正文。
