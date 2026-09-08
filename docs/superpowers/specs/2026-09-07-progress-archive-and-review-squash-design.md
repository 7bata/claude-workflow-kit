# 进度日志按月归档 + 评审轮次压进单元提交 — 设计

日期:2026-09-07 · 状态:Tony 已拍板(「好」),按 kit §七 直接实现

## 0. 目标覆盖声明

- 覆盖 `docs/REQUIREMENTS.md` 目标清单 2026-09-07 条(「你看一下这个是什么问题」+ stella 八月代码量审查诊断)里 Tony 拍板的两项:①进度日志按月归档只留最近的;②评审轮次的修改在合并前压成一个提交。
- 不覆盖:③是否加「测试复用」规则(等档位校准数据出来再定);commit-gate「每次源码提交都要动 Progress.md」的频率本身(Tony 没有拍板改);stella 仓现存 9,380 行 Progress.md 的实际归档动作(属于 stella 项目窗口的事,规则并入后由它自己执行一次)。

## 1. 背景与依据

对 stella 八月历史的核对(本仓 REQUIREMENTS 2026-09-07 条有完整数据):

- 八月 docs 类提交 241 条,居各类之首(fix 235、feat 198);`docs/Progress.md` 9,380 行、385 条日志、月内被改 208 次。根源是 kit 模板 §1「每完成一个操作补一条变更日志」+ commit-gate「staged 含源码必须动 Progress.md」;而 `/whats-next` 只读最近 2~3 条,其余从不被读却每次整读都占上下文。
- fix 235 条里至少 77 条标题写明是评审打回/复审/终验的某一轮;一个单元跑三四轮就留三四条 fix。这是流程形态问题:评审循环本该是单元内部的过程,却以独立 commit 进了 main,让「三分之一提交在返工」这个假象出现,也让档位表规则 4 需要的「按单元的打回率」无法从历史里直接算。

## 2. 规则 A:进度日志按月归档

**规则正文(权威中文措辞,各镜像逐字或按各自段落体例改写,语义不变):**

> **变更日志按月归档**:`docs/Progress.md` 的「变更日志」只保留**当月**条目;每个月第一次批次收尾时,把上个月(及更早)的条目整体剪切到 `docs/archive/Progress-<YYYY-MM>.md`(按条目日期分月,文件格式与主文件的日志段相同、最新在上,首次创建时加一行 `# Progress 归档 — <YYYY-MM>` 标题),主文件「变更日志」标题下保留一行归档索引:`> 更早的日志按月在 docs/archive/Progress-YYYY-MM.md`。「进度总览」状态表不归档。归档动作单独一个 `docs:` 提交,不与源码混提交。读取规则不变:回到项目只读主文件最近 2~3 条;需要追溯历史时才去 archive。

要点:

- 触发点固定在「每月第一次批次收尾」,一个月只动一次,避免每次收尾都剪几条造成新的 docs 抖动。当月内主文件不封顶(条目长度是另一根杠杆,本批不动)。
- 分月依据是条目标题里的日期(`### 2026-08-14 …` / `### [2026-08-14] …` 两种模板体例都有),不按 git 时间。
- `docs/archive/` 目录只放归档文件;`.gitignore` 不变(归档入 git)。
- commit-gate(层 3)不改:它只看 `docs/Progress.md` 有没有被碰,归档提交本身不含源码,不会被拦。
- `/whats-next`(及内部版 `/stellark-whats-next`)读取步骤加一句「更早月份在 `docs/archive/Progress-YYYY-MM.md`,需要追溯历史时才读」。

## 3. 规则 B:评审轮次压进单元提交

**规则正文(权威中文措辞):**

> **评审轮次压进单元提交**:一个单元的首个提交照常 `feat:`/`fix:`;之后评审打回、复审、终验产生的修复,提交时用 `git commit --squash=<该单元首个提交的 sha> -m "评审第 N 轮:<改了什么>"`(仍然每次 commit 后立即 push,备份不变)。并 main 前、门禁判定之前,主对话在 wip 分支上跑 `GIT_EDITOR=true git rebase --autosquash main`,把各轮压进对应单元提交(轮次说明自动进提交正文),再 `git push --force-with-lease origin <wip 分支>`,然后照常 merge。`--force-with-lease` 只许在这一步、只对自己的 wip 分支用;main 与共享分支照旧禁止 force push,实现 agent 的红线不变(这一步由主对话在收尾做,不派发)。单元已并 main 之后由真机/线上反馈引出的修复,照常独立 `fix:` 提交——那才是真返工,统计上应当看得见。评审轮次也不在 `docs/Progress.md` 新开日志条目,追加到该单元条目末尾一行「评审 N 轮:…」。

要点:

- 已在临时仓实测(git 2.53):`git commit --squash=<sha>` 生成 `squash! <原标题>` 提交;`GIT_EDITOR=true git rebase --autosquash main` 非交互完成,结果是一个提交,正文依次含各轮 `-m` 文本;`--fixup=` 会丢掉轮次说明,所以规则用 `--squash=`。
- worktree-sweep hook 的「已并 main」判定用 `merge-base --is-ancestor`,autosquash 后再 `merge --no-ff` 分支仍是 main 的祖先,hook 不受影响(已核对 `worktree-sweep.sh` 第 134 行)。若改用 `git merge --squash` 则判定失效,故不采用。
- 副产品:压完之后 `git log --format=%B | grep -c '^评审第'` 就能按单元数出评审轮次,正是档位表规则 4「打回率 >30% 升起跑档」要的口径,以后校准直接从历史取数。
- Codex 版:git 命令与流程完全相同,措辞去掉「主对话/派发」这类 Claude 编排词,改为「收尾时由你自己做」。

## 4. 镜像位置(实现单元)

每个单元只改自己名下的文件,不碰别的;不做任何 git 操作(commit/push 由主对话统一做);不改 hook 脚本;不改 dev-toolkit 的 `plugin.json`(CI 自动升版)。

| 单元 | 仓库 | 文件 | 版本 |
|---|---|---|---|
| U1 kit 中文 | claude-workflow-kit | `README.zh-CN.md`(§四 docs 表 Progress 行与六节 docs 八件套 Progress 行加「只留当月,更早按月在 docs/archive/」;§五 新增第 5 条=规则 B;§七 第 5 步收尾句加「每月第一次收尾做归档」与「并 main 前先 autosquash」;§九 第 2 步加归档说明)、`plugins/workflow/skills/scaffold/templates/CLAUDE.md.tmpl`(§1 第 1 条尾加「评审轮次不新开条目」;§1「一个操作」段后加规则 A 一段;§5.1 新增第 5 条=规则 B;禁止事项加两行)、`plugins/workflow/skills/scaffold/templates/docs/Progress.md.tmpl`(头注加归档说明;变更日志标题下加归档索引行)、`plugins/workflow/skills/whats-next/SKILL.md`(第 16 行加归档读法)、`plugins/workflow/.claude-plugin/plugin.json` 0.10.0→0.11.0 | 0.11.0 |
| U2 kit 英文 | claude-workflow-kit | `README.md`、`plugins/workflow-en/…` 同 U1 对应位置,英文手译,术语与现有英文版一致(Changelog / Progress Overview / wip branch / main is gated) | 0.11.0 |
| U3 kit codex | claude-workflow-kit | `plugins/workflow-codex/skills/scaffold/templates/AGENTS.md.tmpl`、`…/templates/docs/Progress.md.tmpl`、`…/skills/whats-next/SKILL.md`、`plugins/workflow-codex/.codex-plugin/plugin.json` 0.10.7→0.11.0;措辞按 §3 Codex 版口径 | 0.11.0 |
| U4 dev-toolkit | Platform/dev-toolkit | `WORKFLOW.md`(§五 第 5 条、§六 Progress 行、§七 第 5 步、§九 第 2 步)、`plugins/dev-toolkit/skills/stellark-workflow/SKILL.md`(同上四处)、`plugins/dev-toolkit/skills/stellark-scaffold/templates/CLAUDE.md.tmpl`、`…/templates/docs/Progress.md.tmpl`、`plugins/dev-toolkit/skills/stellark-whats-next/SKILL.md` | CI 自动 |
| U5 huake claude | Platform/claude-toolkit-engineer | `plugins/claude-toolkit-engineer/skills/scaffold/templates/CLAUDE.md.tmpl`、`…/templates/docs/Progress.md.tmpl`、`…/skills/whats-next/SKILL.md`、`plugins/claude-toolkit-engineer/.claude-plugin/plugin.json` 0.22.0→0.23.0、`README.md` 末尾追加「0.23.0 起同步 …」记录段(体例同 0.22.0 段) | 0.23.0 |
| U6 huake codex | Platform/codex-toolkit-engineer | `plugins/codex-toolkit-engineer/skills/scaffold/templates/AGENTS.md.tmpl`、`…/templates/docs/Progress.md.tmpl`、`…/skills/whats-next/SKILL.md`、`plugins/codex-toolkit-engineer/.codex-plugin/plugin.json` 0.10.5→0.11.0 | 0.11.0 |
| U7 本机全局 | `~/.claude-profiles/tech/CLAUDE.md` | §Git push 策略新增第 5 条=规则 B(2026-09-07 入表);§Brainstorming→Ultracode 第 3 步收尾句加「每月第一次收尾归档 Progress」 | 主对话自己改 |

## 5. 验收

- 每个单元的每处镜像都能在文件里找到规则 A、规则 B 的对应文字(grep「按月归档」「--squash=」或英文对应词);版本号按表升。
- 规则 B 文字里必须同时出现:`--squash=`、`GIT_EDITOR=true git rebase --autosquash main`、`--force-with-lease`、「只对自己的 wip 分支」、「main 禁止 force push 不变」、「已并 main 后的反馈修复照常独立 fix」。
- 规则 A 文字里必须同时出现:「只保留当月」、「每月第一次批次收尾」、`docs/archive/Progress-<YYYY-MM>.md`、「进度总览不归档」、「单独一个 docs 提交」。
- 未改动的段落逐字不变(评审用 git diff 核对没有顺手改别处);表格/编号/列表格式没坏;英文版无中文残留。
- 本仓收尾:PLAN.md 当前状态与 Spec 索引、Progress.md 状态表与日志、REQUIREMENTS 2026-09-07 条改 done 附提交号;DECISIONS.inbox 两条 9 月 5 日旧草稿(已在目标清单)清空。
