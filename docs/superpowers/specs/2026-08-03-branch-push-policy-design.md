# push 策略:分支即推 + main 门禁 — Design Spec

> 2026-08-03 ｜ 状态:已获批 ｜ 动机:现行规则「未确认不许 git push」意味着本地电脑损坏时未推送工作全部丢失。

## 新策略(三条核心规则)

1. **分支即推**:日常开发一律在 feature/wip 分支进行;**每次 commit 后立即 push 当前分支到远端,无需确认**——这就是实时异地备份。worktree 流程(superpowers:using-git-worktrees)天然满足"每任务一分支";在主 checkout 上做散活时,动手前先切/建 wip 分支。
2. **main 门禁**:确认点从 push 挪到**并入默认分支**。merge 进 main(或直接在 main 上 commit)必须先获用户确认;确认后 push main + 删除已合并的远端 feature 分支。
3. **无远端兜底**:仓库没有 remote(或分支没有 upstream)时,首次 commit 后提醒用户建远端(内部项目指向 gitlab.stellark.io,个人备份可用 StellarkTony 组),避免"自动 push"静默失效。

安全依据:各项目 CI 已核实 test 任何分支都跑、build/deploy 仅默认分支触发,分支 push 不会误部署。

## 改动清单

### 1. `templates/CLAUDE.md.tmpl`(开源中文版,其余三处同步)

- §1 核心工作流第 1 步改为:「Commit 代码并 push 当前分支 — 原子 commit;**commit 后立即 `git push` 当前 feature/wip 分支(无需确认;无 upstream 时 `-u` 建立)**」
- §5 Git 提交规范加两条:「日常开发不在 main/默认分支上直接 commit;开工先切分支(worktree 流程自动满足)」「merge 进 main 获确认后:push main + 删除远端 feature 分支」
- 「禁止事项」替换:删「在没确认的情况下 git push 到远端」,改为「**在没确认的情况下把改动并入 main/默认分支(merge 或直接 commit)**」
- 新增小节「Git 分支与备份策略」collect 上述三条核心规则 + 无远端兜底提醒

### 2. 同步范围(先盘点再改)

实现第一步:`grep -rn "push\|确认" 各处模板与 skill`,列出实际措辞清单再逐处改,防漏:

| 位置 | 内容 |
|---|---|
| `claude-workflow-kit/plugins/workflow` + `workflow-en` | CLAUDE.md.tmpl(中英)、SKILL.md 若提及 push |
| `Platform/dev-toolkit-engineer`(stellark-scaffold 等) | CLAUDE.md.tmpl + 各 skill 中 push 相关措辞 |
| `Platform/dev-toolkit`(vibe 版 starters + skills) | starter 模板与 stellark-commit 等 skill 的 push 措辞 |
| `~/.claude/CLAUDE.md`(用户全局规则) | 新增 5 行「Git push 策略」小节,使**非 scaffold 项目**的会话也遵守新策略 |

### 3. 与 superpowers 上游 skill 的衔接(只写衔接规则,不改上游插件)

- using-git-worktrees:无需改——分支即推恰好给每个 worktree 分支实时备份
- finishing-a-development-branch:其「merge 回 base」选项 = main 门禁的确认时刻;CLAUDE.md 模板写明确认后的收尾动作(push main、删远端分支)
- 存量项目:用 stellark-update skill 把新版 CLAUDE.md 规则同步到已有生产项目(实现阶段列 runbook,不自动批量跑)

## 验收条款

1. 盘点清单落盘(哪里有旧措辞、改成了什么),无遗漏项
2. 四处(开源中英、engineer、vibe)模板全部体现三条核心规则;英文版语义一致
3. `~/.claude/CLAUDE.md` 有「Git push 策略」小节
4. 全套 grep 复查:「在没确认的情况下 git push」旧措辞零残留(历史 spec/research 除外)
5. 评审档位:本 spec 触及对外发布(开源仓)与全局行为规则 → 评审一律 `opus`/`high`,检查项含「回滚路径:模板改动可单 commit revert」
