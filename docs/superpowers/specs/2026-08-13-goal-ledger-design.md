# goal-ledger:目标台账 + /goal 粘合 — Design Spec

- 日期:2026-08-13
- 状态:已获 Tony 确认(两层结构;台账并入 REQUIREMENTS.md 作收件箱——Tony 原话「goal 里面就是 requirement」;全铺)
- 依据:该内部项目会话交接的活案例——「某功能需求(领域收敛类)」2026-07-27 口头提出、未落任何文档、三周蒸发,2026-08-12 验收才审计出来;「某入口功能」做了但不在用户动线,用户以为没做。根因①对话需求无持久落点;②多批次推进无对账清单。另:`/goal` 为 Claude Code 内置命令(设完成条件、每轮 Haiku 评估、达成自动清除),**会话级不跨会话**(官方文档 code.claude.com/docs/en/goal.md 查证)——故只能作会话内粘合层,治蒸发必须靠持久台账。

## 1. 两层结构

- **第一层(跨会话,治蒸发)**:REQUIREMENTS.md 新增「目标台账」节 + 当轮登记硬规则 + 三个对账点。
- **第二层(会话内,治跑偏)**:ultracode 开工摘要附现成可贴的 `/goal … until …` 命令,把本批验收条款翻译成完成条件。文档明写分工:/goal 管会话内、台账管跨会话。

## 2. 规范文本(canonical,中文;英文/codex 同义适配)

### 2.1 REQUIREMENTS.md 模板新增节(三面模板同款)

```markdown
## 目标台账(收件箱)

> 对话/会议里冒出来的每一条需求、期望、不满,先落这里再说;成熟的整理进上文正式需求,琐碎的也留痕。**不在台账 = 没说过。**

| 日期 | 原话(尽量照录) | 出处 | 状态 | 销账证据 / 去向 |
|---|---|---|---|---|
| YYYY-MM-DD | (占位)"……" | 某次对话/会议 | open | — |

状态:open(未处理)/ done(已实现,证据=commit/截图/spec 条款)/ dropped(明确放弃,写一句原因)/ 升格(已提炼进上文正式需求,注明节名)。
```

### 2.2 当轮登记硬规则(scaffold CLAUDE.md 模板 + workflow prompt)

> 对话中用户表达的需求、期望或不满——哪怕只有一句话——**当轮**登记进 `docs/REQUIREMENTS.md` 的「目标台账」(日期+原话+出处),并回一行「已记入目标台账」。拿不准算不算需求就按 open 登记,宁滥勿漏;**不登记视同没听见,禁止**。

落位:CLAUDE.md.tmpl(zh/en)§2 文档同步规则表**加一行**(改动类型「对话中出现的需求/期望/不满」→ 必改文件「REQUIREMENTS.md 目标台账(当轮,回一行确认)」),并在「禁止事项」加一条「听到需求不登记目标台账」;codex AGENTS.md.tmpl 同构。

### 2.3 三个对账点

1. **brainstorming 开工**(README §七.1 扩一句):先读目标台账未销账项,把与本次相关的列给用户;spec 必须含「**目标覆盖声明**」——本次覆盖台账哪几条、明确不覆盖哪几条及原因。
2. **ultracode 收尾**(README §七.5 扩一句):更新 Progress/PLAN 的同时**销账**(状态改 done 附证据)并把实现中新冒出的目标登记进台账。
3. **/whats-next**(README §九 + 三面 whats-next SKILL):读取清单加 REQUIREMENTS 目标台账;输出加第 **⑤** 部分「未销账目标」——open 状态逐条列出,挂账超 7 天的置顶标注;没有则省略。

### 2.4 /goal 粘合(README §七.4 开工摘要处扩一句)

> 开工摘要末尾附一行现成可贴的目标命令:`/goal "完成 <批次/spec 名>" until "<spec 验收条款要点或本批覆盖的台账条目>全部满足"`——`/goal` 是 Claude Code 会话级内置命令(每轮自动评估完成条件,防长会话做着做着跑偏);它不跨会话,跨批次的持久性靠目标台账。

## 3. 载体清单

| 载体 | 改动 |
|---|---|
| `README.zh-CN.md` / `README.md` | §七.1/.4/.5 三处扩句 + §九 读取清单与输出加⑤(2.3/2.4) |
| `plugins/workflow{,-en}/skills/scaffold/templates/docs/REQUIREMENTS.md.tmpl` | 2.1 节 |
| `plugins/workflow-codex/skills/scaffold/templates/docs/REQUIREMENTS.md.tmpl` | 2.1 节 |
| `plugins/workflow{,-en}/skills/scaffold/templates/CLAUDE.md.tmpl` | 2.2(同步规则表行 + 禁止事项条) |
| `plugins/workflow-codex/skills/scaffold/templates/AGENTS.md.tmpl` | 2.2 同构(/goal 粘合句不进 codex——/goal 是 Claude Code 专属,codex 面只落台账与对账,并注明一句差异) |
| `plugins/workflow{,-en}/skills/whats-next/SKILL.md`、`plugins/workflow-codex/skills/whats-next/SKILL.md` | 2.3 第 3 点 |
| `plugins/workflow{,-en}/skills/scaffold/SKILL.md` | 落盘清单对 REQUIREMENTS 的描述提及目标台账节(一句) |
| 本机 `~/.claude/CLAUDE.md` | 主对话亲自做,个性化措辞(登记硬规则 + 直通流程对账/销账句 + /goal 粘合句,带日期戳) |
| 内部工具包仓 / 内网工作站(merge 后另走 wip+门禁) | stellark-scaffold 模板(REQUIREMENTS.tmpl+CLAUDE.tmpl)+ stellark-whats-next / 对应件同构 |

## 4. 验收条款

1. canonical 语义零丢失,双语同构,codex 面无 /goal 依赖且注明差异。
2. 既有内容零回归(插入点之外 diff 为空);§九输出编号顺延正确(原①~④,新增⑤)。
3. 全部被改 md 严格 YAML/乱码扫描通过。
4. /goal 描述与官方文档一致:会话级、until 语法、自动评估——不得暗示跨会话持久。
5. 「不在台账 = 没说过」「不登记视同没听见」两句硬规则语气在所有载体保留。

## 5. 实施与评审档位

- worktree 分支 `wip/goal-ledger`(主工作树被 ui-sweep 修复占用),commit 即 push。
- ultracode:U1 双语 README(sonnet/medium)∥ U2 模板组 zh/en/codex 五文件(sonnet/medium)∥ U3 whats-next 三面(sonnet/medium);本机 CLAUDE.md 由主对话亲自。逐单元 opus/medium 评审,打回升 high;终审 opus/high(全局方法论门面)。
- 与 `wip/ui-sweep`、`wip/research-internal-first` 一批找 Tony 过 main 门禁;三分支改动面互不重叠(ui-sweep=新插件+sop-generate;本分支=README 调研节之外的段落+模板;research=README §八)——README 双语两分支都改但段落不同,合并顺序任意。
