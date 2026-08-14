# docs 八件套自动更新机制审计(2026-08-14)

> 起因:stella 侧符合度审计发现「三件套」(commit + Progress + PLAN 检查)基本靠 Claude 自觉,
> Tony 指示:①建 DECISIONS 自动采集能力;②逐个查其余 docs 的自动更新现状。
> 方法:Workflow 编排 8 个逐 doc 只读探查代理(sonnet/low)+ 1 个完备性评审票(opus/medium),
> 评审票的关键论断已由主对话逐条亲手复核(见文末「复核记录」)。
> 扫描面:开源 kit(canonical)、stellark dev-toolkit 插件与运行时资产、huake claude-toolkit-engineer、
> 本机 ~/.claude/skills + settings.json hooks + 全局 CLAUDE.md + superpowers 插件。

## 判定口径

- **自动** = harness 强制执行(hook / CI / 脚本),Claude 不自觉也会发生
- **半自动** = 某 skill 被触发时流程里明确有更新该文档这一步
- **纯纪律** = 只有规则文本要求 Claude 记得做,无任何校验兜底

## 逐 doc 结论

| 文档 | 创建 | 持续更新 | 消费方(失真代价) | 定性 |
|---|---|---|---|---|
| Progress.md | scaffold 落盘 | CLAUDE.md 规则表 + stellark-develop skill 步骤("MANDATORY"仍是文字) | whats-next 门禁;**stella portfolio 每 10 分钟轮询派生对外总览** | **写入纯纪律,读取自动** |
| PLAN.md | scaffold 落盘,且收尾自动改写 Phase 0 标题(全体系唯一 skill 写内容步骤) | CLAUDE.md 规则(Phase 推进 / Spec 索引) | whats-next 准入门禁;parallel-do 派工依据;portfolio 轮询 | **写入纯纪律,读取自动** |
| DECISIONS.md | scaffold 预置首条 | 模板头**声称「自动维护」,实为纯纪律**;唯一带 git 动作的契约在 stellark starter CLAUDE.md:84,仍是文字;stellark-deploy/commit skill 有步骤(触发才生效) | stella-roadmap-llm-deriver 喂 LLM 派生路线图;whats-next 读最近条目 | **纯纪律** |
| REQUIREMENTS.md | scaffold 落盘(intake 填实) | 目标台账「当轮落账」全局规则,纯纪律 | whats-next 读未销账项;sop-generate 读;roadmap-deriver 喂 LLM | **纯纪律** |
| ARCHITECTURE.md | scaffold 落盘(SQLite 分支还要手工改写正文) | 仅 CLAUDE.md 规则表;whats-next 明确「不读」 | sop-generate 间接 | **纯纪律,且无任何巡检覆盖** |
| BUSINESS.md | scaffold 七格追问填实(建档半自动) | 此后无任何机制 | sop-generate 生成对外操作手册 | 建档半自动 / **更新纯纪律** |
| DEPLOYMENT.md | scaffold 落盘(stellark starter 面**根本没有**此文档) | 仅 CLAUDE.md 规则表;whats-next 不读 | sop-generate 取部署 URL;deploy-student-site 当托管决策依据 | **纯纪律** |
| MEETINGS.md | scaffold 归档 intake 纪要(建档半自动) | 后续追加无任何机制 | whats-next 读未勾选待办 | 建档半自动 / **更新纯纪律** |

## 横向发现(比逐 doc 结论更重要)

1. **写入侧零自动化**:全体系(四个分发面 + 本机 hooks + superpowers 上游)没有任何 hook、CI job 或脚本会在文档漏更时报错、拦截或补写。所有 hook 都与 docs 无关(auto-scaffold 注入、speak-human 注入、send-to 注册、凭据拦截、stella-reporter 遥测)。
2. **唯一的真自动在读取侧**:stella portfolio 模块按 `PORTFOLIO_POLL_INTERVAL`(默认 10 分钟)轮询各项目 PLAN/Progress,派生总结写回对外项目总览;写回产物手改会被下一轮覆盖。含义:Progress/PLAN 失真会**自动扩散**成对外错误内容,且下游无法手工兜底。
3. **两套文档契约分叉**:kit 八件套(Progress/PLAN/DECISIONS/REQUIREMENTS/ARCHITECTURE/BUSINESS/DEPLOYMENT/MEETINGS)vs stellark starter 六件套(REQUIREMENTS/CHANGELOG/ARCHITECTURE/DECISIONS/HANDOFF/PROGRESS,大写命名,无 PLAN/BUSINESS/DEPLOYMENT/MEETINGS)。同一台机器上两类项目拿到不兼容的文档契约;starter 版契约反而更强(PROGRESS write-ahead、commit 后 CHANGELOG+DECISIONS 带 git 动作)。
4. **台账外成员**:`docs/superpowers/specs/`(whats-next 读、PLAN 索引,失真代价高于 ARCHITECTURE)、`code-base/components.yaml`(github-research 第 0 步读 + 复用记账写回,全体系唯一自带写回+push 的方法论台账,半自动)、CHANGELOG/HANDOFF/HANDOVER(stellark 面)。
5. **DECISIONS 模板名不副实**:模板头写「自动维护。关键决策在 commit 时由 Claude 追加」——描述的是期望,不是机制。这正是 stella 符合度审计戳中的缺口。

## 复核记录(主对话亲手验证评审票论断)

- `setup-project.sh:195` 的 for 循环确为 6 个文档(无 PLAN/BUSINESS/DEPLOYMENT/MEETINGS)✓
- `starters/general/.claude/CLAUDE.md` 的 write-ahead 保证与 commit 后 DECISIONS 追加契约(:60-68,:84)✓
- whats-next 边界情况:PLAN/Progress 缺失即拒判 ✓
- portfolio 10 分钟轮询与 `PORTFOLIO_POLL_INTERVAL` ✓
- 已知瑕疵:REQUIREMENTS 探查代理的 surface_diffs/evidence 字段输出了占位垃圾,该行结论以主对话自有知识(全局 CLAUDE.md 目标台账规则)与评审票交叉确认;PLAN.md 探查代理结构化输出失败,该行由评审票补齐并经复核。

## 原始产物

- Workflow run: `wf_376a7d88-599`(8/9 代理成功,总 43 万 token)
- 逐代理返回值: 会话 subagents/workflows/wf_376a7d88-599/journal.jsonl
