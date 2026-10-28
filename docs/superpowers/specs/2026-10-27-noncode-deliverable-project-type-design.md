# 开新项目加「非代码产出」类型:培训、PPT、讲义、报告当仓库管(公开 kit 通用版,2026-10-27)

## 1. 目标覆盖声明

维护者 2026-10-27 答复「继续,可以出」(对「公开 kit 要不要出『非代码产出』通用版」)。本次覆盖目标清单 2026-10-27 这一行。内部工具包 2026-10-26 已有同名功能(含内部项目管理系统登记与公司代码托管组的默认值),本 spec 是它的通用版:**只保留方法论**——项目类型二选一、非代码产出分支的 intake / 落盘清单 / 目录约定 / 仓内硬规则 / 收尾、模板、auto-scaffold 的静默判定;**不带**任何内部登记、组名、主机名、仓内路径。三个面同批:`workflow`(中文)、`workflow-en`(英文)、`workflow-codex`(Codex,中文)。不覆盖:大文件托管方式(写「团队网盘或对象存储」,不指定产品)、材料的版式与命名规范(各项目自定)。

## 2. 规则正文(README.zh-CN.md §六;README.md §6 英译同义)

(第 2、3 节是首版定稿,第 10~13 节的修订覆盖其中对应的句子,以修订节为准。)

### 2.1 §六步骤 2「决策并确认」清单最前面加一条

「- **项目类型**:**代码项目**(默认,下面各项照常)/ **非代码产出**(培训、PPT、讲义、报告、方案文档这类没有代码的交付物)。先单独问这一问;intake 明显是培训 / 讲义 / PPT / 报告的,推荐非代码产出并说明理由。选了非代码产出,下面各项不问、汇报写「不适用」,改走六之五的「非代码产出分支」。」

§六步骤 3 首句「**落盘 11 个文件**(先逐个检查是否已存在,」改为「**落盘 11 个文件**(非代码产出类型改用六之五的清单;先逐个检查是否已存在,」。

### 2.2 新增「### 六之五、非代码产出项目(培训、PPT、讲义、报告)」,放在六之四之后、「## 七、」之前,全文:

培训、PPT、讲义、报告、方案文档这类没有代码的产出,也当仓库管,逐版留档。步骤 2 选了「非代码产出」类型,`/scaffold` 走「非代码产出分支」:Intake 改问产出是什么、给谁、分几个单元、谁交付、首版截止日(信息不够留占位,不逼问);技术栈、数据库、前端、不变量、模块划分都不问,汇报写「不适用」;落盘 8 个文件加 `材料/.gitkeep`(`.claude/CLAUDE.md`、`AGENTS.md`(与 CLAUDE.md 同文,给 Codex 读,改规则时两份一起改)、`README.md`、`.gitignore`、`docs/` 下 PLAN / Progress / REQUIREMENTS / DECISIONS 四件套);**不生成** Dockerfile、CI 配置、`.env.example`、ARCHITECTURE / DEPLOYMENT / BUSINESS / MEETINGS,也不建 `data/`。

1. **目录约定**:`材料/` 放交付物本体,按单元(讲 / 章 / 期)分子目录,培训类单元内再分 `发给学员/`、`讲师用/`、`源文件/`(其他类型按产出物分子目录,README 写清);仓里只留每个文件的最新版,历史版本靠 git 历史,不另存 `v2.3 存档/` 这类目录,也不进 zip。`docs/` 四件套:`PLAN.md`(单元路线与每版计划)、`Progress.md`(**版本日志**:每出一版加一行「版本 | 日期 | 改了什么 | 提交」,最新在上,项目进展据此一眼看清)、`REQUIREMENTS.md`(受众、交付物清单、目标台账)、`DECISIONS.md`(取舍记录)。`README.md` 写项目一句话、受众、目录说明与「网盘链接」表(文件名 | 版本 | 链接 | 日期)。
2. **仓内硬规则**(写进 CLAUDE.md / AGENTS.md,两份同文):每出一版就提交一次,提交说明写「<类型>: <单元或文件> vN——改了什么」(类型用 docs / chore / fix),不许把几版攒成一次提交,提交后 `docs/Progress.md` 版本日志加一行;单个文件超过 20 MB(视频、录音、大 PDF、大图包)不进 git,放团队网盘或对象存储,在 README「网盘链接」表登记文件名、版本、链接、日期,仓里只留链接,提交前跑 `find 材料 -type f -size +20M` 看有没有漏网的;不写密码、令牌、学员与客户的个人信息(姓名加联系方式、证件号、成绩单原文)进仓,示例用虚构数据并标明「虚构」;分支即推,每次 commit 后立即 push,要给别人看的版本标 git tag(`v1`、`v2`……);本项目没有代码、测试与部署,Workflow、评审链、TDD、日志契约不适用,要用 AI 改材料照常在本仓里做,改完按上面提交。
3. **auto-scaffold**:静默铺设时不问类型——需求句明显是培训 / 讲义 / PPT / 报告这类没有代码的产出,按非代码产出分支铺;拿不准按代码项目,宁可多铺几份代码项目的文档,不可把代码项目铺成材料仓。
4. **收尾汇报**加一行「类型:非代码产出(材料 / docs 四件套;不生成 CI 与部署)」;首次提交说明用「chore: 初始化非代码产出项目骨架(材料 / docs 四件套)」。

## 3. `/scaffold` skill 改动(`plugins/workflow/skills/scaffold/SKILL.md`;英文版同义;Codex 版见第 5 节)

1. 「## CLI / 无网络服务分支」节之后、「## 步骤 1」之前,新增一节「## 非代码产出分支(步骤 3 第 0 条选了「非代码产出」时)」,全文:

> 培训、PPT、讲义、报告、方案文档这类没有代码的交付物也当仓库管:材料逐版留档,每版一次提交。选了这个类型,上面的技术栈基线、SQLite 分支、CLI 分支都不适用;步骤 3 第 1~5 条不问、汇报写「不适用」,步骤 2 的 7 格追问换成下面的追问,步骤 4 改用下面的清单。
>
> 1. **Intake 追问**(代替 7 格业务模型):产出是什么(讲义 / PPT / 报告 / 方案)、给谁(受众)、分几个单元(讲 / 章 / 期)、谁交付、首版截止日;信息不够留占位,不逼问。
> 2. **落盘**(模板目录 `templates/noncode/`,8 个文件 + 1 个占位):`.claude/CLAUDE.md`、`AGENTS.md`(与 CLAUDE.md 同文,给 Codex 读;改规则时两份一起改)、`README.md`、`.gitignore`、`docs/PLAN.md`、`docs/Progress.md`、`docs/REQUIREMENTS.md`、`docs/DECISIONS.md`,以及 `材料/.gitkeep`。冲突保护同代码项目(已存在的列出来问,不静默覆盖)。**不生成** Dockerfile、CI 配置、`.env.example`、`docs/ARCHITECTURE.md`、`docs/DEPLOYMENT.md`、`docs/BUSINESS.md`、`docs/MEETINGS.md`,也不建 `data/.gitkeep`。占位符:`{{PROJECT_NAME}}`、`{{ONE_LINER}}`、`{{DATE}}`、`{{AUDIENCE}}`(受众)、`{{DELIVERABLES_BLOCK}}`(交付物清单,intake 填不出就留 `<!-- 待补:交付物清单 -->`)。
> 3. **目录约定**(已写进模板,CLAUDE.md / AGENTS.md / README 三处一致):`材料/` 放交付物本体,按单元分子目录,培训类单元内再分 `发给学员/`、`讲师用/`、`源文件/`(其他类型按产出物分子目录,README 写清),仓里只留每个文件的最新版,历史版本靠 git 历史,不另存 `v2.3 存档/` 这类目录,也不进 zip;`docs/` 是四件套,`Progress.md` 是**版本日志**(每出一版加一行「版本 | 日期 | 改了什么 | 提交」,最新在上;项目进展据此一眼看清;首次那一行的提交列写「首次提交」,之后每行写短 sha);`README.md` 有项目一句话、受众、目录说明与「网盘链接」表(文件名 | 版本 | 链接 | 日期)。
> 4. **仓内硬规则**(CLAUDE.md / AGENTS.md 同文,模板已写):每出一版就提交一次,提交说明写「<类型>: <单元或文件> vN——改了什么」(类型用 docs / chore / fix),不许把几版攒成一次提交,提交后 `docs/Progress.md` 版本日志加一行;单个文件超过 20 MB(视频、录音、大 PDF、大图包)不进 git,放团队网盘或对象存储、在 README「网盘链接」表登记,仓里只留链接,提交前跑 `find 材料 -type f -size +20M`;不写密码、令牌、学员与客户的个人信息进仓,示例用虚构数据并标明「虚构」;分支即推,要给别人看的版本标 git tag(`v1`、`v2`……);本项目没有代码、测试与部署,Workflow、评审链、TDD、日志契约不适用,要用 AI 改材料照常在本仓里做、改完按上面提交。
> 5. **收尾**:汇报加一行「类型:非代码产出(材料 / docs 四件套;不生成 CI 与部署)」;首次提交说明用「chore: 初始化非代码产出项目骨架(材料 / docs 四件套)」;`docs/PLAN.md` Phase 0 标 ✅ 的规则同代码项目。

2. 步骤 2 的 7 格追问清单之前(「在判断技术栈/DB 之外」那段之前)加一条:「- intake 明显是培训 / 讲义 / PPT / 报告这类没有代码的产出时,步骤 3 推荐「非代码产出」类型,追问改用「非代码产出分支」的第 1 条,不用下面的 7 格」。
3. 步骤 3 清单最前面加「0. **项目类型** —— **代码项目**(默认,下面第 1~5 条照常)/ **非代码产出**(培训、PPT、讲义、报告、方案文档等没有代码的交付物)。先**单独**用一次 AskUserQuestion 问(只问这一问,默认代码项目);intake 明显是培训 / 讲义 / PPT / 报告的,推荐非代码产出并说明理由。选了非代码产出,第 1~5 条不问、汇报写「不适用」,改按上面「非代码产出分支」执行;选了代码项目,第 1 条只陈述、第 2~5 条合成第二次 AskUserQuestion 确认」。
4. 步骤 4 首句「先列出将写入的 11 个目标文件,**逐个检查是否已存在**:」改为「先列出将写入的 11 个目标文件(类型为非代码产出时改用「非代码产出分支」第 2 条的清单:8 个文件 + `材料/.gitkeep`,模板在 `templates/noncode/`,不建 `data/.gitkeep`),**逐个检查是否已存在**:」。模板路径映射那段末尾加一句「非代码产出:`templates/noncode/docs/X.md.tmpl` → `docs/X.md`,`templates/noncode/CLAUDE.md.tmpl` → `.claude/CLAUDE.md`,`templates/noncode/AGENTS.md.tmpl` → `AGENTS.md`,`templates/noncode/README.md.tmpl` → `README.md`,`templates/noncode/gitignore.tmpl` → `.gitignore`;另建 `材料/.gitkeep`。」
5. 步骤 5 收尾代码块之后加一段:「类型为非代码产出时,提交说明改为「chore: 初始化非代码产出项目骨架(材料 / docs 四件套)」;汇报加一行「类型:非代码产出(材料 / docs 四件套;不生成 CI 与部署)」,技术栈 / DB 决策写「不适用」。」
6. 「## Auto 模式」节加一条(放在「数据库默认 PostgreSQL」那条之前):「- **项目类型不问**:需求句明显是培训 / 讲义 / PPT / 报告这类没有代码的产出,走「非代码产出分支」(同样静默,`{{AUDIENCE}}` 与交付物清单能从需求句填的填、填不出留占位);拿不准按代码项目——宁可多铺几份代码项目的文档,不可把代码项目铺成材料仓;」。
7. `hooks/auto-scaffold.md`「触发后动作」第 3 条括注里「技术栈走基线不询问;」之后加「需求句明显是培训 / 讲义 / PPT / 报告这类没有代码的产出,走它的「非代码产出分支」,拿不准按代码项目;」。
8. 模板 `templates/noncode/`(8 个文件):`CLAUDE.md.tmpl`、`AGENTS.md.tmpl`(两份逐字相同)、`README.md.tmpl`、`gitignore.tmpl`、`docs/PLAN.md.tmpl`、`docs/Progress.md.tmpl`、`docs/REQUIREMENTS.md.tmpl`、`docs/DECISIONS.md.tmpl`。以内部工具包的同名模板为底稿(内部路径只写在派工简报里,不进本仓;只读),做且只做这几处改动:① 删掉 `CLAUDE.md.tmpl` / `AGENTS.md.tmpl` 第一行的 HTML 注释(关于内部登记行的那句);② 「公司网盘」→「团队网盘或对象存储」(三处:CLAUDE / AGENTS 第 2 条、README 规则);③ 「身份证」→「证件号」(CLAUDE / AGENTS 第 3 条);④ `Progress.md.tmpl` 引言「项目进展据此生成。」→「项目进展据此一眼看清。」;⑤ 全文 grep 确认没有内部系统名、公司名、组名、主机名(应为 0)。其余逐字保留(含全角标点)。

## 4. 英文面(`README.md` §6 与 `plugins/workflow-en/`)

与第 2、3 节同义英译,不新增、不删减要点。固定译法:非代码产出 → non-code deliverable;`材料/` → `materials/`;`发给学员/` → `for-students/`;`讲师用/` → `for-instructors/`;`源文件/` → `source/`;「网盘链接」表 → "Large files" table(列 File | Version | Link | Date);团队网盘或对象存储 → team file share or object storage;版本日志 → version log;四件套 → the four-doc set;每出一版就提交一次 → one commit per version;`find materials -type f -size +20M`;六之五 → 6e;「非代码产出分支」→ "Non-code deliverable branch";首次提交说明 → `chore: initialize non-code deliverable project skeleton (materials / four-doc set)`;收尾那一行 → `Type: non-code deliverable (materials / four-doc set; no CI or deployment generated)`。英文模板 `plugins/workflow-en/skills/scaffold/templates/noncode/` 8 个文件按中文模板逐段翻译,`CLAUDE.md.tmpl` 与 `AGENTS.md.tmpl` 逐字相同,占位符名不变;英文 `hooks/auto-scaffold.md` 第 3 条同义加半句。英文 README 的目录树里 `templates/ (11 templates)` 改为 `templates/ (11 templates + noncode/ 8 non-code deliverable templates)`。

## 5. Codex 面(`plugins/workflow-codex/skills/scaffold/`)

同第 3 节,差别只有:没有 `.claude/CLAUDE.md`——落盘清单是 7 个文件 + `材料/.gitkeep`(`AGENTS.md`、`README.md`、`.gitignore`、docs 四件套),模板 `templates/noncode/` 7 个文件(无 `CLAUDE.md.tmpl`;`AGENTS.md.tmpl` 内容同中文版 CLAUDE.md.tmpl;`docs/PLAN.md.tmpl` 里「`.claude/CLAUDE.md` + `AGENTS.md` + README」改成「`AGENTS.md` + README」);文中「AskUserQuestion」按该 skill 现有写法改成 Codex 的提问方式(照该文件步骤 3 现有措辞);「## Auto 模式与常驻安装(可选)」里给用户粘贴的规则片段第 3 条「技术栈走基线不询问;」之后同样加「需求句明显是培训 / 讲义 / PPT / 报告这类没有代码的产出,走本 skill 的「非代码产出分支」,拿不准按代码项目;」。README.zh-CN.md 目录树里 Codex 那行「铺 AGENTS.md + 八件套(无 CLAUDE.md.tmpl)」后加「;templates/noncode/ 非代码产出 7 个模板」,中文 `templates/(11 个模板)` 改为 `templates/(11 个模板 + noncode/ 8 个非代码产出模板)`;英文 README 对应两行同改。

## 6. 版本与登记

`plugins/workflow` 与 `plugins/workflow-en` 的 `plugin.json` 0.22.1 → 0.23.0;`plugins/workflow-codex/.codex-plugin/plugin.json` 0.19.1 → 0.20.0;`.claude-plugin/marketplace.json` 里 workflow 的描述「/scaffold 文档脚手架」改「/scaffold 文档脚手架(代码项目 / 非代码产出两类)」,workflow-en 的「/scaffold doc scaffolding」改「/scaffold doc scaffolding (code or non-code deliverable projects)」。`docs/PLAN.md` Spec 索引加一行;`docs/Progress.md` 总览两行版本号与变更日志条目;`docs/REQUIREMENTS.md` 目标清单那行收尾标 done。

## 7. 容易漏的输入与失败情形

- 用户在 intake 说的是「做一个培训网站 / 课程平台」:这是代码项目(交付物是程序),不是非代码产出;步骤 3 第 0 条的推荐只看交付物是不是文件,措辞里「没有代码的交付物」已点明,评审核对 README 与 skill 两处措辞一致。
- auto-scaffold 静默判错类型:规则定为拿不准按代码项目,代价是多几份文档;反向(把代码项目铺成材料仓)不可接受,正文已写明。
- 文件刚好 20 MB:规则说「超过 20 MB」,`find -size +20M` 的语义也是严格大于,两处一致。
- 在已有材料的目录里跑非代码产出分支:首次提交只 add 落盘清单,既有文件与大文件先列给用户、按硬规则分版提交(第 12 节第 1 条);否则 `git add -A` 会把大文件与个人信息一次推进远端历史。
- 已检查,没有别的。

## 8. 验收

三个面各自:README 新节 / 步骤 2 新条 / 步骤 3 括注在;scaffold SKILL 六处改动在、新节在「CLI / 无网络服务分支」与「步骤 1」之间;`templates/noncode/` 文件数(zh / en 各 8,codex 7),CLAUDE 与 AGENTS 模板 `cmp` 相同(zh / en);模板与新文字全文 grep 内部系统名、公司名、组名、主机名 0 处;hooks/auto-scaffold.md 第 3 条新半句在(zh / en);版本号与 marketplace 描述改到;英文面译法与第 4 节固定译法一致、要点数与中文相同;Codex 面清单为 7 文件 + 占位。评审:盲审 2 个 `opus` + `medium`(机器负载高时顺序跑),无 P0/P1 且无矛盾即通过;有 P1 修复后 1 轮 `opus` + `high` 裁决。

## 9. 回滚

纯文档与模板:revert 各单元提交;版本号只升不降,回滚时在下一版说明撤回;revert 之后版本号再升一个补丁号(0.23.1 / 0.20.1),marketplace 描述随 revert 退回,照 2026-10-26 撤回 API key 小节的做法。

## 10. 修订 1(2026-10-27):盲审的修复

盲审(2 个 `opus` + `medium`,顺序跑)。P0 一条:中文面提交 0ba92cb 随提交的本 spec 第 3 节第 8 条写着内部工具包的本机绝对路径(含本机用户名与内部插件名),且该提交已推到公开仓的 wip 分支;工作树里已改成「内部路径只写在派工简报里,不进本仓」但没提交。P1 一条(同一处):改后的句子仍带着内部概念的字样(详见派工简报)。P2 四条:「方案」只出现在 scaffold 步骤 2 新条的触发清单里,步骤 3 第 0 条 / README 六之五 / Auto 模式 / hook 的清单都没有,三个面相同;步骤 4 存在性检查循环与步骤 5 自检命令只覆盖代码项目路径(AGENTS.md、`材料/` 不在扫描范围);Codex PLAN 模板那一句差异没写进第 5 节;Progress 总览 Codex 行「同日加」会被读成 10-26。修复:

1. 本 spec:第 3 节第 8 条①去掉内部概念字样(已改成「关于内部登记行的那句」);第 3 节第 2 条引文里「培训 / 讲义 / PPT / 报告 / 方案这类」改为「培训 / 讲义 / PPT / 报告这类」;第 5 节「`AGENTS.md.tmpl` 内容同中文版 CLAUDE.md.tmpl)」之后补一句「;`docs/PLAN.md.tmpl` 里「`.claude/CLAUDE.md` + `AGENTS.md` + README」改成「`AGENTS.md` + README」」。这些与第 8 条已做的去路径改动一起 `--squash=0ba92cb`。
2. 三个 scaffold SKILL(zh / en / codex)步骤 2 的新条:去掉「/ 方案」(英文去掉对应的 "/ a proposal" 或同义词),使触发清单与步骤 3 第 0 条、README、Auto 模式、hook 一致(都只列培训 / 讲义 / PPT / 报告;类型定义里的「方案文档」是定义,不动)。
3. 三个 scaffold SKILL 步骤 4:存在性检查的代码块之后加一句「类型为非代码产出时,循环里的清单换成 `.claude/CLAUDE.md AGENTS.md README.md .gitignore docs/PLAN.md docs/Progress.md docs/REQUIREMENTS.md docs/DECISIONS.md 材料`(Codex 版去掉 `.claude/CLAUDE.md`)。」(英文同义:`materials`)。步骤 5 自检的代码块之后加一句「类型为非代码产出时,两条自检命令的扫描范围加上 `AGENTS.md`:`grep -rl '{{' .claude AGENTS.md docs README.md`,乱码那条同样加(Codex 版本来就扫 `AGENTS.md` 的不用加)。」。
4. `docs/Progress.md` 总览 workflow-codex 行「0.20.0;同日加「非代码产出」项目类型」改为「0.20.0;2026-10-27 加「非代码产出」项目类型」。
5. 提交归位:第 1 条与 zh SKILL 的改动 `--squash=0ba92cb`;en SKILL 的改动 `--squash=f755f6a`;codex SKILL 与 Progress 的改动 `--squash=f1681ba`。并 main 前 autosquash 后 `--force-with-lease` 重推 wip 分支(0ba92cb 的旧对象在远端仍可按 sha 取到,要不要进一步清理由维护者定)。

验收:spec 全文按派工简报的敏感词表(本机路径、内部概念、公司 / 系统 / 组 / 主机名)grep 0;三个 SKILL 步骤 2 新条无「方案」/「proposal」;三个 SKILL 步骤 4、5 各多一句;Progress 那行日期对;其余文件不动。评审:P0 修复后先 1 轮 `opus` + `medium` 续挖(换镜头),再 1 轮 `opus` + `high` 裁决。

## 11. 修订 2(2026-10-27):续挖轮的修复

续挖(1 个 `opus` + `medium`,镜头:spec 验收覆盖 + 可执行性)。P0 闭合(spec 文本内部词 0),P1 一条:修复提交 21de793 的提交说明里又出现了那个内部概念词,autosquash 后会进公开 main 的单元提交正文——收尾时在重放单元提交时改写说明(主对话做,不在本节)。P2 六条,修法:

1. `docs/Progress.md` 总览 workflow-codex 行里「同日加的 API key 模板改动已撤回」改为「2026-10-26 加的 API key 模板改动已撤回」。
2. 三面 scaffold SKILL「非代码产出分支」第 1 条「Intake 追问」里被修订 1 误删的产出类别恢复:zh / codex 恢复为「产出是什么(讲义 / PPT / 报告 / 方案)」,en 恢复原译(含 proposal);修订 1 只要求改步骤 2 的触发清单,Intake 问的是产出类别,与 REQUIREMENTS 模板「形式」列一致。
3. 三面 scaffold SKILL 步骤 4 占位符替换表补两行:「`{{AUDIENCE}}` | intake「给谁」;填不出留 `<!-- 待补:受众 -->`」「`{{DELIVERABLES_BLOCK}}` | intake 的交付物清单;填不出留 `<!-- 待补:交付物清单 -->`」(en:`<!-- TBD: audience -->`、`<!-- TBD: deliverables list -->`);Auto 模式「项目类型不问」那条里「填不出留占位」改为「填不出留替换表里的待补注释」(en 同义)。
4. 三面 scaffold SKILL 步骤 5:在收尾代码块**之前**加一句「类型为非代码产出时,下面 `git commit -m` 的说明改为「chore: 初始化非代码产出项目骨架(材料 / docs 四件套)」。」;代码块之后原来那段里关于提交说明的半句删掉,只留「汇报加一行「类型:非代码产出(材料 / docs 四件套;不生成 CI 与部署)」,技术栈 / DB 决策写「不适用」。」(en / codex 同义;codex 的提交说明句同样挪到代码块前)。
5. 三面 scaffold SKILL 步骤 4「内容预填」清单末尾加一条:「- 非代码产出:`docs/REQUIREMENTS.md` 填产出定位、受众、交付物清单(模板节名如此,没有产品定位 / 目标用户 / 分期路线图);`docs/DECISIONS.md` 模板自带首条是「材料按代码仓管理」而不是技术栈基线;BUSINESS / MEETINGS 不生成,上面关于它们的两条不适用。」(en 同义;codex 同 zh)。
6. 本 spec 第 10 节第 1 条里「「关于内部登记行的那句」改为「关于内部登记行的那句」」改写成「第 3 节第 8 条①去掉内部概念字样(已改成「关于内部登记行的那句」)」。

提交归位:spec 与 zh SKILL `--squash=0ba92cb`;en SKILL `--squash=f755f6a`;codex SKILL 与 Progress `--squash=f1681ba`。验收:Progress 那行「2026-10-26 加的 API key」1、「同日」0;三面 Intake 第 1 条含「方案」/ proposal 各 1;替换表 `{{AUDIENCE}}` 行与 `{{DELIVERABLES_BLOCK}}` 行各 1;步骤 5 代码块前的非代码提交说明句 1、代码块后不再含「chore: 初始化非代码产出」;内容预填非代码条 1;spec 第 10 节第 1 条新措辞 1;三个 squash 提交说明里无内部概念词。评审:1 轮 `opus` + `high` 裁决。

## 12. 修订 3(2026-10-27):裁决轮(第 3 轮)的修复

裁决(`opus` + `high`,镜头:回滚与可逆性 + 对抗反驳)判 FAIL:续挖那条 P1(squash 提交说明含内部概念词)还没改;新 P1 一条:非代码产出分支在**已有材料的目录**里铺设时,步骤 5 的 `git add -A` 会把目录里原有的大文件与含个人信息的文件放进首次提交,硬规则又要求 commit 后立即 push,进了远端历史只能改写历史才能清;P2 五条:大文件检查命令只扫 `材料/`;误提交后怎么撤没写;`git push` 默认不推 tag;版本日志的「提交」列要填本版 sha 却又要求提交后再加行(每版多一处未提交改动);回滚节没说 revert 后版本号要再升一个补丁号。修法:

1. 三面 scaffold SKILL 步骤 5,「类型为非代码产出时,下面 `git commit -m` 的说明改为…」那句之后接着写:「并且不用代码块里的 `git add -A`:首次提交只 add 落盘清单——`git add .claude AGENTS.md README.md .gitignore docs 材料/.gitkeep`(Codex 版去掉 `.claude`;en 用 `materials/.gitkeep`);add 之前先跑 `find . -path ./.git -prune -o -type f -size +20M -print` 列出目录里已有的大文件,再用 `git status --porcelain` 列出不在落盘清单里的既有文件,两张清单都给用户看过、按仓内硬规则处理(大文件放网盘留链接、含个人信息的不进仓)之后,才按版把它们提交进去。」三面「非代码产出分支」第 5 条「收尾」开头加半句「首次提交只 add 落盘清单,目录里既有的文件先列给用户看(做法见步骤 5);」。
2. 大文件检查命令统一改为 `find . -path ./.git -prune -o -type f -size +20M -print`:三面 `templates/noncode/` 的 CLAUDE / AGENTS(硬规则第 2 条)与 README(规则)模板、三面 SKILL「非代码产出分支」第 4 条、README.zh-CN 六之五第 2 条、README.md 6e 第 2 条里原来的 `find 材料 -type f -size +20M`(en `find materials -type f -size +20M`)全部替换。
3. 同一批位置(三面 CLAUDE / AGENTS 模板硬规则第 2 条末尾、三面 SKILL 第 4 条大文件句末尾、README 六之五 / 6e 第 2 条大文件句末尾)补一句「误把大文件或个人信息提交了:还没 push 的用 `git rm --cached <文件>` 再 `git commit --amend`;已 push 的要改写历史并通知所有协作者,所以提交前先查」。README 模板「规则」第 2 条同样补。
4. 三面 CLAUDE / AGENTS 模板硬规则第 4 条「分支即推」末尾、三面 SKILL 第 4 条 tag 句末尾、README 六之五 / 6e 第 2 条 tag 句末尾补「;打 tag 后 `git push origin vN`(`git push` 默认不推 tag);仓库还没有远端时先建远端,建好前 push 失败不算提交失败」。
5. 版本日志的时机与「提交」列:三面 CLAUDE / AGENTS 模板硬规则第 1 条里「提交后在 `docs/Progress.md` 版本日志加一行「版本 | 日期 | 改了什么 | 提交」,最新在上」改为「提交前先在 `docs/Progress.md` 版本日志加一行「版本 | 日期 | 改了什么 | 提交」(最新在上;「提交」列填该版的 tag 名如 `v3`,不打 tag 的版本先留空、提交后补短 sha 随下一次提交带上),与材料一起提交」;三面 `docs/Progress.md.tmpl` 引言里「「提交」列填提交短 sha(首次那一行固定写「首次提交」)」改为「「提交」列填该版的 tag 名,不打 tag 的版本先留空、提交后补短 sha 随下一次提交带上(首次那一行固定写「首次提交」)」;三面 SKILL 第 3 条「首次那一行的提交列写「首次提交」,之后每行写短 sha」改为「首次那一行的提交列写「首次提交」,之后每行写该版 tag 名,不打 tag 的先留空、提交后补短 sha 随下一次提交带上」,第 4 条「提交后 `docs/Progress.md` 版本日志加一行」改为「提交前 `docs/Progress.md` 版本日志先加一行、与材料一起提交」;README 六之五 / 6e 第 1、2 条里同样的两处同改(第 1 条「每出一版加一行」句不变,只改第 2 条「提交后 … 加一行」为「提交前 … 先加一行、一起提交」);README 模板「规则」第 1 条同改;三面 CLAUDE / AGENTS 模板「目录约定」里 `docs/Progress.md` 的说明若写了「提交后」也同改。英文面同义英译(tag name / leave blank / fill in the short sha with the next commit)。
6. 本 spec 第 9 节回滚末尾补「;revert 之后版本号再升一个补丁号(0.23.1 / 0.20.1),marketplace 描述随 revert 退回,照 2026-10-26 撤回 API key 小节的做法」;第 7 节「容易漏的输入与失败情形」加一条「- 在已有材料的目录里跑非代码产出分支:首次提交只 add 落盘清单,既有文件与大文件先列给用户、按硬规则分版提交(第 12 节第 1 条);否则 `git add -A` 会把大文件与个人信息一次推进远端历史。」并把「已检查,没有别的」保留在末尾。

提交归位:spec、zh SKILL、zh 模板、README.zh-CN `--squash=0ba92cb`;en SKILL、en 模板、README.md `--squash=f755f6a`;codex SKILL 与 codex 模板 `--squash=f1681ba`。提交说明不许出现内部概念词与内部实名。验收:`find 材料 -type f -size +20M` 与 `find materials -type f -size +20M` 全仓新增文字里 0 处;新命令在 zh / en / codex 模板与 SKILL、两份 README 里都在;三面 CLAUDE 与 AGENTS 模板仍 cmp 相同,Codex AGENTS 与 zh CLAUDE 相同;步骤 5 非代码 add 清单句三面各 1;撤销句、tag push 句、版本日志时机句三面各在;spec 第 7、9 节补句在。评审:autosquash 并改写单元提交说明后 1 轮 `opus` + `high` 裁决(链第 4 轮,上限内)。

## 13. 修订 4(2026-10-27):第 4 轮裁决的修复

第 4 轮裁决(`opus` + `high`,镜头:安全)判 FAIL:第 3 轮那条 P1 只闭合了一半——第 12 节第 1 条的 `git add … docs 材料/.gitkeep` 按目录整体 add,目录里原有的 `docs/`、`.claude/` 内容会一起进首次提交;配套的 `git status --porcelain` 默认把未跟踪目录折叠成 `?? docs/`,给用户看的既有文件清单里看不到它们(裁决轮在临时目录实测:docs/学员名单.xlsx 照规则进了暂存区、清单里没有)。P2 五条:目标台账「原话(尽量照录)」会把对话里的个人信息照录进仓;误提交句没说密码、令牌要先作废换新;文档提交 b63f286 的说明写「标 done」但那行还是 doing;第 2、3 节是首版定稿、没注明以修订节为准;README 六之五 / 6e 第 4 条没提首次提交只 add 落盘清单。修法:

1. 三面 scaffold SKILL 步骤 5 的非代码 add 句:`git add .claude AGENTS.md README.md .gitignore docs 材料/.gitkeep` 改为逐个文件 `git add .claude/CLAUDE.md AGENTS.md README.md .gitignore docs/PLAN.md docs/Progress.md docs/REQUIREMENTS.md docs/DECISIONS.md 材料/.gitkeep`(Codex 版去掉 `.claude/CLAUDE.md`;en 用 `materials/.gitkeep`);同句里 `git status --porcelain` 改为 `git -c core.quotePath=false status --porcelain --untracked-files=all`(主对话实测:不加 `-c core.quotePath=false` 时中文文件名按八进制转义显示,用户认不出)。第 12 节第 1 条的命令以本节为准。
2. 三面 `templates/noncode/docs/REQUIREMENTS.md.tmpl` 目标台账的引言(「对话/会议里冒出来的每一条…」那段)末尾补一句「原话里的密码、令牌、学员与客户的个人信息改写成占位再登记(硬规则第 3 条)。」(en 同义)。
3. 误提交句(三面 CLAUDE / AGENTS 模板硬规则第 2 条、README 模板规则第 2 条、三面 SKILL 第 4 条、README 六之五 / 6e 第 2 条)里「已 push 的要改写历史并通知所有协作者,所以提交前先查」改为「已 push 的要改写历史并通知所有协作者;误提交的密码、令牌先作废换新,改写历史收不回已被拉取的值,所以提交前先查」(en 同义)。
4. 本 spec 第 2 节标题下加一行「(第 2、3 节是首版定稿,第 10~13 节的修订覆盖其中对应的句子,以修订节为准。)」。
5. README.zh-CN 六之五第 4 条、README.md 6e 第 4 条开头补「首次提交只 add 落盘清单,目录里既有文件先列给用户看(做法见 `/scaffold` 非代码产出分支);」(en 同义)。
6. 文档提交 b63f286 的说明与台账状态不一致:收尾第二个文档提交把那行标 done 并在说明里注明,不改写已推的历史。

提交归位:spec、zh SKILL、zh 模板、README.zh-CN `--squash=109062a`;en SKILL、en 模板、README.md `--squash=1e71017`;codex SKILL 与 codex 模板 `--squash=60882b6`。验收:三面 add 句逐个文件、`--untracked-files=all` 各 1;`git add .claude AGENTS.md` 与 `git add AGENTS.md README.md .gitignore docs ` 0 处;台账补句三面各 1;作废换新句在上述各处;spec 第 2 节注一行;README 两处第 4 条补句;三组模板 cmp 相同。评审:评审链已满 4 轮上限;这条 P1 是命令写法的机械修正,由主对话用 grep 与临时目录实测核对闭合,不再开第 5 轮(原因记进评审链)。
